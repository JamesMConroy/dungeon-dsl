// Page-side handle on the render worker. Debounces edits, keeps one render in
// flight at a time, drops results for anything but the newest text, and replaces
// a stuck worker. Callers see only RenderEvents, never the worker.
import type { RenderRequest, Result, WorkerMessage } from "./render-protocol";

export type RenderEvent =
  | { kind: "loading" }
  | { kind: "rendered"; svg: string; ms: number; result: Result }
  | { kind: "invalid"; result: Result }
  | { kind: "render-failed"; message: string }
  | { kind: "timed-out" }
  | { kind: "boot-failed"; message: string };

export type RenderClient = {
  /** Asks for a render of this text; supersedes any earlier request. */
  request(text: string): void;
};

export type RenderClientOptions = {
  onEvent(event: RenderEvent): void;
  debounceMs?: number;
  watchdogMs?: number;
  spawnWorker?: () => Worker;
};

const spawnRenderWorker = () => new Worker(new URL("./render.worker.ts", import.meta.url), { type: "module" });

function toEvent(message: Extract<WorkerMessage, { seq: number }>): RenderEvent {
  switch (message.type) {
    case "rendered":
      return { kind: "rendered", svg: message.svg, ms: message.ms, result: message.result };
    case "invalid":
      return { kind: "invalid", result: message.result };
    case "render-failed":
      return { kind: "render-failed", message: message.message };
  }
}

export function createRenderClient({
  onEvent,
  debounceMs = 150,
  watchdogMs = 2000,
  spawnWorker = spawnRenderWorker,
}: RenderClientOptions): RenderClient {
  let worker: Worker;
  let ready = false;
  let latestSeq = 0;
  let waiting: RenderRequest | null = null;
  let inFlightSeq: number | null = null;
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let watchdogTimer: ReturnType<typeof setTimeout> | undefined;

  function spawn() {
    ready = false;
    inFlightSeq = null;
    onEvent({ kind: "loading" });
    const spawned = spawnWorker();
    worker = spawned;
    spawned.onmessage = (event: MessageEvent<WorkerMessage>) => handleMessage(event.data);
    spawned.onerror = (event) => {
      if (ready) replaceWorker({ kind: "render-failed", message: event.message });
      else onEvent({ kind: "boot-failed", message: event.message });
    };
  }

  /**
   * Replaces a dead or stuck worker. The text it choked on is not retried, as
   * it would only choke the new worker too; a newer edit is what renders next.
   */
  function replaceWorker(outcome: RenderEvent) {
    clearTimeout(watchdogTimer);
    worker.onmessage = worker.onerror = null;
    worker.terminate();
    spawn();
    // After spawn's "loading", so the outcome is what the page ends up showing.
    onEvent(outcome);
  }

  function sendWaiting() {
    if (!ready || inFlightSeq !== null || !waiting) return;
    inFlightSeq = waiting.seq;
    worker.postMessage(waiting);
    waiting = null;
    watchdogTimer = setTimeout(() => replaceWorker({ kind: "timed-out" }), watchdogMs);
  }

  function handleMessage(message: WorkerMessage) {
    switch (message.type) {
      case "ready":
        ready = true;
        sendWaiting();
        return;
      case "boot-failed":
        onEvent({ kind: "boot-failed", message: message.message });
        return;
      case "rendered":
      case "invalid":
      case "render-failed":
        clearTimeout(watchdogTimer);
        inFlightSeq = null;
        if (message.seq === latestSeq) onEvent(toEvent(message));
        sendWaiting();
    }
  }

  spawn();

  return {
    request(text) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        waiting = { seq: ++latestSeq, text };
        sendWaiting();
      }, debounceMs);
    },
  };
}
