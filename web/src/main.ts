// Wires the Playground's parts together; the behaviour lives in the modules.
import goblinWarren from "../../examples/goblin_warren.yaml?raw";
import { createEditor } from "./editor";
import { bundledExamples } from "./examples";
import { createLayout } from "./layout";
import { createMapPane } from "./map-pane";
import { createRenderClient, type RenderEvent } from "./render-client";
import { createToolbar } from "./toolbar";
import "./style.css";

const { toolbar: toolbarSlot, editorPane, mapPane } = createLayout(document.querySelector<HTMLElement>("#app")!);
const pane = createMapPane(mapPane);

function showRenderEvent(event: RenderEvent) {
  switch (event.kind) {
    case "loading":
      pane.showLoading();
      return;
    case "rendered":
      pane.showMap(event.svg, event.ms);
      toolbar.setLastGoodMap(event.svg);
      return;
    case "render-failed":
      pane.showMessage(event.message);
      return;
    case "timed-out":
      pane.showMessage("Rendering took too long and was stopped. Keep editing to try again.");
      return;
    case "boot-failed":
      pane.showMessage(`Couldn't load Python. Reload the page to try again.\n${event.message}`);
  }
}

const renderer = createRenderClient({ onEvent: showRenderEvent });

const editor = createEditor(editorPane, goblinWarren, (text) => renderer.request(text));
const toolbar = createToolbar(toolbarSlot, {
  examples: bundledExamples,
  currentYaml: () => editor.text(),
  onLoadExample(example) {
    editor.setText(example.yaml);
    // The document no longer matches any Permalink. Replacing, not assigning
    // location.hash, leaves no stray "#" and no history entry.
    history.replaceState(null, "", location.pathname + location.search);
  },
});
renderer.request(goblinWarren);
