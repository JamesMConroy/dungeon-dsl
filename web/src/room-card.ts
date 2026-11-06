// Builds a Room's card from the Dungeon's data. Knows nothing about where the
// card is shown. Everything from the YAML goes in as text, never as markup,
// because a Permalink can carry YAML written by anyone.
import type { DoorData, DungeonData, RoomData } from "./dungeon";

function element<K extends keyof HTMLElementTagNameMap>(tag: K, className: string, text?: string) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

const doorSummary = (door: DoorData) =>
  [door.type, door.state, door.dc === null ? null : `DC ${door.dc}`].filter(Boolean).join(", ");

const oneWayDoorsIn = (dungeon: DungeonData, room: RoomData) =>
  dungeon.rooms.flatMap((source) =>
    room.exits.some((door) => door.target === source.id)
      ? []
      : source.exits.filter((door) => door.target === room.id).map((door) => ({ source, door })),
  );

export function renderEmptyRoomCard(): HTMLElement {
  return element("p", "room-card-empty", "Click a Room or a legend line to see its card.");
}

export function renderRoomCard(
  dungeon: DungeonData,
  room: RoomData,
  onRoomLink: (roomId: string) => void,
): HTMLElement {
  const number = (roomId: string) => dungeon.rooms.findIndex((r) => r.id === roomId) + 1;

  function roomLink(roomId: string): HTMLElement {
    const linked = dungeon.rooms.find((r) => r.id === roomId);
    if (!linked) return element("span", "", roomId);
    const link = element("button", "room-link", `${number(roomId)}. ${linked.name}`);
    link.type = "button";
    link.addEventListener("click", () => onRoomLink(roomId));
    return link;
  }

  function doorItem(lead: string, roomId: string, door: DoorData): HTMLElement {
    const item = element("li", "");
    item.append(`${lead} `, roomLink(roomId), " ", element("span", "door-summary", doorSummary(door)));
    return item;
  }

  function doorList(title: string, testId: string, items: HTMLElement[]): HTMLElement[] {
    if (items.length === 0) return [];
    const list = element("ul", "door-list");
    list.dataset.testid = testId;
    list.append(...items);
    return [element("h3", "", title), list];
  }

  const card = element("article", "room-details");

  const title = element("h2", "");
  title.append(element("span", "room-number", String(number(room.id))), room.name);

  const chips = element("div", "chips");
  chips.dataset.testid = "room-chips";
  if (room.entrance) chips.append(element("span", "chip chip-entrance", "entrance"));
  for (const value of [room.size, room.terrain.replaceAll("_", " "), room.light]) {
    if (value) chips.append(element("span", "chip", value));
  }

  card.append(title, element("div", "room-id", room.id), chips);
  if (room.description) card.append(element("p", "read-aloud", room.description));
  card.append(
    ...doorList(
      "Exits",
      "room-exits",
      room.exits.map((door) => doorItem(`${door.direction.toUpperCase()} →`, door.target, door)),
    ),
    ...doorList(
      "One-way in",
      "room-doors-in",
      oneWayDoorsIn(dungeon, room).map(({ source, door }) => doorItem("from", source.id, door)),
    ),
  );
  return card;
}
