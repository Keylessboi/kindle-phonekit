# Contributing to PhoneKit

Thanks for helping. PhoneKit is intentionally small, self-contained, and
dependency-free, and it runs on an e-ink Kindle screen with tight constraints.
Please keep that spirit.

## Ground rules

1. **No new dependencies.** Everything runs off POSIX shell + the Python
   standard library. A pull request that adds `pip install`-able packages will
   be sent back.
2. **No mass reformatting.** Don't run a formatter across files you didn't
   meaningfully change; it makes review noisy.
3. **Keep it small and focused.** One PR, one change. Prefix the title with
   the area: `llm:`, `xmpp:`, `reader:`, `feed:`, `notes:`, `dashboard:`,
   `qr:`, `menu:`, `docs:`.
4. **Stick to the e-ink budget.** Large fonts, no images in app pages, no
   animations, no drag input. Every byte costs battery and renders slowly.

## Before you write code

Open an issue for non-trivial changes so we agree on the approach first. For
small fixes and docs you can go straight to a PR.

- Read `tests/README.md` before touching servers or scripts. The suite drives
  the *real* code against local mocks, and `test_static.py` enforces that any
  new environment variable a server reads is exported by its launcher and
  documented in `config.env`. If you add a config knob, expect that test to
  demand you wire it up everywhere.
- Follow the existing pattern. Each app lives in `ext/<name>/` with a
  `*_server.py` or `bridge.py`, plus `start.sh`, `stop.sh`, and `config.env`.
  Mirror `ext/llm/` closely.

## Local checks

```sh
python -m pytest tests/ -v      # the whole suite must pass
sh -n $(find extensions -name '*.sh')   # shell syntax
python -m py_compile <your .py>         # python compiles
```

GitHub Actions runs the matrix (Python 3.9–3.14) on every PR. The CI job named
`static` runs `sh -n`, `py_compile`, and the config sanity checks.

## Pull request checklist

- [ ] One focused change.
- [ ] New env var: exported by launcher **and** documented in `config.env`.
- [ ] `python -m pytest tests/ -q` green.
- [ ] No new runtime dependencies.
- [ ] No unrelated reformatting.

## Where to look

- `extensions/phonekit/ext/` — the apps and scripts.
- `tests/` — the scenario-driven suite (see `tests/README.md`).
- `docs/research/` — product viability notes (lightly maintained).
- `marketing/` — grounded campaign copy; keep claims in sync with the code.

Thanks for keeping the calm device calm.