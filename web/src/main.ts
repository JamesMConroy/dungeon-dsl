// Wires the Playground's parts together; the behaviour lives in the modules.
import goblinWarren from "../../examples/goblin_warren.yaml?raw";
import { createEditor } from "./editor";
import { createLayout } from "./layout";
import { createMapPane } from "./map-pane";
import { createRenderClient, type RenderEvent } from "./render-client";
import { createRoomExplorer } from "./room-explorer";
import "./style.css";

const { editorPane, mapPane, cardPane } = createLayout(document.querySelector<HTMLElement>("#app")!);
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

createEditor(editorPane, goblinWarren, (text) => renderer.request(text));
renderer.request(goblinWarren);
