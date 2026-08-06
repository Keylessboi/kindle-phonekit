# Security Policy

PhoneKit is a self-contained KUAL extension for jailbroken Kindles. It runs
entirely on the device and talks to the network only when a feature requires it
(LLM chat, XMPP, feed fetching).

## Supported

| Component                       | Supported |
|---------------------------------|-----------|
| Latest `master` / `main`        | ✅        |
| Tagged releases                 | ✅        |
| Older unreleased branches       | ❌        |

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Email the
maintainers privately or open a draft security advisory.

When reporting, include:

- Where you found it (which `ext/*` component, which config path).
- The exact steps to reproduce.
- What an attacker could do with it.

## What matters here

The highest-value things to look at, in order:

1. **Credentials** — API keys and XMPP passwords are stored in plain text in
   `config.env`. Code must never log them, leak them into HTML, or send them to
   an unintended host. TLS verification must stay on by default
   (`PK_XMPP_NO_VERIFY` is an explicit opt-in).
2. **HTML escaping** — every server renders user/upstream text into web pages;
   it must be escaped to avoid reflected content issues in the Kindle browser.
3. **Local-only binding** — servers bind to `127.0.0.1`, never `0.0.0.0`.
4. **Shell quoting** — scripts pass argument text; proper quoting prevents
   injection via menu params.

## Disclosure

We aim to acknowledge reports within 5 days and ship a fix on the next commit.

## Changes

Updates to this policy are tracked in git history.