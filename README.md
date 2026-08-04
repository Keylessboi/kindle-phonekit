# PhoneKit

<p align="center">
  <img src="marketing/pocket-assistant/assets/readme-banner.png"
       alt="PhoneKit: Your calm Kindle can also be useful. Clock, timer, on-screen chat, and XMPP messenger in one self-contained KUAL extension."
       width="100%">
</p>

Turn a jailbroken Kindle into a pocket assistant. A self-contained KUAL
extension that adds phone-like functions to the e-ink screen:

**Clock** – a big, readable 24-hour (or 12-hour) digital clock that avoids
burn-in by doing a full screen refresh every minute and clearing on Home.

**Timer** – a full-screen countdown timer. The Kindle has no speaker, so when
the time runs out it flashes the whole screen instead of beeping.

**LLM chat** – chat with any OpenAI-compatible endpoint right on the Kindle.
The extension runs a tiny local server plus a web page in the Kindle's built-in
browser. Ollama, llama.cpp, vLLM, OpenAI, or OpenRouter all work; just set the
URL, model, and optional API key in one config file.

**XMPP messenger** – the Kindle cannot run Android apps, so the Monocles and
Cheogram clients are opened in the browser (they have web ports). An optional
on-screen bridge connects directly to your XMPP server over TLS, authenticates
with SCRAM-SHA-1, and flashes incoming messages on the e-ink screen.

**AI Web Apps** – quick jump links to Open WebUI, ChatGPT, Claude, and Gemini in
the browser.

Everything is plain shell + Python from the Python standard library only. There
is no compiled code and no external dependency to install.

---

## 1. Jailbreak and install KUAL (kindle-mobile)

KUAL ("Kindle Unified Application Launcher") is how the extension is launched.
There is no one-size-fits-all jailbreak, so do the piece for your firmware now,
then come back here.

1. **Find your firmware version.** On the Kindle Home, tap the search
   (magnifying glass) icon and type `;711` (a semicolon, then 711), then
   Enter. A settings menu opens; the last item on top shows something like
   `FW 5.17.0`. Note your model (Basic, Paperwhite, etc.) and firmware.
2. **Pick a jailbreak.** As of 2026 the two current tools are:
   - **Sanctuary** – for firmware 5.16.4 through 5.18.3.
   - **SpringBreak** – for the Kindle Basic (KT5), Paperwhite 5 SE (PW5 SE),
     Kindle 4 (KT4), and Paperwhite 4 (PW4) on 5.19.2 and 5.18.1.1.1.
   Both re-enable the store, install the hotfix, and ship the "KPM" package
   manager. Sanctioned devices (blacklisted/serialized) and unregistered
   Kindles are fine with Sanctuary.
3. **Run the jailbreak**, following its instructions exactly. After it finishes
   and the Kindle reboots, the KPM package manager is available.
4. **Install the KUAL launcher.** Grab `KindleLauncher` (the `kindlelauncher-*.tar.gz`
   release) from its GitHub releases, unpack it, and copy the resulting
   `extensions/` folder to the Kindle's USB root (`/mnt/us/extensions/` on the
   device; the USB drive's top level on your computer). Eject and reboot the
   Kindle. On the Home screen press the **KindleComicCreator** button / Menu,
   then "Launch KUAL".

> KUAL itself is not bundled by every jailbreak. If it is not present after the
> jailbreak, install it as above before continuing. Any jailbreak on these
> firmware lines will also give you **USB networking** and the `mntroot ro`
> command; neither is required for PhoneKit.

---

## 2. Install PhoneKit

Copy the `phonekit` folder so it ends up at `/mnt/us/extensions/phonekit`:

```
extensions/
└── phonekit/
    ├── config.xml
    ├── menu.json
    └── ext/
```

From the computer that has the Kindle USB-mounted, do:

```sh
cp -r extensions/phonekit /Volumes/Kindle/extensions/phonekit   # macOS
cp -r extensions/phonekit /media/Kindle/extensions/phonekit     # Linux
```

(Rename the drive mount to yours if needed.) Eject the USB drive. After the
Kindle re-mounts it, open KUAL and you will see the **PhoneKit** menu.

It is safe to edit the `*.sh` files with a plain text editor on your computer.
Use Unix line endings (LF), not Windows CRLF — the Kindle shell rejects CRLF.

---

## 3. Configure

Almost everything is set in one of two `config.env` files. They use plain
`KEY="value"` lines.

### 3.1 LLM (`ext/llm/config.env`)

| Variable          | Meaning                                                |
|-------------------|--------------------------------------------------------|
| `PK_LLM_API_URL`  | Full OpenAI-compatible chat completions URL            |
| `PK_LLM_API_KEY`  | API key (`""` for local Ollama/llama.cpp)              |
| `PK_LLM_MODEL`    | Model name, e.g. `qwen2.5:7b-instruct`                 |
| `PK_LLM_SYSTEM`   | Optional system prompt (shown to every chat)           |

The default points at Ollama on the Kindle itself:
`http://127.0.0.1:11434/v1/chat/completions` with model `qwen2.5:7b-instruct`.

- **Running an LLM on the Kindle:** install the `Koreader`/`Kindle` Ollama
  build (a `kual-ollama` style package) or run Ollama from a Python build that
  has network. Then start it before using the LLM menu.
- **Using a remote API:** point `PK_LLM_API_URL` at your provider and set the
  key. The Kindle has Wi-Fi; keep answers short for a fast, readable reply.

### 3.2 XMPP (`ext/xmpp/config.env`)

| Variable          | Meaning                                                       |
|-------------------|---------------------------------------------------------------|
| `PK_XMPP_URL`     | Browser client to open (default `https://app.cheogram.com`)   |
| `PK_XMPP_JID`     | Your full `user@server` (for the on-screen bridge)            |
| `PK_XMPP_PASS`    | Your password                                                |
| `PK_XMPP_HOST`    | Optional server host (default: JID domain)                   |
| `PK_XMPP_PORT`    | Optional server port (default 5222)                          |
| `PK_XMPP_NO_VERIFY` | `1` to skip TLS cert checks (insecure; leave `0` on)       |

- **Browser client:** choose Cheogram World Wide Web (`https://app.cheogram.com`,
  best with Snikket or JMP, needs a websocket-capable server) or Monocles Web
  (`https://chat.monocles.de`, classic XMPP). Set `PK_XMPP_URL` and pick
  "XMPP → Open client" in the menu.
- **On-screen bridge:** fill in `PK_XMPP_JID` and `PK_XMPP_PASS`, then pick
  "XMPP → Start bridge". Incoming messages are logged to `/tmp/phonekit_xmpp.txt`
  and flashed on the screen. SCRAM-SHA-1 is used when the server offers it;
  PLAIN is the fallback. Stop it from the menu when done.

---

## 4. Use it

Open **KUAL → PhoneKit**:

- **Clock** – full-width clock. Argument `12` gives 12-hour format. Press Home
  to exit.
- **Timer** – starts a 300-second (5 minute) countdown. To change the default,
  edit `menu.json`: the Timer entry carries a parameter, e.g.
  `"params": ["900"]` for 15 minutes.
- **LLM → Start** – starts the server and opens the chat page in the browser.
  **LLM → Stop** shuts it down.
- **XMPP →** Open client / Start bridge / Stop bridge.
- **AI Web Apps** – ChatGPT, Claude, Gemini, Open WebUI.

---

## 5. Notes & limitations

- **No speaker.** Timer and message alerts flash the screen rather than beep.
- **E-ink refresh.** The clock force-refreshes every minute to avoid ghosting;
  this is normal.
- **No drag-and-drop text input.** For the LLM, type into the browser's on-screen
  keyboard or the hardware keyboard if your model has one.
- **Security.** Prefer SCRAM-SHA-1 over PLAIN. Never leave `PK_XMPP_NO_VERIFY=1`
  set on a real account. API keys in `config.env` are plain text.

The aim is zero bloat and zero dependencies: safe to carry on a spare device,
trivially editable, and easy to remove (delete the `phonekit` folder).