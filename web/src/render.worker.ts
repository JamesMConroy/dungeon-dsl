// Module worker that hosts Pyodide and our wheel, and turns YAML into SVG.
import { loadPyodide, version } from "pyodide";
import type { RenderRequest, WorkerMessage } from "./render-protocol";

const INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${version}/full/`;
const WHEEL_URL = new URL(import.meta.env.BASE_URL + import.meta.env.VITE_WHEEL_URL, self.location.origin).href;

// Imports run during boot so the first render doesn't pay for them.
const RENDER_MODULE = `
import json
import yaml
from dungeon_dsl.models import Dungeon
from dungeon_dsl.svg import render_svg

def render(text):
    try:
        return json.dumps({"svg": render_svg(Dungeon.model_validate(yaml.safe_load(text)))})
    except Exception as e:
        return json.dumps({"error": str(e)})

render
`;

type PythonRender = (text: string) => string;

const post = (message: WorkerMessage) => self.postMessage(message);

async function boot(): Promise<PythonRender> {
  const pyodide = await loadPyodide({ indexURL: INDEX_URL, packages: ["pydantic", "pyyaml"] });
  await pyodide.loadPackage(WHEEL_URL);
  return pyodide.runPython(RENDER_MODULE) as PythonRender;
}

function handleRequest(render: PythonRender, { seq, text }: RenderRequest) {
  const started = performance.now();
  const result = JSON.parse(render(text)) as { svg: string } | { error: string };
  if ("svg" in result) {
    post({ type: "rendered", seq, svg: result.svg, ms: performance.now() - started });
  } else {
    post({ type: "render-failed", seq, message: result.error });
  }
}

boot().then(
  (render) => {
    self.onmessage = (event: MessageEvent<RenderRequest>) => handleRequest(render, event.data);
    post({ type: "ready" });
  },
  (error: unknown) => post({ type: "boot-failed", message: String(error) }),
);
