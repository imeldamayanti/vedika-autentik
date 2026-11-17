/* Initial load in v3 API mode: the /kesehatan answer arrives before /antrean, so the screen must not be
   re-rendered while M.antrean is still null ("Cannot read properties of null").

   The API is faked with page.route (no backend): /kesehatan answers immediately, /antrean is delayed.

   Usage:
     python3 -m http.server 8899          # from the repo root
     node tests/alur-v3-api-awal.test.js
   Optional env: CHROME=/path/to/chrome, PW_HEADLESS=false, QUEUE_DELAY_MS=1500 */

const { chromium } = require("playwright");

const TARGET = (process.env.TARGET_URL || "http://localhost:8899/").replace(/#.*$/, "");
const QUEUE_DELAY_MS = parseInt(process.env.QUEUE_DELAY_MS || "1500", 10);
const SETTLE_MS = QUEUE_DELAY_MS + 1500;

const lolos = [];
const gagal = [];
const cek = (syarat, nama, detail) => {
  if (syarat) { lolos.push(nama); console.log("  LULUS  " + nama); }
  else { gagal.push(nama); console.log("  GAGAL  " + nama + (detail ? " :: " + detail : "")); }
};

const DONE_ID = "CALL-P-T1-2026-08";
const QUEUED_ID = "CALL-P-T2-2026-08";
const DONE_PATIENT = "Rahmat Hidayat";
const QUEUED_PATIENT = "Dewi Lestari";

const health = { api: "ok", db: "ok", pembaca: "ok", versi_aturan: "2026.10" };

const queueRow = (over) => Object.assign({
  umur: 54, rs: "RS01", nama_rs: "RS Melati Sehat", ditagih: 11, indikator: ["I1", "I2"],
  label: null, keputusan_tindakan: null, prioritas: false, percobaan: 0, coba_lagi_setelah: null,
  dipilih: "aturan"
}, over);

const queue = {
  bulan: "2026-08",
  angka: {
    pasien_aktif: 300, terpicu: 30, dipilih: 32, hanya_model: 2, sudah_ditelepon: 1, tidak_sesuai: 1,
    rs_perlu_klarifikasi: 0, antre: 1, menunggu_keputusan: 1
  },
  pengaturan: {
    mode_otomatis: false, jeda: false, jam_mulai: "09:00", jam_selesai: "17:00",
    jeda_wa_menit: 1, jeda_percobaan_menit: 2,
    dalam_jam: true, waktu_server: "2026-10-06T09:20:00+07:00",
    stasiun: { aktif: true, siap: true, alasan: null, perangkat: "Pixel 7", terakhir_terlihat: "2026-10-06T09:19:58+07:00" }
  },
  daftar_rs: [{ id_rs: "RS01", nama: "RS Melati Sehat" }, { id_rs: "RS02", nama: "RSU Bakti Mulia" }],
  baris: [
    queueRow({ id: QUEUED_ID, pasien: QUEUED_PATIENT, umur: 47, penerima: { nama: QUEUED_PATIENT, hubungan: "peserta" }, status: "antre", dipilih: "keduanya" }),
    queueRow({ id: DONE_ID, pasien: DONE_PATIENT, penerima: { nama: DONE_PATIENT, hubungan: "peserta" }, status: "selesai", label: "tidak_sesuai", percobaan: 1 })
  ]
};

const callDetail = {
  id: DONE_ID, sumber: "panggilan", pasien: DONE_PATIENT, umur: 54, rs: "RS01", nama_rs: "RS Melati Sehat", bulan: "2026-08", ditagih: 11,
  tanggal: ["2026-08-03", "2026-08-04", "2026-08-06", "2026-08-10", "2026-08-11", "2026-08-13", "2026-08-16", "2026-08-17", "2026-08-20", "2026-08-24", "2026-08-27"],
  tanda_tanggal: { "2026-08-16": "Minggu", "2026-08-17": "Libur nasional" },
  indikator: ["I1", "I2"],
  dipilih: "aturan",
  anomali: null,
  tanggal_libur: ["2026-08-16", "2026-08-17"],
  penerima: { nama: DONE_PATIENT, hubungan: "peserta" },
  status: "selesai", percobaan: 1, waktu: "2026-10-06T08:12:08+07:00",
  log: [
    { status: "wa_terkirim", waktu: "2026-10-06T08:11:00+07:00", percobaan: 1, catatan: null },
    { status: "menelepon", waktu: "2026-10-06T08:12:00+07:00", percobaan: 1, catatan: null },
    { status: "tersambung", waktu: "2026-10-06T08:12:08+07:00", percobaan: 1, catatan: null },
    { status: "merekam", waktu: "2026-10-06T08:12:08+07:00", percobaan: 1, catatan: null },
    { status: "membaca_jawaban", waktu: "2026-10-06T08:13:40+07:00", percobaan: 1, catatan: null },
    { status: "selesai", waktu: "2026-10-06T08:13:45+07:00", percobaan: 1, catatan: null }
  ],
  durasi: 92,
  transkrip: [
    { detik: 0, pembicara: "ai", teks: "Selamat pagi, saya asisten otomatis dari BPJS Kesehatan." },
    { detik: 45, pembicara: "penerima", teks: "Tiga kali saja." }
  ],
  tangkapan_sementara: null,
  jawaban: {
    status_panggilan: "terjawab", penerima: "peserta", hubungan: null, hadir: true,
    jumlah_min: 3, jumlah_maks: 3, keyakinan: "tinggi", tanda_bahaya: [],
    membantah_tanggal_libur: true, kutipan_kunci: "Tiga kali saja.",
    ringkasan: "Peserta menjalani 3 sesi di bulan Agustus."
  },
  label: "tidak_sesuai",
  alasan: "Ditagih 11 sesi, versi penerima paling banyak 3 sesi (selisih 8).",
  selisih: 8, toleransi: 2, saran: "klarifikasi",
  rekaman: null, hapus_pada: null,
  konteks_rs: { rs: "RS01", tidak_sesuai: 1, terjawab: 1, status: "Normal" },
  pesan_wa: { dari: "0800-0000-0165", pemberitahuan: "Halo " + DONE_PATIENT + ". Ini BPJS Kesehatan.", cadangan: null },
  keputusan: null,
  galat_pembaca: null
};

const hospitalSummary = (id, nama, over) => Object.assign({
  id_rs: id, nama, aktif: 68, terpicu: 0, persen: 0,
  funnel: { patient_months: 68, selected: 0, expected: 2.3, z: -1.2, position: "within" },
  sesuai: 0, tidak_sesuai: 0, tidak_yakin: 0, tidak_terhubung: 0, menolak: 0, terjawab: 0, rasio: 0, status: "Normal",
  panggilan: []
}, over);

const summary = {
  bulan: "2026-08",
  aturan: "Perlu klarifikasi RS jika tidak sesuai >= 3 DAN rasio tidak sesuai/terjawab >= 10%",
  panggilan_selesai: 1,
  kinerja_model: { n: 1, model: 0, model_tidak_sesuai: 0, aturan: 1, aturan_tidak_sesuai: 1 },
  rs: [
    hospitalSummary("RS01", "RS Melati Sehat", {
      terpicu: 2, persen: 2.9, tidak_sesuai: 1, terjawab: 1, rasio: 1,
      funnel: { patient_months: 68, selected: 2, expected: 2.3, z: -0.2, position: "within" },
      panggilan: [{ id: DONE_ID, pasien: DONE_PATIENT, label: "tidak_sesuai", ditagih: 11, jumlah_min: 3, jumlah_maks: 3, selisih: 8 }]
    }),
    hospitalSummary("RS02", "RSU Bakti Mulia")
  ]
};

const decisions = [];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const json = (route, body) => route.fulfill({
  status: 200,
  contentType: "application/json",
  headers: { "access-control-allow-origin": "*" },
  body: JSON.stringify(body)
});

/* Fake API: health answers immediately, the queue answers late, so the health callback in segarkan() wins the race. */
async function mockApi(page) {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/kesehatan") return json(route, health);
    if (path === "/api/v1/antrean") { await sleep(QUEUE_DELAY_MS); return json(route, queue); }
    if (path === "/api/v1/ringkasan-rs") return json(route, summary);
    if (path === "/api/v1/keputusan") return json(route, decisions);
    if (path === "/api/v1/panggilan/" + DONE_ID) return json(route, callDetail);
    return route.fulfill({ status: 404, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify({ galat: { kode: "panggilan_tidak_ada", pesan: "tidak ada" } }) });
  });
}

async function openFresh(browser, hash) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await mockApi(page);
  await page.goto(TARGET + hash);
  await page.waitForTimeout(SETTLE_MS);
  return { context, page, errors };
}

(async () => {
  const browser = await chromium.launch({ headless: process.env.PW_HEADLESS !== "false", executablePath: process.env.CHROME || undefined });

  console.log("\nMode API, /antrean tiba " + QUEUE_DELAY_MS + " ms setelah /kesehatan");
  for (const [hash, screen] of [["#/autentik", "antrean"], ["#/ringkasan-rs", "ringkasan RS"], ["#/kartu/" + DONE_ID, "kartu bukti"]]) {
    const { context, page, errors } = await openFresh(browser, hash);
    cek(errors.length === 0, "tanpa galat JavaScript saat memuat " + screen + " (" + hash + ")", errors.slice(0, 3).join(" | "));
    const text = await page.innerText("body");
    if (hash === "#/autentik") {
      cek(text.includes(QUEUED_PATIENT) && text.includes(DONE_PATIENT), "antrean menampilkan data API, bukan simulasi", text.replace(/\s+/g, " ").slice(0, 200));
      const badges = await page.$$eval(".lencana-simulasi", (el) => el.map((x) => x.textContent.trim()));
      cek(badges.length === 0, "tanpa tanda Simulasi atau Prototipe di mode API", badges.join(" | "));
    }
    if (hash.startsWith("#/kartu/")) cek(text.includes(DONE_PATIENT), "kartu bukti menampilkan pasien dari API", text.replace(/\s+/g, " ").slice(0, 200));
    await context.close();
  }

  await browser.close();
  console.log("\n" + lolos.length + " lulus, " + gagal.length + " gagal");
  process.exit(gagal.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
