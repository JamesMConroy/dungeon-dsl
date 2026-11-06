// The Playground's page structure. Owns where panes sit, not what they hold.

export type Layout = {
  editorPane: HTMLElement;
  mapPane: HTMLElement;
};

export function createLayout(root: HTMLElement): Layout {
  root.className = "workbench";

  const editorPane = document.createElement("section");
  editorPane.className = "pane editor-pane";
  editorPane.setAttribute("aria-label", "Dungeon YAML");

  const mapPane = document.createElement("section");
  mapPane.className = "pane map-pane";
  mapPane.setAttribute("aria-label", "Dungeon Map");

  root.append(editorPane, mapPane);
  return { editorPane, mapPane };
}
