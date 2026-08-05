## What / why

<!-- One sentence on the change and the problem it solves. -->

Closes #<!-- issue number -->

## How it was verified

<!-- For every code change, the test suite must stay green. -->

- [ ] `python -m pytest tests/ -q` passes
- [ ] `sh -n` passes on every touched script
- [ ] All touched `.py` files pass `python -m py_compile`
- [ ] `menu.json` still validates as JSON (if touched)
- [ ] Any new env var is exported by its launcher and documented in `config.env`

## Scope check

- [ ] I did not run a formatter across unrelated files
- [ ] I kept this PR focused on one change

## Notes

<!-- Anything a reviewer should know, or screenshots for UI changes. -->