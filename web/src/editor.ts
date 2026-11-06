// The YAML editor. Knows nothing about rendering; it reports text changes.
import { yaml } from "@codemirror/lang-yaml";
import { basicSetup, EditorView } from "codemirror";

export function createEditor(parent: HTMLElement, doc: string, onChange: (text: string) => void): void {
  new EditorView({
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
}
