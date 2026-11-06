list:
  just -l

examples format="svg":
  for e in examples/*.yaml ; do uv run dungeon-dsl $e -f {{format}} > ${e%%\.*}.svg ; done


example-svg:
  uv run dungeon-dsl examples/goblin_warren.yaml -f svg > out.svg

flowchart-ascii:
  uv run dungeon-dsl examples/goblin_warren.yaml | mermaid-ascii -

flowchart-png:
  uv run dungeon-dsl examples/goblin_warren.yaml | mise exec -- mmdc -i - -o out.png -b white


lint:
  uv run ruff check .
  uv run ruff format --check .

typecheck:
  uv run pyright

test:
  uv run pytest

# Exercises the lower bounds in pyproject.toml, including the pydantic 2.12 line Pyodide ships.
test-lowest:
  uv run --isolated --resolution lowest-direct pytest

web-install:
  npm --prefix web ci

# Wheel at a content-hashed path and the JSON Schema, then the site, into web/dist.
web-build: web-install
  node web/scripts/stage-wheel.mjs
  npm --prefix web run build

# Re-run to pick up model changes: the wheel and JSON Schema are staged once at start.
web-dev: web-install
  node web/scripts/stage-wheel.mjs
  npm --prefix web run dev

# Corp laptop: Playwright and Pyodide downloads may need
# NODE_EXTRA_CA_CERTS=/opt/netskope/netskope-cert-bundle.pem (Netskope TLS interception).
# CI passes --with-deps.
web-browsers *args:
  npm --prefix web exec -- playwright install chromium {{args}}

# Vitest: the permalink codec. No build needed.
web-unit: web-install
  npm --prefix web run test:unit

# Smoke test against `vite preview`; run web-build first.
web-test:
  npm --prefix web run test:e2e
