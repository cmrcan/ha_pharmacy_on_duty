import { spawnSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { createInterface } from "node:readline/promises";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const packagePath = path.join(projectRoot, "package.json");
const packageLockPath = path.join(projectRoot, "package-lock.json");
const manifestPath = path.join(
  projectRoot,
  "custom_components/nobetci_eczane/manifest.json",
);

const packageJson = JSON.parse(await readFile(packagePath, "utf8"));
const currentVersion = packageJson.version;
const arguments_ = process.argv.slice(2);
const assumeYes = arguments_.includes("--yes");
let requestedVersion = arguments_.find((argument) => !argument.startsWith("-"));

function run(command, argumentsList, options = {}) {
  const result = spawnSync(command, argumentsList, {
    cwd: projectRoot,
    encoding: "utf8",
    stdio: options.capture ? "pipe" : "inherit",
  });
  if (result.status !== 0) {
    const detail = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
    throw new Error(
      `${command} ${argumentsList.join(" ")} başarısız oldu${detail ? `:\n${detail}` : ""}`,
    );
  }
  return (result.stdout || "").trim();
}

async function ask(question) {
  const prompt = createInterface({ input: process.stdin, output: process.stdout });
  const answer = await prompt.question(question);
  prompt.close();
  return answer;
}

if (!requestedVersion) {
  if (!process.stdin.isTTY) {
    throw new Error("Sürümü argüman olarak verin: npm run release -- 0.5.4");
  }
  requestedVersion = await ask(
    `Yeni sürüm numarası (mevcut ${currentVersion}): `,
  );
}

const nextVersion = requestedVersion.trim().replace(/^v/i, "");
const semverPattern = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
if (!semverPattern.test(nextVersion)) {
  throw new Error(`Geçersiz sürüm numarası: ${requestedVersion}`);
}
if (nextVersion === currentVersion) {
  throw new Error(`Yeni sürüm mevcut sürümden farklı olmalı: ${currentVersion}`);
}

run("git", ["rev-parse", "--is-inside-work-tree"], { capture: true });
const branch = run("git", ["branch", "--show-current"], { capture: true });
if (!branch) {
  throw new Error("Detached HEAD durumunda release oluşturulamaz");
}
run("git", ["remote", "get-url", "origin"], { capture: true });
const tagCheck = spawnSync(
  "git",
  ["show-ref", "--verify", "--quiet", `refs/tags/v${nextVersion}`],
  { cwd: projectRoot },
);
if (tagCheck.status === 0) {
  throw new Error(`v${nextVersion} etiketi zaten mevcut`);
}

function replaceRequired(content, pattern, replacement, label) {
  if (!pattern.test(content)) {
    throw new Error(`${label} içinde sürüm alanı bulunamadı`);
  }
  return content.replace(pattern, replacement);
}

const packageLock = JSON.parse(await readFile(packageLockPath, "utf8"));
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
const constPath = path.join(
  projectRoot,
  "custom_components/nobetci_eczane/const.py",
);
const apiPath = path.join(projectRoot, "custom_components/nobetci_eczane/api.py");
const readmePath = path.join(projectRoot, "README.md");

packageJson.version = nextVersion;
packageLock.version = nextVersion;
packageLock.packages[""].version = nextVersion;
manifest.version = nextVersion;

const constSource = replaceRequired(
  await readFile(constPath, "utf8"),
  /CARD_VERSION = "[^"]+"/,
  `CARD_VERSION = "${nextVersion}"`,
  "const.py",
);
const apiSource = replaceRequired(
  await readFile(apiPath, "utf8"),
  /HomeAssistant-NobetciEczane\/[^ ]+/,
  `HomeAssistant-NobetciEczane/${nextVersion}`,
  "api.py",
);
const readmeSource = replaceRequired(
  await readFile(readmePath, "utf8"),
  /nobetci-eczane-card\.js\?v=[0-9A-Za-z.-]+/,
  `nobetci-eczane-card.js?v=${nextVersion}`,
  "README.md",
);

await Promise.all([
  writeFile(packagePath, `${JSON.stringify(packageJson, null, 2)}\n`),
  writeFile(packageLockPath, `${JSON.stringify(packageLock, null, 2)}\n`),
  writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`),
  writeFile(constPath, constSource),
  writeFile(apiPath, apiSource),
  writeFile(readmePath, readmeSource),
]);

const build = spawnSync(process.execPath, ["scripts/build.mjs"], {
  cwd: projectRoot,
  stdio: "inherit",
});
if (build.status !== 0) {
  throw new Error("Kart build işlemi başarısız oldu");
}

run(process.execPath, ["--test", "tests/card.test.mjs"]);

const changedFiles = run("git", ["status", "--short"], { capture: true });
if (!changedFiles) {
  throw new Error("Commit edilecek değişiklik bulunamadı");
}

console.log(`\nSürüm ${currentVersion} → ${nextVersion} olarak güncellendi.`);
console.log("Commit edilecek dosyalar:");
console.log(changedFiles);

if (!assumeYes) {
  if (!process.stdin.isTTY) {
    throw new Error("Onaysız kullanım için --yes ekleyin");
  }
  const confirmation = await ask(
    `\nTüm değişiklikler commit edilip origin/${branch} ve v${nextVersion} etiketi push edilsin mi? [e/H]: `,
  );
  if (!/^(e|evet|y|yes)$/i.test(confirmation.trim())) {
    console.log("Release iptal edildi; dosya değişiklikleri çalışma klasöründe bırakıldı.");
    process.exit(0);
  }
}

run("git", ["add", "-A"]);
run("git", ["commit", "-m", `Release v${nextVersion}`]);
run("git", ["push", "origin", branch]);
run("git", ["tag", "-a", `v${nextVersion}`, "-m", `Release v${nextVersion}`]);
run("git", ["push", "origin", `v${nextVersion}`]);

console.log(`\nRelease v${nextVersion} başarıyla commit edildi ve GitHub'a gönderildi.`);
