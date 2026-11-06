// The bundled example Dungeons: every YAML file in the repo's examples/ folder.
const files = import.meta.glob<string>("../../examples/*.yaml", { query: "?raw", import: "default", eager: true });

export type Example = { name: string; yaml: string };

export const bundledExamples: Example[] = Object.entries(files).map(([path, yaml]) => ({
  name: path.replace(/^.*\/|\.yaml$/g, ""),
  yaml,
}));
