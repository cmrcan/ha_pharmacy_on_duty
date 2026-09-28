import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { build, context } from "esbuild";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const packageJson = JSON.parse(
  await readFile(path.join(projectRoot, "package.json"), "utf8"),
);
const watch = process.argv.includes("--watch");

const options = {
  absWorkingDir: projectRoot,
  entryPoints: ["src/nobetci-eczane-card.js"],
  outfile:
    "custom_components/nobetci_eczane/static/nobetci-eczane-card.js",
  bundle: true,
  charset: "utf8",
  define: {
    __CARD_VERSION__: JSON.stringify(packageJson.version),
  },
  format: "iife",
  legalComments: "none",
  minify: !watch,
  sourcemap: watch ? "inline" : false,
  target: ["es2022"],
  banner: {
    js: `/* Nöbetçi Eczane Card v${packageJson.version} — generated; edit src/ instead. */`,
  },
};

if (watch) {
  const buildContext = await context(options);
  await buildContext.watch();
  console.log("Kart kaynağı izleniyor; değişiklikler static çıktısına yazılacak.");
} else {
  await build(options);
}
