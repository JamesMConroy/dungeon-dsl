// The Playground's page structure. Owns where panes sit, not what they hold.

export type Layout = {
  toolbar: HTMLElement;
  editorPane: HTMLElement;
  mapPane: HTMLElement;
  cardPane: HTMLElement;
  isMapFirst(): boolean;
};

const MAP_FIRST = "(max-width: 820px)";

export function createLayout(root: HTMLElement): Layout {
  root.className = "workbench";

  // Only an attribute changes, and CSS does the rest: no pane is ever rebuilt or
  // moved, so crossing the breakpoint can't lose the editor's text or the selection.
  const mapFirst = window.matchMedia(MAP_FIRST);
  const applyLayout = () => {
    root.dataset.layout = mapFirst.matches ? "map-first" : "workbench";
  };
  mapFirst.addEventListener("change", applyLayout);
  applyLayout();

  const toolbar = document.createElement("header");
  toolbar.className = "toolbar";

  const editorPane = document.createElement("section");
  editorPane.className = "pane editor-pane";
  editorPane.setAttribute("aria-label", "Dungeon YAML");

  const mapPane = document.createElement("section");
  mapPane.className = "pane map-pane";
  mapPane.setAttribute("aria-label", "Dungeon Map");

  const cardPane = document.createElement("aside");
  cardPane.className = "pane card-pane";
  cardPane.setAttribute("aria-label", "Room card");
  cardPane.dataset.testid = "room-card";

  root.append(toolbar, editorPane, mapPane, cardPane);
  return { toolbar, editorPane, mapPane, cardPane, isMapFirst: () => mapFirst.matches };
}
