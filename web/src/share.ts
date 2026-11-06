// The Share button and the line beside it, which also reports links that couldn't be opened.
import { encodePermalink, PermalinkError } from "./permalink";

// Discord's message cap; the tightest limit a link is likely to meet.
const LONG_LINK_CHARS = 2000;

export type ShareControl = {
  showBadLink(message: string): void;
  clear(): void;
};

export function createShareControl(parent: HTMLElement, currentYaml: () => string): ShareControl {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Share";
  button.dataset.testid = "share-button";

  const status = document.createElement("span");
  status.className = "share-status";
  status.setAttribute("role", "status");
  status.dataset.testid = "share-status";

  // Only shown when the clipboard refuses, so the link can still be copied by hand.
  const manualCopy = document.createElement("input");
  manualCopy.className = "permalink-field";
  manualCopy.readOnly = true;
  manualCopy.hidden = true;
  manualCopy.setAttribute("aria-label", "Permalink");
  manualCopy.dataset.testid = "permalink-field";

  parent.append(button, status, manualCopy);

  function report(state: string, message: string) {
    status.dataset.state = state;
    status.textContent = message;
  }

  function clear() {
    delete status.dataset.state;
    delete status.dataset.linkLength;
    delete status.dataset.tooLong;
    status.textContent = "";
    manualCopy.hidden = true;
  }

  async function share() {
    clear();
    let fragment: string;
    try {
      fragment = await encodePermalink(currentYaml());
    } catch (error) {
      report("refused", error instanceof PermalinkError ? error.message : "Couldn't make a link for this Dungeon.");
      return;
    }

    const url = new URL(location.href);
    url.hash = fragment;
    const link = url.href;
    status.dataset.linkLength = String(link.length);
    const tooLong = link.length > LONG_LINK_CHARS;
    if (tooLong) status.dataset.tooLong = "true";
    const lengthNote = tooLong ? ` Too long for Discord, which allows ${LONG_LINK_CHARS} in a message.` : "";

    try {
      await navigator.clipboard.writeText(link);
      report("copied", `Link copied: ${link.length} characters.${lengthNote}`);
    } catch {
      report("copy-failed", `Couldn't reach the clipboard. Copy this ${link.length}-character link:${lengthNote}`);
      manualCopy.value = link;
      manualCopy.hidden = false;
      manualCopy.select();
    }
  }

  button.addEventListener("click", () => void share());

  return {
    showBadLink(message) {
      clear();
      report("bad-link", message);
    },
    clear,
  };
}
