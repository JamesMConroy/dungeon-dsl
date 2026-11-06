// The clickable list of Problems. Knows nothing of the editor; it reports which
// Problem was picked.
import type { Problem } from "./render-protocol";

export type ProblemList = {
  show(problems: Problem[]): void;
};

export function createProblemList(parent: HTMLElement, onSelect: (problem: Problem) => void): ProblemList {
  const list = document.createElement("ul");
  list.className = "problem-list";
  list.setAttribute("aria-label", "Problems");
  list.hidden = true;
  parent.append(list);

  function row(problem: Problem): HTMLLIElement {
    const line = document.createElement("span");
    line.className = "problem-line";
    line.textContent = problem.span ? `Line ${problem.span.start.line}: ` : "";

    const button = document.createElement("button");
    button.type = "button";
    button.dataset.testid = "problem";
    button.dataset.severity = problem.severity;
    button.dataset.code = problem.code;
    button.append(line, problem.message);
    button.addEventListener("click", () => onSelect(problem));

    const item = document.createElement("li");
    item.append(button);
    return item;
  }

  return {
    show(problems) {
      list.replaceChildren(...problems.map(row));
      list.hidden = problems.length === 0;
    },
  };
}
