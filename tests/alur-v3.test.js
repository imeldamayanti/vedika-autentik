/* Uji alur Vedika Autentik v3 (konfirmasi suara) di mode simulasi: API sengaja diputus, layar memakai data-v3.js.

   Pemakaian:
     python3 -m http.server 8899          # dari akar repositori
     node tests/alur-v3.test.js           # TARGET_URL=https://... untuk menguji hasil deploy
   Variabel opsional: CHROME=/path/ke/chrome, PW_HEADLESS=false */

const { chromium } = require("playwright");

const TARGET = (process.env.TARGET_URL || "http://localhost:8899/").replace(/#.*$/, "");

const lolos = [];
const gagal = [];
const cek = (syarat, nama, detail) => {
  if (syarat) { lolos.push(nama); console.log("  LULUS  " + nama); }
  else { gagal.push(nama); console.log("  GAGAL  " + nama + (detail ? " :: " + detail : "")); }
};

async function tanpaGeserSamping(page, nama) {
  const lebih = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  cek(lebih <= 1, nama, "halaman melebar " + lebih + "px");
}

(async () => {
  const browser = await chromium.launch({ headless: process.env.PW_HEADLESS !== "false", executablePath: process.env.CHROME || undefined });
  const konteks = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await konteks.newPage();
  const galat = [];
  page.on("pageerror", (e) => galat.push(e.message));
  /* Tanpa API: semua permintaan /api/v1 diputus, jadi aplikasi jatuh ke simulasi. */
  await page.route("**/api/v1/**", (rute) => rute.abort());

  console.log("\nMasuk dan strip status");
  await page.goto(TARGET);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.click('[data-aksi="masuk"]');
  await page.goto(TARGET + "#/autentik");
  await page.waitForSelector("#stripStatus");
  const strip = await page.textContent("#stripStatus");
  cek(strip.includes("Mode simulasi"), "strip status tampil dengan keadaan Mode simulasi", strip.slice(0, 80));
  cek((await page.$$("#stripStatus .siap-ikon")).length === 1 && (await page.$$("#stripStatus b")).length === 1, "strip status menampilkan tepat satu keadaan");
  const chip = await page.$$eval("#stripStatus .sehat span", (el) => el.map((x) => x.textContent.trim()));
  cek(["API", "Database", "Pembaca jawaban"].every((n) => chip.includes(n)) && chip.some((n) => n.indexOf("Saluran telepon") === 0), "chip kesehatan: API, Database, Pembaca jawaban, Saluran telepon", chip.join(" | "));
  cek((await page.$$(".lencana-simulasi")).length >= 1, "label Simulasi tetap tampil");

  console.log("\nAntrean");
  const tombol = await page.$$eval('[data-aksi="telepon"]', (el) => el.map((x) => x.textContent.trim()));
  cek(tombol.length >= 7 && tombol.every((t) => t === "Dahulukan"), "baris antrean memakai tombol Dahulukan", tombol.length + " tombol: " + tombol.slice(0, 3).join(", "));
  cek(!(await page.content()).includes("Telepon sekarang"), "tidak ada lagi teks Telepon sekarang");
  cek((await page.getAttribute('[data-aksi="telepon"][data-id="S1"]', "title")) === "Pindahkan ke urutan berikutnya", "tooltip Dahulukan");
  cek(!(await page.content()).includes("masih stub"), "teks 'masih stub' sudah dihapus");

  console.log("\nS1 sampai kartu bukti");
  await page.click('[data-aksi="telepon"][data-id="S1"]');
  await page.goto(TARGET + "#/panggilan/S1");
  await page.waitForSelector("#panggilan");
  cek(await page.isVisible("text=Pesan WA terkirim"), "tahap Pesan WA terkirim tampil di layar panggilan");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Alt+KeyL"); /* pintasan demo: lompat ke akhir panggilan */
  await page.waitForURL(/#\/kartu\/S1/, { timeout: 10000 });
  await page.waitForSelector(".angka-tiga");
  const angka = await page.$$eval(".angka-tiga .besar", (el) => el.map((x) => parseInt(x.textContent, 10)));
  cek(angka[0] === 11 && angka[1] === 3, "kartu bukti S1: ditagih 11, versi peserta 3", angka.join(" / "));
  cek(angka[2] === 8, "selisih 8 sesi", String(angka[2]));
  cek((await page.textContent(".judul-label .label")).trim() === "Tidak sesuai", "label Tidak sesuai");
  await page.goto(TARGET + "#/ringkasan-rs");
  cek(await page.isVisible("text=RS Melati Sehat kini berstatus Perlu klarifikasi RS (3 tidak sesuai dari 5 terjawab)"), "RS Melati menjadi Perlu klarifikasi RS (3 dari 5)");

  console.log("\nLebar 390 px");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [hash, nama] of [["#/autentik", "antrean"], ["#/kartu/S1", "kartu bukti"], ["#/panggilan/S2", "panggilan"], ["#/ringkasan-rs", "ringkasan RS"]]) {
    await page.goto(TARGET + hash);
    await page.waitForSelector(".isi");
    await tanpaGeserSamping(page, "tanpa geser samping di " + nama + " (390 px)");
  }
  await page.goto(TARGET + "#/autentik");
  cek(await page.isVisible("#stripStatus"), "strip status tetap tampil di 390 px");

  cek(galat.length === 0, "tidak ada galat JavaScript", galat.slice(0, 3).join(" | "));
  await browser.close();
  console.log("\n" + lolos.length + " lulus, " + gagal.length + " gagal");
  process.exit(gagal.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
