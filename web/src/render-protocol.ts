// Messages between the render client (page) and the render worker, and the
// JSON form of Python's load() Result that they carry.

export type Position = { line: number; col: number };
export type Span = { start: Position; end: Position };

/** Lines and columns are 1-based and columns count code points; the end is exclusive. */
export type Problem = {
  severity: "error" | "warning";
  code: string;
  message: string;
  loc: (string | number)[];
  span: Span | null;
};

/** `dungeon` is the plain JSON of the Dungeon model, null whenever there's an Error. */
export type Result = {
  dungeon: Record<string, unknown> | null;
  problems: Problem[];
};

export type RenderRequest = { seq: number; text: string };

export type WorkerMessage =
  | { type: "ready" }
  | { type: "boot-failed"; message: string }
  | { type: "rendered"; seq: number; svg: string; ms: number; result: Result }
  | { type: "invalid"; seq: number; result: Result }
  | { type: "render-failed"; seq: number; message: string };
