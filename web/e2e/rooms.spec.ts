import { expect, test, type Page } from "@playwright/test";

const map = (page: Page) => page.getByTestId("dungeon-map");
const room = (page: Page, id: string) => map(page).locator(`.room[data-room-id="${id}"]`);
const legendLine = (page: Page, id: string) => map(page).locator(`text[data-room-id="${id}"]`);
const card = (page: Page) => page.getByTestId("room-card");
const cardTitle = (page: Page) => card(page).getByRole("heading", { level: 2 });

const WHITE = "rgb(255, 255, 255)";
const BLACK = "rgb(0, 0, 0)";

async function expectHighlighted(page: Page, id: string, highlighted: boolean) {
  const floor = expect(room(page, id).locator("rect"));
  const line = expect(legendLine(page, id));
  if (highlighted) {
    await floor.not.toHaveCSS("fill", WHITE);
    await line.not.toHaveCSS("fill", BLACK);
  } else {
    await floor.toHaveCSS("fill", WHITE);
    await line.toHaveCSS("fill", BLACK);
  }
}

async function replaceYaml(page: Page, text: string) {
  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText(text);
}

const ONE_WAY = `name: One-way
rooms:
  - id: hall
    name: Hall
    entrance: true
    exits:
      - { target: pit, direction: e, type: secret, state: locked, dc: 14 }
  - id: pit
    name: Pit
`;

test.beforeEach(async ({ page }) => {
  await page.goto("./");
  await expect(map(page).locator(".room")).toHaveCount(5);
});

test("hovering a Room highlights it and its legend line", async ({ page }) => {
  await expectHighlighted(page, "throne_room", false);

  await room(page, "throne_room").hover();
  await expectHighlighted(page, "throne_room", true);
  await expectHighlighted(page, "entrance", false);

  await card(page).hover();
  await expectHighlighted(page, "throne_room", false);
});

test("hovering a legend line highlights it and its Room", async ({ page }) => {
  await legendLine(page, "treasure_room").hover();
  await expectHighlighted(page, "treasure_room", true);

  await card(page).hover();
  await expectHighlighted(page, "treasure_room", false);
});

test("clicking a Room shows its card", async ({ page }) => {
  await room(page, "entrance").click();

  await expect(cardTitle(page)).toContainText("1");
  await expect(cardTitle(page)).toContainText("Grand Hall");
  await expect(card(page)).toContainText("entrance");
  for (const chip of ["entrance", "large", "stone floor", "dim"]) {
    await expect(card(page).getByTestId("room-chips")).toContainText(chip);
  }
  await expect(card(page)).toContainText("A cavernous chamber with a vaulted ceiling.");

  const exits = card(page).getByTestId("room-exits").getByRole("listitem");
  await expect(exits).toHaveCount(2);
  for (const part of ["N", "2. North Passage", "archway", "open"]) {
    await expect(exits.nth(0)).toContainText(part);
  }
  for (const part of ["E", "4. Storage Chamber", "wooden", "closed", "DC 10"]) {
    await expect(exits.nth(1)).toContainText(part);
  }
  await expect(card(page).getByTestId("room-doors-in")).toHaveCount(0);
});

test("exit links switch the card, and the selected Room follows", async ({ page }) => {
  await room(page, "entrance").click();

  await card(page).getByRole("button", { name: "2. North Passage" }).click();
  await expect(cardTitle(page)).toContainText("North Passage");

  await expect(room(page, "corridor_north").locator("rect")).not.toHaveCSS("fill", WHITE);
  await expect(room(page, "entrance").locator("rect")).toHaveCSS("fill", WHITE);
});

test("clicking a legend line shows that Room's card", async ({ page }) => {
  await legendLine(page, "escape_tunnel").click();

  await expect(cardTitle(page)).toContainText("Hidden Escape Route");
});

test("the card lists One-way Doors leading in, linking back", async ({ page }) => {
  await replaceYaml(page, ONE_WAY);
  await expect(map(page).locator(".room")).toHaveCount(2);

  await room(page, "pit").click();

  const doorsIn = card(page).getByTestId("room-doors-in").getByRole("listitem");
  await expect(doorsIn).toHaveCount(1);
  for (const part of ["1. Hall", "secret", "locked", "DC 14"]) {
    await expect(doorsIn).toContainText(part);
  }
  await expect(card(page).getByTestId("room-exits")).toHaveCount(0);

  await card(page).getByRole("button", { name: "1. Hall" }).click();
  await expect(cardTitle(page)).toContainText("Hall");
  await expect(card(page).getByTestId("room-doors-in")).toHaveCount(0);
});

test("the card follows edits, and closes when its Room goes away", async ({ page }) => {
  await room(page, "throne_room").click();
  await expect(cardTitle(page)).toContainText("Goblin Throne");

  await page.locator(".cm-line", { hasText: 'name: "Goblin Throne"' }).click();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.type(" Annex");

  await expect(cardTitle(page)).toContainText("Goblin Throne Annex");
  await expect(room(page, "throne_room").locator("rect")).not.toHaveCSS("fill", WHITE);

  await replaceYaml(page, ONE_WAY);
  await expect(map(page).locator(".room")).toHaveCount(2);
  await expect(cardTitle(page)).toHaveCount(0);
});

test("markup in a Dungeon's strings stays inert in the map and the card", async ({ page }) => {
  await replaceYaml(
    page,
    `name: Hostile
rooms:
  - id: '"><img src=x onerror=window.pwned=1>'
    name: "<img src=x onerror=window.pwned=1>"
    description: "<img src=x onerror=window.pwned=1>"
    entrance: true
`,
  );
  await expect(map(page).locator(".room")).toHaveCount(1);

  await map(page).locator(".room").click();

  await expect(cardTitle(page)).toContainText("<img src=x");
  await expect(page.locator("#app img")).toHaveCount(0);
  expect(await page.evaluate(() => "pwned" in window)).toBe(false);
});
