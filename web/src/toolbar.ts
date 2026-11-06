// The Playground's toolbar: the example picker and the downloads. It holds no
// document of its own, only the last good map, which outlives a broken edit.
import type { Example } from "./examples";

export type ToolbarOptions = {
  examples: Example[];
  onLoadExample(example: Example): void;
  currentYaml(): string;
};

export type Toolbar = {
  /** Records the newest successfully rendered Dungeon Map, for Download SVG. */
  setLastGoodMap(svg: string): void;
};

// Long enough for any browser to have started reading the blob.
const REVOKE_DOWNLOAD_URL_AFTER_MS = 10_000;

function saveFile(filename: string, type: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), REVOKE_DOWNLOAD_URL_AFTER_MS);
}

function createButton(label: string, onClick: () => void) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

export function createToolbar(
  parent: HTMLElement,
  { examples, onLoadExample, currentYaml }: ToolbarOptions,
): Toolbar {
  const picker = document.createElement("select");
  picker.setAttribute("aria-label", "Load example");
  picker.add(new Option("Examples…", "", true, true));
  picker.options[0].disabled = true;
  for (const example of examples) picker.add(new Option(example.name));
  picker.addEventListener("change", () => {
    const chosen = examples.find((example) => example.name === picker.value);
    // Back to the placeholder, so picking the same example again reloads it.
    picker.selectedIndex = 0;
    if (chosen) onLoadExample(chosen);
  });

  let lastGoodMap = "";
  const downloadSvg = createButton("Download SVG", () => saveFile("dungeon.svg", "image/svg+xml", lastGoodMap));
  downloadSvg.disabled = true;
  const downloadYaml = createButton("Download YAML", () => saveFile("dungeon.yaml", "application/yaml", currentYaml()));

  parent.append(picker, downloadSvg, downloadYaml);

  return {
    setLastGoodMap(svg) {
      lastGoodMap = svg;
      downloadSvg.disabled = false;
    },
  };
}
