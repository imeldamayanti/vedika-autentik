/* Klien API Vedika Autentik v3 (Kontrak A, docs/api-contract-v3.md) beserta adaptor ke bentuk yang dipakai app-v3.js.

   Bentuk objek di app-v3.js sama dengan data-v3.js (tanggal berupa angka hari, transkrip [A/P, detik, teks],
   tandaTanggal berkunci hari), jadi layar cukup mengganti sumber data. Perbedaan bentuk ditangani di sini.

   Alamat API: window.VEDIKA_API_BASE bila diisi; di localhost http://localhost:8000; di produksi kosong
   (satu origin, Vercel meneruskan /api/* ke API). Tanpa login di prototipe. Bila API mati, app-v3.js memakai
   data-v3.js dan simulasinya (data-v3.js tidak dihapus). */

(function (global) {
  "use strict";

  const lokal = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  const BASE = global.VEDIKA_API_BASE != null ? global.VEDIKA_API_BASE : (lokal ? "http://localhost:8000" : "");
  const PREFIX = "/api/v1";
  const url = (p) => BASE + p;

  /* ---------- HTTP ---------- */

  async function panggil(metode, jalur, isi) {
    const r = await fetch(url(PREFIX + jalur), {
      method: metode,
      headers: isi !== undefined ? { "Content-Type": "application/json" } : {},
      body: isi !== undefined ? JSON.stringify(isi) : undefined,
      signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) {
      let g = null;
      try { g = (await r.json()).galat; } catch (e) { /* bukan JSON galat seragam */ }
      const e = new Error(g ? g.pesan : "HTTP " + r.status);
      e.kode = g ? g.kode : "http_" + r.status;
      e.status = r.status;
      throw e;
    }
    return r.status === 204 ? null : r.json();
  }

  /* Sehat berarti API dan database ok. Pembaca jawaban yang mati tidak menghentikan demo: label jadi Tidak yakin. */
  async function sehat() {
    try {
      const r = await fetch(url(PREFIX + "/kesehatan"), { signal: AbortSignal.timeout(2500) });
      if (!r.ok) return false;
      const j = await r.json();
      return j.api === "ok" && j.db === "ok";
    } catch (e) { return false; }
  }

  const antrean = () => panggil("GET", "/antrean");
  const panggilan = (id) => panggil("GET", "/panggilan/" + encodeURIComponent(id));
  const ringkasanRs = () => panggil("GET", "/ringkasan-rs");
  const keputusan = () => panggil("GET", "/keputusan");
  const ubahPengaturan = (isi) => panggil("PUT", "/pengaturan", isi);
  const mulai = (id) => panggil("POST", "/panggilan/" + encodeURIComponent(id) + "/mulai");
  const putuskan = (id, isi) => panggil("POST", "/panggilan/" + encodeURIComponent(id) + "/keputusan", isi);
  const resetDemo = () => panggil("POST", "/demo/reset");

  /* ---------- format ---------- */

  const BULAN_PENDEK = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  const BULAN_PANJANG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
  const HARI = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];

  /* API selalu membalas waktu ISO berzona WIB (+07:00); jam dibaca apa adanya dari teksnya, tanpa zona peramban. */
  const angkaHari = (iso) => parseInt(iso.slice(8, 10), 10);
  const jamTeks = (iso) => (iso ? iso.slice(11, 13) + "." + iso.slice(14, 16) : "");
  const waktuTeks = (iso) => (iso ? angkaHari(iso) + " " + BULAN_PENDEK[parseInt(iso.slice(5, 7), 10) - 1] + " " + iso.slice(0, 4) + ", " + jamTeks(iso) : "");

  function hariIni(iso) {
    const d = new Date(iso.slice(0, 10) + "T00:00:00Z");
    return HARI[d.getUTCDay()] + ", " + angkaHari(iso) + " " + BULAN_PANJANG[parseInt(iso.slice(5, 7), 10) - 1] + " " + iso.slice(0, 4);
  }

  /* ---------- adaptor ---------- */

  /* Kelompok status tampilan (chip di tabel antrean), tabel "Kelompok status tampilan" di kontrak. */
  const KELOMPOK = { antre: "antre", wa_terkirim: "wa", menelepon: "menelepon", tersambung: "menelepon", merekam: "menelepon", membaca_jawaban: "menelepon", selesai: "selesai", tidak_terhubung: "tidak_terhubung" };
  const SKENARIO_SUARA = ["S1", "S2", "S3", "S4", "S6", "S8"];

  function keBaris(b) {
    return {
      id: b.id, pasien: b.pasien, umur: b.umur, rs: b.rs, namaRs: b.nama_rs, ditagih: b.ditagih, indikator: b.indikator,
      penerima: b.penerima, status: b.status, st: KELOMPOK[b.status], label: b.label, keputusanTindakan: b.keputusan_tindakan,
      prioritas: b.prioritas, percobaan: b.percobaan
    };
  }

  function keKeputusan(k) {
    if (!k) return null;
    return { tindakan: k.tindakan, alasan: k.alasan, ikutSaran: k.ikut_saran, oleh: k.verifikator, waktu: waktuTeks(k.waktu) };
  }

  /* Penerima bilang tidak pernah datang (hadir false) tanpa angka: versinya 0 sesi, selisihnya seluruh tagihan. */
  function jawabanTerhitung(d) {
    const j = d.jawaban;
    if (!j || j.hadir !== false || j.jumlah_maks != null) return { jawaban: j, selisih: d.selisih };
    return { jawaban: Object.assign({}, j, { jumlah_min: 0, jumlah_maks: 0 }), selisih: d.selisih != null ? d.selisih : d.ditagih };
  }

  function kePasien(d) {
    const skenario = (/^CALL-P-(S\d)-/.exec(d.id) || [])[1];
    const hitung = jawabanTerhitung(d);
    const tanda = {};
    Object.keys(d.tanda_tanggal).forEach((iso) => { tanda[angkaHari(iso)] = d.tanda_tanggal[iso]; });
    return {
      id: d.id, sumber: d.sumber, pasien: d.pasien, umur: d.umur, rs: d.rs, namaRs: d.nama_rs, ditagih: d.ditagih,
      tanggal: d.tanggal.map(angkaHari), tandaTanggal: tanda, indikator: d.indikator, tanggalLibur: d.tanggal_libur.map(angkaHari),
      penerima: d.penerima, status: d.status, st: KELOMPOK[d.status], percobaan: d.percobaan, log: d.log,
      waktu: waktuTeks(d.waktu), waktuIso: d.waktu, durasi: d.durasi,
      transkrip: d.transkrip.map((t) => [t.pembicara === "ai" ? "A" : "P", t.detik, t.teks]),
      tangkapan: d.tangkapan_sementara, jawaban: hitung.jawaban, label: d.label, alasan: d.alasan,
      selisih: hitung.selisih, toleransi: d.toleransi, saran: d.saran,
      rekaman: d.rekaman ? url(d.rekaman) : null, hapusPada: d.hapus_pada,
      suara_langsung: skenario && SKENARIO_SUARA.indexOf(skenario) >= 0 ? "assets/rekaman/" + skenario : null,
      konteksRs: d.konteks_rs, pesanWa: d.pesan_wa, keputusan: keKeputusan(d.keputusan), galatPembaca: d.galat_pembaca
    };
  }

  /* Satu bentuk untuk layar Ringkasan RS, sama dengan hasil ringkasanRs() di data-v3.js ditambah daftar rinci. */
  function keRingkasan(r) {
    return {
      jumlah: r.panggilan_selesai,
      rs: r.rs.map((x) => ({
        id: x.id_rs, nama: x.nama, aktif: x.aktif, terpicu: x.terpicu, persen: x.persen,
        c: { sesuai: x.sesuai, tidak_sesuai: x.tidak_sesuai, tidak_yakin: x.tidak_yakin, tidak_terhubung: x.tidak_terhubung, menolak: x.menolak, terjawab: x.terjawab, rasio: x.rasio, status: x.status },
        daftar: x.panggilan
      }))
    };
  }

  function keRiwayat(daftar) {
    return daftar.filter((k) => k.terkini).map((k) => ({
      id: k.panggilan_id, pasien: k.pasien, umur: k.umur, namaRs: k.nama_rs, label: k.label,
      tindakan: k.tindakan, ikutSaran: k.ikut_saran, alasan: k.alasan, oleh: k.verifikator, waktu: waktuTeks(k.waktu)
    }));
  }

  global.API3 = {
    BASE, url, sehat, antrean, panggilan, ringkasanRs, keputusan, ubahPengaturan, mulai, putuskan, resetDemo,
    keBaris, kePasien, keRingkasan, keRiwayat, hariIni, waktuTeks, jamTeks
  };
})(window);
