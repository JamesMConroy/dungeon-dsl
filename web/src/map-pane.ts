// The Dungeon Map pane: the inline SVG, plus whatever status belongs over it.
// The map stays up when a later render fails, so the DM keeps their bearings.

export type MapPane = {
  /** Holds the inline SVG; stays put when a re-render replaces the SVG. */
  map: HTMLElement;
  showLoading(): void;
  showMap(svg: string, renderMs: number): void;
  showMessage(message: string): void;
  /** Keeps the last good map on show, greyed, under a banner. */
  showInvalid(errorCount: number): void;
};

export function createMapPane(parent: HTMLElement): MapPane {
  parent.dataset.testid = "map-pane";

  const status = document.createElement("div");
  status.className = "map-status";
  status.setAttribute("role", "status");

  const banner = document.createElement("div");
  banner.className = "map-banner";
  banner.dataset.testid = "map-banner";
  banner.setAttribute("role", "alert");
  banner.hidden = true;

  const map = document.createElement("div");
  map.className = "map";
  map.dataset.testid = "dungeon-map";

  parent.append(status, banner, map);

  return {
    map,
    showLoading() {
      parent.dataset.state = "loading";
      banner.hidden = true;
      status.textContent = "Loading Python…";
    },
    showMap(svg, renderMs) {
      parent.dataset.state = "ready";
      banner.hidden = true;
      status.textContent = `Rendered in ${Math.round(renderMs)} ms`;
      map.innerHTML = svg;
    },
    showMessage(message) {
      parent.dataset.state = "message";
      banner.hidden = true;
      status.textContent = message;
    },
    showInvalid(errorCount) {
      parent.dataset.state = "invalid";
      status.textContent = "";
      const errors = errorCount === 1 ? "1 Error" : `${errorCount} Errors`;
      banner.textContent = map.childElementCount
        ? `${errors}. Showing the last good Dungeon Map.`
        : `${errors}. Nothing to draw yet.`;
      banner.hidden = false;
    },
  };
}
