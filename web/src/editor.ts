// The YAML editor. Knows nothing about rendering; it reports text changes.
import { yaml } from "@codemirror/lang-yaml";
import { basicSetup, EditorView } from "codemirror";

export type Editor = {
  text(): string;
  /** Replaces the whole document; reports through onChange like any other edit. */
  setText(text: string): void;
};

export function createEditor(parent: HTMLElement, doc: string, onChange: (text: string) => void): Editor {
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
    text: () => view.state.doc.toString(),
    setText(text) {
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: text } });
    },
  };
}
