// Builds our wheel and stages it at a content-hashed path under public/, so a
// new deploy can never pair fresh page code with a stale cached package. The
// file keeps its wheel name because Pyodide's loadPackage parses it.
// The path reaches the app as VITE_WHEEL_URL, through a gitignored .env.local.
// Also generates the models' JSON Schema, which the editor's autocomplete bundles.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { copyFileSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const webDir = join(import.meta.dirname, "..");
const repoDir = join(webDir, "..");
const stageDir = join(webDir, "public", "py");
const schemaDir = join(webDir, "src", "generated");

const schema = execFileSync(
  "uv",
  ["run", "--quiet", "python", "-c", "import json; from dungeon_dsl.models import Dungeon; print(json.dumps(Dungeon.model_json_schema()))"],
  { cwd: repoDir, encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] },
);
mkdirSync(schemaDir, { recursive: true });
writeFileSync(join(schemaDir, "dungeon.schema.json"), schema);

const outDir = mkdtempSync(join(tmpdir(), "dungeon-wheel-"));
try {
  execFileSync("uv", ["build", "--wheel", "--quiet", "--out-dir", outDir], { cwd: repoDir, stdio: "inherit" });
  const [wheel] = readdirSync(outDir).filter((name) => name.endsWith(".whl"));
  if (!wheel) throw new Error(`uv build produced no wheel in ${outDir}`);

  const hash = createHash("sha256").update(readFileSync(join(outDir, wheel))).digest("hex").slice(0, 16);
  const relativePath = `py/${hash}/${wheel}`;

  rmSync(stageDir, { recursive: true, force: true });
  mkdirSync(join(stageDir, hash), { recursive: true });
  copyFileSync(join(outDir, wheel), join(webDir, "public", relativePath));
  writeFileSync(join(webDir, ".env.local"), `VITE_WHEEL_URL=${relativePath}\n`);
  console.log(relativePath);
} finally {
  rmSync(outDir, { recursive: true, force: true });
}
