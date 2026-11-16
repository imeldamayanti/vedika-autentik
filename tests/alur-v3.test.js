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

  console.log("\nSumber pemilihan di antrean (aturan ATAU model anomali)");
  const namaAntre = () => page.$$eval("tbody tr", (tr) => tr.filter((r) => r.querySelector(".status-chip--antre")).map((r) => r.querySelector(".nama-berkas b").textContent));
  const chipBaris = (nama) => page.$$eval("tbody tr", (tr, n) => { const r = tr.find((x) => x.querySelector(".nama-berkas b").textContent === n); const c = r && r.querySelector(".chip-dipilih"); return c ? { teks: c.textContent, kelas: c.className, judul: c.title } : null; }, nama);
  cek((await page.$$(".chip-dipilih")).length === 16 && (await page.$$(".chip-pola")).length === 0, "tiap baris punya chip sumber pemilihan, tanpa chip skor pola", String((await page.$$(".chip-dipilih")).length));
  const s1 = await chipBaris("Andi Pratama"), m1 = await chipBaris("Sari Wulandari"), s3 = await chipBaris("Budi Santoso");
  cek(s1 && s1.teks === "Aturan + model", "S1 dipilih aturan dan model", JSON.stringify(s1));
  cek(m1 && m1.teks === "Model" && m1.kelas.includes("chip-dipilih--model") && m1.judul.includes("tidak terkena aturan"), "M1 hanya dipilih model, dengan keterangan", JSON.stringify(m1));
  cek(s3 && s3.teks === "Aturan", "S3 hanya dipilih aturan", JSON.stringify(s3));
  cek((await page.textContent("tbody tr:nth-child(2) .chip-ind-wadah")).includes("Lebih dari 8 sesi/bulan"), "indikator tampil sebagai chip berarti (gaya opsi 3)");
  cek((await page.$$("tbody .label + .status-chip, tbody .status-chip + .label")).length === 0, "baris selesai hanya menampilkan label hasil");
  const kaki = await page.textContent(".catatan-kaki");
  cek(kaki.includes("Model anomali menandai") && !kaki.includes("Skor pola"), "catatan kaki menjelaskan model anomali, bukan skor pola", kaki);
  cek((await page.textContent(".keterangan-pemicu")).includes("aturan (dua indikator atau lebih) atau model anomali"), "keterangan antrean menyebut aturan ATAU model");
  const atas = await page.$$eval("tbody tr .nama-berkas b", (el) => el.slice(0, 2).map((x) => x.textContent));
  cek(atas[0] === "Slamet Riyadi" && atas[1] === "Andi Pratama", "urutan antrean tetap: S6 lalu S1", atas.join(", "));
  cek((await namaAntre()).length === 12, "12 pasien antre, termasuk dua yang hanya dipilih model", (await namaAntre()).join(", "));
  const kpi = await page.textContent(".kartu-angka .kpi:first-child");
  cek(kpi.includes("Pasien dipilih") && kpi.includes("32") && kpi.includes("30 aturan + 2 model"), "kartu angka: 32 dipilih (30 aturan + 2 model)", kpi.replace(/\s+/g, " "));
  cek(await page.evaluate(() => window.DATA3.UJI.length === 0 && window.DATA3.UJI_POLA.length === 0 && window.DATA3.UJI_ANOMALI.length === 0), "uji mandiri data simulasi (label, pola, model anomali) bersih");

  console.log("\nPasien yang hanya dipilih model");
  await page.click('tbody tr:has(b:text-is("Sari Wulandari")) a');
  await page.waitForSelector(".pola-kartu");
  const m1kartu = await page.textContent(".pola-kartu");
  cek(m1kartu.includes("Mengapa dipilih") && m1kartu.includes("tidak ada indikator aktif") && m1kartu.includes("tanpa rujukan FKTP") && m1kartu.includes("kab/kota lain"), "kartu M1 menjelaskan alasan model: tanpa rujukan dan lintas kab/kota", m1kartu.replace(/\s+/g, " ").slice(0, 260));
  cek(await page.isVisible("text=Sari Wulandari belum ditelepon"), "kartu M1 menyatakan belum ditelepon");
  cek(!/fraud|curang/i.test(m1kartu), "alasan model tanpa kata fraud atau curang");
  await page.goto(TARGET + "#/autentik");
  await page.waitForSelector("#stripStatus");

  console.log("\nS1 sampai kartu bukti");
  await page.click('[data-aksi="telepon"][data-id="S1"]');
  await page.waitForSelector(".status-chip--wa");
  cek((await namaAntre()).length === 11, "setelah Dahulukan, S1 keluar dari antre", (await namaAntre()).join(", "));
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
  const kartuS1 = await page.textContent(".pola-kartu");
  cek((await page.textContent(".pola-kartu h2")) === "Mengapa dipilih" && (await page.textContent(".pola-kartu .chip-dipilih")) === "Aturan + model", "kartu bukti S1: Mengapa dipilih, aturan + model");
  cek(kartuS1.includes("3 indikator aktif") && kartuS1.includes("Model anomali:") && kartuS1.includes("hari Minggu"), "kartu S1 memuat alasan aturan dan model", kartuS1.replace(/\s+/g, " ").slice(0, 260));
  cek(!/fraud|curang/i.test(kartuS1), "bagian Mengapa dipilih tanpa kata fraud atau curang");
  await page.goto(TARGET + "#/kartu/R3");
  await page.waitForSelector(".pola-kartu");
  cek((await page.textContent(".pola-kartu .chip-dipilih")) === "Aturan" && (await page.textContent(".pola-kartu")).includes("model tidak menandainya"), "kartu R3: hanya aturan, model tidak menandai");
  await page.goto(TARGET + "#/ringkasan-rs");
  await page.waitForSelector(".baris-pembanding");
  const pembanding = await page.$$eval(".baris-pembanding", (el) => el.map((x) => x.textContent.trim()));
  cek(pembanding.length === 5 && pembanding[0].includes("Terpicu 39,7% · rata-rata RS sejenis 1,5% · batas 95% RS sejenis 8,2%"), "Ringkasan RS: baris pembanding RS sejenis nasional", pembanding[0]);
  cek((await page.$$(".baris-pembanding .lencana-pola")).length === 2 && pembanding[0].includes("Di atas 95% RS sejenis") && pembanding[0].includes("Jauh di atas harapan"), "hanya RS Melati berlencana: di atas 95% RS sejenis dan jauh di atas harapan corong");
  cek(pembanding[0].includes("dipilih 27, harapan menurut umur pasien 2,3") && pembanding.slice(1).every((t) => t.includes("harapan menurut umur pasien")), "Ringkasan RS: corong dipilih dibanding harapan menurut umur", pembanding[0]);
  const kinerja = await page.textContent(".kinerja-pola");
  cek(kinerja.includes("Sumber pemilihan dan hasil panggilan") && kinerja.includes("2 dari 2 panggilan yang ditandai model berakhir Tidak sesuai") && kinerja.includes("1 dari 3 panggilan yang hanya dipilih aturan") && kinerja.includes("5 panggilan terjawab"), "kartu sumber pemilihan dan hasil panggilan", kinerja);
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
