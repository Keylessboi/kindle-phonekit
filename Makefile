# PhoneKit developer convenience targets.
# These mirror exactly what CI runs; CI is the source of truth.

PY ?= python3

.PHONY: test static check clean site

test:
	$(PY) -m pytest tests/ -q

static:
	sh -n $(shell find extensions -name '*.sh' | tr '\n' ' ')
	$(PY) -m py_compile $(shell find extensions -name '*.py' | tr '\n' ' ')

# Tests + static (the CI equivalent).
check: test static

# Serve the static marketing / Pages site locally.
site:
	$(PY) -m http.server 8080 -d pages

clean:
	rm -rf .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
	find . -name '*.pyc' -delete