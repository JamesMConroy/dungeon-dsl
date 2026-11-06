import { expect, test, type Page } from "@playwright/test";

const offered = (page: Page) => page.locator(".cm-tooltip-autocomplete .cm-completionLabel");

/** Puts `doc` in the editor with the cursor at its end, then types `typed` key by key. */
async function typeInto(page: Page, doc: string, typed: string) {
  await page.goto("./");
  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  if (doc) await page.keyboard.insertText(doc);
  await page.keyboard.type(typed);
}

/** Takes the selected option. The list ignores Enter for its first moments, against accidental picks. */
async function accept(page: Page) {
  await page.waitForTimeout(150);
  await page.keyboard.press("Enter");
}

async function expectOffered(page: Page, labels: string[]) {
  await expect.poll(async () => (await offered(page).allTextContents()).sort()).toEqual([...labels].sort());
}

const room = "rooms:\n  - id: a\n    ";
const door = `${room}exits:\n      - target: b\n        `;

for (const [where, doc, typed, labels] of [
  ["a Room's size", room, "size: ", ["tiny", "small", "medium", "large", "vast"]],
  ["a Room's light", room, "light: ", ["dark", "dim", "bright"]],
  ["a Door's direction", door, "direction: ", ["n", "s", "e", "w", "ne", "nw", "se", "sw"]],
  ["a Door's type", door, "type: ", ["wooden", "stone", "iron", "secret", "archway"]],
  ["a Door's state", door, "state: ", ["open", "closed", "locked", "barred"]],
  ["a Door written inline", `${room}exits:\n      - {target: b, `, "state: ", ["open", "closed", "locked", "barred"]],
  ["a list of inline Doors", room, "exits: [{target: b, state: ", ["open", "closed", "locked", "barred"]],
  ["a quoted value", room, 'light: "', ["dark", "dim", "bright"]],
] as const) {
  test(`typing ${where} offers exactly the allowed values`, async ({ page }) => {
    await typeInto(page, doc, typed);
    await expectOffered(page, [...labels]);
  });
}

test("a value is offered with Rooms below it too", async ({ page }) => {
  await typeInto(page, "rooms:\n  - id: a\n  - id: b\n", "");
  await page.locator(".cm-line", { hasText: "id: a" }).click();
  await page.keyboard.press("End");
  await page.keyboard.press("Enter");
  await page.keyboard.type("light: ");
  await expectOffered(page, ["dark", "dim", "bright"]);
});

test("a partly typed value narrows the list, and picking one completes it", async ({ page }) => {
  await typeInto(page, room, "size: me");
  await expectOffered(page, ["medium"]);
  await accept(page);
  await expect(page.locator(".cm-activeLine")).toHaveText("    size: medium");
});

for (const [where, doc, typed, label] of [
  ["the Dungeon", "", "roo", "rooms"],
  ["a Room", room, "terr", "terrain"],
  ["a Room's first line", "rooms:\n  - ", "terr", "terrain"],
  ["a Door", door, "dire", "direction"],
  ["a Door's first line", `${room}exits:\n      - `, "dire", "direction"],
  ["a Door written inline", `${room}exits:\n      - {`, "dire", "direction"],
] as const) {
  test(`typing a key in ${where} offers it`, async ({ page }) => {
    await typeInto(page, doc, typed);
    await expectOffered(page, [label]);
  });
}

test("asking for keys on a blank line offers the ones the Room can still take", async ({ page }) => {
  await typeInto(page, room, "");
  await page.keyboard.press("Control+Space");
  await expectOffered(page, ["name", "description", "size", "terrain", "light", "entrance", "isolation", "exits"]);
});

test("a key already in the mapping isn't offered again", async ({ page }) => {
  await typeInto(page, "name: x\n", "nam");
  await page.waitForTimeout(300);
  await expect(offered(page)).toHaveCount(0);
});

test("picking a key goes straight on to its allowed values", async ({ page }) => {
  await typeInto(page, room, "ligh");
  await expectOffered(page, ["light"]);
  await accept(page);
  await expect(page.locator(".cm-activeLine")).toHaveText("    light: ");
  await expectOffered(page, ["dark", "dim", "bright"]);
});

test("a finished value leaves Enter to start a new line", async ({ page }) => {
  await typeInto(page, room, "size: large");
  await page.waitForTimeout(300);
  await page.keyboard.press("Enter");
  await expect(offered(page)).toHaveCount(0);
  await expect(page.locator(".cm-line", { hasText: "size: large" })).toBeVisible();
  await expect(page.locator(".cm-activeLine")).not.toContainText("large");
});

for (const [where, doc, typed] of [
  ["free text", room, "terrain: "],
  ["a Door's target", door, "target: "],
  ["a comment", room, "# size: "],
  ["a block of text", `${room}description: |\n      `, "size: "],
] as const) {
  test(`nothing is offered in ${where}`, async ({ page }) => {
    await typeInto(page, doc, typed);
    // Give the list time to open if it was going to.
    await page.waitForTimeout(300);
    await expect(offered(page)).toHaveCount(0);
  });
}
