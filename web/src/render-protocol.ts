// Messages between the render client (page) and the render worker.

export type RenderRequest = { seq: number; text: string };

export type WorkerMessage =
  | { type: "ready" }
  | { type: "boot-failed"; message: string }
  | { type: "rendered"; seq: number; svg: string; ms: number }
  | { type: "render-failed"; seq: number; message: string };
