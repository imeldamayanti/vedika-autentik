// Rekam layar prototipe Vedika Autentik dalam satu take.
// Mencatat penanda waktu tiap adegan (w1..w7) dan waktu setiap klik (untuk efek suara),
// serta menggambar cincin sorot oranye di elemen yang sedang dibicarakan narasi.
import puppeteer from "/Users/imelda/.npm/_npx/8cedff245f11905c/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js";
import { writeFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const chromeRoot = join(homedir(), ".cache/puppeteer/chrome");
const ver = readdirSync(chromeRoot)[0];
const exe = join(chromeRoot, ver, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
const OUT = process.argv[2] || "videos/raw/demo-screen.mp4";
const URL = "http://localhost:8765/index.html";
const W = 1536, H = 864;

const browser = await puppeteer.launch({ executablePath: exe, headless: true, defaultViewport: { width: W, height: H, deviceScaleFactor: 1.25 }, args: ["--hide-scrollbars"] });
const page = await browser.newPage();
await page.goto(URL, { waitUntil: "networkidle0" });
await page.evaluate(() => localStorage.clear());
await page.reload({ waitUntil: "networkidle0" });

await page.evaluate(() => {
  const c = document.createElement("div");
  c.id = "kursor";
  c.style.cssText = "position:fixed;left:0;top:0;width:28px;height:28px;margin:-4px 0 0 -4px;z-index:99999;pointer-events:none;transition:transform .6s cubic-bezier(.45,0,.2,1);";
  c.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24"><path d="M3 2l7 19 3-8 8-3z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  const r = document.createElement("div");
  r.id = "riak";
  r.style.cssText = "position:fixed;left:0;top:0;width:52px;height:52px;margin:-26px 0 0 -26px;border-radius:50%;border:3px solid #f26b21;background:rgba(242,107,33,.18);z-index:99998;pointer-events:none;opacity:0;";
  document.body.append(c, r);
  window.__gerak = (x, y) => { c.style.transform = `translate(${x}px,${y}px)`; };
  window.__klik = (x, y) => { r.style.left = x + "px"; r.style.top = y + "px"; r.animate([{ opacity: 1, transform: "scale(.4)" }, { opacity: 0, transform: "scale(1.6)" }], { duration: 550 }); };
  // cincin sorot: bingkai oranye berdenyut mengelilingi elemen, lalu hilang
  window.__sorot = (sel, ms, pad = 8) => {
    const el = typeof sel === "string" ? document.querySelector(sel) : sel;
    if (!el) return;
    const b = el.getBoundingClientRect();
    const d = document.createElement("div");
    d.style.cssText = `position:fixed;left:${b.left - pad}px;top:${b.top - pad}px;width:${b.width + pad * 2}px;height:${b.height + pad * 2}px;border:3px solid #f26b21;border-radius:12px;box-shadow:0 0 0 6px rgba(242,107,33,.22),0 0 40px rgba(242,107,33,.45);z-index:99997;pointer-events:none;opacity:0;`;
    document.body.append(d);
    d.animate([{ opacity: 0, transform: "scale(1.06)" }, { opacity: 1, transform: "scale(1)", offset: 0.15 }, { opacity: 1, offset: 0.85 }, { opacity: 0 }], { duration: ms, fill: "forwards" });
    setTimeout(() => d.remove(), ms + 50);
  };
});

const rec = await page.screencast({ path: OUT, speed: 1, scale: 1.25 });
const t0 = Date.now();
const marks = {};
const clicks = [];
const now = () => +((Date.now() - t0) / 1000).toFixed(2);
const mark = (n) => { marks[n] = now(); console.log(n, marks[n]); };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function center(sel) {
  const el = await page.waitForSelector(sel, { visible: true });
  await el.evaluate((e) => e.scrollIntoView({ block: "center", behavior: "instant" }));
  const b = await el.boundingBox();
  return { el, x: b.x + b.width / 2, y: b.y + b.height / 2 };
}
async function klik(sel, pause = 700) {
  const { el, x, y } = await center(sel);
  await page.evaluate((x, y) => window.__gerak(x, y), x, y);
  await wait(700);
  await page.evaluate((x, y) => window.__klik(x, y), x, y);
  clicks.push(now());
  await el.click();
  await wait(pause);
}
async function gerak(sel) {
  const { x, y } = await center(sel);
  await page.evaluate((x, y) => window.__gerak(x, y), x, y);
  await wait(700);
}
const sorot = (sel, ms = 2200, pad = 8) => page.evaluate((s, m, p) => window.__sorot(s, m, p), sel, ms, pad);
const ke = async (hash, pause = 1200) => { await page.evaluate((h) => { location.hash = h; }, hash); await wait(pause); };

mark("mulai");
await wait(1000);
await klik('[data-aksi="masuk"]', 1200);
if (await page.$('[data-aksi="tur-tutup"]')) await page.click('[data-aksi="tur-tutup"]');
await wait(500);
await ke("#/autentik", 1500);

// w1: unggah
mark("w1");
await sorot("#tombolDemo", 1800, 10);
await wait(1000);
await klik("#tombolDemo", 300);

// w2: pemeriksaan jalan, lalu kualitas scan berkas buram
mark("w2");
await page.waitForFunction(() => document.querySelector(".ringkas-hasil") || /berkas selesai diperiksa/i.test(document.body.innerText), { timeout: 30000 });
mark("w2-selesai");
await wait(1200);

// w3: antrean berlabel
mark("w3");
await ke("#/autentik", 600);
await page.evaluate(() => window.scrollTo({ top: document.querySelector(".tabel-antrean, .tabel--kartu")?.getBoundingClientRect().top + scrollY - 160, behavior: "smooth" }));
await wait(1500);
await sorot(".segmen", 2000, 6);
await wait(1800);
const adaPrioritas = await page.$('[data-aksi="saring"][data-nilai="prioritas"]');
if (adaPrioritas) { await klik('[data-aksi="saring"][data-nilai="prioritas"]', 1300); await klik('[data-aksi="saring"][data-nilai="semua"], [data-aksi="saring"]', 1200); }
await wait(800);

// w4: kartu bukti angka disunting
mark("w4");
await ke("#/berkas/VA-DST-01/bukti", 1800);
if (await page.$('[data-aksi="saklar-sorot"]')) { await klik('[data-aksi="saklar-sorot"]', 800); await klik('[data-aksi="saklar-sorot"]', 1000); }
mark("w4-scroll");
const yTarget = await page.evaluate(() => {
  const els = [...document.querySelectorAll(".sorot")];
  const e = els.sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top)[0] || els[0];
  return e ? e.getBoundingClientRect().top + window.scrollY - window.innerHeight * 0.4 : 0;
});
await page.evaluate((y) => window.scrollTo({ top: y, behavior: "smooth" }), yTarget);
await wait(2400);
mark("w4-sorot");
await wait(2400);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
await wait(1100);
if (await page.$('[data-aksi="fokus"]')) { await klik('[data-aksi="fokus"]', 2200); }

// w5: berkas kembar
mark("w5");
await ke("#/berkas/VA-KMB-01/bukti", 1800);
await sorot(".halaman-berkas.dua", 3200, 4);
await wait(5000);

// w6: konfirmasi peserta
mark("w6");
await ke("#/berkas/VA-KMB-01/peserta", 1800);
await sorot(".ponsel", 2400, 8);
await wait(1800);
await page.evaluate(() => { [...document.querySelectorAll(".ponsel-balas button")].forEach((b) => { if (/Tidak pernah/i.test(b.textContent)) b.id = "balas-tidak"; }); });
await klik("#balas-tidak", 5200);

// w7: keputusan
mark("w7");
await ke("#/berkas/VA-KMB-01/bukti", 1500);
await sorot(".saran", 2200, 6);
await wait(1500);
await klik('[data-aksi="setujui"]', 5000);
mark("selesai");

await rec.stop();
marks.klik = clicks;
writeFileSync(OUT.replace(/\.mp4$/, ".marks.json"), JSON.stringify(marks, null, 2));
await page.screenshot({ path: OUT.replace(/\.mp4$/, "-akhir.png") });
await browser.close();
