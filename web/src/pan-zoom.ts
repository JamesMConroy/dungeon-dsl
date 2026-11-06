// Pan and zoom for the Dungeon Map, by rewriting the SVG's viewBox. Listens on
// the map's container, so it survives each re-render replacing the SVG.

export type PanZoom = {
  /** Call after the map's SVG is replaced: keeps the view while the bounds match, else refits. */
  mapReplaced(): void;
};

type Point = { x: number; y: number };

// Past this much movement a press is a drag, not a click.
const DRAG_THRESHOLD_PX = 4;
// Limits on the viewBox's width, as multiples of the fitted width.
const NARROWEST_VIEW = 1 / 8;
const WIDEST_VIEW = 2;
const BUTTON_ZOOM = 1.25;
const WHEEL_ZOOM_PER_PX = 0.002;
const WHEEL_PX_PER_LINE = 16;

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);
const midpoint = (a: Point, b: Point) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });

export function createPanZoom(map: HTMLElement, controlsParent: HTMLElement, onViewChange: () => void): PanZoom {
  let fitted: string | null = null;
  let view: string | null = null;

  const pointers = new Map<number, Point>();
  let dragging = false;
  let dragged = false;

  const svg = () => map.querySelector("svg");

  function setViewBox(element: SVGSVGElement, x: number, y: number, width: number, height: number) {
    view = `${x} ${y} ${width} ${height}`;
    element.setAttribute("viewBox", view);
    onViewChange();
  }

  function pan(dx: number, dy: number) {
    const element = svg();
    const scale = element?.getScreenCTM()?.a;
    if (!element || !scale) return;
    const { x, y, width, height } = element.viewBox.baseVal;
    setViewBox(element, x - dx / scale, y - dy / scale, width, height);
  }

  /** Scales the viewBox by `factor`, holding the map still at a point on the screen. */
  function zoom(factor: number, around: Point) {
    const element = svg();
    const screenToMap = element?.getScreenCTM()?.inverse();
    if (!element || !screenToMap || fitted === null) return;
    const { x, y, width, height } = element.viewBox.baseVal;
    const fittedWidth = Number(fitted.split(" ")[2]);
    const newWidth = Math.min(fittedWidth * WIDEST_VIEW, Math.max(fittedWidth * NARROWEST_VIEW, width * factor));
    const applied = newWidth / width;
    const held = new DOMPoint(around.x, around.y).matrixTransform(screenToMap);
    setViewBox(element, held.x - (held.x - x) * applied, held.y - (held.y - y) * applied, newWidth, height * applied);
  }

  function zoomAtCentre(factor: number) {
    const { left, top, width, height } = map.getBoundingClientRect();
    zoom(factor, { x: left + width / 2, y: top + height / 2 });
  }

  function fit() {
    view = null;
    if (fitted !== null) svg()?.setAttribute("viewBox", fitted);
    onViewChange();
  }

  function movePointer(pointerId: number, to: Point) {
    const from = pointers.get(pointerId);
    if (!from) return;
    if (!dragging) {
      if (pointers.size < 2 && distance(from, to) < DRAG_THRESHOLD_PX) return;
      dragging = dragged = true;
      map.dataset.dragging = "";
    }
    // Only now: capturing at the press would retarget a plain click away from its Room.
    map.setPointerCapture(pointerId);
    pointers.set(pointerId, to);

    const other = [...pointers].find(([id]) => id !== pointerId)?.[1];
    if (other) {
      const before = midpoint(from, other);
      const after = midpoint(to, other);
      pan(after.x - before.x, after.y - before.y);
      const spread = distance(to, other);
      if (spread > 0) zoom(distance(from, other) / spread, after);
    } else {
      pan(to.x - from.x, to.y - from.y);
    }
  }

  function releasePointer(event: PointerEvent) {
    pointers.delete(event.pointerId);
    if (pointers.size === 0) {
      dragging = false;
      delete map.dataset.dragging;
    }
  }

  map.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    if (pointers.size === 0) dragged = false;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  });
  window.addEventListener("pointermove", (event) => movePointer(event.pointerId, { x: event.clientX, y: event.clientY }));
  window.addEventListener("pointerup", releasePointer);
  window.addEventListener("pointercancel", releasePointer);

  // The click a drag ends with isn't a click on whatever lies under it.
  map.addEventListener(
    "click",
    (event) => {
      if (dragged) event.stopImmediatePropagation();
      dragged = false;
    },
    { capture: true },
  );

  map.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const pixels = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? event.deltaY * WHEEL_PX_PER_LINE : event.deltaY;
      zoom(Math.exp(pixels * WHEEL_ZOOM_PER_PX), { x: event.clientX, y: event.clientY });
    },
    { passive: false },
  );

  const controls = document.createElement("div");
  controls.className = "map-controls";
  for (const [label, text, action] of [
    ["Zoom in", "+", () => zoomAtCentre(1 / BUTTON_ZOOM)],
    ["Zoom out", "−", () => zoomAtCentre(BUTTON_ZOOM)],
    ["Fit map", "Fit", fit],
  ] as const) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.setAttribute("aria-label", label);
    button.addEventListener("click", action);
    controls.append(button);
  }
  controlsParent.append(controls);

  return {
    mapReplaced() {
      const element = svg();
      const bounds = element?.getAttribute("viewBox") ?? null;
      if (bounds !== fitted) {
        fitted = bounds;
        view = null;
      } else if (view !== null) {
        element?.setAttribute("viewBox", view);
      }
    },
  };
}
