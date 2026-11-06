// Wires the Playground's parts together; the behaviour lives in the modules.
import goblinWarren from "../../examples/goblin_warren.yaml?raw";
import { createEditor } from "./editor";
import { createLayout } from "./layout";
import { createMapPane } from "./map-pane";
import { decodePermalink } from "./permalink";
import { createRenderClient, type RenderEvent } from "./render-client";
import { createShareControl } from "./share";
import "./style.css";

const { toolbar, editorPane, mapPane } = createLayout(document.querySelector<HTMLElement>("#app")!);
const pane = createMapPane(mapPane);

function showRenderEvent(event: RenderEvent) {
  switch (event.kind) {
    case "loading":
      pane.showLoading();
      return;
    case "rendered":
      pane.showMap(event.svg, event.ms);
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

const share = createShareControl(toolbar, () => editor.text());

/** The Dungeon in the URL's Permalink, if there is one and it can be read. */
async function readPermalink(): Promise<string | null> {
  if (!location.hash) return null;
  try {
    const yaml = await decodePermalink(location.hash);
    share.clear();
    return yaml;
  } catch (error) {
    share.showBadLink((error as Error).message);
    return null;
  }
}

const initial = (await readPermalink()) ?? goblinWarren;
const editor = createEditor(editorPane, initial, (text) => renderer.request(text));
renderer.request(initial);

// A link pasted into an open tab changes only the fragment, so the page doesn't reload.
window.addEventListener("hashchange", async () => {
  const yaml = await readPermalink();
  if (yaml !== null) editor.setText(yaml);
});
