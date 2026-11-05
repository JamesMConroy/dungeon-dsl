# Pyodide feasibility and cold start

Researched 2026-11-05 for [issue 02](https://github.com/JamesMConroy/dungeon-dsl/issues/3).

Confidence tags: **[verified]** = I ran it or read it straight from the primary artifact. **[docs]** = stated in official Pyodide docs, not tested here. **[estimate]** = my extrapolation, treat as a ballpark.

## TL;DR

- Yes, it runs. On Pyodide **314.0.7** (current stable, Python 3.14.2) `dungeon_dsl` renders `examples/goblin_warren.yaml` and the SVG is **byte-identical** to native CPython (same sha256). Tested in Node with the `pyodide@314.0.7` npm package. **[verified]**
- **The catch:** Pyodide's bundled pydantic is **2.12.5**, which does not satisfy our `pydantic>=2.13.4`. The code only uses `BaseModel`, `Field` and `model_validator`, all v2.0-era APIs, so 2.12.5 works fine. **[verified]**
- **Second catch:** `pyproject.toml` lists `pyright`, `pyrefly` and `typer` as *runtime* dependencies and has no `[build-system]`. As written, a wheel would make micropip try to resolve pyrefly, which has no wasm wheel. Install with no dependency resolution, or fix the metadata.
- Cold start is about **8.2 MB over the wire** (brotli) and about **1.3 s to the first render** in Node with a warm cache. A warm render takes **about 9 ms**. **[verified]**

## 1. Package availability

Source: the 314.0.7 lockfile, https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide-lock.json (`info: python 3.14.2, abi 2026_0, emscripten 5.0.3`, 357 packages). Release: https://github.com/pyodide/pyodide/releases/tag/314.0.7 (2026-09-14). **[verified]**

| Package | Version in Pyodide 314.0.7 | Meets our pin? |
|---|---|---|
| pydantic | 2.12.5 | **No** (needs >=2.13.4) |
| pydantic-core | 2.41.5 (wasm32 wheel) | n/a (pinned exactly by pydantic) |
| pyyaml | 6.0.3 (wasm32 wheel, includes `_yaml` C ext) | Yes |
| typing-extensions / annotated-types / typing-inspection | 4.15.0 / 0.7.0 / 0.4.2 | Yes for pydantic 2.12 |
| micropip | 0.11.1 | n/a |
| typer, pyrefly, pyright | absent | n/a (`click` and `rich` are present) |

Notes:
- Versioning changed. After 0.29.x, Pyodide switched to `<pyver>.x.y` (314.x = CPython 3.14). 0.29.5 and 0.27.8 are maintenance releases on older lines. 315.0.0a2 is a prerelease. Source: GitHub releases API, https://api.github.com/repos/pyodide/pyodide/releases. **[verified]**
- `requires-python = ">=3.13"` is satisfied by 3.14.2. **[verified]**

### Getting pydantic >= 2.13 anyway

- pydantic **2.13.x** pins `pydantic-core==2.46.x`. PyPI has **no** emscripten wheel for 2.46.x, so 2.13 cannot be installed in Pyodide 314. Sources: https://pypi.org/pypi/pydantic/2.13.4/json and https://pypi.org/pypi/pydantic-core/json. **[verified]**
- pydantic-core **≥2.47.0** publishes `cp314-cp314-pyemscripten_2026_0_wasm32` wheels on PyPI, which match Pyodide 314's ABI. pydantic **2.14.x** pins core 2.50.x, so `micropip.install("pydantic==2.14.3")` works. It pulled core 2.50.4 from PyPI and rendered identically. **[verified]**
- Pyodide 314 accepts `pyemscripten`-tagged wheels from PyPI (changelog 0.29.4 / 314.0.2 note "packages now have PyEmscripten wheels in PyPI"): https://pyodide.org/en/stable/project/changelog.html. **[docs + verified]**
- Cost: the playground would then depend on PyPI/pythonhosted at runtime (or we self-host those 4 wheels). It also adds about 1–2 s and a micropip resolve. pydantic 2.14 needs `typing-extensions>=4.16`, which is newer than the bundled 4.15, so that comes from PyPI too. Not worth it unless we actually need 2.13+ features. **[verified for function; opinion on worth]**

## 2. Loading our own package

Options, per https://pyodide.org/en/stable/usage/loading-custom-python-code.html and https://pyodide.org/en/stable/usage/loading-packages.html: **[docs]**

1. **Same-origin wheel + `pyodide.loadPackage(url)`.** Tested. It needs no micropip (saves about 111 KB) and does no dependency resolution, which is exactly what we want because we preload `pydantic`/`pyyaml` from the lockfile. The URL filename must be a valid PEP 427 wheel name. **[verified]**
2. **Same-origin wheel + `micropip.install(url, deps=False)`.** Also tested (via `emfs:`). It is the docs' "best way", but micropip adds weight and, with `deps=True`, would trip on `pydantic>=2.13.4` and `pyrefly`. **[verified]**
3. `pyodide.unpackArchive(buf, "zip")` of the wheel or a tarball. It works per the docs, with no dependency resolution and no dist-info registration semantics. This is fine too, with no real advantage over (1). **[docs]**
4. Writing individual `.py` files into the FS. The docs recommend against it in favor of archives. Avoid it. **[docs]**

**Recommendation:** (1). Build the wheel in CI and ship it next to the site as `dungeon_dsl-<ver>-py3-none-any.whl`. A content-hashed directory is fine as long as the *filename* stays a valid wheel name.

Prereqs in the repo (observed in `/pyproject.toml`): **[verified]**
- Add a `[build-system]` (hatchling or uv_build). A throwaway hatchling build of just `dungeon_dsl/` gave a 9.9 KB wheel.
- Move `pyright`/`pyrefly` to the dev group and `typer` to an optional `cli` extra (only `main.py` imports typer and yaml). These are wrong as runtime deps regardless of the web work.
- Either relax `pydantic>=2.13.4` to `>=2.12` or accept that the web build installs with no dependency resolution against 2.12.5. Relaxing is more honest.

## 3. Cold-start cost

Wire sizes measured from jsDelivr with `Accept-Encoding: br` (jsDelivr serves brotli and `cache-control: public, max-age=31536000`). **[verified]**

| File | Raw | Wire |
|---|---|---|
| pyodide.asm.wasm | 9.60 MB | 3.44 MB |
| python_stdlib.zip | 2.55 MB | 2.51 MB |
| pyodide.asm.mjs | 1.25 MB | 0.26 MB |
| pyodide-lock.json + pyodide.mjs | 0.14 MB | 0.03 MB |
| **Core subtotal** | **13.5 MB** | **≈6.24 MB** |
| pydantic_core wasm wheel | 1.31 MB | 1.31 MB |
| pydantic wheel | 0.46 MB | 0.45 MB |
| pyyaml wheel | 0.11 MB | 0.11 MB |
| typing_extensions + annotated_types + typing_inspection | 0.07 MB | 0.07 MB |
| **Deps subtotal** | **1.95 MB** | **≈1.94 MB** |
| our wheel | 0.01 MB | 0.01 MB |
| **Total** | **≈15.5 MB** | **≈8.2 MB** |

(Add micropip, 0.11 MB, only if you use option 2 or the PyPI pydantic route.)

Timings in Node 26 on an Apple-silicon laptop, wheels already cached locally, so this is init cost without network: **[verified]**
- `loadPyodide()` takes about 0.75 s. Loading pydantic+pyyaml adds about 0.1 s, and our wheel about 0.2 s. The first render (import + validate + SVG) takes about 0.27 s, for **about 1.3 s total to the first SVG**.
- The steady-state render of goblin_warren (68 KB SVG) takes **about 9 ms** (mean of 20).
- A cold run that also fetched the wheels from jsDelivr came in around 1.9 s total on corp wifi.

Browser estimates: **[estimate, low-medium confidence; not measured in a browser]**
- Desktop broadband, first visit: about 2–4 s (≈8 MB download plus wasm compile; browsers stream-compile wasm). Repeat visits rely on the HTTP cache because of the year-long immutable cache headers, so expect about 1–1.5 s.
- Mid-range phone on 4G (~10 Mbps): about 7–10 s on first visit, mostly download, plus slower wasm compile and init. Repeat visits take about 2–4 s.

**Lazy loading:** yes. Start the worker on page load (or on first focus of the editor), show a "loading Python…" state, and keep the editor usable meanwhile; queue the latest text and render once ready. `loadPyodide({ packages: ["pydantic", "pyyaml"] })` preloads the deps in the same call (tested). **[verified]**

## 4. Web Worker pattern and cancellation

- **A module worker is mandatory** as of 314.0.0. `pyodide.asm.js` became `pyodide.asm.mjs`, and classic `importScripts()` workers are no longer supported. Use `new Worker(new URL("./py.worker.ts", import.meta.url), { type: "module" })`, which Vite handles natively. Sources: https://pyodide.org/en/stable/usage/webworker.html and the changelog 314.0.0 "BREAKING CHANGE". **[docs]**
- The canonical pattern in the docs is a request/response with an `id` per message: https://pyodide.org/en/stable/usage/webworker.html. **[docs]**
- **True interruption** (`pyodide.setInterruptBuffer` → `KeyboardInterrupt`) needs a `SharedArrayBuffer`, which needs COOP/COEP headers: https://pyodide.org/en/stable/usage/keyboard-interrupts.html. **[docs]** **GitHub Pages cannot set custom headers**, so this is off the table. The `coi-serviceworker` shim is possible but hacky. **[medium confidence on GH Pages headers; this is well-known but I did not re-verify a GH doc]**
- **What to do instead.** Renders take about 10–20 ms, so cancellation mostly doesn't matter:
  - Debounce typing (around 150–250 ms) on the main thread.
  - Track latest-wins with a monotonically increasing `seq`. The worker keeps only the newest pending request (coalescing) and the main thread drops any result whose `seq` is not the latest.
  - Add a watchdog for pathological input (say >2 s). Call `worker.terminate()` and spawn a fresh worker. Re-init costs about 1 s from the HTTP cache, which is acceptable for a rare event. Show "render timed out".
- Validation errors surface in JS as `PythonError` with pydantic's message text, e.g. `rooms  Field required [type=missing…]`. It's better to catch `ValidationError` in Python and return structured `{ok, svg | errors: e.errors()}` so the UI can map `loc` to editor positions. **[verified that errors propagate; the structuring is a suggestion]**

## 5. Version pinning: CDN vs self-host

- **CDN:** `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/` is version-pinned in the path and immutable-cached for a year. Pin the npm `pyodide` package to an exact version (`"pyodide": "314.0.7"`, no caret) and derive `indexURL` from its exported `version`. The bundler docs recommend this as the default. Lockfile wheels are then pinned by the lockfile itself, so loadPackage versions can't drift. Source: https://pyodide.org/en/stable/usage/working-with-bundlers.html and https://pyodide.org/en/stable/usage/downloading-and-deploying.html. **[docs + verified URLs]**
- **Self-host:** `vite-plugin-static-copy` copies `node_modules/pyodide/*` into `dist/assets`. The npm package is the core set (13 MB on disk) and **excludes wheels**, so either pass `packageBaseUrl` at jsDelivr (hybrid) or extract the 6 needed wheels from `pyodide-314.0.7.tar.bz2` (337 MB release asset) into the build. The docs say to list exact `.whl` filenames, not a glob. The docs note those Vite instructions were tested on Pyodide 0.26.2 / Vite 5, so expect minor drift. **[docs]**
- GH Pages serves `.wasm` with the right MIME type and the docs name it as a valid host. **[docs]** Whether GH Pages brotli/gzips `.wasm` I did **not** verify. If it doesn't, the self-hosted wasm transfer goes from 3.4 MB to 9.6 MB, which is a real reason to prefer jsDelivr for the runtime. **[unverified]**
- **Recommendation:** load the runtime and lockfile wheels from jsDelivr pinned at `v314.0.7`, and self-host only our own wheel. Self-host everything only if offline use or CDN independence becomes a requirement.

## Reproduction

Scratch harness (not committed): `npm i pyodide@314.0.7`. Build the wheel from `dungeon_dsl/` with a minimal hatchling pyproject, then in Node run `loadPyodide({packages:["pydantic","pyyaml"]})` → `loadPackage(wheelPath)` → `render_svg(Dungeon.model_validate(yaml.safe_load(src)))`. Compare the sha256 against `uv run` on CPython.
