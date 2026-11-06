// The Permalink codec: a Dungeon's YAML text <-> a URL fragment, `#1.<base64url(deflate-raw(yaml))>`.
// Compressed output can differ between browsers, so never use a Permalink string
// as an identifier or cache key.

/** Comfortably above any real Dungeon; a small link can inflate to far more (deflate reaches ~1032:1). */
export const MAX_YAML_BYTES = 1 << 20;

const INPUT_SLICE_BYTES = 1024;

export type PermalinkRejection = "unsupported-version" | "malformed" | "too-large";

export class PermalinkError extends Error {
  constructor(
    readonly reason: PermalinkRejection,
    message: string,
  ) {
    super(message);
    this.name = "PermalinkError";
  }
}

const malformed = () => new PermalinkError("malformed", "This link is damaged, so its Dungeon can't be loaded.");
const tooLarge = () => new PermalinkError("too-large", "This Dungeon is over the 1 MB limit for links.");

function toBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(text: string): Uint8Array<ArrayBuffer> {
  // atob accepts the standard alphabet, padding and whitespace; a Permalink has none of them.
  if (!/^[A-Za-z0-9_-]+$/.test(text) || text.length % 4 === 1) throw malformed();
  const binary = atob(text.replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

/** Rejects text past the cap, since no decoder would accept the link. */
export async function encodePermalink(yaml: string): Promise<string> {
  const text = new Blob([yaml]);
  if (text.size > MAX_YAML_BYTES) throw tooLarge();
  const compressed = text.stream().pipeThrough(new CompressionStream("deflate-raw"));
  return `#1.${toBase64Url(new Uint8Array(await new Response(compressed).arrayBuffer()))}`;
}

/**
 * Feeds the compressed bytes in small slices and only on demand: a browser may inflate a
 * whole input chunk at once, and 1 KB of deflate can't expand past about 1 MB, so stopping
 * here bounds the work however the browser buffers.
 */
function sliced(bytes: Uint8Array<ArrayBuffer>): ReadableStream<Uint8Array<ArrayBuffer>> {
  let offset = 0;
  return new ReadableStream(
    {
      pull(controller) {
        if (offset >= bytes.length) return controller.close();
        controller.enqueue(bytes.slice(offset, offset + INPUT_SLICE_BYTES));
        offset += INPUT_SLICE_BYTES;
      },
    },
    { highWaterMark: 0 },
  );
}

async function inflate(compressed: Uint8Array<ArrayBuffer>): Promise<Uint8Array<ArrayBuffer>> {
  const reader = sliced(compressed).pipeThrough(new DecompressionStream("deflate-raw")).getReader();
  const output = new Uint8Array(MAX_YAML_BYTES);
  let length = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return output.slice(0, length);
    if (length + value.length > MAX_YAML_BYTES) {
      void reader.cancel().catch(() => {});
      throw tooLarge();
    }
    output.set(value, length);
    length += value.length;
  }
}

/** Takes `location.hash`. Rejects with a PermalinkError whose message is fit to show the DM. */
export async function decodePermalink(fragment: string): Promise<string> {
  const match = /^#([^.]*)\.(.*)$/s.exec(fragment);
  if (match?.[1] !== "1") {
    throw new PermalinkError(
      "unsupported-version",
      "This link wasn't made by this version of the Playground, so its Dungeon can't be loaded.",
    );
  }

  const compressed = fromBase64Url(match[2]);
  try {
    // ignoreBOM keeps the text verbatim; by default the decoder would drop a leading mark.
    return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(await inflate(compressed));
  } catch (error) {
    throw error instanceof PermalinkError ? error : malformed();
  }
}
