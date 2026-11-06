// The YAML editor. Knows nothing about rendering; it reports text changes and
// shows the Problems it's handed.
import { yaml } from "@codemirror/lang-yaml";
import { setDiagnostics, type Diagnostic } from "@codemirror/lint";
import type { Text } from "@codemirror/state";
import { basicSetup, EditorView } from "codemirror";
import type { Position, Problem } from "./render-protocol";

export type EditorHandle = {
  /** Underlines these Problems, replacing any shown before. */
  showProblems(problems: Problem[]): void;
  /** Moves the cursor to the Problem and scrolls it into view. */
  revealProblem(problem: Problem): void;
};

/** Document offset of a Problem position. Clamped, as the text may have moved on since it was checked. */
function offsetOf(doc: Text, { line, col }: Position): number {
  if (line > doc.lines) return doc.length;
  const { from, text } = doc.line(line);
  // Columns count code points, the editor counts UTF-16 units.
  return from + Array.from(text).slice(0, col - 1).join("").length;
}

function rangeOf(doc: Text, problem: Problem): { from: number; to: number } {
  if (!problem.span) return { from: 0, to: Math.min(1, doc.length) };
  const from = offsetOf(doc, problem.span.start);
  const to = offsetOf(doc, problem.span.end);
  if (to > from) return { from, to };
  // Where the parser gave up has no width, but an underline needs some.
  const line = doc.lineAt(from);
  if (from < line.to) return { from, to: from + 1 };
  return { from: Math.max(line.from, from - 1), to: from };
}

export function createEditor(parent: HTMLElement, doc: string, onChange: (text: string) => void): EditorHandle {
  const view = new EditorView({
    parent,
    doc,
    extensions: [
      basicSetup,
      yaml(),
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) onChange(update.state.doc.toString());
      }),
    ],
  });

  return {
    showProblems(problems) {
      const diagnostics = problems.map(
        (problem): Diagnostic => ({
          ...rangeOf(view.state.doc, problem),
          severity: problem.severity,
          message: problem.message,
          source: problem.code,
        }),
      );
      view.dispatch(setDiagnostics(view.state, diagnostics));
    },
    revealProblem(problem) {
      const { from } = rangeOf(view.state.doc, problem);
      view.dispatch({ selection: { anchor: from }, effects: EditorView.scrollIntoView(from, { y: "center" }) });
      view.focus();
    },
  };
}
