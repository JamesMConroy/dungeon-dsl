// Wires the Playground's parts together; the behaviour lives in the modules.
import goblinWarren from "../../examples/goblin_warren.yaml?raw";
import { createEditor } from "./editor";
import { bundledExamples } from "./examples";
import { createLayout } from "./layout";
import { createMapPane } from "./map-pane";
import { decodePermalink, PermalinkError } from "./permalink";
import { createRenderClient, type RenderEvent } from "./render-client";
import { createRoomExplorer } from "./room-explorer";
import { createShareControl } from "./share";
import { createToolbar } from "./toolbar";
import "./style.css";

const {
  toolbar: toolbarSlot,
  editorPane,
  mapPane,
  cardPane,
} = createLayout(document.querySelector<HTMLElement>("#app")!);
const pane = createMapPane(mapPane);
const explorer = createRoomExplorer(pane.map, cardPane);

function showRenderEvent(event: RenderEvent) {
  switch (event.kind) {
    case "loading":
      pane.showLoading();
      return;
    case "rendered":
      pane.showMap(event.svg, event.ms);
      explorer.show(event.dungeon);
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

/** The URL's Permalink: its Dungeon, why it can't be opened, or null if there isn't one. */
async function readPermalink(): Promise<string | PermalinkError | null> {
  if (!location.hash) return null;
  return decodePermalink(location.hash).catch((error: PermalinkError) => error);
}

const opened = await readPermalink();
const initial = typeof opened === "string" ? opened : goblinWarren;

const editor = createEditor(editorPane, initial, (text) => renderer.request(text));
const toolbar = createToolbar(toolbarSlot, {
  examples: bundledExamples,
  currentYaml: () => editor.text(),
  onLoadExample(example) {
    editor.setText(example.yaml);
    share.clear();
    // The document no longer matches any Permalink. Replacing, not assigning
    // location.hash, leaves no stray "#" and no history entry.
    history.replaceState(null, "", location.pathname + location.search);
  },
});
const share = createShareControl(toolbarSlot, () => editor.text());
if (opened instanceof PermalinkError) share.showBadLink(opened.message);
renderer.request(initial);

// A link pasted into an open tab changes only the fragment, so the page doesn't reload.
window.addEventListener("hashchange", async () => {
  const pasted = await readPermalink();
  if (pasted instanceof PermalinkError) {
    share.showBadLink(pasted.message);
  } else if (pasted !== null) {
    share.clear();
    editor.setText(pasted);
  }
});
