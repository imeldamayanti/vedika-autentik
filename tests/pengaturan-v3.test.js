/* Uji halaman Pengaturan Vedika Autentik v3 (nomor penelepon, pesan pertama, pesan cadangan, aturan panggilan,
   uji coba, riwayat perubahan) di mode simulasi: API diputus, pengaturan disimpan di localStorage.

   Pemakaian:
     python3 -m http.server 8899          # dari akar repositori
     node tests/pengaturan-v3.test.js     # TARGET_URL=https://... untuk menguji hasil deploy
   Variabel opsional: CHROME=/path/ke/chrome, PW_HEADLESS=false */

const { chromium } = require("playwright");

const TARGET = (process.env.TARGET_URL || "http://localhost:8899/").replace(/#.*$/, "");

const lolos = [];
const gagal = [];
const cek = (syarat, nama, detail) => {
  if (syarat) { lolos.push(nama); console.log("  LULUS  " + nama); }
  else { gagal.push(nama); console.log("  GAGAL  " + nama + (detail ? " :: " + detail : "")); }
};

const PESAN_S1 = "Halo Andi Pratama, kami dari BPJS Kesehatan. Sekitar 1 menit lagi kami akan menelepon dari nomor 0800-0000-0165 untuk konfirmasi singkat layanan fisioterapi Andi Pratama di RS Melati Sehat bulan Agustus. Teleponnya sekitar 2 menit, mohon diangkat.\n\n" +
  "Ini bukan tagihan. Kami tidak akan meminta NIK, kode OTP, nomor rekening, atau pembayaran. Ragu pesan ini asli? Hubungi Care Center 165.";

(async () => {
  const browser = await chromium.launch({ headless: process.env.PW_HEADLESS !== "false", executablePath: process.env.CHROME || undefined });
  const konteks = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await konteks.newPage();
  const galat = [];
  page.on("pageerror", (e) => galat.push(e.message));
  page.on("dialog", (d) => d.accept());
  await page.route("**/api/v1/**", (rute) => rute.abort());

  await page.goto(TARGET);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForSelector("#stripStatus");

  console.log("\nTemplat pesan (data-v3.js)");
  const D = (fn, arg) => page.evaluate(fn, arg);
  cek((await D(() => window.DATA3.pesanPemberitahuan(window.DATA3.SKENARIO.S1))) === PESAN_S1, "pesan pertama bawaan memakai teks Richard, placeholder terisi");
  cek((await D(() => window.DATA3.cekTemplat("Halo {{nama}}, hubungi {{nomor}} {{menit}} {{pasien}}", "wa"))).length === 0, "templat sah tidak punya galat");
  cek((await D(() => window.DATA3.cekTemplat("Halo {{nama}} {{menit}} {{pasien}}", "wa"))).some((g) => g.includes("{{nomor}}")), "placeholder {{nomor}} wajib ada");
  cek((await D(() => window.DATA3.cekTemplat("Halo {{nama}} {{nomor}} {{menit}} {{pasien}} {{xyz}}", "wa"))).some((g) => g.includes("{{xyz}}")), "placeholder tak dikenal ditolak");
  cek((await D(() => window.DATA3.cekTemplat("Halo {{nama}} {{nomor}} {{menit}} {{pasien}} https://contoh.id", "wa"))).some((g) => g.includes("tautan")), "tautan ditolak");
  cek((await D(() => window.DATA3.cekTemplat("x".repeat(900) + "{{nama}} {{nomor}} {{menit}} {{pasien}}", "wa"))).some((g) => g.includes("karakter")), "templat terlalu panjang ditolak");
  cek((await D(() => window.DATA3.cekTemplat("Berapa kali {{pasien}}", "cadangan"))).length === 0 && (await D(() => window.DATA3.cekTemplat("Halo", "cadangan"))).length > 0, "templat cadangan wajib memuat {{pasien}}");
  cek((await D(() => [0, 1, 160, 161, 320, 321].map((n) => window.DATA3.jumlahSms(n)))).join() === "0,1,1,2,2,3", "hitung SMS: 160 karakter per pesan");
  cek((await D(() => { const D = window.DATA3; D.ubahPengaturan({ templat_wa: "Halo {{nama}} {{nomor}} {{menit}} {{pasien}}" }); const t = D.pesanPemberitahuan(D.SKENARIO.S1); D.ubahPengaturan({ templat_wa: D.PENGATURAN_BAWAAN.templat_wa }); return t.includes("NIK") && t.includes("Care Center 165"); })), "paragraf keamanan selalu ikut terkirim, walau templat diubah");
  const dipilih = (aturan) => page.evaluate((a) => window.DATA3.hitungDipilih(a), aturan);
  cek((await dipilih({})) === 16, "indikator pemicu bawaan: 16 pasien dipilih", String(await dipilih({})));
  cek((await dipilih({ indikator_min: 3, sertakan_model: false })) === 7, "minimal 3 indikator tanpa model: 7 pasien", String(await dipilih({ indikator_min: 3, sertakan_model: false })));
  cek((await dipilih({ indikator_min: 2, sertakan_model: false })) === 14, "minimal 2 indikator tanpa model: 14 pasien", String(await dipilih({ indikator_min: 2, sertakan_model: false })));

  console.log("\nRute dan menu");
  const menu = await page.$$eval(".nav a, .nav button", (el) => el.map((x) => x.textContent.trim()));
  cek(menu.includes("Pengaturan"), "menu bawah memuat Pengaturan", menu.join(" | "));
  await page.click('.nav a[href="#/pengaturan"]');
  await page.waitForSelector("#kartu-nomor");
  cek((await page.title()).startsWith("Pengaturan"), "judul tab Pengaturan", await page.title());
  cek((await page.textContent(".judul-laman")).trim() === "Pengaturan" && (await page.$$("h1")).length === 1, "judul Pengaturan satu h1 di bilah atas");
  cek((await page.getAttribute('.nav a[href="#/pengaturan"]', "aria-current")) === "page", "menu Pengaturan ditandai aktif");
  for (const id of ["nomor", "pesan", "cadangan", "panggilan", "uji", "riwayat"]) cek(!!(await page.$("#kartu-" + id)), "kartu " + id + " ada");

  console.log("\nKartu nomor penelepon");
  cek((await page.textContent("#kartu-nomor .nomor-aktif")).trim() === "0800-0000-0165", "menampilkan nomor aktif");
  await page.click('#kartu-nomor [data-aksi="ganti-nomor"]');
  await page.fill('[data-f="nomor_baru"]', "abc");
  cek(await page.isDisabled('[data-aksi="simpan-nomor"]'), "nomor tidak sah menonaktifkan tombol simpan");
  await page.fill('[data-f="nomor_baru"]', "0812-3456-7890");
  cek(await page.isDisabled('[data-aksi="simpan-nomor"]'), "nomor sah tanpa alasan masih nonaktif");
  await page.fill('[data-f="alasan_nomor"]', "Nomor tim penguji");
  cek(!(await page.isDisabled('[data-aksi="simpan-nomor"]')), "nomor sah dengan alasan: tombol simpan menyala");
  await page.click('[data-aksi="simpan-nomor"]');
  cek((await page.textContent("#kartu-nomor .nomor-aktif")).trim() === "0812-3456-7890", "nomor baru tampil sebagai nomor aktif");
  cek((await page.textContent("#kartu-pesan .pratinjau-wa")).includes("0812-3456-7890"), "pratinjau pesan memakai nomor baru");
  cek((await page.textContent("#kartu-riwayat")).includes("Nomor penelepon") && (await page.textContent("#kartu-riwayat")).includes("Nomor tim penguji"), "riwayat mencatat penggantian nomor beserta alasan");
  await page.reload();
  await page.waitForSelector("#kartu-nomor");
  cek((await page.textContent("#kartu-nomor .nomor-aktif")).trim() === "0812-3456-7890", "nomor tetap setelah muat ulang");

  console.log("\nKartu pesan pertama");
  const kotak = '[data-f="templat_wa"]';
  cek((await page.inputValue(kotak)).startsWith("Halo {{nama}}, kami dari BPJS Kesehatan.") && !(await page.inputValue(kotak)).includes("Ini bukan tagihan"), "editor berisi teks Richard tanpa paragraf keamanan");
  const kunci = await page.textContent("#kartu-pesan .paragraf-kunci");
  cek(kunci.includes("Ini bukan tagihan") && kunci.includes("Care Center 165") && (await page.$$('#kartu-pesan .paragraf-kunci textarea')).length === 0, "paragraf keamanan tampil terkunci, bukan kolom isian", kunci.slice(0, 60));
  const pratinjau = () => page.textContent("#kartu-pesan .pratinjau-wa .gelembung p");
  cek((await pratinjau()).includes("Andi Pratama") && (await pratinjau()).includes("Ini bukan tagihan"), "pratinjau HP terisi data contoh dan memuat paragraf keamanan");
  await page.fill(kotak, "Halo {{nama}}, sebentar lagi ({{menit}} menit) kami menelepon dari {{nomor}} soal {{pasien}}. Mohon diangkat.");
  cek((await pratinjau()).includes("sebentar lagi (1 menit)") && (await pratinjau()).includes("soal Andi Pratama"), "pratinjau ikut berubah saat mengetik");
  cek(!(await page.isDisabled('[data-aksi="simpan-pesan"]')), "templat sah: tombol simpan menyala");
  await page.fill(kotak, "Halo {{nama}}, kami menelepon sebentar lagi. {{menit}} {{pasien}}");
  cek(await page.isDisabled('[data-aksi="simpan-pesan"]') && (await page.textContent("#kartu-pesan .galat-templat")).includes("{{nomor}}"), "tanpa {{nomor}}: simpan nonaktif dan galat dijelaskan");
  await page.fill(kotak, "Halo {{nama}}, lihat https://contoh.id {{nomor}} {{menit}} {{pasien}}");
  cek(await page.isDisabled('[data-aksi="simpan-pesan"]') && (await page.textContent("#kartu-pesan .galat-templat")).includes("tautan"), "tautan: simpan nonaktif");
  await page.fill(kotak, "Halo {{nama}}, kami menelepon dari {{nomor}} dalam {{menit}} menit soal {{pasien}}.");
  await page.click('[data-aksi="simpan-pesan"]');
  cek((await page.inputValue(kotak)).startsWith("Halo {{nama}}, kami menelepon dari"), "templat tersimpan");
  cek((await page.evaluate(() => window.DATA3.pesanPemberitahuan(window.DATA3.SKENARIO.S1))).startsWith("Halo Andi Pratama, kami menelepon dari 0812-3456-7890 dalam 1 menit"), "pesan yang dipakai panggilan memakai templat tersimpan");
  await page.click('[data-aksi="bawaan-pesan"]');
  cek((await page.inputValue(kotak)).startsWith("Halo {{nama}}, kami dari BPJS Kesehatan."), "Kembalikan ke bawaan memulihkan teks Richard");
  await page.click('[data-aksi="simpan-pesan"]');
  await page.click('#kartu-pesan [data-f="saluran"][value="sms"]');
  cek((await page.textContent("#kartu-pesan .hitung-karakter")).includes("SMS"), "saluran SMS menampilkan hitungan SMS per 160 karakter", await page.textContent("#kartu-pesan .hitung-karakter"));
  await page.click('#kartu-pesan [data-f="saluran"][value="wa"]');
  await page.click('[data-aksi="sisip"][data-ph="rs"]');
  cek((await page.inputValue(kotak)).includes("{{rs}}"), "chip placeholder menyisipkan {{rs}} ke editor");
  await page.click('[data-aksi="bawaan-pesan"]');

  console.log("\nKartu pesan cadangan");
  const kotakCad = '[data-f="templat_cadangan"]';
  cek((await page.inputValue(kotakCad)).startsWith("Kami belum berhasil menelepon.") && !(await page.inputValue(kotakCad)).includes("1) 1–2 kali"), "editor cadangan berisi teks tanpa daftar pilihan");
  cek((await page.textContent("#kartu-cadangan .paragraf-kunci")).includes("1) 1–2 kali") && (await page.textContent("#kartu-cadangan .paragraf-kunci")).includes("6) tidak pernah terapi di sana"), "pilihan jawaban 1–6 terkunci");
  await page.fill(kotakCad, "Halo");
  cek(await page.isDisabled('[data-aksi="simpan-cadangan"]'), "cadangan tanpa {{pasien}}: simpan nonaktif");
  await page.click('[data-aksi="bawaan-cadangan"]');

  console.log("\nKartu panggilan");
  cek((await page.inputValue('[data-f="jam_mulai"]')) === "08:00" && (await page.inputValue('[data-f="jam_selesai"]')) === "16:00", "jam panggilan bawaan 08:00 sampai 16:00");
  cek((await page.textContent("#kartu-panggilan .efek-antrean")).includes("16 pasien"), "efek indikator bawaan: 16 pasien", await page.textContent("#kartu-panggilan .efek-antrean"));
  await page.fill('[data-f="indikator_min"]', "3");
  await page.uncheck('[data-f="sertakan_model"]');
  cek((await page.textContent("#kartu-panggilan .efek-antrean")).includes("7 pasien"), "minimal 3 indikator tanpa model: 7 pasien", await page.textContent("#kartu-panggilan .efek-antrean"));
  await page.fill('[data-f="jam_mulai"]', "17:00");
  cek(await page.isDisabled('[data-aksi="simpan-panggilan"]') && (await page.textContent("#kartu-panggilan .galat-templat")).includes("jam"), "jam mulai setelah jam selesai: simpan nonaktif");
  await page.fill('[data-f="jam_mulai"]', "09:00");
  await page.fill('[data-f="batas_harian"]', "25");
  await page.selectOption('[data-f="hari"]', "senin_sabtu");
  await page.click('[data-aksi="simpan-panggilan"]');
  await page.reload();
  await page.waitForSelector("#kartu-panggilan");
  cek((await page.inputValue('[data-f="jam_mulai"]')) === "09:00" && (await page.inputValue('[data-f="batas_harian"]')) === "25" && (await page.inputValue('[data-f="hari"]')) === "senin_sabtu" && (await page.inputValue('[data-f="indikator_min"]')) === "3", "aturan panggilan tersimpan setelah muat ulang");
  cek(!(await page.isChecked('[data-f="sertakan_model"]')), "pilihan model anomali tersimpan");
  cek((await page.textContent("#kartu-riwayat")).includes("Aturan panggilan"), "riwayat mencatat perubahan aturan panggilan");

  console.log("\nKartu uji coba");
  await page.click('[data-aksi="kirim-uji"]');
  await page.waitForSelector("#kartu-uji .hasil-uji li");
  await page.waitForFunction(() => document.querySelectorAll("#kartu-uji .hasil-uji li.selesai").length >= 2, null, { timeout: 8000 });
  const hasil = await page.$$eval("#kartu-uji .hasil-uji li", (el) => el.map((x) => x.textContent.replace(/\s+/g, " ").trim()));
  cek(hasil.some((t) => t.includes("Pesan terkirim")) && hasil.some((t) => t.includes("Telepon tersambung")), "uji coba menampilkan hasil pesan dan telepon", hasil.join(" | "));
  cek((await page.textContent("#kartu-riwayat")).includes("Uji coba"), "uji coba tercatat di riwayat");

  console.log("\nKetahanan");
  await page.evaluate(() => localStorage.setItem("vedika.pengaturan.v1", JSON.stringify({ pengaturan: { indikator_aktif: null, jam_mulai: 5, nomor_penelepon: "0812-3456-7890" }, riwayat: "rusak" })));
  await page.goto(TARGET + "#/autentik");
  await page.reload();
  await page.goto(TARGET + "#/pengaturan");
  await page.waitForSelector("#kartu-panggilan");
  cek((await page.inputValue('[data-f="jam_mulai"]')) === "08:00" && (await page.textContent("#kartu-nomor .nomor-aktif")).trim() === "0812-3456-7890", "data tersimpan yang rusak diabaikan per kunci, kunci sah tetap dipakai");
  await page.goto(TARGET + "#/autentik");
  await page.waitForSelector("#stripStatus");
  await page.click('[data-aksi="ulang-demo"]');
  await page.goto(TARGET + "#/pengaturan");
  await page.waitForSelector("#kartu-nomor");
  cek((await page.textContent("#kartu-nomor .nomor-aktif")).trim() === "0812-3456-7890", "Mulai ulang demo tidak menghapus pengaturan");
  await page.goto(TARGET + "#/autentik");
  await page.waitForSelector("#stripStatus");
  await page.click('[data-aksi="telepon"][data-id="S1"]');
  await page.goto(TARGET + "#/panggilan/S1");
  await page.waitForSelector("#panggilan");
  await page.click('[data-aksi="wa"][data-jenis="pemberitahuan"]').catch(() => {});
  const wa = await page.textContent("#modalWa .gelembung.dari-bpjs p").catch(() => "");
  cek(wa.includes("0812-3456-7890") && wa.includes("Ini bukan tagihan"), "layar WA di panggilan memakai nomor dan pesan dari Pengaturan", wa.slice(0, 80));
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(TARGET + "#/pengaturan");
  await page.waitForSelector("#kartu-nomor");
  const lebih = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  cek(lebih <= 1, "tanpa geser samping di Pengaturan (390 px)", "melebar " + lebih + "px");

  cek(galat.length === 0, "tidak ada galat JavaScript", galat.slice(0, 3).join(" | "));
  await browser.close();
  console.log("\n" + lolos.length + " lulus, " + gagal.length + " gagal");
  process.exit(gagal.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
