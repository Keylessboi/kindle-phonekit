#!/usr/bin/env python3
"""PhoneKit QR display.

Generates a QR code as a PNG with the Python standard library only (the Kindle
has no Pillow) and displays it on the e-ink screen with `eips -g`.

Usage:
    python3 qr.py "https://example.com/wifi"            # show on screen
    python3 qr.py -o /tmp/qr.png "hello"                # write a PNG file

The QR encoder is a compact byte-mode implementation (Reed-Solomon error
correction level M). It auto-selects a version large enough for the payload.
Designed for small practical payloads (Wi-Fi join strings, URLs, contact text);
very long payloads raise QRTooLong.
"""

import sys
import zlib

# ---- Reed-Solomon (GF(256), generator 0x11d) -------------------------------

def _gf_mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        hi = a & 0x80
        a <<= 1
        if hi:
            a ^= 0x11D
        b >>= 1
    return r


def _rs_generator(n):
    # Product (x - alpha^0)(x - alpha^1)...(x - alpha^(n-1))
    poly = [1]
    for i in range(n):
        poly = _rs_multiply(poly, [1, _GF_EXP[i]])
    return poly


def _rs_multiply(a, b):
    res = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        for j, bv in enumerate(b):
            res[i + j] ^= _gf_mul(av, bv)
    return res


def _rs_remainder(data, gen):
    res = data + [0] * (len(gen) - 1)
    for i in range(len(data)):
        factor = res[i]
        if factor:
            for j, gv in enumerate(gen[1:]):
                res[i + j + 1] ^= _gf_mul(gv, factor)
    return res[-(len(gen) - 1):]


# GF(256) tables
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256
x = 1
for i in range(255):
    _GF_EXP[i] = x
    _GF_LOG[x] = i
    x <<= 1
    if x & 0x100:
        x ^= 0x11D
for i in range(255, 512):
    _GF_EXP[i] = _GF_EXP[i - 255]

# ---- QR structure tables ----------------------------------------------------
# Byte-mode capacity per version at EC level M (data codewords). Versions 1..10.
_CAPACITY = [0, 16, 28, 44, 64, 86, 108, 124, 154, 182, 216]
# Reed-Solomon block layout per version at level M: list of (count, total
# codewords per block, data codewords per block). Errors per block = total-data.
_RS_BLOCKS = {
    1:  [(1, 26, 16)],
    2:  [(1, 44, 28)],
    3:  [(1, 70, 44)],
    4:  [(2, 50, 32)],
    5:  [(2, 67, 43)],
    6:  [(4, 43, 27)],
    7:  [(4, 49, 31)],
    8:  [(2, 60, 38), (2, 61, 39)],
    9:  [(3, 58, 36), (2, 59, 37)],
    10: [(4, 69, 43), (1, 70, 44)],
}

_ALIGNMENT = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
}

_FORMAT_BITS = {  # (level M, mask 0..7)
    (0, 0): 0b101010000010010,
    (0, 1): 0b101000100100101,
    (0, 2): 0b101111001111100,
    (0, 3): 0b101101101001011,
    (0, 4): 0b100010111111001,
    (0, 5): 0b100000011001110,
    (0, 6): 0b100111110010111,
    (0, 7): 0b100101010100000,
}

_VERSION_BITS = {
    7: 0b000111110010010100,
    8: 0b001000010110111100,
    9: 0b001001101010011001,
    10: 0b001010010011010011,
}


class QRTooLong(Exception):
    pass


class QRCode:
    def __init__(self, data, ec_level="M"):
        self.data = data.encode("utf-8")
        self.version = self._pick_version(len(self.data))
        self.size = 17 + 4 * self.version
        self.matrix = [[None] * self.size for _ in range(self.size)]

    def _pick_version(self, nbytes):
        for v in range(1, 11):
            if nbytes <= _CAPACITY[v]:
                return v
        raise QRTooLong(
            "payload too long for versions 1-10 (%d bytes, max %d)"
            % (nbytes, _CAPACITY[10])
        )

    def _codewords(self):
        capacity = _CAPACITY[self.version]
        data = self.data
        # Byte mode: 4-bit indicator 0100, then 8-bit count (v1-9) or
        # 16-bit count (v10+), then the data bytes, as one bitstream.
        bits = [0, 1, 0, 0]
        n = len(data)
        nbits = 8 if self.version < 10 else 16
        for i in range(nbits - 1, -1, -1):
            bits.append((n >> i) & 1)
        for b in data:
            for i in range(7, -1, -1):
                bits.append((b >> i) & 1)
        # Terminator: up to 4 zero bits, then zeros to the next byte
        # boundary, then alternating 0xEC/0x11 pad codewords.
        capacity_bits = capacity * 8
        term = min(4, capacity_bits - len(bits))
        bits.extend([0] * term)
        while len(bits) % 8 != 0:
            bits.append(0)
        pad_byte = 0xEC
        while len(bits) < capacity_bits:
            for i in range(7, -1, -1):
                bits.append((pad_byte >> i) & 1)
            pad_byte = 0x11 if pad_byte == 0xEC else 0xEC
        data_cw = []
        for i in range(0, len(bits), 8):
            b = 0
            for bit in bits[i:i + 8]:
                b = (b << 1) | bit
            data_cw.append(b)
        # Split into RS blocks, append error-correction codewords per block,
        # then interleave: all block data codewords, then all block EC
        # codewords (the order the zigzag data path expects).
        blocks = []
        idx = 0
        for count, total, dc in _RS_BLOCKS[self.version]:
            ec = total - dc
            gen = _rs_generator(ec)
            for _ in range(count):
                block_data = data_cw[idx:idx + dc]
                idx += dc
                ec_cw = _rs_remainder(block_data, gen)
                blocks.append((block_data, ec_cw))
        out = []
        max_dc = max(len(bd) for bd, _ in blocks)
        max_ec = max(len(ec) for _, ec in blocks)
        for i in range(max_dc):
            for bd, _ in blocks:
                if i < len(bd):
                    out.append(bd[i])
        for i in range(max_ec):
            for _, ec_cw in blocks:
                if i < len(ec_cw):
                    out.append(ec_cw[i])
        return out

    def build(self, mask=2):
        size = self.size
        codewords = self._codewords()
        # place all non-data patterns first (finders, timing, alignment,
        # format, version) so the data zigzag treats them as occupied cells
        self._place_finders()
        self._place_timing()
        self._place_alignment()
        self._place_format(mask)
        if self.version >= 7:
            self._place_version()
        # place data, applying the mask inline as we write each data cell
        data_bits = self._data_bits(codewords)
        self._place_data(data_bits, mask)
        return self.matrix

    # -- function patterns ------------------------------------------------
    def _place_finders(self):
        # Draw each 7x7 finder probe plus its 1-module white separator border
        # (a 9x9 region) so those border cells are never mistaken for data.
        for (r0, c0) in [(0, 0), (0, self.size - 7), (self.size - 7, 0)]:
            for r in range(-1, 8):
                if r0 + r < 0 or r0 + r >= self.size:
                    continue
                for c in range(-1, 8):
                    if c0 + c < 0 or c0 + c >= self.size:
                        continue
                    dark = (
                        (0 <= r <= 6 and c in (0, 6))
                        or (0 <= c <= 6 and r in (0, 6))
                        or (2 <= r <= 4 and 2 <= c <= 4)
                    )
                    self.matrix[r0 + r][c0 + c] = 1 if dark else 0

    def _place_timing(self):
        s = self.size
        for i in range(8, s - 8):
            if self.matrix[i][6] is None:
                self.matrix[i][6] = 1 if i % 2 == 0 else 0
            if self.matrix[6][i] is None:
                self.matrix[6][i] = 1 if i % 2 == 0 else 0

    def _place_alignment(self):
        centers = _ALIGNMENT[self.version]
        if not centers:
            return
        last = centers[-1]
        # skip the three alignment positions that would overlap a finder:
        # (top-left 6,6), (6,last), (last,6)
        for cr in centers:
            for cc in centers:
                if (cr == 6 and cc == 6) or (cr == 6 and cc == last) or (cr == last and cc == 6):
                    continue
                for i in range(-2, 3):
                    for j in range(-2, 3):
                        v = 1 if (abs(i) == 2 or abs(j) == 2) or (i == 0 and j == 0) else 0
                        r, c = cr + i, cc + j
                        if 0 <= r < self.size and 0 <= c < self.size:
                            if self.matrix[r][c] is None:
                                self.matrix[r][c] = v

    # -- data placement ----------------------------------------------------
    def _data_bits(self, codewords):
        bits = []
        for cw in codewords:
            for i in range(7, -1, -1):
                bits.append((cw >> i) & 1)
        return bits

    def _place_data(self, data_bits, mask):
        # Standard QR zigzag: process column-pairs (col, col-1) right to left,
        # visiting both columns row-by-row, toggling vertical direction each pair.
        # The mask is applied inline as each data cell is written, so format
        # and version cells (already placed) are never masked.
        s = self.size
        idx = 0
        inc = -1
        row = s - 1
        for col in range(s - 1, 0, -2):
            if col <= 6:
                col -= 1
            while True:
                for c in (col, col - 1):
                    if self.matrix[row][c] is None:
                        v = data_bits[idx] if idx < len(data_bits) else 0
                        idx += 1
                        if self._mask_bit(mask, row, c):
                            v ^= 1
                        self.matrix[row][c] = v
                row += inc
                if row < 0 or row >= s:
                    row -= inc
                    inc = -inc
                    break

    @staticmethod
    def _mask_bit(mask, r, c):
        if mask == 0:
            return (r + c) % 2 == 0
        if mask == 1:
            return r % 2 == 0
        if mask == 2:
            return c % 3 == 0
        if mask == 3:
            return (r + c) % 3 == 0
        if mask == 4:
            return (r // 2 + c // 3) % 2 == 0
        if mask == 5:
            return (r * c) % 2 + (r * c) % 3 == 0
        if mask == 6:
            return ((r * c) % 2 + (r * c) % 3) % 2 == 0
        return ((r + c) % 2 + (r * c) % 3) % 2 == 0

    def _place_format(self, mask):
        bits = _FORMAT_BITS[(0, mask)]
        s = self.size
        # vertical strip in column 8 (two legs: top rows 0-8, bottom rows s-7..s)
        for i in range(15):
            bit = 1 if (bits >> i) & 1 else 0
            if i < 6:
                self.matrix[i][8] = bit
            elif i < 8:
                self.matrix[i + 1][8] = bit
            else:
                self.matrix[s - 15 + i][8] = bit
        # horizontal strip in row 8 (two legs)
        for i in range(15):
            bit = 1 if (bits >> i) & 1 else 0
            if i < 8:
                self.matrix[8][s - 1 - i] = bit
            elif i < 9:
                self.matrix[8][15 - i] = bit
            else:
                self.matrix[8][15 - i - 1] = bit
        # always-dark module
        self.matrix[s - 8][8] = 1

    def _place_version(self):
        bits = _VERSION_BITS[self.version]
        s = self.size
        for i in range(18):
            bit = 1 if (bits >> i) & 1 else 0
            self.matrix[i // 3][i % 3 + s - 11] = bit
            self.matrix[i % 3 + s - 11][i // 3] = bit

    def render_png(self, scale=4, quiet=4):
        """Return PNG bytes (grayscale, 1-bit-ish) with zlib (stdlib only)."""
        s = self.size + quiet * 2
        px = [[255] * (s * scale) for _ in range(s * scale)]
        for r in range(self.size):
            for c in range(self.size):
                if self.matrix[r][c]:
                    for dy in range(scale):
                        for dx in range(scale):
                            px[(r + quiet) * scale + dy][(c + quiet) * scale + dx] = 0
        w = s * scale
        h = w
        # PNG: signature, IHDR, IDAT (zlib of raw scanlines), IEND
        def chunk(tag, data):
            out = len(data).to_bytes(4, "big") + tag + data
            crc = zlib.crc32(tag + data) & 0xFFFFFFFF
            return out + crc.to_bytes(4, "big")

        raw = bytearray()
        for row in px:
            raw.append(0)  # filter type 0
            for v in row:
                raw.append(v)
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", w.to_bytes(4, "big") + h.to_bytes(4, "big") +
                     b"\x08\x00\x00\x00\x00")  # 8-bit, grayscale
        png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        png += chunk(b"IEND", b"")
        return png


def main():
    args = sys.argv[1:]
    out_file = None
    if args and args[0] == "-o" and len(args) >= 2:
        out_file = args[1]
        args = args[2:]
    if not args:
        sys.stderr.write("usage: qr.py [-o out.png] <text>\n")
        return 2
    text = " ".join(args)
    try:
        qr = QRCode(text)
        qr.build(mask=2)
        png = qr.render_png(scale=4, quiet=4)
    except QRTooLong as exc:
        sys.stderr.write("qr error: %s\n" % exc)
        return 1
    if out_file:
        with open(out_file, "wb") as fh:
            fh.write(png)
        return 0
    # display on screen
    tmp = "/tmp/phonekit_qr.png"
    with open(tmp, "wb") as fh:
        fh.write(png)
    import subprocess
    for prog in ("/usr/sbin/eips", "/usr/bin/eips"):
        try:
            subprocess.call([prog, "-g", tmp])
            return 0
        except OSError:
            continue
    sys.stderr.write("qr error: no eips binary found; wrote %s\n" % tmp)
    return 1


if __name__ == "__main__":
    sys.exit(main())
