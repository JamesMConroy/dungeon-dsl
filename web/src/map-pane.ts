// The Dungeon Map pane: the inline SVG, plus whatever status belongs over it.
// The map stays up when a later render fails, so the DM keeps their bearings.

export type MapPane = {
  /** Holds the inline SVG; stays put when a re-render replaces the SVG. */
  map: HTMLElement;
  showLoading(): void;
  showMap(svg: string, renderMs: number): void;
  showMessage(message: string): void;
};

export function createMapPane(parent: HTMLElement): MapPane {
  parent.dataset.testid = "map-pane";

  const status = document.createElement("div");
  status.className = "map-status";
  status.setAttribute("role", "status");

  const map = document.createElement("div");
  map.className = "map";
  map.dataset.testid = "dungeon-map";

  parent.append(status, map);

  return {
    map,
    showLoading() {
      parent.dataset.state = "loading";
      status.textContent = "Loading Python…";
    },
    showMap(svg, renderMs) {
      parent.dataset.state = "ready";
      status.textContent = `Rendered in ${Math.round(renderMs)} ms`;
      map.innerHTML = svg;
    },
    showMessage(message) {
      parent.dataset.state = "message";
      status.textContent = message;
    },
  };
}
