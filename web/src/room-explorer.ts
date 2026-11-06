// Clicking around the Dungeon Map: highlights a Room and its legend line
// together, and keeps the selected Room's card showing. Listens on the map's
// container, so it survives each re-render replacing the SVG.
import type { DungeonData } from "./dungeon";
import { renderEmptyRoomCard, renderRoomCard } from "./room-card";

export type RoomExplorer = {
  /** Call after the map's SVG is replaced with a drawing of this Dungeon. */
  show(dungeon: DungeonData): void;
  /** Deselects the Room, closing its card. */
  clear(): void;
};

export function createRoomExplorer(
  map: HTMLElement,
  cardHost: HTMLElement,
  onCardPainted: (roomId: string | null) => void,
): RoomExplorer {
  let dungeon: DungeonData | null = null;
  let selectedId: string | null = null;

  const hooksFor = (roomId: string) => map.querySelectorAll(`[data-room-id="${CSS.escape(roomId)}"]`);

  const roomIdAt = (target: EventTarget | null) =>
    (target as Element).closest<SVGElement>("[data-room-id]")?.dataset.roomId;

  function setHighlight(target: EventTarget | null, on: boolean) {
    const roomId = roomIdAt(target);
    if (roomId !== undefined) hooksFor(roomId).forEach((hook) => hook.classList.toggle("highlighted", on));
  }

  function paintSelection() {
    map.querySelectorAll(".selected").forEach((hook) => hook.classList.remove("selected"));
    if (selectedId !== null) hooksFor(selectedId).forEach((hook) => hook.classList.add("selected"));

    const room = dungeon?.rooms.find((r) => r.id === selectedId);
    if (dungeon && room) cardHost.replaceChildren(renderRoomCard(dungeon, room, select));
    else cardHost.replaceChildren(renderEmptyRoomCard());
    onCardPainted(room ? room.id : null);
  }

  function select(roomId: string) {
    selectedId = roomId;
    paintSelection();
    cardHost.scrollTop = 0;
  }

  map.addEventListener("mouseover", (event) => setHighlight(event.target, true));
  map.addEventListener("mouseout", (event) => setHighlight(event.target, false));
  map.addEventListener("click", (event) => {
    const roomId = roomIdAt(event.target);
    if (roomId !== undefined) select(roomId);
  });

  paintSelection();

  return {
    show(next) {
      dungeon = next;
      if (!next.rooms.some((r) => r.id === selectedId)) selectedId = null;
      paintSelection();
    },
    clear() {
      selectedId = null;
      paintSelection();
    },
  };
}
