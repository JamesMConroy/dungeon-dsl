// A Dungeon's data as the worker delivers it: the models, dumped to JSON.

export type DoorData = {
  target: string;
  direction: string;
  type: string;
  state: string;
  dc: number | null;
};

export type RoomData = {
  id: string;
  name: string;
  description: string;
  size: string;
  terrain: string;
  light: string;
  entrance: boolean;
  exits: DoorData[];
};

export type DungeonData = {
  name: string;
  rooms: RoomData[];
};
