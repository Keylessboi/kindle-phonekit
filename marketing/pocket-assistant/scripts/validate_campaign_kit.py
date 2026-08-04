#!/usr/bin/env python3
"""Validate a create-marketing-kit campaign manifest.

The skill ships a bundled validator, but this copy of the skill is missing
scripts/validate_campaign_kit.py, so this is an equivalent drop-in in the
campaign folder. It checks:

  * the manifest parses as JSON and is well-formed;
  * every listed PNG exists, is a real PNG, and matches its stated
    width/height;
  * every listed SVG master exists and parses as well-formed XML;
  * every PNG is no older than the SVG master it was exported from
    (freshness guard: an export older than its source is stale).

Usage:
    python3 scripts/validate_campaign_kit.py campaign-manifest.json
"""

import json
import os
import sys
import xml.etree.ElementTree as ET


def png_dimensions(path):
    """Return (width, height) from the PNG IHDR, or None if not a PNG."""
    with open(path, "rb") as fh:
        sig = fh.read(8)
    if sig != b"\x89PNG\r\n\x1a\n":
        return None
    with open(path, "rb") as fh:
        fh.read(8)  # signature
        ihdr = fh.read(4)  # IHDR length
        fh.read(4)  # "IHDR"
        width = int.from_bytes(fh.read(4), "big")
        height = int.from_bytes(fh.read(4), "big")
    return (width, height)


def main():
    if len(sys.argv) != 2:
        print("usage: validate_campaign_kit.py <campaign-manifest.json>")
        return 1
    manifest_path = sys.argv[1]
    base_dir = os.path.dirname(os.path.abspath(manifest_path))

    with open(manifest_path, "r") as fh:
        manifest = json.load(fh)

    errors = []
    for asset in manifest.get("assets", []):
        path = asset["path"]
        fmt = asset["format"]
        full = os.path.join(base_dir, path)

        if not os.path.exists(full):
            errors.append(f"missing: {path}")
            continue

        if fmt == "PNG":
            dims = png_dimensions(full)
            if dims is None:
                errors.append(f"not a PNG: {path}")
            elif dims != (asset["width"], asset["height"]):
                errors.append(
                    f"size mismatch {path}: expected "
                    f"{asset['width']}x{asset['height']}, got {dims[0]}x{dims[1]}"
                )
        elif fmt == "SVG":
            try:
                ET.parse(full)
            except ET.ParseError as exc:
                errors.append(f"malformed SVG {path}: {exc}")

    # Freshness guard: exports must not predate their SVG masters.
    svg_mtime = {}
    for asset in manifest.get("assets", []):
        if asset["format"] == "SVG":
            full = os.path.join(base_dir, asset["path"])
            if os.path.exists(full):
                svg_mtime[asset["path"]] = os.path.getmtime(full)
    for asset in manifest.get("assets", []):
        if asset["format"] != "PNG":
            continue
        master = asset.get("master")
        if not master or master not in svg_mtime:
            continue
        png_newer = os.path.getmtime(
            os.path.join(base_dir, asset["path"])
        ) >= svg_mtime[master]
        if not png_newer:
            errors.append(
                f"stale export {asset['path']} (older than source {master})"
            )

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())