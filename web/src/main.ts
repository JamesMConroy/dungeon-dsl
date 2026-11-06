// Wires the Playground's parts together; the behaviour lives in the modules.
import goblinWarren from "../../examples/goblin_warren.yaml?raw";
import { createEditor } from "./editor";
import { createLayout } from "./layout";
import { createMapPane } from "./map-pane";
import { createProblemList } from "./problem-list";
import { createRenderClient, type RenderEvent } from "./render-client";
import type { Problem } from "./render-protocol";
import "./style.css";

const { editorPane, mapPane } = createLayout(document.querySelector<HTMLElement>("#app")!);
const pane = createMapPane(mapPane);

function showProblems(problems: Problem[]) {
  editor.showProblems(problems);
  problemList.show(problems);
}

function showRenderEvent(event: RenderEvent) {
  switch (event.kind) {
    case "loading":
      pane.showLoading();
      return;
    case "rendered":
      pane.showMap(event.svg, event.ms);
      showProblems(event.result.problems);
      return;
    case "invalid":
      pane.showInvalid(event.result.problems.filter((problem) => problem.severity === "error").length);
      showProblems(event.result.problems);
      return;
    case "render-failed":
      pane.showMessage(event.message);
      showProblems([]);
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
const problemList = createProblemList(editorPane, (problem) => editor.revealProblem(problem));
renderer.request(goblinWarren);
