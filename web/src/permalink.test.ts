import { deflateRawSync } from "node:zlib";
import { afterEach, describe, expect, it, vi } from "vitest";
import { bundledExamples } from "./examples";
import { decodePermalink, encodePermalink, MAX_YAML_BYTES, PermalinkError } from "./permalink";

const base64url = (bytes: Buffer) => bytes.toString("base64url");

async function reasonFor(fragment: string) {
  const error = await decodePermalink(fragment).catch((caught: unknown) => caught);
  expect(error).toBeInstanceOf(PermalinkError);
  return (error as PermalinkError).reason;
}

describe("round trip", () => {
  it("finds the bundled examples", () => {
    expect(bundledExamples.map((example) => example.name)).toContain("goblin_warren");
  });

  it.each(bundledExamples)("reproduces $name verbatim", async ({ yaml }) => {
    expect(yaml).not.toBe("");
    expect(await decodePermalink(await encodePermalink(yaml))).toBe(yaml);
  });

  it("keeps non-ASCII text and a leading byte order mark", async () => {
    const yaml = "﻿name: Höhle des Drachen 🐉\n";

    expect(await decodePermalink(await encodePermalink(yaml))).toBe(yaml);
  });

  it("emits the version prefix and only URL-safe characters", async () => {
    expect(await encodePermalink("name: Goblin Warren\n")).toMatch(/^#1\.[A-Za-z0-9_-]+$/);
  });

  it("decodes a link made by another encoder", async () => {
    // Compressed output differs between browsers; every decoder must read them all.
    const fragment = `#1.${base64url(deflateRawSync(Buffer.from("name: Goblin Warren\n"), { level: 1 }))}`;

    expect(await decodePermalink(fragment)).toBe("name: Goblin Warren\n");
  });
});

describe("rejected links", () => {
  it.each(["", "#", "#abc", "#.abc", "#abc.def"])("needs a version prefix: '%s'", async (fragment) => {
    expect(await reasonFor(fragment)).toBe("unsupported-version");
  });

  it.each(["#2.abcd", "#0.abcd", "#01.abcd"])("needs a known version: %s", async (fragment) => {
    expect(await reasonFor(fragment)).toBe("unsupported-version");
  });

  it.each(["#1.", "#1.ab+d", "#1.ab/d", "#1.abc=", "#1.a b", "#1.abcde"])(
    "needs valid base64url: '%s'",
    async (fragment) => {
      expect(await reasonFor(fragment)).toBe("malformed");
    },
  );

  it("needs a deflate stream", async () => {
    expect(await reasonFor(`#1.${base64url(Buffer.from([0xff, 0xff, 0xff, 0xff]))}`)).toBe("malformed");
  });

  it("needs a complete deflate stream", async () => {
    const whole = deflateRawSync(Buffer.from("rooms: []\n".repeat(50)));

    expect(await reasonFor(`#1.${base64url(whole.subarray(0, whole.length - 4))}`)).toBe("malformed");
  });

  it("needs UTF-8 text", async () => {
    expect(await reasonFor(`#1.${base64url(deflateRawSync(Buffer.from([0xc3, 0x28])))}`)).toBe("malformed");
  });
});

describe("size cap", () => {
  const spaces = (bytes: number) => `#1.${base64url(deflateRawSync(Buffer.alloc(bytes, " ")))}`;

  /** Counts what the browser's decompressor produces, however the codec reads it. */
  function countInflatedBytes() {
    const counter = { bytes: 0 };
    const Native = globalThis.DecompressionStream;
    vi.stubGlobal(
      "DecompressionStream",
      class {
        readonly writable: WritableStream<BufferSource>;
        readonly readable: ReadableStream<Uint8Array>;
        constructor(format: CompressionFormat) {
          const native = new Native(format);
          this.writable = native.writable;
          this.readable = native.readable.pipeThrough(
            new TransformStream<Uint8Array, Uint8Array>({
              transform(chunk, controller) {
                counter.bytes += chunk.length;
                controller.enqueue(chunk);
              },
            }),
          );
        }
      },
    );
    return counter;
  }

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("accepts text right at the cap", async () => {
    expect(await decodePermalink(spaces(MAX_YAML_BYTES))).toHaveLength(MAX_YAML_BYTES);
  });

  it("rejects a payload one byte past the cap", async () => {
    expect(await reasonFor(spaces(MAX_YAML_BYTES + 1))).toBe("too-large");
  });

  it("stops inflating a 100 MB bomb soon after the cap", async () => {
    const inflated = countInflatedBytes();

    expect(await reasonFor(spaces(100 * 1024 * 1024))).toBe("too-large");

    expect(inflated.bytes).toBeGreaterThan(MAX_YAML_BYTES);
    expect(inflated.bytes).toBeLessThan(4 * MAX_YAML_BYTES);
  });

  it("won't encode a Dungeon its own decoder would reject", async () => {
    const error = await encodePermalink(" ".repeat(MAX_YAML_BYTES + 1)).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(PermalinkError);
    expect((error as PermalinkError).reason).toBe("too-large");
  });

  it("counts the cap in bytes, not characters", async () => {
    const error = await encodePermalink("é".repeat(MAX_YAML_BYTES / 2 + 1)).catch((caught: unknown) => caught);

    expect((error as PermalinkError).reason).toBe("too-large");
  });
});
