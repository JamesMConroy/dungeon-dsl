import { randomBytes } from "node:crypto";
import { deflateRawSync } from "node:zlib";
import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";
import { encodePermalink } from "../src/permalink";

const goblinWarren = readFileSync(new URL("../../examples/goblin_warren.yaml", import.meta.url), "utf8");

const dungeonMap = (page: Page) => page.getByTestId("dungeon-map").locator("svg");
const editor = (page: Page) => page.locator(".cm-content");
const status = (page: Page) => page.getByTestId("share-status");

const annexedWarren = goblinWarren.replace('name: "Grand Hall"', 'name: "Grand Hall Annex"');

test("Share then reload with the link reproduces the Dungeon", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("./");
  await expect(dungeonMap(page)).toContainText("Grand Hall");

  await page.locator(".cm-line", { hasText: 'name: "Grand Hall"' }).click();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.type(" Annex");
  await page.getByTestId("share-button").click();

  await expect(status(page)).toHaveAttribute("data-state", "copied");
  const link = await page.evaluate(() => navigator.clipboard.readText());
  expect(link).toMatch(/\/dungeon-dsl\/#1\.[A-Za-z0-9_-]+$/);
  await expect(status(page)).toHaveAttribute("data-link-length", String(link.length));
  await expect(status(page)).not.toHaveAttribute("data-too-long", "true");

  await page.goto(link);
  await page.reload();

  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");
  await expect(editor(page)).toContainText('name: "Grand Hall Annex"');
  await expect(status(page)).not.toHaveAttribute("data-state", "bad-link");
});

test("opening a Permalink loads its Dungeon instead of the default example", async ({ page }) => {
  await page.goto(`./${await encodePermalink(annexedWarren)}`);

  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");
  await expect(editor(page)).toContainText('name: "Grand Hall Annex"');
});

test("pasting a Permalink into an open tab loads its Dungeon", async ({ page }) => {
  await page.goto("./");
  await expect(dungeonMap(page)).toContainText("Grand Hall");

  // Only the fragment differs, so the browser doesn't reload the page.
  await page.goto(`./${await encodePermalink(annexedWarren)}`);

  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");
  await expect(editor(page)).toContainText('name: "Grand Hall Annex"');
});

const hostile = `#1.${deflateRawSync(Buffer.alloc(100 * 1024 * 1024, " ")).toString("base64url")}`;

for (const [name, fragment] of [
  ["no version", "#abc"],
  ["an unknown version", "#2.abcd"],
  ["malformed base64", "#1.a!b"],
  ["a decompression bomb", hostile],
]) {
  test(`a Permalink with ${name} shows a message and falls back to the default example`, async ({ page }) => {
    await page.goto(`./${fragment}`);

    await expect(status(page)).toHaveAttribute("data-state", "bad-link");
    await expect(status(page)).not.toBeEmpty();
    await expect(dungeonMap(page)).toContainText("Grand Hall");
    await expect(editor(page)).toContainText('name: "Grand Hall"');
  });
}

test("a bad Permalink pasted into an open tab keeps the DM's work", async ({ page }) => {
  await page.goto(`./${await encodePermalink(annexedWarren)}`);
  await expect(dungeonMap(page)).toContainText("Grand Hall Annex");

  await page.goto("./#2.abcd");

  await expect(status(page)).toHaveAttribute("data-state", "bad-link");
  await expect(editor(page)).toContainText('name: "Grand Hall Annex"');
});

test("loading an example dismisses a bad Permalink's message", async ({ page }) => {
  await page.goto("./#2.abcd");
  await expect(status(page)).toHaveAttribute("data-state", "bad-link");

  await page.getByLabel("Load example").selectOption("size_test");

  await expect(status(page)).toBeEmpty();
  await expect(page).toHaveURL(/\/dungeon-dsl\/$/);
});

test("Share warns when the link is too long for chat apps",async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  // Hex digits barely compress, which keeps the link long.
  const padded = `${goblinWarren}# ${randomBytes(2500).toString("hex")}\n`;
  await page.goto(`./${await encodePermalink(padded)}`);
  await expect(editor(page)).toContainText('name: "Grand Hall"');

  await page.getByTestId("share-button").click();

  await expect(status(page)).toHaveAttribute("data-state", "copied");
  await expect(status(page)).toHaveAttribute("data-too-long", "true");
  const link = await page.evaluate(() => navigator.clipboard.readText());
  expect(link.length).toBeGreaterThan(2000);
});

test("Share still offers the link when the clipboard refuses", async ({ page }) => {
  await page.addInitScript(() => {
    navigator.clipboard.writeText = () => Promise.reject(new DOMException("denied", "NotAllowedError"));
  });
  await page.goto("./");

  await page.getByTestId("share-button").click();

  await expect(status(page)).toHaveAttribute("data-state", "copy-failed");
  await expect(page.getByTestId("share-link")).toHaveValue(/#1\.[A-Za-z0-9_-]+$/);
});
