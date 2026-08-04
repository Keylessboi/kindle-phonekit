# PhoneKit — "Pocket Assistant" campaign kit

One campaign kit for PhoneKit, the self-contained KUAL extension that turns a
jailbroken Kindle into a pair of useful tools plus an on-screen AI chat and
messenger. This kit is grounded in the repository's own files. Nothing here is
invented.

## Campaign thesis

**Audience:** people who already jailbreak their Kindle (or are curious about
it), run KUAL, and want more from the device than reading. Tinkerers, privacy
minded, minimalists. People who like the idea of a calm, low-distraction
device that also does a bit of "smart" work.

**Their current tension:** the Kindle is quiet and focused, but it only
reads. Their phone has all the "smart" functions — and all the noise. They
want the calm device to also be useful without being a distraction.

**The evidence-backed change:** PhoneKit adds a clock, a countdown timer, an
OpenAI-compatible chat, and an XMPP bridge to the e-ink screen, in plain
shell + Python with zero external dependencies. It is not a reinvented phone;
it is a small set of focused tools that live inside the calm screen.

**Campaign promise:** *Your Kindle already stays calm. With PhoneKit, it also
stays useful.*

## Message hierarchy

1. **Promise** — Your calm Kindle can also be useful.
2. **Supporting value** — A clock, timer, on-screen AI chat, and messenger
   that run on the e-ink screen, with no compiled code and nothing to install.
3. **Proof points** —
   - Built from plain shell and Python standard library only.
   - Works with any OpenAI-compatible chat endpoint (Ollama on the device,
     llama.cpp, vLLM, OpenAI, OpenRouter).
   - The XMPP bridge talks to your server over TLS with SCRAM-SHA-1.
   - Runs entirely from a single `phonekit` folder under KUAL.
4. **Honest qualifier** — It needs a jailbroken Kindle with KUAL, and it is
   by nature a small, focused toolset — not a phone replacement.
5. **Call to action** — Install the extension and open it from KUAL.

This is one repeated idea: calm **and** useful. Every asset says that.

## Claims ledger

All claims below were checked against `README.md`, `menu.json`,
`config.xml`, and the `ext/` config files in this repository.

### Verified
- PhoneKit is a **KUAL extension** that lives at
  `/mnt/us/extensions/phonekit` (one folder) and appears as a **PhoneKit**
  menu item in KUAL. — `README.md`
- It adds a **Clock** (24-hour default, `12` argument for 12-hour), a
  **Timer** (default 300 s, editable via `menu.json`), **LLM Chat**, **XMPP**
  (browser clients + an optional on-screen bridge), and **AI Web Apps**
  (Open WebUI, ChatGPT, Claude, Gemini shortcuts). — `menu.json`,
  `README.md`
- The clock avoids burn-in with a full screen refresh and clears on Home, and
  the timer **flashes the screen** when done because the Kindle has no
  speaker. — `README.md`, `clock.sh`
- The LLM side runs a **tiny local server** plus a page in the Kindle's
  built-in browser. It talks to **any OpenAI-compatible chat-completions
  endpoint**: the config names Ollama, llama.cpp, vLLM, OpenAI, and
  OpenRouter. — `README.md`, `llm/config.env`
- The XMPP bridge connects **directly to your XMPP server over TLS**,
  authenticates with **SCRAM-SHA-1** (PLAIN fallback), and flashes incoming
  messages on the e-ink screen. — `README.md`, `xmpp/config.env`
- Everything is **plain shell + Python from the standard library only**. No
  compiled code, no external dependency to install. Removing PhoneKit is
  deleting the folder. — `README.md`
- Default LLM model is `qwen2.5:7b-instruct`; the default URL points at
  Ollama on the device itself. — `llm/config.env`
- Version `1.0.0`; extension author field in `config.xml` is the placeholder
  `You`. — `config.xml`

### Inference (not directly proven by the repo)
- "Calm / low-distraction / focused" reads as the product's intended spirit
  and is a fair description of e-ink use, but the repo does not claim any
  measured focus benefit. Phrase as a tone, not a metric.
- "Privacy minded / minimalists / tinkerers" as the audience is my framing
  from the feature set and the jailbreak/KUAL prerequisite, not a customer
  statement.

### Unknown / deliberately excluded
- **No screenshots exist in the repo.** The campaign cannot show real
  on-screen captures. The artwork below is an editorial illustration, not a
  product screenshot, and must never be presented as one.
- **No customer testimonials, metrics, or numbers** anywhere. None are
  asserted.
- **Battery life, response times, and compatibility across every Kindle
  model/firmware** are not verified. Not claimed.
- **Security posture** is deliberately soft in the repo: `PK_XMPP_NO_VERIFY=1`
  skips TLS checks (insecure, documented), and API keys are plain text in
  `config.env`. The campaign must not claim PhoneKit is "secure by default";
  it must say SCRAM-SHA-1 is preferred over PLAIN and that the user should
  leave verification on.

### Guardrails (what the copy must never say)
- No "it replaced my phone" or "try it on any Kindle".
- No credentials, keys, or account details shown or implied.
- No fabricated screenshots, numbers, or happy customers.
- No "secure", "private", or "encrypted" without the documented qualifications.
- The illustration is art, not a product screenshot.

## Deliverables

| Asset | Format | Size | Role |
|---|---|---|---|
| `assets/hero-landscape.png` | PNG | 1600x900 | README + website hero banner |
| `assets/feed-portrait.png` | PNG | 1080x1350 | Social feed post |
| `assets/story-cover.png` | PNG | 1080x1920 | Story / reel cover |
| `assets/readme-banner.svg` | SVG (editable) | 1600x400 | In-repo README banner |
| `channel-copy.md` | Markdown | — | Website, README, launch, social variants |
| `guardrails.md` | Markdown | — | Prohibited / qualified / preferred terms |
| `prompts.md` | Markdown | — | Art brief + exact generation prompts |
| `campaign-manifest.json` | JSON | — | Machine-read asset manifest |

## Usage
- Website / README hero: `assets/hero-landscape.png` (with alt text).
- One banner near the top of the README: `assets/readme-banner.svg`.
- Social feed: `assets/feed-portrait.png`.
- Story / reel: `assets/story-cover.png`.
- Channel text: `channel-copy.md`, constrained by `guardrails.md`.

## How this was validated
- Every claim was checked against the repo (see ledger above).
- The SVG masters were exported to PNG at their exact listed dimensions.
- Every final asset was run through the two-reviewer visual check from the
  `visual-qa` skill.
- The teaser confusion about "offline" was removed: PhoneKit still needs an
  LLM endpoint for chat and a network for XMPP. It is *low-distraction*, not
  *offline*.