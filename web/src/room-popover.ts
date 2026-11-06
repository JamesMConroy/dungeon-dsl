// In Map-first the card pane floats beside the selected Room. Knows nothing about
// the selection itself: it's told which Room to sit by, and reports dismissal.

export type RoomPopover = {
  /** Where the card's contents go. */
  body: HTMLElement;
  /** Opens beside this Room, or closes on null. Call again after the map is redrawn. */
  anchorTo(roomId: string | null): void;
  /** Call when the Room may have moved on screen. */
  reposition(): void;
};

const GAP_PX = 8;
const MARGIN_PX = 8;

const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(value, high));

export function createRoomPopover(
  cardPane: HTMLElement,
  map: HTMLElement,
  { isMapFirst, onDismiss }: { isMapFirst(): boolean; onDismiss(): void },
): RoomPopover {
  let anchorId: string | null = null;

  const body = document.createElement("div");
  body.className = "card-body";

  const close = document.createElement("button");
  close.type = "button";
  close.className = "card-close";
  close.textContent = "×";
  close.setAttribute("aria-label", "Close room card");
  close.addEventListener("click", onDismiss);

  cardPane.append(close, body);

  function reposition() {
    if (anchorId === null || !isMapFirst()) return;
    const anchor = map.querySelector(`.room[data-room-id="${CSS.escape(anchorId)}"]`);
    if (!anchor) return;

    const room = anchor.getBoundingClientRect();
    const { width, height } = cardPane.getBoundingClientRect();
    const screenWidth = document.documentElement.clientWidth;
    const screenHeight = document.documentElement.clientHeight;

    let left = room.left;
    let top = room.top;
    if (room.right + GAP_PX + width <= screenWidth - MARGIN_PX) left = room.right + GAP_PX;
    else if (room.left - GAP_PX - width >= MARGIN_PX) left = room.left - GAP_PX - width;
    else if (room.bottom + GAP_PX + height <= screenHeight - MARGIN_PX) top = room.bottom + GAP_PX;
    else top = room.top - GAP_PX - height;

    cardPane.style.left = `${clamp(left, MARGIN_PX, screenWidth - width - MARGIN_PX)}px`;
    cardPane.style.top = `${clamp(top, MARGIN_PX, screenHeight - height - MARGIN_PX)}px`;
  }

  map.addEventListener("click", (event) => {
    const onRoom = (event.target as Element).closest("[data-room-id]");
    if (!onRoom && anchorId !== null && isMapFirst()) onDismiss();
  });

  // Also fires when the layout changes, once the new layout has been applied.
  new ResizeObserver(reposition).observe(map);

  return {
    body,
    reposition,
    anchorTo(roomId) {
      anchorId = roomId;
      cardPane.toggleAttribute("data-open", roomId !== null);
      reposition();
    },
  };
}
