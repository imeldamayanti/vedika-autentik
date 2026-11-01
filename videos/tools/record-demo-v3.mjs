// Rekam layar Vedika Autentik v3 (mode simulasi S1) dalam satu take realtime.
// Aplikasi berjalan realtime (panggilan S1 ±75 dtk), jadi semua adegan D1–D6 direkam berurutan
// lalu dipotong per adegan di komposisi HyperFrames memakai penanda waktu di *.marks.json.
//
// Kondisi awal bersih: localStorage kosong, RS Melati Normal (2/4), S1 Antre.
// Selama panggilan S1 berjalan, take mampir ke Ringkasan RS untuk merekam keadaan "sebelum" (Normal 2/4).
//
//   node videos/tools/record-demo-v3.mjs [keluaran.mp4]
// Butuh server statis di http://localhost:8765 (python3 -m http.server 8765 dari akar repo).
import puppeteer from "/Users/imelda/.npm/_npx/8cedff245f11905c/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js";
import { writeFileSync, readdirSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { homedir, tmpdir } from "node:os";
import { join, dirname } from "node:path";

const chromeRoot = join(homedir(), ".cache/puppeteer/chrome");
const ver = readdirSync(chromeRoot)[0];
const exe = join(chromeRoot, ver, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
const OUT = process.argv[2] || "videos/v3/assets/screen/demo.mp4";
mkdirSync(dirname(OUT), { recursive: true });
const URL = "http://localhost:8765/index.html";
const W = 1440, H = 810, DSF = +(process.env.DSF || 2);

// defaultViewport null + --force-device-scale-factor: hanya cara ini frame screencast keluar dalam piksel fisik (2x).
// Tinggi jendela ditambah 87 px untuk tepi jendela headless supaya area halaman tepat W x H.
const browser = await puppeteer.launch({ executablePath: exe, headless: true, defaultViewport: null, args: ["--hide-scrollbars", `--force-device-scale-factor=${DSF}`, `--window-size=${W},${H + 87}`] });
const page = await browser.newPage();
const ukuran = await page.evaluate(() => [innerWidth, innerHeight, devicePixelRatio]);
console.log("viewport", ukuran);
if (ukuran[0] !== W || ukuran[1] !== H) throw new Error(`viewport ${ukuran} bukan ${W}x${H}`);
await page.goto(URL, { waitUntil: "networkidle0" });
await page.evaluate(() => localStorage.clear());
await page.reload({ waitUntil: "networkidle0" });

// kursor besar + cincin klik (digambar di halaman supaya ikut terekam)
await page.evaluate(() => {
  const c = document.createElement("div");
  c.id = "kursor";
  c.style.cssText = "position:fixed;left:0;top:0;width:34px;height:34px;margin:-4px 0 0 -4px;z-index:99999;pointer-events:none;transition:transform .7s cubic-bezier(.45,0,.2,1);transform:translate(1100px,500px);";
  c.innerHTML = '<svg width="34" height="34" viewBox="0 0 24 24"><path d="M3 2l7 19 3-8 8-3z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  const r = document.createElement("div");
  r.id = "riak";
  r.style.cssText = "position:fixed;left:0;top:0;width:56px;height:56px;margin:-28px 0 0 -28px;border-radius:50%;border:3px solid #f26b21;background:rgba(242,107,33,.18);z-index:99998;pointer-events:none;opacity:0;";
  document.body.append(c, r);
  window.__gerak = (x, y) => { c.style.transform = `translate(${x}px,${y}px)`; };
  window.__klik = (x, y) => { r.style.left = x + "px"; r.style.top = y + "px"; r.animate([{ opacity: 1, transform: "scale(.4)" }, { opacity: 0, transform: "scale(1.6)" }], { duration: 550 }); };
});

// masuk dulu (di luar rekaman), mulai dari antrean bersih
await page.click('[data-aksi="masuk"]');
await page.evaluate(() => { location.hash = "#/autentik"; });
await page.waitForSelector('tr[data-tujuan="#/panggilan/S1"]');
await new Promise((r) => setTimeout(r, 800));

// Perekam CDP sendiri: puppeteer.screencast menjatuhkan frame dan memampatkan waktu, sehingga penanda
// tidak sinkron dengan video. Di sini tiap frame JPEG disimpan beserta timestamp-nya, lalu dirakit
// ke 30 fps konstan dengan durasi asli (frame terakhir ditahan sampai akhir take).
const frameDir = mkdtempSync(join(tmpdir(), "va3-frames-"));
const frames = [];
const cdp = await page.createCDPSession();
const t0 = Date.now();
cdp.on("Page.screencastFrame", (f) => {
  const i = frames.length;
  frames.push({ f: join(frameDir, `${String(i).padStart(6, "0")}.jpg`), t: f.metadata.timestamp * 1000 - t0 });
  writeFileSync(frames[i].f, Buffer.from(f.data, "base64"));
  cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
});
await cdp.send("Page.startScreencast", { format: "jpeg", quality: 88, everyNthFrame: 1, maxWidth: W * DSF, maxHeight: H * DSF });
const marks = {};
const clicks = [];
const now = () => +((Date.now() - t0) / 1000).toFixed(2);
const mark = (n) => { marks[n] = now(); console.log(n, marks[n]); };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function pusat(sel) {
  const el = await page.waitForSelector(sel, { visible: true });
  await el.evaluate((e) => e.scrollIntoView({ block: "nearest", behavior: "instant" }));
  const b = await el.boundingBox();
  return { el, x: b.x + b.width / 2, y: b.y + b.height / 2 };
}
async function gerak(sel, pause = 800, dx = 0, dy = 0) {
  const { x, y } = await pusat(sel);
  await page.evaluate((x, y) => window.__gerak(x, y), x + dx, y + dy);
  await wait(pause);
}
async function klik(sel, pause = 700) {
  const { el, x, y } = await pusat(sel);
  await page.evaluate((x, y) => window.__gerak(x, y), x, y);
  await wait(800);
  await page.evaluate((x, y) => window.__klik(x, y), x, y);
  clicks.push(now());
  await el.click();
  await wait(pause);
}
const ke = async (hash, pause = 1200) => { await page.evaluate((h) => { location.hash = h; }, hash); await wait(pause); };
const gulir = async (y, pause) => { await page.evaluate((y) => window.scrollTo({ top: y, behavior: "smooth" }), y); await wait(pause); };

mark("mulai");

// ---------- D1 antrean: kursor ke baris Pak Andi lalu ke chip indikator
mark("d1");
await wait(1500);
await gerak('tr[data-tujuan="#/panggilan/S1"] .nama-berkas', 1800);
await gerak('tr[data-tujuan="#/panggilan/S1"] .chip-ind-wadah', 2200, -60, 0);
await gerak('tr[data-tujuan="#/panggilan/S1"] .angka', 2200);
await wait(3000);

// ---------- D2 mode otomatis
mark("d2");
await klik('[data-aksi="otomatis"]', 300);
mark("panggilan-mulai"); // mulaiPanggilan(S1) jalan seketika; detik layar panggilan = t - ini
const tCall = marks["panggilan-mulai"];
await wait(5200); // status WA terkirim → Menelepon

// ---------- D3 layar panggilan
mark("d3");
await klik('tr[data-tujuan="#/panggilan/S1"]', 800);
await gerak(".transkrip", 1500, 100, -80);
await wait(6500);

// mampir ke Ringkasan RS: keadaan sebelum S1 dihitung (Normal 2/4)
mark("d5-sebelum");
await ke("#/ringkasan-rs", 1500);
await gerak('[data-aksi="lihat-kartu-rs"][data-id="RS01"]', 1200, -300, 0);
await wait(6000);
mark("d5-sebelum-selesai");

// kembali ke panggilan sebelum pertanyaan "berapa kali" (rekam 35 dtk => layar 41 dtk)
while (now() - tCall < 31) await wait(200);
await ke("#/panggilan/S1", 600);
mark("d3-panggilan-lagi");
await gerak(".transkrip", 800, 100, -80);
while (now() - tCall < 61) await wait(250);
await gerak(".isian", 1000, 0, -40);

// tunggu selesai: aplikasi pindah sendiri ke kartu bukti
await page.waitForFunction(() => location.hash.startsWith("#/kartu/S1"), { timeout: 40000, polling: 250 });
mark("d4");
await wait(1800);
await gerak(".tiga-kartu section:nth-child(3)", 1800);
await gerak(".tiga-kartu .tanggal-sesi", 2200);
await gerak(".tiga-kartu section:nth-child(1) .besar", 1200);
await gulir(380, 1500);
await gerak(".kutipan", 2200);
await gerak(".pemutar audio", 2500);
await wait(1500);

// ---------- D5 ringkasan RS sesudah S1
mark("d5");
await klik('a[href="#/ringkasan-rs"]', 1800);
await gerak(".perubahan-rs", 3200);
await klik('[data-aksi="lihat-kartu-rs"][data-id="RS01"]', 3500);

// ---------- D6 keputusan
mark("d6");
await ke("#/kartu/S1", 1500);
await gulir(0, 400);
await page.evaluate(() => { const b = document.querySelector('[data-aksi="setujui"]'); if (b) b.scrollIntoView({ block: "center", behavior: "smooth" }); });
await wait(1600);
await klik('[data-aksi="setujui"]', 800);
mark("d6-putusan");
await wait(4500);
mark("selesai");

const tAkhir = now();
await cdp.send("Page.stopScreencast");
await wait(300);
const daftar = frames.filter((x) => x.t >= 0 || true);
const baris = daftar.map((x, i) => {
  const next = i + 1 < daftar.length ? daftar[i + 1].t : tAkhir * 1000;
  const mulaiT = i === 0 ? 0 : x.t; // frame pertama ditahan dari detik 0
  return `file '${x.f}'\nduration ${Math.max(0.001, (next - mulaiT) / 1000).toFixed(4)}`;
});
baris.push(`file '${daftar[daftar.length - 1].f}'`);
const daftarFile = join(frameDir, "list.txt");
writeFileSync(daftarFile, baris.join("\n"));
execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", daftarFile, "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-movflags", "+faststart", OUT], { stdio: "inherit" });
rmSync(frameDir, { recursive: true, force: true });
console.log("frame mentah:", frames.length, "durasi take:", tAkhir);
marks.klik = clicks;
marks.panggilanMulai = tCall;
writeFileSync(OUT.replace(/\.mp4$/, ".marks.json"), JSON.stringify(marks, null, 2));
await page.screenshot({ path: OUT.replace(/\.mp4$/, "-akhir.png") });
await browser.close();
