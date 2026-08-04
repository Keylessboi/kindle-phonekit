# Guardrails — PhoneKit "Pocket Assistant"

Rules for any copy, alt text, caption, or remix of this campaign. If a phrase
violates a rule below, change it.

## Prohibited (never say, never imply)

- **"Replaces your phone"** — it is a focused toolset, not a phone
  replacement.
- **"Works on any Kindle"** — it needs a jailbroken Kindle with KUAL; every
  firmware/jailbreak combo is not guaranteed.
- **"Secure by default", "private", "encrypted"** — the repo documents that
  `PK_XMPP_NO_VERIFY=1` skips TLS checks (insecure), and API keys sit in
  plain text in `config.env`. SCRAM-SHA-1 is *preferred*; the copy must say
  so and must not promise security.
- **"Offline"** — chat needs an LLM endpoint (even if that endpoint is on the
  device) and XMPP needs a network. The honest word is **low-distraction**,
  not **offline**.
- **Any fabricated number, screenshot, testimonial, or customer.**
- **Credentials, keys, JIDs, or passwords** in any asset or example.
- **Fake UI chrome** — the illustration is art, and must never be shown as a
  screenshot of the extension.

## Required qualifiers

- Every feature list must carry: "needs a jailbroken Kindle and KUAL."
- When security is mentioned, add: "SCRAM-SHA-1 is preferred; keep TLS
  verification on; API keys are plain text in config.env."
- When "calm" or "low-distraction" is used, it is a tone, not a measured claim.

## Preferred terms

- "OpenAI-compatible endpoint" (covers Ollama, llama.cpp, vLLM, OpenAI,
  OpenRouter).
- "KUAL extension" (not "app" or "plugin").
- "Plain shell and Python from the standard library."
- "One removable folder."

## Release-stage language

- Version `1.0.0`, repository fresh this week. Use "self-contained",
  "focused toolset", "zero dependencies" (all verified) — never "battle
  tested", "production-grade", or "enterprise".
- The `config.xml` author field is the placeholder `You`; the campaign does
  not brand its author.

## Tone

- Human, understated, honest.
- Prefer short sentences and plain words.
- No manufactured urgency, no hype, no unsupported superlatives.