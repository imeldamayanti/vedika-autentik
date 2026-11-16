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

  console.log("\nHalaman awal dan strip status");
  await page.goto(TARGET);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForSelector("#stripStatus");
  cek(!(await page.$('[data-aksi="masuk"]')) && (await page.title()).startsWith("Antrean konfirmasi"), "langsung membuka antrean, tanpa layar masuk", await page.title());
  const menu = await page.$$eval(".nav a, .nav button", (el) => el.map((x) => x.textContent.trim()));
  cek(!menu.some((m) => m.startsWith("Beranda") || m.startsWith("Verifikasi klaim")), "menu tanpa Beranda dan tanpa menu mati", menu.join(" | "));
  const strip = await page.textContent("#stripStatus");
  cek(strip.includes("Panggilan otomatis mati"), "strip status menunjukkan keadaan panggilan otomatis", strip.slice(0, 80));
  cek((await page.$$("#stripStatus .siap-ikon")).length === 1 && (await page.$$("#stripStatus b")).length === 1, "strip status menampilkan tepat satu keadaan");
  cek((await page.$$("#stripStatus .sehat")).length === 0, "simulasi tanpa chip kesehatan yang semuanya merah");
  const tanda = await page.$$eval(".lencana-simulasi", (el) => el.map((x) => x.textContent.trim()));
  cek(tanda.length === 1 && tanda[0] === "Simulasi" && !(await page.$(".catatan-prototipe")), "tepat satu tanda Simulasi", tanda.join(" | "));

  console.log("\nAntrean");
  const tombol = await page.$$eval('[data-aksi="telepon"]', (el) => el.map((x) => x.textContent.trim()));
  cek(tombol.length >= 7 && tombol.every((t) => t === "Dahulukan"), "baris antrean memakai tombol Dahulukan", tombol.length + " tombol: " + tombol.slice(0, 3).join(", "));
  cek(!(await page.content()).includes("Telepon sekarang"), "tidak ada lagi teks Telepon sekarang");
  cek((await page.getAttribute('[data-aksi="telepon"][data-id="S1"]', "title")) === "Pindahkan ke urutan berikutnya", "tooltip Dahulukan");
  cek(!(await page.content()).includes("masih stub"), "teks 'masih stub' sudah dihapus");

  console.log("\nSkor pola di antrean");
  /* Skor tiap baris berstatus Antre, dari atas ke bawah. */
  const skorAntre = () => page.$$eval("tbody tr", (tr) => tr
    .filter((r) => r.querySelector(".status-chip--antre") && r.querySelector(".chip-pola"))
    .map((r) => parseFloat(r.querySelector(".chip-pola").textContent.replace("Pola", "").replace(",", "."))));
  const menurun = (d) => d.every((x, i) => i === 0 || d[i - 1] >= x);
  cek((await page.$$(".chip-pola")).length === 14, "tiap baris antrean punya chip skor pola", String((await page.$$(".chip-pola")).length));
  const chipS1 = await page.$eval("tbody tr:nth-child(2) .chip-pola", (el) => ({ teks: el.textContent.trim(), kelas: el.className, judul: el.title, lebar: el.querySelector("i b").style.width }));
  cek(chipS1.teks === "Pola 1,00" && chipS1.kelas.includes("chip-pola--tinggi") && chipS1.lebar === "100%", "chip S1: Pola 1,00 bergaya tinggi dengan batang penuh", JSON.stringify(chipS1));
  cek(chipS1.judul === "Skor pola 1,00, pola tidak biasa", "tooltip chip menyebut skor dan pola tidak biasa", chipS1.judul);
  cek((await page.$$(".chip-ind")).length === 0 && (await page.textContent("tbody tr:nth-child(2) .ind-teks")) === "Melebihi 8 · 3x seminggu · Libur", "indikator sebagai teks biasa, bukan chip berwarna");
  cek((await page.$$("tbody .label + .status-chip, tbody .status-chip + .label")).length === 0, "baris selesai hanya menampilkan label hasil");
  cek((await page.textContent(".catatan-kaki")).includes("Skor pola hanya menentukan urutan panggilan."), "catatan skor pola cukup sekali, di bawah tabel");
  const atas = await page.$$eval("tbody tr .nama-berkas b", (el) => el.slice(0, 2).map((x) => x.textContent));
  cek(atas[0] === "Slamet Riyadi" && atas[1] === "Andi Pratama", "skor 1,00 diurutkan menurut logit: S6 lalu S1", atas.join(", "));
  const awal = await skorAntre();
  cek(awal.length === 10 && menurun(awal) && awal[0] === 1 && awal[9] < 0.2, "antrean terurut skor pola menurun", awal.join(" "));
  cek((await page.$$(".chip-pola:not(.chip-pola--tinggi)")).length >= 2, "skor di bawah ambang memakai chip netral");
  cek(await page.evaluate(() => window.DATA3.UJI_POLA.length === 0 && window.DATA3.UJI.length === 0), "uji mandiri data simulasi (label dan skor pola) bersih");

  console.log("\nS1 sampai kartu bukti");
  await page.click('[data-aksi="telepon"][data-id="S1"]');
  await page.waitForSelector(".status-chip--wa");
  const sesudah = await skorAntre();
  cek(sesudah.length === 9 && menurun(sesudah), "setelah Dahulukan, sisa antrean tetap terurut skor pola", sesudah.join(" "));
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
  cek((await page.textContent(".pola-kartu h2")) === "Alasan prioritas", "kartu bukti punya bagian Alasan prioritas");
  const alasan = await page.$$eval(".pola-kartu .pola-alasan li", (el) => el.map((x) => x.textContent));
  cek(alasan.length === 2 && alasan.some((a) => a.includes("hari Minggu atau libur")) && alasan.every((a) => a.includes("sesi")), "kartu S1 memuat dua alasan: sesi dan hari Minggu atau libur", alasan.join(" | "));
  cek((await page.textContent(".pola-kartu .pola-kombinasi")) === "Gabungan indikator ini muncul pada kurang dari 0,03% tagihan bulanan fisioterapi nasional 2024.", "kalimat gabungan indikator");
  cek((await page.textContent(".pola-kartu .pola-catatan")) === "Dibandingkan dengan data sampel BPJS 2024.", "catatan sumber data singkat");
  cek(await page.isVisible(".pola-kartu .lencana-pola"), "lencana Pola tidak biasa di kartu S1");
  cek(!/fraud|curang/i.test(await page.textContent(".pola-kartu")), "bagian skor pola tanpa kata fraud atau curang");
  await page.goto(TARGET + "#/kartu/R3");
  await page.waitForSelector(".pola-kartu");
  cek(!(await page.$(".pola-kartu .lencana-pola")) && (await page.textContent(".pola-kartu .chip-pola")).trim() === "Pola 0,12", "kartu berskor rendah (R3) tanpa lencana, chip netral");
  await page.goto(TARGET + "#/ringkasan-rs");
  await page.waitForSelector(".baris-pembanding");
  const pembanding = await page.$$eval(".baris-pembanding", (el) => el.map((x) => x.textContent.trim()));
  cek(pembanding.length === 5 && pembanding[0].includes("Terpicu 39,7% · rata-rata RS sejenis 1,5% · batas 95% RS sejenis 8,2%"), "Ringkasan RS: baris pembanding RS sejenis nasional", pembanding[0]);
  cek((await page.$$(".baris-pembanding .lencana-pola")).length === 1 && pembanding[0].includes("Di atas 95% RS sejenis"), "hanya RS Melati berlencana Di atas 95% RS sejenis");
  const kinerja = await page.textContent(".kinerja-pola");
  cek(kinerja.includes("Skor pola dan hasil panggilan") && kinerja.includes("2 dari 2 panggilan berpola tidak biasa berakhir Tidak sesuai") && kinerja.includes("5 panggilan terjawab"), "kartu Skor pola dan hasil panggilan", kinerja);
  cek(await page.isVisible("text=RS Melati Sehat kini berstatus Perlu klarifikasi RS (3 tidak sesuai dari 5 terjawab)"), "RS Melati menjadi Perlu klarifikasi RS (3 dari 5)");

  console.log("\nBahasa");
  for (const [hash, nama] of [["#/autentik", "antrean"], ["#/ringkasan-rs", "ringkasan RS"], ["#/riwayat", "riwayat"], ["#/kartu/R1", "kartu bukti"]]) {
    await page.goto(TARGET + hash);
    await page.waitForSelector(".isi");
    const teks = await page.innerText("#isi");
    const salah = ["bulan-pasien", "bukan putusan", "Mengapa diprioritaskan", "vs hasil", "Username", ";"].filter((x) => teks.includes(x));
    cek(salah.length === 0, "teks " + nama + " tanpa istilah dan pola kalimat lama", salah.join(", "));
  }

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
