// Autocomplete for the YAML editor, driven by the JSON Schema generated from
// the models, so a value added to a model appears here with no change to this file.
import {
  insertCompletionText,
  pickedCompletion,
  startCompletion,
  type Completion,
  type CompletionContext,
  type CompletionResult,
} from "@codemirror/autocomplete";
import { yamlLanguage } from "@codemirror/lang-yaml";
import type { EditorView } from "@codemirror/view";
import type { SyntaxNode } from "@lezer/common";
import dungeonSchema from "./generated/dungeon.schema.json";

/** The parts of JSON Schema that pydantic emits for the models and we complete from. */
type Schema = {
  type?: string;
  $ref?: string;
  anyOf?: Schema[];
  enum?: string[];
  items?: Schema;
  properties?: Record<string, Schema>;
};

const definitions: Record<string, Schema> = dungeonSchema.$defs;

/** Follows $ref, and picks the useful branch of a nullable field's anyOf. */
function resolve(schema: Schema | undefined): Schema | undefined {
  if (!schema) return undefined;
  if (schema.$ref) return resolve(definitions[schema.$ref.split("/").pop()!]);
  if (schema.anyOf) return schema.anyOf.map(resolve).find((branch) => branch?.enum || branch?.properties || branch?.items);
  return schema;
}

function keyOf(pair: SyntaxNode, text: string): string {
  const key = pair.getChild("Key");
  return key ? text.slice(key.from, key.to).replace(/^["']|["']$/g, "") : "";
}

/** The schema of the value at `node`, found by walking up to the document. */
function schemaOf(node: SyntaxNode, text: string): Schema | undefined {
  const parent = node.parent;
  if (!parent || parent.name === "Document") return dungeonSchema;
  if (parent.name === "Pair") return resolve(schemaOf(parent.parent!, text)?.properties?.[keyOf(parent, text)]);
  if (parent.name === "Item") return resolve(schemaOf(parent.parent!, text)?.items);
  // Anchors and tags wrap a value without changing what it is.
  return schemaOf(parent, text);
}

function keyOption(key: string): Completion {
  return {
    label: key,
    type: "property",
    // Goes straight on to the value, as its allowed values are the point.
    apply(view: EditorView, completion: Completion, from: number, to: number) {
      const separator = view.state.sliceDoc(to, to + 1) === ":" ? "" : ": ";
      view.dispatch({
        ...insertCompletionText(view.state, key + separator, from, to),
        annotations: pickedCompletion.of(completion),
      });
      startCompletion(view);
    },
  };
}

function complete(context: CompletionContext): CompletionResult | null {
  const { state, pos, explicit } = context;
  const word = context.matchBefore(/[\w-]*/)!;

  // An empty value or a blank line has no node to look at, so ask what a word
  // would be if it were typed at the cursor. Two letters, as the parser doesn't
  // take a lone letter at the end of the document as a key.
  const doc = state.doc.toString();
  const probe = "xx";
  const text = doc.slice(0, pos) + probe + doc.slice(pos);
  const node = yamlLanguage.parser.parse(text).resolveInner(pos + probe.length, -1);
  if (node.name !== "Literal" && node.name !== "QuotedLiteral") return null;

  const pair = node.parent?.name === "Key" ? node.parent.parent! : null;
  const schema = resolve(schemaOf(pair ? pair.parent! : node, text));

  let labels: string[];
  let toOption: (label: string) => Completion;
  if (schema?.enum) {
    labels = schema.enum;
    toOption = (label) => ({ label, type: "enum" });
  } else if (schema?.properties) {
    // Offering every key on each new line would get in the way of typing, so wait for a word.
    if (word.from === pos && !explicit) return null;
    const used = pair?.parent?.getChildren("Pair").filter((other) => other.from !== pair.from);
    const usedKeys = new Set(used?.map((other) => keyOf(other, text)));
    labels = Object.keys(schema.properties).filter((key) => !usedKeys.has(key));
    toOption = keyOption;
  } else {
    return null;
  }

  // A finished word has nothing left to offer, and an open list would swallow Enter.
  const prefix = state.sliceDoc(word.from, pos);
  const matching = labels.filter((label) => label.startsWith(prefix));
  if (matching.length === 1 && matching[0] === prefix) return null;

  return { from: word.from, options: labels.map(toOption) };
}

/** Adds the completions to the YAML language. */
export const schemaCompletion = yamlLanguage.data.of({ autocomplete: complete });
