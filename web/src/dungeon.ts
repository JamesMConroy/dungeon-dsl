// The part of a Dungeon's data the Room card reads, from the worker's JSON dump of
// the models. The dump also carries `level`, `theme` and each Room's `isolation`,
// which nothing here reads.

export type DoorData = {
  target: string;
  direction: "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw";
  type: "wooden" | "stone" | "iron" | "secret" | "archway";
  state: "open" | "closed" | "locked" | "barred";
  dc: number | null;
};

export type RoomData = {
  id: string;
  name: string;
  description: string;
  size: "tiny" | "small" | "medium" | "large" | "vast";
  terrain: string;
  light: "dark" | "dim" | "bright";
  entrance: boolean;
  exits: DoorData[];
};

export type DungeonData = {
  name: string;
  rooms: RoomData[];
};
