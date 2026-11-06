// Map-first's slide-out for the YAML: the button that opens it, with its Problem
// badge, and the header that closes it. The editor pane itself stays in place in
// the DOM, so its text and undo history outlive any change of layout.

export type Drawer = {
  showProblemCount(count: number): void;
};

export function createDrawer(toolbar: HTMLElement, editorPane: HTMLElement): Drawer {
  const badge = document.createElement("span");
  badge.className = "problem-badge";
  badge.dataset.testid = "problem-count";
  badge.hidden = true;

  const open = document.createElement("button");
  open.type = "button";
  open.className = "drawer-button";
  open.setAttribute("aria-expanded", "false");
  open.append("Edit YAML", badge);

  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "Close";
  close.setAttribute("aria-label", "Close YAML");

  const title = document.createElement("strong");
  title.textContent = "YAML";

  const header = document.createElement("div");
  header.className = "drawer-header";
  header.append(title, close);

  function setOpen(isOpen: boolean) {
    editorPane.toggleAttribute("data-open", isOpen);
    open.setAttribute("aria-expanded", String(isOpen));
  }
  open.addEventListener("click", () => setOpen(true));
  close.addEventListener("click", () => setOpen(false));

  toolbar.prepend(open);
  editorPane.prepend(header);

  return {
    showProblemCount(count) {
      badge.textContent = String(count);
      badge.hidden = count === 0;
    },
  };
}
