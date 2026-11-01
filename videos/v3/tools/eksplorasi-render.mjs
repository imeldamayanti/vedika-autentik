// Render still eksplorasi Babak 1 (tools/eksplorasi.html) ke renders/eksplorasi/*.png, 1920x1080.
//   node videos/v3/tools/eksplorasi-render.mjs [A1 A2 ...]
import puppeteer from "/Users/imelda/.npm/_npx/8cedff245f11905c/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js";
import { readdirSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "../renders/eksplorasi");
mkdirSync(OUT, { recursive: true });
const chromeRoot = join(homedir(), ".cache/puppeteer/chrome");
const exe = join(chromeRoot, readdirSync(chromeRoot)[0], "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
const FRAMES = process.argv.slice(2).length ? process.argv.slice(2) : ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"];

const browser = await puppeteer.launch({ executablePath: exe, headless: true, args: ["--allow-file-access-from-files"] });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
for (const f of FRAMES) {
  await page.goto(pathToFileURL(join(HERE, "eksplorasi.html")).href + "?f=" + f, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  await new Promise((r) => setTimeout(r, 150));
  await page.screenshot({ path: join(OUT, `${f}.png`) });
  console.log("ok", f);
}
await browser.close();
