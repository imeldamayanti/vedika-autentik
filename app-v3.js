/* Vedika Autentik v3: simulasi konfirmasi suara peserta di aplikasi verifikasi klaim.

   Alur: masuk → beranda → Autentik (antrean konfirmasi) → panggilan berlangsung →
   kartu bukti → keputusan verifikator → ringkasan rumah sakit → riwayat.

   Tidak ada telepon atau AI yang berjalan di sini. Dua sumber data:
   - API (api-v3.js, Kontrak A v3): dipakai bila API dan database sehat saat halaman dimuat. Agen suara dan
     pembaca jawaban di belakangnya masih stub, jadi semua layar tetap berlabel Simulasi. Layar menyegarkan
     data tiap 1 detik.
   - Simulasi (data-v3.js): jalur cadangan bila API mati atau terputus di tengah jalan. Panggilan adalah
     simulasi dari data tulisan tangan. */

(function () {
  "use strict";

  const D = window.DATA3;
  const A3 = window.API3;

  /* Mode API. hidup = data dari API; baris = baris antrean; detail = panggilan yang pernah dibuka (kunci id API);
     lalu = status terakhir tiap panggilan (untuk toast saat selesai). Selebihnya penanda sekali-jalan. */
  const M = {
    hidup: false, antrean: null, baris: [], detail: {}, ringkasan: null, riwayat: null, sig: {}, gagal: 0, sibuk: false,
    timer: null, lalu: {}, tidakAda: {}, lihat: {}, terisi: {}, waDibuka: {}, kartuDibuka: {}, waktuServer: null
  };

  /* ================================================================== util */

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* Ikon garis 24px, satu ketebalan untuk seluruh antarmuka. */
  const IKON = {
    perisai: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    rumah: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    berkas: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M9 15h6"/><path d="M9 11h6"/>',
    riwayat: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    ulang: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    cek: '<path d="M20 6 9 17l-5-5"/>',
    telepon: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    awas: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    jeda: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    main: '<polygon points="6 3 20 12 6 21 6 3"/>',
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    pengguna: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    kunci: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    suara: '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/><path d="M16 9a5 5 0 0 1 0 6"/><path d="M19.364 18.364a9 9 0 0 0 0-12.728"/>',
    bisu: '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/><path d="m22 9-6 6"/><path d="m16 9 6 6"/>',
    mik: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
    tambah: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    video: '<path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/>',
    lencanaCek: '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>'
  };
  const ikon = (n) => '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + IKON[n] + "</svg>";
  const logoVeritas = '<img src="assets/veritas-mark.svg" alt="" aria-hidden="true">';

  const labelChip = (kunci, besar) => '<span class="label label--' + kunci + (besar ? " label--besar" : "") + '">' + D.LABEL[kunci].nama + "</span>";
  const koma = (n) => String(n).replace(".", ",");
  const tunggal = (id) => D.SEMUA[id];

  /* Jam kerja simulasi: demo selalu terasa berlangsung pagi hari di kantor cabang. */
  const MULAI = Date.now();
  const menitSekarang = () => 9 * 60 + 20 + Math.floor((Date.now() - MULAI) / 60000);
  const formatJam = (m) => String(Math.floor(m / 60)).padStart(2, "0") + "." + String(m % 60).padStart(2, "0");

  /* ================================================================ status */

  const KUNCI_SIMPAN = "vedika.konfirmasi.v1";

  /* hasil: panggilan skenario yang sudah selesai, {id: {menit}}. Panggilan yang sedang
     berjalan tidak disimpan; setelah muat ulang ia kembali Antre.
     keputusan: {id: {tindakan, alasan, ikutSaran, oleh, waktu}} untuk panggilan skenario dan latar. */
  function statusAwal() {
    return { masuk: false, hasil: {}, keputusan: {} };
  }

  function muat() {
    try {
      const s = JSON.parse(localStorage.getItem(KUNCI_SIMPAN));
      if (s && typeof s === "object") return Object.assign(statusAwal(), s);
    } catch (e) { /* penyimpanan peramban tidak tersedia: mulai dari awal */ }
    return statusAwal();
  }

  let S = muat();
  const simpan = () => {
    try { localStorage.setItem(KUNCI_SIMPAN, JSON.stringify(S)); } catch (e) { /* diabaikan */ }
  };

  /* Status tampilan yang tidak perlu bertahan setelah halaman dimuat ulang. */
  const ui = {
    menuBuka: false, filterRs: "", filterStatus: "",
    otomatis: false, jeda: false, aktif: null, timer: null, timerBerikut: null, wa: null,
    pilihLain: false, tindakanLain: null, catatan: null, rsBuka: null, bisu: false, ubah: null
  };

  const STATUS = { antre: "Antre", wa: "WA terkirim", menelepon: "Menelepon", selesai: "Selesai", tidak_terhubung: "Tidak terhubung" };

  /* ============================================================== perute */

  /* #/beranda, #/autentik, #/panggilan/:id, #/kartu/:id, #/ringkasan-rs, #/riwayat */
  function rute() {
    const bagian = (location.hash || "").replace(/^#\/?/, "").split("/").filter(Boolean);
    return { nama: bagian[0] || "beranda", id: bagian[1] || null };
  }
  const ke = (h) => { if (location.hash !== h) location.hash = h; else gambar(true); };

  /* ======================================================= panggilan simulasi */

  /* Percakapan berjalan sepanjang rekaman (p.durasi, dari assets/rekaman/waktu.json), jadi transkrip
     dan suara seirama. Hanya jeda pesan WA ke panggilan (PRD R2.2, bawaan prototipe 1 menit) dan
     penyusunan kartu yang dipadatkan. */
  const SIM = { sambung: 4, rekam: 6, kartu: 4, jedaBerikut: 12000 };

  const tidakTerhubung = (p) => p.jawaban.status_panggilan === "tidak_terhubung";

  /* Titik waktu layar (detik sejak panggilan dimulai) untuk tiap tahap. S5 punya dua percobaan
     yang gagal lalu chat cadangan; skenario lain tersambung, merekam, lalu dibaca. */
  function titik(p) {
    if (tidakTerhubung(p)) return { coba1: 4, gagal1: 9, coba2: 12, gagal2: 17, chat: 19, kartu: 22, total: 24 };
    const akhir = SIM.rekam + p.durasi;
    return { sambung: SIM.sambung, rekam: SIM.rekam, akhir: akhir, kartu: akhir + SIM.kartu, total: akhir + SIM.kartu + 2 };
  }

  function statusSim(p, t) {
    const k = titik(p);
    if (tidakTerhubung(p)) return t >= k.chat ? "tidak_terhubung" : t >= k.coba1 ? "menelepon" : "wa";
    return t >= k.sambung ? "menelepon" : "wa";
  }

  /* ---------- sumber data: API atau simulasi ---------- */

  const BERJALAN = ["wa_terkirim", "menelepon", "tersambung", "merekam", "membaca_jawaban"];
  const berjalan = (st) => BERJALAN.indexOf(st) >= 0;
  const selesaiSt = (st) => st === "selesai" || st === "tidak_terhubung";
  const barisApi = (id) => M.baris.find((b) => b.id === id) || null;
  const adaAktif = () => (M.hidup ? M.baris.some((b) => berjalan(b.status)) : !!ui.aktif);
  const otomatisAktif = () => (M.hidup ? M.antrean.pengaturan.mode_otomatis : ui.otomatis);
  const jedaAktif = () => (M.hidup ? M.antrean.pengaturan.jeda : ui.jeda);
  const dataPasien = (id) => (M.hidup ? M.detail[id] || null : tunggal(id));
  const namaRs = (id) => {
    const r = M.hidup && M.antrean.daftar_rs.find((x) => x.id_rs === id);
    return r ? r.nama : D.namaRs(id);
  };
  const selisihP = (p) => (p.selisih !== undefined ? p.selisih : D.selisih(p));
  const toleransiP = (p) => (p.toleransi != null ? p.toleransi : D.TOLERANSI);
  const saranP = (p) => p.saran || D.SARAN[p.label];
  /* Percobaan tidak diangkat (S5): tanpa suara, hanya log percobaan dan chat cadangan. */
  const modeCoba = (p) => p.status === "tidak_terhubung" || (p.log || []).some((l) => l.catatan === "tidak_diangkat");
  const tanpaSuaraP = (p) => (M.hidup ? modeCoba(p) : tidakTerhubung(p));

  function statusBaris(id) {
    if (M.hidup) { const b = barisApi(id); return b ? b.st : "antre"; }
    if (D.LATAR[id]) return "selesai";
    if (S.hasil[id]) return tidakTerhubung(tunggal(id)) ? "tidak_terhubung" : "selesai";
    if (ui.aktif && ui.aktif.id === id) return ui.aktif.status;
    return "antre";
  }

  const labelBaris = (id) => {
    if (M.hidup) { const b = barisApi(id); return b ? b.label : null; }
    return D.LATAR[id] || S.hasil[id] ? tunggal(id).label : null;
  };

  /* Semua panggilan yang sudah selesai (simulasi): 4 latar sebelum demo dan skenario yang sudah dijalankan. */
  const panggilanSelesai = () => Object.keys(D.LATAR).map((id) => D.LATAR[id]).concat(Object.keys(S.hasil).map((id) => D.SKENARIO[id]));

  function angka() {
    if (M.hidup) {
      const a = M.antrean.angka;
      return { terpicu: a.terpicu, aktif: a.pasien_aktif, ditelepon: a.sudah_ditelepon, tidakSesuai: a.tidak_sesuai, rsKlarifikasi: a.rs_perlu_klarifikasi };
    }
    const selesai = panggilanSelesai();
    return {
      terpicu: D.PASIEN_TERPICU, aktif: D.PASIEN_AKTIF, ditelepon: selesai.length,
      tidakSesuai: selesai.filter((p) => p.label === "tidak_sesuai").length,
      rsKlarifikasi: D.ringkasanRs(selesai).filter((r) => r.status === "Perlu klarifikasi RS").length
    };
  }

  const menungguKeputusan = () => (M.hidup ? M.antrean.angka.menunggu_keputusan : panggilanSelesai().filter((p) => p.label === "tidak_sesuai" && !S.keputusan[p.id]).length);
  const hariIniTeks = () => (M.hidup && M.waktuServer ? A3.hariIni(M.waktuServer) : D.HARI_INI);

  function mulaiPanggilan(id) {
    const p = D.SKENARIO[id];
    if (!p || S.hasil[id] || ui.aktif) return;
    clearTimeout(ui.timerBerikut);
    ui.aktif = { id: id, mulai: Date.now(), menit: menitSekarang(), status: "wa", terisi: {}, barisLihat: 0, sig: "" };
    ui.timer = setInterval(tick, 250);
    const r = rute();
    if (r.nama === "panggilan" && r.id === id) bukaWa(id, "pemberitahuan", true); else gambar(true);
    toast("Pesan WA terkirim ke " + p.penerima.nama + ". Panggilan untuk " + p.pasien + " dimulai.", "#/panggilan/" + id, "Buka panggilan");
  }

  function tick() {
    const a = ui.aktif;
    if (!a) return;
    const p = D.SKENARIO[a.id];
    const t = (Date.now() - a.mulai) / 1000;
    if (t >= titik(p).total) { selesaikan(a.id); return; }
    const st = statusSim(p, t);
    const r = rute(), dilihat = r.nama === "panggilan" && r.id === a.id;
    /* Chat cadangan S5 muncul sendiri di layar ponsel bila verifikator sedang menonton panggilannya. */
    if (tidakTerhubung(p) && t >= titik(p).chat && !a.chatDibuka) {
      a.chatDibuka = true;
      if (dilihat) { a.status = st; bukaWa(a.id, "cadangan", true); return; }
    }
    /* Status hanya tampil di antrean dan layar panggilan; di layar lain jangan merender ulang agar isian alasan tidak terganggu. */
    if (st !== a.status) { a.status = st; if (r.nama === "autentik" || r.nama === "panggilan") gambar(true); return; }
    if (dilihat) { suaraMain(p, t); perbaruiPanggilan(p, t); }
  }

  function selesaikan(id) {
    const p = D.SKENARIO[id];
    clearInterval(ui.timer);
    suaraHenti();
    S.hasil[id] = { menit: ui.aktif.menit };
    ui.aktif = null;
    simpan();
    /* Bila verifikator sedang menonton panggilan ini, pindah sendiri ke kartu bukti. */
    const r = rute();
    if (r.nama === "panggilan" && r.id === id) ke("#/kartu/" + id); else gambar(true);
    toast("Panggilan selesai: " + p.pasien + " · " + D.LABEL[p.label].nama + ".", "#/kartu/" + id, "Buka kartu bukti");
    if (ui.otomatis && !ui.jeda) ui.timerBerikut = setTimeout(lanjutOtomatis, SIM.jedaBerikut);
  }

  /* Mode otomatis (R1.5): satu panggilan aktif, lalu berikutnya menurut urutan antrean. */
  function lanjutOtomatis() {
    if (!ui.otomatis || ui.jeda || ui.aktif) return;
    const id = D.URUTAN_ANTREAN.find((x) => D.SKENARIO[x] && !S.hasil[x]);
    if (id) { mulaiPanggilan(id); return; }
    ui.otomatis = false;
    toast("Semua panggilan di antrean sudah selesai. Panggilan otomatis dinonaktifkan.");
    gambar(true);
  }

  /* ============================================================== kerangka */

  function kerangka(r, isi, jejak) {
    const dalamAutentik = r.nama === "autentik" || r.nama === "panggilan" || r.nama === "kartu";
    const aktif = (ya) => (ya ? ' aria-current="page"' : "");
    const menunggu = menungguKeputusan();
    return '<div class="kerangka">' +
      '<aside class="sisi' + (ui.menuBuka ? " buka" : "") + '" id="sisi">' +
        '<a class="merek" href="#/beranda"><span class="merek-ikon">' + ikon("perisai") + "</span><span><b>VEDIKA</b><span>Verifikasi Digital Klaim</span></span></a>" +
        '<nav class="nav" aria-label="Menu utama">' +
          '<a href="#/beranda"' + aktif(r.nama === "beranda") + ">" + ikon("rumah") + "Beranda</a>" +
          '<span class="nav-judul kapital">Verifikasi</span>' +
          '<button class="mati" type="button" aria-disabled="true" title="Menu Vedika yang sudah ada, tidak termasuk prototipe">' + ikon("berkas") + "Verifikasi klaim<small>Sudah ada</small></button>" +
          '<a class="nav-autentik induk" href="#/autentik">' + logoVeritas + "Autentik" +
            (menunggu ? '<span class="lencana" title="Panggilan Tidak sesuai yang belum diputuskan">' + menunggu + "</span>" : "") + "</a>" +
          '<div class="nav-sub">' +
            '<a href="#/autentik"' + aktif(dalamAutentik) + ">Antrean konfirmasi</a>" +
            '<a href="#/ringkasan-rs"' + aktif(r.nama === "ringkasan-rs") + ">Ringkasan RS</a>" +
          "</div>" +
          '<a href="#/riwayat"' + aktif(r.nama === "riwayat") + ">" + ikon("riwayat") + "Riwayat keputusan</a>" +
        "</nav>" +
        '<div class="sisi-kaki nav">' +
          '<button type="button" data-aksi="ulang-demo">' + ikon("ulang") + "Mulai ulang demo</button>" +
          '<p class="catatan-prototipe"><b>Simulasi Healthkathon 2026.</b> Semua data fiktif.<br>' +
            (M.hidup ? "Data dari API. Agen suara dan pembaca jawaban masih stub." : "Data simulasi lokal (API tidak tersambung).") + "</p>" +
        "</div>" +
      "</aside>" +
      '<div class="kolom">' +
        '<header class="atas">' +
          '<button class="tombol-menu" type="button" data-aksi="menu" aria-label="Buka menu">' + ikon("menu") + "</button>" +
          '<div class="jejak-rute">' + jejak + "</div>" +
          '<div class="atas-kanan"><span class="lencana-simulasi">Simulasi</span>' +
            '<div class="pengguna"><span class="avatar"><img src="assets/foto/verifikator.png" alt="" width="34" height="34"></span><div><b>' + D.VERIFIKATOR.nama + "</b><span>" + D.VERIFIKATOR.peran + " · " + D.VERIFIKATOR.kantor + "</span></div></div></div>" +
        "</header>" +
        '<main class="isi" id="isi">' + isi + "</main>" +
      "</div></div>";
  }

  /* ============================================================== masuk */

  function lamanMasuk() {
    return '<div class="masuk"><div class="masuk-foto"><img src="assets/foto/kantor.jpg" alt=""></div><div class="masuk-bungkus">' +
      '<div class="merek-ikon">' + ikon("perisai") + "</div>" +
      "<h1>VEDIKA</h1><p>Verifikasi Digital Klaim</p>" +
      '<span class="lencana-simulasi">Simulasi</span>' +
      '<div class="masuk-kartu">' +
        "<h2>Otentikasi pengguna</h2>" +
        '<div class="medan"><span class="kapital">Username</span><div class="medan-isi">' + ikon("pengguna") + "rsantoso.kc0901</div></div>" +
        '<div class="medan"><span class="kapital">Kata sandi</span><div class="medan-isi">' + ikon("kunci") + "••••••••••</div></div>" +
        '<button class="btn btn--primer btn--lebar btn--kapital" type="button" data-aksi="masuk">Masuk sebagai verifikator demo</button>' +
        '<p class="masuk-catatan">Akun fiktif. Tidak ada data yang dikirim.</p>' +
      "</div>" +
      '<p class="masuk-versi">Simulasi Vedika Autentik · Healthkathon 2026</p>' +
    "</div></div>";
  }

  /* ========================================================== layar (isi bertahap) */

  const kosong = (judul, teks) => '<div class="kosong"><b>' + esc(judul) + "</b>" + esc(teks) + "</div>";
  const kepala = (judul, ket) => '<div class="kepala"><div><h1>' + esc(judul) + "</h1><p>" + esc(ket) + "</p></div></div>";

  /* ============================================================== beranda */

  function lamanBeranda() {
    const menunggu = M.hidup ? M.antrean.angka.antre : D.URUTAN_ANTREAN.filter((id) => statusBaris(id) === "antre").length;
    const a = angka();
    return kepala("Beranda", hariIniTeks() + " · " + D.VERIFIKATOR.kantor) +
      '<div class="pengumuman"><span class="merek-ikon merek-ikon--veritas">' + logoVeritas + "</span>" +
        "<div><b>Autentik kini mengonfirmasi lewat suara</b><p>AI menelepon peserta atau keluarganya untuk memastikan sesi fisioterapi benar-benar dijalani. Keputusan tetap di tangan Anda.</p></div>" +
        '<a class="btn btn--primer" href="#/autentik">Buka antrean</a></div>' +
      '<div class="judul-seksi"><h2>Konfirmasi suara, layanan ' + D.BULAN + "</h2><span>Pasien terpicu = dua indikator aktif atau lebih</span></div>" +
      kartuAngka() +
      '<div class="tautan-kartu">' +
        '<a href="#/autentik"><b>Antrean konfirmasi</b><span>' + menunggu + " pasien menunggu ditelepon. Aktifkan panggilan otomatis atau telepon satu per satu.</span>" + '<span class="btn btn--kecil">Buka antrean</span></a>' +
        '<a href="#/ringkasan-rs"><b>Ringkasan per rumah sakit</b><span>' + (a.rsKlarifikasi ? a.rsKlarifikasi + " rumah sakit perlu klarifikasi." : "Belum ada rumah sakit yang perlu klarifikasi.") + " Satu jawaban tidak cukup mengubah status.</span>" + '<span class="btn btn--kecil">Lihat ringkasan</span></a>' +
      "</div>";
  }
  /* ============================================================== antrean */

  const penerimaTeks = (p) => (p.penerima.hubungan === "peserta" ? "Peserta" : esc(p.penerima.nama) + ' <span class="redup">(' + esc(p.penerima.hubungan) + ")</span>");

  function kartuAngka() {
    const a = angka();
    return '<div class="kartu-angka">' +
      '<div class="angka-terpicu"><b>' + a.terpicu + "</b><span>pasien terpicu dari " + a.aktif + " aktif</span></div>" +
      '<div class="angka-ditelepon"><b>' + a.ditelepon + "</b><span>sudah ditelepon</span></div>" +
      '<div class="angka-tidak-sesuai"><b>' + a.tidakSesuai + "</b><span>tidak sesuai</span></div>" +
      '<div class="angka-klarifikasi"><b>' + a.rsKlarifikasi + "</b><span>RS perlu klarifikasi</span></div>" +
    "</div>";
  }

  /* Tujuan klik baris: kartu bukti bila sudah selesai, layar panggilan bila bisa ditelepon, kosong bila belum ada panggilan. */
  function tujuanBaris(p) {
    if (M.hidup) return selesaiSt(p.status) ? "#/kartu/" + p.id : "#/panggilan/" + p.id;
    if (D.LATAR[p.id] || S.hasil[p.id]) return "#/kartu/" + p.id;
    if (D.SKENARIO[p.id]) return "#/panggilan/" + p.id;
    return null;
  }

  /* Baris antrean (satu bentuk untuk API dan simulasi), sudah disaring menurut rumah sakit dan status. */
  function barisAntrean() {
    const dasar = M.hidup ? M.baris : D.URUTAN_ANTREAN.map((id) => Object.assign({ st: statusBaris(id) }, tunggal(id)));
    return dasar
      .filter((p) => !ui.filterRs || p.rs === ui.filterRs)
      .filter((p) => !ui.filterStatus || p.st === ui.filterStatus)
      .map((p) => {
        const lab = labelBaris(p.id);
        const putusan = M.hidup ? p.keputusanTindakan : S.keputusan[p.id] && S.keputusan[p.id].tindakan;
        return { p: p, st: p.st, lab: lab, putusan: putusan || null, tujuan: tujuanBaris(p), bisaTelepon: M.hidup ? p.status === "antre" : !!D.SKENARIO[p.id] && p.st === "antre" };
      });
  }

  const daftarRsPilihan = () => (M.hidup ? M.antrean.daftar_rs.map((r) => ({ id: r.id_rs, nama: r.nama })) : D.RS.map((r) => ({ id: r.id, nama: r.nama })));

  function lamanAntrean() {
    const sibuk = adaAktif();
    const baris = barisAntrean().map((b) => {
      const p = b.p, tujuan = b.tujuan, lab = b.lab;
      let aksi;
      if (b.bisaTelepon) {
        aksi = '<button class="btn btn--kecil btn--primer" type="button" data-aksi="telepon" data-id="' + p.id + '"' + (sibuk ? ' disabled title="Satu panggilan aktif pada satu waktu"' : "") + ">" + ikon("telepon") + "Telepon sekarang</button>";
      } else if (tujuan) {
        aksi = '<a class="btn btn--kecil" href="' + tujuan + '">Lihat</a>';
      } else {
        aksi = '<span class="redup">Belum ditelepon</span>';
      }
      return "<tr" + (tujuan ? ' class="bisa-klik" data-aksi="buka-baris" data-tujuan="' + tujuan + '"' : "") + ">" +
        '<td class="nama-berkas"><b>' + esc(p.pasien) + "</b><span>" + p.umur + " th</span></td>" +
        '<td class="sembunyi-hp">' + esc(namaRs(p.rs)) + "</td>" +
        '<td class="angka sembunyi-hp">' + p.ditagih + " sesi</td>" +
        '<td class="lebar-penuh"><div class="chip-ind-wadah">' + p.indikator.map((i) => '<span class="chip-ind chip-ind--' + i + '" title="' + esc(D.INDIKATOR[i].arti) + '">' + D.INDIKATOR[i].nama + "</span>").join("") + "</div></td>" +
        '<td class="sembunyi-hp">' + penerimaTeks(p) + "</td>" +
        '<td><div class="sel-status"><span class="status-chip status-chip--' + b.st + '">' + STATUS[b.st] + "</span>" + (lab ? labelChip(lab) + "<small>" + (b.putusan ? D.TINDAKAN[b.putusan].status : "Belum diputuskan") + "</small>" : "") + "</div></td>" +
        '<td class="aksi lebar-penuh">' + aksi + "</td></tr>";
    }).join("");

    const oto = otomatisAktif(), jd = jedaAktif();
    const keadaan = jd ? "Dijeda. Panggilan yang berjalan diselesaikan dulu." : sibuk ? "1 panggilan berjalan." : M.hidup && !M.antrean.pengaturan.dalam_jam ? "Di luar jam panggilan otomatis." : "Menyiapkan panggilan berikutnya.";

    return '<div class="kepala"><div><h1>Antrean konfirmasi · layanan ' + D.BULAN + "</h1>" +
        '<p class="keterangan-pemicu">Pasien masuk antrean jika dua indikator atau lebih aktif. Panggilan otomatis berjalan pukul 09.00–17.00 dan hanya satu panggilan aktif pada satu waktu.</p></div></div>' +
      '<div class="antrean-atas">' + kartuAngka() + '<div class="bar-antrean"><span class="kapital">Filter</span>' +
        '<select class="pilih" data-aksi="saring-rs" aria-label="Saring menurut rumah sakit"><option value="">Semua RS</option>' +
          daftarRsPilihan().map((r) => '<option value="' + r.id + '"' + (ui.filterRs === r.id ? " selected" : "") + ">" + esc(r.nama) + "</option>").join("") + "</select>" +
        '<select class="pilih" data-aksi="saring-status" aria-label="Saring menurut status"><option value="">Semua status</option>' +
          Object.keys(STATUS).map((k) => '<option value="' + k + '"' + (ui.filterStatus === k ? " selected" : "") + ">" + STATUS[k] + "</option>").join("") + "</select>" +
        '<div class="kanan">' + (oto ? '<span class="redup" style="font-size:12.5px">' + keadaan + "</span>" : "") +
          '<button class="btn btn--otomatis" type="button" data-aksi="otomatis" aria-pressed="' + oto + '">' + ikon("telepon") + "Panggilan otomatis: <b>" + (oto ? "AKTIF" : "NONAKTIF") + "</b></button>" +
          '<button class="btn" type="button" data-aksi="jeda"' + (oto ? "" : " disabled") + ">" + ikon(jd ? "main" : "jeda") + (jd ? "Lanjutkan" : "Jeda") + "</button></div></div></div>" +
      '<section class="panel tabel-antrean">' +
        (baris
          ? '<div class="tabel-bungkus"><table class="tabel tabel--kartu"><thead><tr><th>Pasien</th><th>Rumah sakit</th><th>Ditagih</th><th>Indikator aktif</th><th>Penerima telepon</th><th>Status</th><th></th></tr></thead><tbody>' + baris + "</tbody></table></div>"
          : '<div class="kosong"><b>Tidak ada pasien yang cocok</b>Ubah saringan rumah sakit atau status.</div>') +
        '<p class="catatan-kaki">Indikator: Melebihi 8 sesi sebulan · 3x seminggu · 6 bulan berturut-turut · Libur (Minggu atau libur nasional). Pasien dengan satu indikator saja tidak ditelepon.</p>' +
      "</section>";
  }
  /* ============================================================== panggilan */

  const mmss = (d) => Math.floor(d / 60) + ":" + String(Math.floor(d % 60)).padStart(2, "0");
  const detikLayar = () => (ui.aktif ? (Date.now() - ui.aktif.mulai) / 1000 : null);
  const TANDA_BAHAYA = { tanda_tangan_tanpa_layanan: "Tanda tangan tanpa layanan", diminta_membayar: "Diminta membayar", layanan_berbeda: "Layanan berbeda" };

  /* Detik panggilan nyata yang sudah direkam pada detik layar t. */
  const detikRekam = (p, t) => Math.max(0, Math.min(p.durasi, t - SIM.rekam));

  /* Jumlah baris transkrip yang sudah muncul pada detik layar t. */
  const barisTampil = (p, t) => (t == null ? 0 : p.transkrip.filter((l) => t >= SIM.rekam + l[1]).length);

  /* ---------- suara ---------- */

  /* Suara panggilan = potongan per baris (assets/rekaman/<S>/<nn>.mp3) yang diputar saat barisnya muncul.
     Hanya terdengar selama layar Panggilan panggilan itu terbuka; tiba di tengah panggilan, baris yang
     sedang berjalan diputar dari posisi yang sesuai. Peramban bisa menolak autoplay: diabaikan, transkrip tetap jalan. */
  const suara = { id: null, klip: [], idx: -1 };

  function suaraHenti() {
    suara.klip.forEach((a) => { a.pause(); a.removeAttribute("src"); a.load(); });
    suara.id = null; suara.klip = []; suara.idx = -1;
  }

  function suaraMain(p, t) {
    if (!p.suara_langsung) return;
    if (suara.id !== p.id) {
      suaraHenti();
      suara.id = p.id;
      suara.klip = p.transkrip.map((l, i) => {
        const a = new Audio(p.suara_langsung + "/" + String(i + 1).padStart(2, "0") + ".mp3");
        a.preload = "auto"; a.muted = ui.bisu;
        return a;
      });
    }
    const n = barisTampil(p, t);
    if (n - 1 <= suara.idx) return;
    suara.idx = n - 1;
    const a = suara.klip[n - 1], telat = t - SIM.rekam - p.transkrip[n - 1][1];
    if (telat > 0.3) a.currentTime = telat;
    a.play().catch(() => { /* autoplay ditolak */ });
  }

  /* Hentikan suara bila layar Panggilan panggilan yang berjalan tidak sedang dibuka. */
  function suaraSelaraskan() {
    const r = rute();
    if (M.hidup) { if (r.nama !== "panggilan") suaraHenti(); return; }
    if (!(ui.aktif && r.nama === "panggilan" && r.id === ui.aktif.id)) suaraHenti();
  }

  const tombolBisu = () => '<button class="btn btn--kecil" type="button" data-aksi="bisu" aria-pressed="' + ui.bisu + '">' + ikon(ui.bisu ? "bisu" : "suara") + (ui.bisu ? "Suara mati" : "Suara nyala") + "</button>";

  /* Peristiwa S5 yang muncul di kolom transkrip: tidak ada suara, hanya log percobaan. */
  function logPercobaan(p, t) {
    const k = titik(p);
    return [
      [k.coba1, "Percobaan 1: memanggil " + p.penerima.nama + "…"], [k.gagal1, "Tidak diangkat."],
      [k.coba2, "Percobaan 2 (jeda 2 menit, dipadatkan): memanggil lagi…"], [k.gagal2, "Tidak diangkat."],
      [k.chat, "Chat cadangan dikirim ke WhatsApp penerima."]
    ].filter((e) => t != null && t >= e[0]);
  }

  /* Tahap progres dan keadaannya (menunggu, jalan, selesai, gagal) pada detik layar t; t kosong = belum mulai. */
  function langkahSim(p, t) {
    const k = titik(p), a = ui.aktif && ui.aktif.id === p.id ? ui.aktif : null;
    const jam = (x) => (a ? formatJam(a.menit + x) : "");
    const st = (mulai, akhir) => (t == null || t < mulai ? "menunggu" : t < akhir ? "jalan" : "selesai");
    const tautanWa = (jenis, teks) => '<button class="tautan-kecil" type="button" data-aksi="wa" data-id="' + p.id + '" data-jenis="' + jenis + '">' + teks + "</button>";
    const wa = { nama: "Pesan WA terkirim", state: t == null ? "menunggu" : "selesai", jam: jam(0), ket: t == null ? "" : tautanWa("pemberitahuan", "Lihat pesan") };
    if (tidakTerhubung(p)) {
      const coba = (n, mulai, akhir, x) => {
        const s = st(mulai, akhir);
        return { nama: "Percobaan " + n, state: s === "selesai" ? "gagal" : s, ket: s === "jalan" ? "Memanggil…" : s === "selesai" ? "Tidak diangkat" : "", jam: jam(x) };
      };
      return [
        wa, coba(1, k.coba1, k.gagal1, D.JEDA_PESAN_MENIT), coba(2, k.coba2, k.gagal2, D.JEDA_PESAN_MENIT + 3),
        { nama: "Chat cadangan terkirim", state: st(k.gagal2, k.chat), jam: jam(D.JEDA_PESAN_MENIT + 4), ket: st(k.gagal2, k.chat) === "selesai" ? tautanWa("cadangan", "Lihat chat · pilihan 1–6") : "" },
        { nama: "Kartu bukti", state: st(k.chat, k.total), jam: jam(D.JEDA_PESAN_MENIT + 4), ket: st(k.chat, k.total) === "jalan" ? "Menyusun kartu bukti" : "" }
      ];
    }
    const sambung = st(0, k.sambung), rekam = st(k.rekam, k.akhir), baca = st(k.akhir, k.kartu), kartu = st(k.kartu, k.total);
    const jamBaca = jam(D.JEDA_PESAN_MENIT + Math.ceil(p.durasi / 60));
    return [
      wa,
      { nama: "Panggilan tersambung", state: t == null ? "menunggu" : sambung, jam: jam(D.JEDA_PESAN_MENIT), ket: sambung === "jalan" ? "Menunggu jeda pesan, dipadatkan" : "" },
      { nama: "Merekam", state: rekam, jam: jam(D.JEDA_PESAN_MENIT),
        ket: rekam === "jalan" ? '<span id="durasiLive">' + mmss(detikRekam(p, t)) + "</span> direkam" : rekam === "selesai" ? "Durasi " + mmss(p.durasi) : "" },
      { nama: "Membaca jawaban", state: baca, jam: jamBaca, ket: baca === "jalan" ? "Mengubah percakapan menjadi isian" : "" },
      { nama: "Kartu bukti", state: kartu, jam: jamBaca, ket: kartu === "jalan" ? "Menyusun kartu bukti" : "" }
    ];
  }

  /* ---------- panggilan dari API ---------- */

  const tautanWaBtn = (id, jenis, teks) => '<button class="tautan-kecil" type="button" data-aksi="wa" data-id="' + id + '" data-jenis="' + jenis + '">' + teks + "</button>";
  const jamLog = (p, status, fn) => {
    const l = (p.log || []).filter((x) => x.status === status && (!fn || fn(x)))[0];
    return l ? A3.jamTeks(l.waktu) : "";
  };
  const URUT_STATUS = ["antre", "wa_terkirim", "menelepon", "tersambung", "merekam", "membaca_jawaban", "selesai"];
  const idxStatus = (st) => (st === "tidak_terhubung" ? 6 : URUT_STATUS.indexOf(st));
  const detikTerakhir = (p) => (p.transkrip.length ? p.transkrip[p.transkrip.length - 1][1] : 0);

  /* Tahap progres dari status dan log panggilan. Percobaan yang tidak diangkat mengganti tahap tersambung/merekam
     dengan Percobaan 1, Percobaan 2, dan Chat cadangan. */
  function langkahApi(p) {
    const i = idxStatus(p.status), log = p.log || [];
    const wa = { nama: "Pesan WA terkirim", state: i >= 1 || log.some((l) => l.status === "wa_terkirim") ? "selesai" : "menunggu", jam: jamLog(p, "wa_terkirim"), ket: "" };
    if (wa.state === "selesai") wa.ket = tautanWaBtn(p.id, "pemberitahuan", "Lihat pesan");
    if (modeCoba(p)) {
      const gagal = (n) => log.some((l) => l.status === "menelepon" && l.percobaan === n && l.catatan === "tidak_diangkat");
      const mulaiN = (n) => log.some((l) => l.status === "menelepon" && l.percobaan === n && !l.catatan);
      const coba = (n) => ({ nama: "Percobaan " + n, state: gagal(n) ? "gagal" : mulaiN(n) ? "jalan" : "menunggu", jam: jamLog(p, "menelepon", (x) => x.percobaan === n && !x.catatan), ket: gagal(n) ? "Tidak diangkat" : mulaiN(n) ? "Memanggil…" : "" });
      const chat = log.some((l) => l.status === "tidak_terhubung");
      return [
        wa, coba(1), coba(2),
        { nama: "Chat cadangan terkirim", state: chat ? "selesai" : p.status === "tidak_terhubung" ? "jalan" : "menunggu", jam: jamLog(p, "tidak_terhubung"), ket: chat ? tautanWaBtn(p.id, "cadangan", "Lihat chat · pilihan 1–6") : "" },
        { nama: "Kartu bukti", state: chat ? "selesai" : "menunggu", jam: jamLog(p, "tidak_terhubung"), ket: "" }
      ];
    }
    return [
      wa,
      { nama: "Panggilan tersambung", state: i >= 3 ? "selesai" : i === 2 ? "jalan" : "menunggu", jam: jamLog(p, "tersambung"), ket: i === 1 ? "Menunggu jeda pesan" : i === 2 ? "Memanggil…" : "" },
      { nama: "Merekam", state: i >= 5 ? "selesai" : i >= 3 ? "jalan" : "menunggu", jam: jamLog(p, "tersambung"),
        ket: i >= 3 && i < 5 ? '<span id="durasiLive">' + mmss(detikTerakhir(p)) + "</span> direkam" : i >= 5 && p.durasi != null ? "Durasi " + mmss(p.durasi) : "" },
      { nama: "Membaca jawaban", state: i === 5 ? "jalan" : i >= 6 ? "selesai" : "menunggu", jam: jamLog(p, "membaca_jawaban"), ket: i === 5 ? "Mengubah percakapan menjadi isian" : "" },
      { nama: "Kartu bukti", state: i >= 6 ? "selesai" : "menunggu", jam: jamLog(p, "selesai"), ket: "" }
    ];
  }

  /* Transkrip langsung dari API. Baris yang baru tiba diberi tanda "baru"; baris yang sudah ada saat layar dibuka tidak. */
  function transkripApi(p) {
    if (modeCoba(p)) {
      const baris = [];
      (p.log || []).forEach((l) => {
        if (l.status === "menelepon" && !l.catatan) baris.push("Percobaan " + l.percobaan + ": memanggil " + p.penerima.nama + "…");
        else if (l.catatan === "tidak_diangkat") baris.push("Tidak diangkat.");
        else if (l.status === "tidak_terhubung") baris.push("Chat cadangan dikirim ke WhatsApp penerima.");
      });
      return baris.length ? baris.map((x) => '<div class="baris-trans baris-trans--sistem">' + esc(x) + "</div>").join("") : '<p class="kosong-trans">Menunggu percobaan pertama…</p>';
    }
    const n = p.transkrip.length;
    if (!n) return '<p class="kosong-trans">' + (p.status === "antre" ? "Transkrip muncul di sini setelah panggilan tersambung." : "Menunggu panggilan tersambung…") + "</p>";
    const baru = M.lihat[p.id] != null ? M.lihat[p.id] : n;
    M.lihat[p.id] = n;
    const baris = p.transkrip.map((l, i) => '<div class="baris-trans baris-trans--' + (l[0] === "A" ? "ai" : "p") + (i >= baru ? " baru" : "") + '"><div class="peran">' + (l[0] === "A" ? "AI" : "Penerima") +
      "<time>" + mmss(l[1]) + "</time></div>" + esc(l[2]) + "</div>").join("");
    const lanjut = p.status === "tersambung" || p.status === "merekam";
    const berikut = p.transkrip[n - 1][0] === "A" ? "P" : "A";
    return baris + (lanjut ? '<div class="baris-trans baris-trans--tunggu' + (berikut === "P" ? " p" : "") + '" aria-hidden="true"><span class="titik-ketik"><i></i><i></i><i></i></span></div>' : "");
  }

  /* Panel "Yang ditangkap AI": dari tangkapan_sementara selama panggilan, dari jawaban setelah selesai. Isian yang belum ada tampil "–". */
  function isianApi(p) {
    const j = p.jawaban || p.tangkapan || {};
    const ada = { penerima: "penerima" in j, hadir: "hadir" in j, jumlah: "jumlah_min" in j || "jumlah_maks" in j, keyakinan: "keyakinan" in j, libur: "membantah_tanggal_libur" in j, bahaya: "tanda_bahaya" in j };
    return ISIAN.map((x) => {
      const a = ada[x[0]], kunci = p.id + ":" + x[0];
      const baru = a && !M.terisi[kunci];
      if (a) M.terisi[kunci] = true;
      const bahaya = a && x[0] === "bahaya" && (j.tanda_bahaya || []).length;
      return "<div><dt>" + x[1] + "</dt><dd class=\"" + (a ? "" : "kosong-isi") + (baru ? " baru" : "") + (bahaya ? " bahaya" : "") + '">' +
        (a ? esc(nilaiIsian(p, x[0], j)) : p.label === "tidak_terhubung" ? "Tidak ada" : "–") + "</dd></div>";
    }).join("");
  }

  /* Suara langsung dari potongan per baris (assets/rekaman/<S>/<nn>.mp3) saat baris baru tiba dari API.
     Tiba di tengah panggilan: baris yang sudah ada dilewati, hanya baris berikutnya yang diputar. */
  function suaraApi(p) {
    if (!p.suara_langsung || !berjalan(p.status)) return;
    if (suara.id !== p.id) { suaraHenti(); suara.id = p.id; suara.idx = p.transkrip.length - 1; }
    const n = p.transkrip.length;
    if (n - 1 <= suara.idx) return;
    suara.idx = n - 1;
    const a = new Audio(p.suara_langsung + "/" + String(n).padStart(2, "0") + ".mp3");
    a.muted = ui.bisu;
    suara.klip.push(a);
    a.play().catch(() => { /* autoplay ditolak */ });
  }

  function htmlLangkah(p, t) {
    return (M.hidup ? langkahApi(p) : langkahSim(p, t)).map((l) => '<li class="' + l.state + '"><span class="ikon">' + (l.state === "selesai" ? ikon("cek") : l.state === "gagal" ? ikon("x") : "") + "</span>" +
      "<div><b>" + l.nama + "</b>" + (l.ket ? "<small>" + l.ket + "</small>" : "") + "</div><time>" + (l.state === "menunggu" ? "" : l.jam) + "</time></li>").join("");
  }

  function htmlTranskrip(p, t) {
    if (M.hidup) return transkripApi(p);
    const a = ui.aktif && ui.aktif.id === p.id ? ui.aktif : null;
    if (tidakTerhubung(p)) {
      const log = logPercobaan(p, t);
      return log.length ? log.map((e) => '<div class="baris-trans baris-trans--sistem">' + esc(e[1]) + "</div>").join("")
        : '<p class="kosong-trans">' + (t == null ? "Log percobaan muncul di sini setelah panggilan dimulai." : "Menunggu percobaan pertama…") + "</p>";
    }
    const n = barisTampil(p, t), k = titik(p);
    if (!n) return '<p class="kosong-trans">' + (t == null ? "Transkrip muncul di sini setelah panggilan tersambung." : "Menunggu panggilan tersambung…") + "</p>";
    const baru = a ? a.barisLihat : n;
    const baris = p.transkrip.slice(0, n).map((l, i) => '<div class="baris-trans baris-trans--' + (l[0] === "A" ? "ai" : "p") + (i >= baru ? " baru" : "") + '"><div class="peran">' + (l[0] === "A" ? "AI" : "Penerima") +
      "<time>" + mmss(l[1]) + "</time></div>" + esc(l[2]) + "</div>").join("");
    if (a) a.barisLihat = n;
    const berikut = p.transkrip[n];
    const ketik = berikut && t < k.akhir ? '<div class="baris-trans baris-trans--tunggu' + (berikut[0] === "P" ? " p" : "") + '" aria-hidden="true"><span class="titik-ketik"><i></i><i></i><i></i></span></div>' : "";
    return baris + ketik;
  }

  const ISIAN = [["penerima", "Penerima"], ["hadir", "Hadir"], ["jumlah", "Jumlah sesi"], ["keyakinan", "Keyakinan"], ["libur", "Tanggal libur"], ["bahaya", "Tanda bahaya"]];

  function nilaiIsian(p, k, j) {
    j = j || p.jawaban;
    if (k === "penerima") return j.penerima === "peserta" ? "Peserta" : j.hubungan ? "Keluarga (" + j.hubungan + ")" : "Keluarga";
    if (k === "hadir") return j.hadir === true ? "Ya" : j.hadir === false ? "Tidak" : "Tidak dijawab";
    if (k === "jumlah") return j.jumlah_min == null ? "Tidak dijawab" : j.jumlah_min === j.jumlah_maks ? j.jumlah_min + " sesi" : j.jumlah_min + "–" + j.jumlah_maks + " sesi";
    if (k === "keyakinan") return j.keyakinan === "tinggi" ? "Tinggi" : j.keyakinan === "rendah" ? "Rendah" : "–";
    if (k === "libur") return !p.tanggalLibur.length ? "Tidak ditanyakan" : j.membantah_tanggal_libur === true ? "Membantah" : j.membantah_tanggal_libur === false ? "Mengakui" : "Tidak jelas";
    return (j.tanda_bahaya || []).length ? j.tanda_bahaya.map((x) => TANDA_BAHAYA[x]).join(", ") : "Tidak ada";
  }

  /* Isian terisi bertahap menurut baris transkrip; setelah rekaman selesai semuanya terisi. */
  function terisi(p, t) {
    if (tidakTerhubung(p) || t == null) return [];
    const n = barisTampil(p, t), selesaiRekam = t >= titik(p).akhir;
    return ISIAN.map((x) => x[0]).filter((k) => selesaiRekam || (p.tangkap[k] != null && n > p.tangkap[k]));
  }

  function htmlIsian(p, t) {
    if (M.hidup) return isianApi(p);
    const a = ui.aktif && ui.aktif.id === p.id ? ui.aktif : null;
    const isi = terisi(p, t);
    const tanpaJawaban = tidakTerhubung(p);
    return ISIAN.map((x) => {
      const ada = isi.includes(x[0]);
      const baru = ada && a && !a.terisi[x[0]];
      if (ada && a) a.terisi[x[0]] = true;
      const bahaya = ada && x[0] === "bahaya" && p.jawaban.tanda_bahaya.length;
      return "<div><dt>" + x[1] + "</dt><dd class=\"" + (ada ? "" : "kosong-isi") + (baru ? " baru" : "") + (bahaya ? " bahaya" : "") + '">' + (ada ? esc(nilaiIsian(p, x[0])) : tanpaJawaban && t != null && t >= titik(p).chat ? "Tidak ada" : "–") + "</dd></div>";
    }).join("");
  }

  function catatanSimulasi(p) {
    if (M.hidup) return "Simulasi: agen suara dan pembaca jawaban masih stub; data panggilan dibaca dari API tiap detik. Suara dari rekaman buatan (ElevenLabs), bukan panggilan nyata.";
    return tidakTerhubung(p) ? "Simulasi: dua percobaan tanpa jawaban dipadatkan menjadi sekitar 25 detik. Tidak ada suara yang diputar."
      : "Simulasi: percakapan berjalan sepanjang rekaman, " + mmss(p.durasi) + ". Suara dari rekaman buatan (ElevenLabs), bukan panggilan nyata.";
  }

  /* Keadaan layar HP penerima, dibaca dari tahap progres yang sama dengan kolom Progres (simulasi dan API). */
  function keadaanPonsel(p, t) {
    const l = M.hidup ? langkahApi(p) : langkahSim(p, t);
    const belum = { mode: "diam", teks: t == null && !M.hidup ? "Belum ada panggilan" : "Menunggu panggilan" };
    if (tanpaSuaraP(p)) {
      const coba = l.filter((x) => x.nama.indexOf("Percobaan") === 0);
      if (coba.some((x) => x.state === "jalan")) return { mode: "dering", teks: "Berdering…" };
      if (coba.some((x) => x.state === "gagal")) return { mode: "tak", teks: "Tidak diangkat" };
      return belum;
    }
    const sambung = l[1], rekam = l[2];
    if (rekam.state === "selesai") return { mode: "akhir", teks: "Panggilan berakhir" };
    if (rekam.state === "jalan" || sambung.state === "selesai") return { mode: "aktif", teks: "Tersambung" };
    if (sambung.state === "jalan") {
      const dering = M.hidup ? sambung.ket === "Memanggil…" : t >= titik(p).sambung - 2;
      return dering ? { mode: "dering", teks: "Berdering…" } : { mode: "diam", teks: "Menunggu jeda pesan" };
    }
    return belum;
  }

  /* Mockup layar telepon penerima. Pemanggil hanya nomor tim (Simulasi), bukan nama atau logo BPJS. */
  /* Durasi di layar HP: menghitung mundur (sisa) bila lama panggilan sudah diketahui. */
  const sisaTeks = (p, detik) => (p.durasi != null ? "Sisa " + mmss(Math.max(0, Math.ceil(p.durasi - detik))) : mmss(detik));

  const STATUS_HP = '<svg class="sinyal" viewBox="0 0 18 12" fill="currentColor" aria-hidden="true"><rect x="0" y="8" width="3" height="4" rx="1"/><rect x="5" y="5.5" width="3" height="6.5" rx="1"/><rect x="10" y="3" width="3" height="9" rx="1"/><rect x="15" y="0" width="3" height="12" rx="1"/></svg>' +
    '<svg class="baterai" viewBox="0 0 27 12" aria-hidden="true"><rect x=".5" y=".5" width="22" height="11" rx="3.5" fill="none" stroke="currentColor" opacity=".55"/><rect x="2" y="2" width="17" height="8" rx="2" fill="currentColor"/><rect x="24" y="4" width="2" height="4" rx="1" fill="currentColor" opacity=".55"/></svg>';

  /* Mockup layar telepon penerima. Pemanggil hanya nomor tim (Simulasi), bukan nama atau logo BPJS.
     kartu: bingkai yang sama di kartu bukti, layar menampilkan hasil akhir panggilan; tambahan: html di bawah keterangan. */
  function htmlPonsel(p, t, kartu, tambahan) {
    const tak = p.label === "tidak_terhubung";
    const k = kartu ? { mode: tak ? "tak" : "akhir", teks: tak ? "Tidak diangkat" : "Panggilan berakhir" } : keadaanPonsel(p, t);
    const nomor = M.hidup ? p.pesanWa.dari : D.NOMOR_PENELEPON;
    const jam = kartu ? waktuPanggilan(p).split(", ").pop() : M.hidup ? A3.jamTeks(M.waktuServer) : formatJam(menitPanggilan(p.id));
    const detik = kartu ? 0 : Math.max(0, M.hidup ? detikTerakhir(p) : detikRekam(p, t));
    const baris = k.mode === "aktif" ? '<span class="durasi-ponsel">' + sisaTeks(p, detik) + "</span>"
      : k.mode === "akhir" && p.durasi != null ? "Durasi " + mmss(p.durasi) : "";
    const bulat = (kelas, nama, isi) => '<span class="tombol-telp ' + kelas + '">' + isi + "<small>" + nama + "</small></span>";
    const kisi = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><circle cx="6" cy="5" r="1.7"/><circle cx="12" cy="5" r="1.7"/><circle cx="18" cy="5" r="1.7"/><circle cx="6" cy="11" r="1.7"/><circle cx="12" cy="11" r="1.7"/><circle cx="18" cy="11" r="1.7"/><circle cx="6" cy="17" r="1.7"/><circle cx="12" cy="17" r="1.7"/><circle cx="18" cy="17" r="1.7"/></svg>';
    const opsi = '<div class="telp-opsi">' + bulat("", "Bisukan", ikon("mik")) + bulat("", "Keypad", kisi) + bulat("", "Speaker", ikon("suara")) +
      bulat("", "Tambah", ikon("tambah")) + bulat("", "Video", ikon("video")) + bulat("", "Kontak", ikon("pengguna")) + "</div>";
    const akhiri = '<div class="telp-aksi">' + bulat("merah", "Akhiri", ikon("telepon")) + "</div>";
    const bawah = k.mode === "dering" ? '<div class="telp-aksi telp-aksi--dering">' + bulat("merah", "Tolak", ikon("telepon")) + bulat("hijau", "Jawab", ikon("telepon")) + "</div>"
      : opsi + akhiri;
    const info = '<div class="telp-info"><span class="telp-foto">' + ikon("telepon") + "</span><b>" + esc(nomor) + "</b><span>Nomor tim · Simulasi</span>" +
      '<p class="telp-status">' + k.teks + '</p><p class="telp-durasi">' + baris + "</p>" +
      '<div class="gelombang" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div>';
    return '<div class="kol-ponsel"><div class="ponsel ponsel--telp ponsel--' + k.mode + '" role="img" aria-label="Simulasi layar telepon penerima: ' + k.teks + '">' +
      '<div class="ponsel-layar"><span class="poni"></span><div class="status-ponsel"><b>' + jam + "</b><span>" + STATUS_HP + "</span></div>" +
      info + bawah + "</div></div>" +
      '<p class="ponsel-ket">Layar HP penerima: <b>' + esc(p.penerima.nama) + (p.penerima.hubungan === "peserta" ? "" : " (" + esc(p.penerima.hubungan) + ")") + "</b></p>" + (tambahan || "") + "</div>";
  }

  /* Di kartu bukti, memutar rekaman membuat layar HP ikut berjalan: durasi menghitung mundur sampai rekaman habis. */
  function ponselRekaman(a, nama) {
    const hp = document.querySelector(".ponsel--telp");
    if (!hp || !a.duration) return;
    const status = hp.querySelector(".telp-status"), durasi = hp.querySelector(".telp-durasi");
    const ganti = (mode, teks, info) => {
      hp.className = hp.className.replace(/ponsel--(akhir|aktif)/, "ponsel--" + mode);
      status.textContent = teks; durasi.textContent = info;
    };
    if (nama === "ended" || a.ended) ganti("akhir", "Panggilan berakhir", "Durasi " + mmss(a.duration));
    else if (a.paused) ganti("akhir", "Rekaman dijeda", "Sisa " + mmss(Math.ceil(a.duration - a.currentTime)));
    else ganti("aktif", "Tersambung", "Sisa " + mmss(Math.ceil(a.duration - a.currentTime)));
  }
  /* Sorot baris transkrip yang sedang diucapkan dan gulirkan daftar ke sana (hanya di dalam daftar, halaman tidak ikut bergeser). */
  let barisSorot = -1;
  function sorotTranskrip(a, nama) {
    const daftar = document.getElementById("transkripSinkron");
    if (!daftar) return;
    const baris = daftar.children;
    let idx = -1;
    if (nama !== "ended") for (let i = 0; i < baris.length; i++) if (Number(baris[i].dataset.detik) <= a.currentTime) idx = i;
    if (idx === barisSorot) return;
    barisSorot = idx;
    for (let i = 0; i < baris.length; i++) baris[i].classList.toggle("sedang", i === idx);
    const el = baris[idx] || baris[0];
    if (el) daftar.scrollTo({ top: Math.max(0, el.offsetTop - daftar.clientHeight / 2 + el.offsetHeight / 2), behavior: "smooth" });
  }

  ["play", "pause", "ended", "timeupdate", "seeked"].forEach((n) => document.addEventListener(n, (e) => {
    if (e.target.tagName === "AUDIO" && e.target.closest(".pemutar--ponsel")) { ponselRekaman(e.target, n); sorotTranskrip(e.target, n); }
  }, true));

  function isiPanggilan(p, t) {
    const tanpaSuara = tanpaSuaraP(p);
    return '<div class="panggilan-grid" id="panggilan">' + htmlPonsel(p, t) +
      '<section class="panel kol-trans"><div class="panel-kepala"><h2>' + (tanpaSuara ? "Log panggilan" : "Transkrip langsung") + "</h2>" + (p.suara_langsung ? '<div class="kanan">' + tombolBisu() + "</div>" : "") + '</div><div class="transkrip" id="transkrip" aria-live="polite">' + htmlTranskrip(p, t) + "</div></section>" +
      '<div class="kol-kiri"><section class="panel"><div class="panel-kepala"><h2>Progres</h2></div><ol class="progres">' + htmlLangkah(p, t) + "</ol>" +
        '<p class="catatan-simulasi">' + catatanSimulasi(p) + "</p></section>" +
      '<section class="panel"><div class="panel-kepala"><h2>Yang ditangkap AI</h2></div><dl class="isian">' + htmlIsian(p, t) + "</dl></section></div>" +
    "</div>";
  }

  function lamanPanggilan(id) {
    const p = M.hidup ? M.detail[id] : D.SKENARIO[id];
    if (!p) {
      if (M.hidup && !M.tidakAda[id]) return kepala("Memuat panggilan", "Mengambil data dari API…");
      return kepala("Panggilan tidak ditemukan", "Hanya pasien di antrean yang punya panggilan.") + '<section class="panel"><div class="belum-mulai"><b>Tidak ada panggilan untuk ' + esc(id || "") + '</b><a class="btn btn--primer" href="#/autentik">Ke antrean konfirmasi</a></div></section>';
    }
    const berlangsung = M.hidup ? berjalan(p.status) : !!(ui.aktif && ui.aktif.id === id);
    const selesai = M.hidup ? selesaiSt(p.status) : !!S.hasil[id];
    const t = !M.hidup && berlangsung ? detikLayar() : null;
    const libur = p.tanggalLibur.length ? p.tanggalLibur.join(" dan ") + " " + D.BULAN_PENDEK : "tidak ada";
    const kodeStatus = M.hidup ? p.st : berlangsung ? ui.aktif.status : "antre";
    const aksi = berlangsung ? '<span class="status-chip status-chip--' + kodeStatus + '">' + STATUS[kodeStatus] + "</span>"
      : selesai ? "" : '<button class="btn btn--primer" type="button" data-aksi="telepon" data-id="' + id + '"' + (adaAktif() ? ' disabled title="Satu panggilan aktif pada satu waktu"' : "") + ">" + ikon("telepon") + "Telepon sekarang</button>";
    const kop = '<div class="kepala-panggilan"><div><h1>' + esc(p.pasien) + " · " + esc(namaRs(p.rs)) + " · " + D.BULAN + "</h1>" +
      '<div class="meta-panggilan"><span><b>Ditagih</b>' + p.ditagih + " sesi</span>" +
        '<span><b>Indikator</b><span class="chip-ind-wadah">' + p.indikator.map((i) => '<span class="chip-ind chip-ind--' + i + '" title="' + esc(D.INDIKATOR[i].arti) + '">' + D.INDIKATOR[i].nama + "</span>").join("") + "</span></span>" +
        "<span><b>Tanggal libur</b>" + libur + "</span><span><b>Penerima</b>" + penerimaTeks(p) + "</span></div></div>" +
      '<div class="kepala-aksi">' + aksi + "</div></div>";
    if (selesai) {
      return kop + '<section class="panel"><div class="belum-mulai"><b>Panggilan sudah selesai</b><p>Hasilnya ada di kartu bukti.</p><a class="btn btn--primer" href="#/kartu/' + id + '">Buka kartu bukti</a></div></section>';
    }
    return kop + isiPanggilan(p, t);
  }

  /* ================================================================ mockup WA */

  /* Menit (jam simulasi) saat panggilan dimulai, untuk cap waktu di gelembung. */
  const menitPanggilan = (id) => (ui.aktif && ui.aktif.id === id ? ui.aktif.menit : S.hasil[id] ? S.hasil[id].menit : menitSekarang());

  const gelembungWa = (teks, jam) => '<div class="gelembung dari-bpjs"><p>' + esc(teks) + "</p><small>" + jam + "</small></div>";

  /* Isi obrolan WA. Simulasi: jam dari menit panggilan. API: jam dari log panggilan dan teks dari pesan_wa. */
  function obrolanWa(p, cadangan) {
    if (M.hidup) {
      const jam0 = jamLog(p, "wa_terkirim") || A3.jamTeks(M.waktuServer);
      const tak = (p.log || []).filter((l) => l.catatan === "tidak_diangkat").map((l) => '<div class="gelembung sistem">Panggilan suara tak terjawab · ' + A3.jamTeks(l.waktu) + "</div>").join("");
      return '<span class="tanggal-obrolan">Hari ini</span>' + gelembungWa(p.pesanWa.pemberitahuan, jam0) +
        (cadangan && p.pesanWa.cadangan ? tak + gelembungWa(p.pesanWa.cadangan, jamLog(p, "tidak_terhubung") || jam0) : "");
    }
    const m = menitPanggilan(p.id);
    return '<span class="tanggal-obrolan">Hari ini</span>' + gelembungWa(D.pesanPemberitahuan(p), formatJam(m)) +
      (cadangan ? '<div class="gelembung sistem">Panggilan suara tak terjawab · ' + formatJam(m + D.JEDA_PESAN_MENIT) + "</div>" +
        '<div class="gelembung sistem">Panggilan suara tak terjawab · ' + formatJam(m + D.JEDA_PESAN_MENIT + 3) + "</div>" +
        gelembungWa(D.pesanCadangan(p), formatJam(m + D.JEDA_PESAN_MENIT + 4)) : "");
  }

  /* Komponen ponsel dari v2. Pengirim hanya nomor tim (Simulasi), bukan nama atau logo BPJS. */
  function modalWa() {
    const p = M.hidup ? M.detail[ui.wa.id] : D.SKENARIO[ui.wa.id], cadangan = ui.wa.jenis === "cadangan";
    if (!p) return "";
    const obrolan = obrolanWa(p, cadangan);
    const nomor = M.hidup ? p.pesanWa.dari : D.NOMOR_PENELEPON;
    const jedaWa = M.hidup ? M.antrean.pengaturan.jeda_wa_menit : D.JEDA_PESAN_MENIT;
    const petunjuk = cadangan ? "Penerima belum membalas. Jawaban 1–6 menggantikan panggilan." : "Penerima belum membalas. Pesan ini tanpa tautan.";
    const aturan = cadangan
      ? ["Dikirim setelah dua kali panggilan tidak diangkat (jeda 2 menit di prototipe, 2 jam di produksi).", "Satu pertanyaan, jawaban cukup dengan angka 1–6.", "Tanpa tautan, tidak meminta data pribadi atau pembayaran.", "Tidak dijawab bukan sinyal negatif: label tetap Tidak terhubung."]
      : ["Dikirim sebelum panggilan. Jeda " + jedaWa + " menit di prototipe, 10 menit di produksi.", "Tanpa tautan, karena penipu sering menyamar sebagai BPJS.", "Tidak meminta data pribadi, kode OTP, atau pembayaran.", "Mengarahkan penerima mengecek ke Care Center 165."];
    return '<div class="modal-wa" id="modalWa" data-aksi="tutup-wa"><div class="modal-wa-kartu" data-aksi="diam" role="dialog" aria-modal="true" aria-label="Simulasi layar WhatsApp penerima">' +
      '<button class="modal-wa-tutup" type="button" data-aksi="tutup-wa" aria-label="Tutup">' + ikon("x") + "</button>" +
      '<div class="ponsel"><div class="ponsel-layar"><div class="ponsel-kepala"><span class="foto">' + ikon("pengguna") + "</span><div><b>" + esc(nomor) + "</b><span>Nomor tim · Simulasi</span></div></div>" +
        '<div class="obrolan">' + obrolan + '</div><div class="ponsel-balas"><span class="petunjuk">' + petunjuk + "</span></div></div></div>" +
      '<div class="modal-wa-info"><span class="kapital">' + (cadangan ? "Chat cadangan" : "Pesan pemberitahuan") + "</span><h2>" + esc(p.penerima.nama) + (p.penerima.hubungan === "peserta" ? "" : " (" + esc(p.penerima.hubungan) + ")") + "</h2>" +
        "<p>" + (cadangan ? "Sistem tidak berhasil menelepon, lalu mengirim pertanyaan lewat chat." : "Penerima tahu akan ditelepon dan tidak mengira panggilan ini penipuan.") + "</p>" +
        '<ul class="aturan">' + aturan.map((t) => "<li>" + ikon("cek") + "<span>" + t + "</span></li>").join("") + "</ul></div>" +
    "</div></div>";
  }

  let timerWa = null;
  function bukaWa(id, jenis, otomatis) {
    clearTimeout(timerWa);
    ui.wa = { id: id, jenis: jenis };
    gambar(true);
    if (otomatis) timerWa = setTimeout(tutupWa, 7000);
  }
  function tutupWa() {
    clearTimeout(timerWa);
    if (!ui.wa) return;
    ui.wa = null;
    const el = document.getElementById("modalWa");
    if (el) el.remove();
  }

  /* Perbarui hanya bagian panggilan bila ada yang berubah, supaya transkrip tidak berkedip. */
  function perbaruiPanggilan(p, t) {
    const a = ui.aktif;
    const sig = [langkahSim(p, t).map((l) => l.state[0]).join(""), barisTampil(p, t), terisi(p, t).length, logPercobaan(p, t).length, t >= titik(p).akhir, keadaanPonsel(p, t).mode].join("|");
    const el = document.getElementById("panggilan");
    if (el && sig !== a.sig) {
      a.sig = sig;
      el.outerHTML = isiPanggilan(p, t);
      const tr = document.getElementById("transkrip");
      if (tr) tr.scrollTop = tr.scrollHeight;
    }
    const dt = Math.max(0, detikRekam(p, t));
    document.querySelectorAll("#durasiLive").forEach((d) => { d.textContent = mmss(dt); });
    document.querySelectorAll(".durasi-ponsel").forEach((d) => { d.textContent = sisaTeks(p, dt); });
  }

  /* Pintasan tersembunyi Alt+L: lompat ke akhir panggilan yang sedang berjalan, hasilnya sama dengan menunggu. */
  function lompatAkhir() {
    if (M.hidup || !ui.aktif) return;
    suaraHenti();
    ui.aktif.mulai = Date.now() - (titik(D.SKENARIO[ui.aktif.id]).total + 1) * 1000;
    tick();
  }
  /* ============================================================ kartu bukti */

  const daftarTanggal = (t) => t.join(" dan ") + " " + D.BULAN_PENDEK;

  function waktuPanggilan(p) {
    if (M.hidup) return p.waktu || "–";
    return D.LATAR[p.id] ? D.LATAR[p.id].waktu : "6 Okt 2026, " + formatJam(S.hasil[p.id].menit);
  }

  /* Versi penerima, selisih, dan keterangannya untuk tiga kartu. Yang tidak dihitung tampil "–". */
  function ringkasKartu(p) {
    const j = p.jawaban, dihitung = p.label === "tidak_sesuai" || p.label === "sesuai";
    let versi = "–", versiKet = "", gaya = "netral";
    if (p.label === "tidak_terhubung") versiKet = "Tidak diangkat 2 kali.";
    else if (p.label === "menolak") versiKet = "Penerima menolak menjawab.";
    else {
      versi = j.jumlah_min === j.jumlah_maks ? j.jumlah_min : j.jumlah_min + "–" + j.jumlah_maks;
      versiKet = p.label === "tidak_yakin" ? "Perkiraan, keyakinan rendah."
        : j.membantah_tanggal_libur === true ? "Membantah sesi pada " + daftarTanggal(p.tanggalLibur) + "." : "";
    }
    const sel = selisihP(p), tol = toleransiP(p);
    let selisihTeks = "–", selisihKet = "Tidak dihitung.";
    if (dihitung) {
      selisihTeks = sel;
      selisihKet = "Toleransi " + tol + " sesi, " + (sel > tol ? "terlampaui." : "dalam batas.");
      gaya = sel > tol ? "beda" : "sama";
    }
    return { versi: versi, versiKet: versiKet, selisih: selisihTeks, selisihKet: selisihKet, gaya: gaya, versiGaya: p.label === "tidak_sesuai" ? "beda" : p.label === "sesuai" ? "sama" : "netral" };
  }

  /* Keputusan (R5.3): setujui saran, atau pilih tindakan lain dengan alasan wajib. */
  const alasanTerisi = () => !!(ui.tindakanLain && ui.catatan && ui.catatan.trim());

  function aksiKeputusan(p) {
    if (!ui.pilihLain) {
      return '<div class="saran-tombol"><button class="btn btn--primer" type="button" data-aksi="setujui" data-id="' + p.id + '">' + ikon("cek") + "Setujui saran</button>" +
        '<button class="btn btn--hantu" type="button" data-aksi="pilih-lain">Pilih tindakan lain</button>' +
        (ui.ubah === p.id ? '<button class="btn btn--hantu" type="button" data-aksi="batal-ubah">Batal</button>' : "") + "</div>";
    }
    const lain = D.PILIHAN_TINDAKAN.filter((x) => x !== saranP(p));
    return '<div class="pilihan-lain" role="radiogroup" aria-label="Tindakan lain">' +
      lain.map((x) => '<label class="' + (ui.tindakanLain === x ? "dipilih" : "") + '"><input type="radio" name="tindakan" data-aksi="tindakan-lain" value="' + x + '"' + (ui.tindakanLain === x ? " checked" : "") + ">" +
        "<span><b>" + D.TINDAKAN[x].nama + "</b><span>" + D.TINDAKAN[x].akibat + "</span></span></label>").join("") +
      '<label class="catatan-medan"><span class="kapital">Alasan tidak mengikuti saran</span><textarea data-aksi="catatan" rows="3" placeholder="Contoh: pasien baru pindah RS bulan ini, sudah dikonfirmasi lewat telepon ke RS.">' + esc(ui.catatan || "") + "</textarea>" +
        '<span class="petunjuk-alasan">Alasan wajib diisi. Catatan ini masuk ke riwayat keputusan.</span></label>' +
      '<div class="saran-tombol"><button class="btn btn--primer" type="button" data-aksi="simpan-lain" data-id="' + p.id + '"' + (alasanTerisi() ? "" : " disabled") + ">Simpan keputusan</button>" +
      '<button class="btn btn--hantu" type="button" data-aksi="batal-lain">Kembali ke saran</button></div></div>';
  }

  function putusanTerpilih(p, k) {
    const t = D.TINDAKAN[k.tindakan];
    return '<div class="putusan"><b>' + ikon("lencanaCek") + t.status + "</b>" +
      "<p>" + esc(k.oleh) + " memilih <b>" + t.nama + "</b> pada " + esc(k.waktu) + (k.ikutSaran ? ", sesuai saran sistem." : ", berbeda dari saran sistem.") + "</p>" +
      (k.alasan ? "<blockquote>" + esc(k.alasan) + "</blockquote>" : "") +
      '<div class="aksi"><a class="btn btn--kecil" href="#/riwayat">Lihat di riwayat</a><button class="btn btn--kecil" type="button" data-aksi="batal-putusan" data-id="' + p.id + '">Ubah keputusan</button></div></div>';
  }

  function putuskan(id, tindakan, alasan, ikutSaran) {
    const p = tunggal(id);
    S.keputusan[id] = { tindakan: tindakan, alasan: alasan, ikutSaran: ikutSaran, oleh: D.VERIFIKATOR.nama, waktu: "6 Okt 2026, " + formatJam(menitSekarang()) };
    ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null;
    simpan();
    gambar(true);
    toast(D.TINDAKAN[tindakan].status + " · " + p.pasien, "#/riwayat", "Lihat riwayat");
  }

  function lamanKartu(id) {
    const p = dataPasien(id);
    if (M.hidup && !p && !M.tidakAda[id]) return kepala("Memuat kartu bukti", "Mengambil data dari API…");
    if (M.hidup ? !p : !p || !(D.LATAR[id] || D.SKENARIO[id])) {
      return kepala("Kartu bukti tidak ditemukan", "Kartu bukti hanya ada untuk pasien yang sudah ditelepon.") + '<section class="panel"><div class="belum-mulai"><b>Tidak ada kartu untuk ' + esc(id || "") + '</b><a class="btn btn--primer" href="#/autentik">Ke antrean konfirmasi</a></div></section>';
    }
    if (M.hidup ? !selesaiSt(p.status) : D.SKENARIO[id] && !S.hasil[id]) {
      return kepala("Kartu bukti belum tersedia", p.pasien) + '<section class="panel"><div class="belum-mulai"><b>' + esc(p.pasien) + ' belum ditelepon</b><p>Kartu bukti dibuat setelah panggilan selesai.</p><a class="btn btn--primer" href="#/panggilan/' + id + '">Ke layar panggilan</a></div></section>';
    }
    const j = p.jawaban, rk = ringkasKartu(p), latar = M.hidup ? p.sumber === "sintetis-riwayat" : !!D.LATAR[id];
    const saran = D.TINDAKAN[saranP(p)];
    const rs = M.hidup ? p.konteksRs : D.ringkasanRs(panggilanSelesai()).find((r) => r.id_rs === p.rs);
    const bahaya = j.tanda_bahaya.length;
    const simpanTeks = p.label === "tidak_sesuai" || p.label === "sesuai";

    const tanggal = '<div class="tanggal-sesi">' + p.tanggal.map((h) => {
      const tanda = p.tandaTanggal[h];
      return '<span class="tgl' + (tanda ? " tgl--tanda" : "") + '">' + h + (tanda ? "<small>" + tanda + "</small>" : "") + "</span>";
    }).join("") + "</div>";
    const nTanda = Object.keys(p.tandaTanggal).length;

    const durasi = p.label === "tidak_terhubung" ? "2 percobaan, tidak diangkat" : p.durasi != null ? "durasi " + mmss(p.durasi) : "durasi tidak tercatat";
    const kop = '<div class="kepala-kartu"><div><h1>' + esc(p.pasien) + " · " + esc(namaRs(p.rs)) + "</h1>" +
      '<div class="meta-panggilan"><span><b>Layanan</b>Fisioterapi · ' + D.BULAN + "</span><span><b>Panggilan</b>" + waktuPanggilan(p) + " · " + durasi + "</span><span><b>Penerima</b>" + penerimaTeks(p) + "</span></div></div>" +
      labelChip(p.label, true) + "</div>";

    const peringatan = bahaya ? '<div class="tanda-bahaya" role="alert">' + ikon("awas") + "<div><b>Tanda bahaya: " + esc(j.tanda_bahaya.map((x) => TANDA_BAHAYA[x]).join(", ")) + "</b><p>" + esc(j.ringkasan) + "</p></div></div>" : "";

    const ketTgl = nTanda ? nTanda + " tanggal di Minggu atau libur (kuning)." : "Tidak ada di Minggu atau libur.";
    const angka = (nama, nilai, gaya) => '<div class="' + gaya + '"><span class="kapital">' + nama + '</span><div class="besar">' + nilai + (nilai === "–" ? "" : "<small>sesi</small>") + "</div></div>";
    const ringkasan = '<section class="ringkasan-tagihan"><div class="angka-tiga">' +
      angka("Ditagih RS", p.ditagih, "netral") + angka("Versi peserta", rk.versi, rk.versiGaya) + angka("Selisih", rk.selisih, rk.gaya) + "</div>" +
      '<div class="tgl-blok"><span class="kapital">Tanggal ditagih</span>' + tanggal + "</div>" +
      '<ul class="ket-ringkas"><li>' + ketTgl + "</li>" + (rk.versiKet ? "<li><b>Versi peserta:</b> " + esc(rk.versiKet) + "</li>" : "") +
      "<li><b>Selisih:</b> " + esc(rk.selisihKet) + "</li></ul></section>";

    let bukti, pemutar = "";
    if (latar) bukti = '<p class="tanpa-rekaman">Riwayat latar sebelum demo: rekaman dan transkrip tidak tersedia di simulasi.</p>';
    else if (p.rekaman) { bukti = ""; pemutar = '<div class="pemutar pemutar--ponsel"><audio controls preload="metadata" src="' + p.rekaman + '">Peramban tidak mendukung pemutar audio.</audio><small>Rekaman simulasi, suara buatan (ElevenLabs).</small></div>'; }
    else bukti = '<p class="tanpa-rekaman">Tidak ada rekaman atau transkrip yang disimpan untuk label ' + D.LABEL[p.label].nama + ". Hanya status dan hasil terstruktur.</p>";
    /* Transkrip mengikuti rekaman: baris yang sedang diucapkan disorot (lihat sorotTranskrip), klik baris untuk melompat. */
    const transkrip = simpanTeks && !latar && p.rekaman
      ? '<section class="transkrip-sinkron"><div class="panel-kepala"><h2>Transkrip</h2><div class="kanan">' + p.transkrip.length + " ucapan · klik baris untuk melompat</div></div>" +
        '<div class="transkrip transkrip--sinkron" id="transkripSinkron">' + p.transkrip.map((l) => '<div class="baris-trans baris-trans--' + (l[0] === "A" ? "ai" : "p") + '" data-aksi="loncat" data-detik="' + l[1] + '" role="button" tabindex="0"><div class="peran">' + (l[0] === "A" ? "AI" : "Penerima") + "<time>" + mmss(l[1]) + "</time></div>" + esc(l[2]) + "</div>").join("") + "</div></section>" : "";

    const kutipan = '<section class="panel"><div class="panel-kepala"><h2>Kutipan kunci</h2></div>' +
      (j.kutipan_kunci ? '<blockquote class="kutipan">' + esc(j.kutipan_kunci) + '</blockquote><p class="kutipan-ringkasan">' + esc(j.ringkasan) + "</p>"
        : '<p class="kutipan-ringkasan" style="padding-top:16px">Tidak ada kutipan. ' + esc(j.ringkasan) + "</p>") +
      bukti +
      '<div class="catatan-bukti"><span>' + ikon("kunci") + esc(D.RETENSI[p.label]) + "</span><span>" + ikon("kunci") + "Identitas penerima tidak dibagikan ke RS.</span></div></section>";

    const konteks = '<div class="konteks"><span><b>' + esc(namaRs(p.rs)) + "</b>: " + rs.tidak_sesuai + " dari " + rs.terjawab + " jawaban tidak sesuai · Status <b>" + rs.status + "</b></span></div>";
    const keputusan = M.hidup ? p.keputusan : S.keputusan[id];
    const tampilPutusan = keputusan && ui.ubah !== id;
    const sarankan = '<section class="panel saran saran-kartu"><div class="saran-isi"><span class="kapital">Langkah yang disarankan</span><h3>' + saran.nama + "</h3>" +
      "<p>" + esc(p.alasan) + " " + esc(saran.akibat) + "</p>" + konteks + (tampilPutusan ? "" : aksiKeputusan(p)) +
      '<p class="catatan-saran">Rekaman hanya bukti awal, bukan satu-satunya dasar menolak klaim.</p></div>' +
      (tampilPutusan ? putusanTerpilih(p, keputusan) : "") + "</section>";

    return kop + peringatan + '<div class="kartu-grid">' + htmlPonsel(p, null, true, pemutar + transkrip) +
      '<div class="kartu-tengah">' + ringkasan + kutipan + '</div><div class="kartu-saran">' + sarankan + "</div></div>";
}
  /* ============================================================ ringkasan RS */

  const persenRs = (x) => koma(x.toFixed(1)) + "%";

  /* Satu bentuk untuk API dan simulasi: {jumlah, rs: [{id, nama, aktif, terpicu, persen, c, daftar}]}. */
  function dataRingkasan() {
    if (M.hidup) return M.ringkasan;
    const selesai = panggilanSelesai();
    const ring = D.ringkasanRs(selesai);
    return {
      jumlah: selesai.length,
      rs: D.RS.map((r, i) => ({
        id: r.id, nama: r.nama, aktif: r.aktif, terpicu: r.terpicu, persen: r.persen, c: ring[i],
        daftar: selesai.filter((p) => p.rs === r.id).map((p) => ({
          id: p.id, pasien: p.pasien, label: p.label, ditagih: p.ditagih, jumlah_min: p.jawaban.jumlah_min, jumlah_maks: p.jawaban.jumlah_maks, selisih: D.selisih(p)
        }))
      }))
    };
  }

  function lamanRingkasanRs() {
    const data = dataRingkasan();
    if (!data) return kepala("Memuat ringkasan RS", "Mengambil data dari API…");
    const baris = data.rs.map((r) => {
      const c = r.c, buka = ui.rsBuka === r.id;
      const rinci = r.daftar.length
        ? '<ul class="daftar-rinci">' + r.daftar.map((d) => {
          const versi = d.jumlah_min === d.jumlah_maks ? d.jumlah_min : d.jumlah_min + "–" + d.jumlah_maks;
          const ringkas = d.label === "tidak_terhubung" ? "Panggilan tidak diangkat" : d.label === "menolak" ? "Menolak menjawab"
            : d.jumlah_maks == null ? "Jawaban belum bisa dibaca otomatis"
            : d.ditagih + " ditagih · versi peserta " + versi + (d.label === "tidak_yakin" ? " (perkiraan)" : " · selisih " + d.selisih);
          return "<li><b>" + esc(d.pasien) + "</b>" + labelChip(d.label) + "<span>" + ringkas + '</span><a class="btn btn--kecil" href="#/kartu/' + d.id + '">Buka kartu</a></li>';
        }).join("") + "</ul>"
        : '<p class="daftar-rinci kosong-rinci">Belum ada panggilan selesai untuk rumah sakit ini.</p>';
      return "<tr>" +
        '<td class="nama-berkas"><b>' + esc(r.nama) + "</b><span>" + r.id + "</span></td>" +
        '<td class="angka sembunyi-hp">' + r.aktif + "</td>" +
        '<td class="angka">' + r.terpicu + ' <span class="redup-kecil">(' + persenRs(r.persen) + ")</span></td>" +
        '<td class="angka sembunyi-hp">' + c.terjawab + "</td>" +
        '<td class="angka">' + c.tidak_sesuai + (c.terjawab ? ' <span class="redup-kecil">(' + Math.round(c.rasio * 100) + "%)</span>" : "") + "</td>" +
        '<td><span class="label label--' + (c.status === "Normal" ? "sesuai" : "tidak_sesuai") + '">' + c.status + "</span></td>" +
        '<td class="aksi lebar-penuh"><button class="btn btn--kecil" type="button" data-aksi="lihat-kartu-rs" data-id="' + r.id + '" aria-expanded="' + buka + '">' + (buka ? "Tutup kartu" : "Lihat kartu") + "</button></td></tr>" +
        (buka ? '<tr class="rinci"><td colspan="7" class="lebar-penuh">' + rinci + "</td></tr>" : "");
    }).join("");

    /* Banner narasi demo: hanya bila RS Melati memang baru beralih ke Perlu klarifikasi RS karena S1. */
    const melati = data.rs.find((r) => r.id === "RS01");
    const s1 = M.hidup ? barisApi("CALL-P-S1-2026-08") : null;
    const sesudahS1 = M.hidup ? !!(s1 && selesaiSt(s1.status) && s1.label === "tidak_sesuai" && melati && melati.c.status === "Perlu klarifikasi RS" && melati.c.tidak_sesuai === 3 && melati.c.terjawab === 5) : !!S.hasil.S1;
    return '<div class="kepala"><div><h1>Ringkasan per rumah sakit · layanan ' + D.BULAN + "</h1>" +
        '<p class="keterangan-pemicu">Berdasarkan ' + data.jumlah + " panggilan yang sudah selesai.</p></div></div>" +
      '<div class="keterangan-aturan"><b>Satu jawaban belum cukup.</b> Rumah sakit berstatus <b>Perlu klarifikasi RS</b> jika ada <b>3 jawaban tidak sesuai atau lebih</b> DAN jumlahnya <b>10% atau lebih dari yang terjawab</b>. Tidak yakin, Tidak terhubung, dan Menolak tidak dihitung.</div>' +
      (sesudahS1 ? '<div class="perubahan-rs">Setelah panggilan Andi Pratama (S1), RS Melati Sehat berubah dari Normal (2 tidak sesuai dari 4 terjawab) menjadi Perlu klarifikasi RS (3 dari 5).</div>' : "") +
      '<section class="panel"><div class="tabel-bungkus"><table class="tabel tabel--kartu"><thead><tr><th>Rumah sakit</th><th>Pasien aktif</th><th>Terpicu</th><th>Terjawab</th><th>Tidak sesuai</th><th>Status</th><th></th></tr></thead><tbody>' + baris + "</tbody></table></div>" +
        '<p class="catatan-kaki">Identitas penerima telepon tidak pernah tampil di data yang dibagikan ke rumah sakit. Terpicu = pasien dengan dua indikator aktif atau lebih.</p></section>';
  }
  /* ============================================================== riwayat */

  /* Keputusan terkini tiap panggilan, terbaru dulu, satu bentuk untuk API dan simulasi. */
  function dataRiwayat() {
    if (M.hidup) return M.riwayat;
    return Object.keys(S.keputusan).filter((id) => tunggal(id)).map((id) => {
      const p = tunggal(id), k = S.keputusan[id];
      return { id: id, pasien: p.pasien, umur: p.umur, namaRs: namaRs(p.rs), label: p.label, tindakan: k.tindakan, ikutSaran: k.ikutSaran, alasan: k.alasan, oleh: k.oleh, waktu: k.waktu };
    }).reverse();
  }

  function lamanRiwayat() {
    const daftar = dataRiwayat();
    if (!daftar) return kepala("Memuat riwayat keputusan", "Mengambil data dari API…");
    const isi = daftar.length
      ? '<div class="tabel-bungkus"><table class="tabel tabel--kartu"><thead><tr><th>Waktu</th><th>Pasien</th><th>Rumah sakit</th><th>Label</th><th>Tindakan</th><th>Saran sistem</th><th>Alasan</th><th>Verifikator</th></tr></thead><tbody>' +
        daftar.map((x) => '<tr class="bisa-klik" data-aksi="buka-baris" data-tujuan="#/kartu/' + x.id + '"><td class="redup">' + esc(x.waktu) + '</td><td class="nama-berkas"><b>' + esc(x.pasien) + "</b><span>" + x.umur + " th</span></td>" +
          '<td class="sembunyi-hp">' + esc(x.namaRs) + "</td><td>" + labelChip(x.label) + "</td><td><b>" + D.TINDAKAN[x.tindakan].nama + '</b></td><td class="sembunyi-hp">' +
          (x.ikutSaran ? "Diikuti" : '<b style="color:var(--cek-fg)">Tidak diikuti</b>') + '</td><td class="alasan lebar-penuh">' + esc(x.alasan || "–") + '</td><td class="sembunyi-hp">' + esc(x.oleh) + "</td></tr>").join("") +
        "</tbody></table></div>"
      : '<div class="riwayat-kosong"><b>Belum ada keputusan</b><p>Setiap keputusan di kartu bukti tercatat di sini, lengkap dengan waktu, tindakan, dan alasannya.</p><a class="btn btn--primer" href="#/autentik">Buka antrean konfirmasi</a></div>';
    return '<div class="kepala"><div><h1>Riwayat keputusan</h1><p>Semua keputusan verifikator atas panggilan konfirmasi: siapa, kapan, apa, dan alasannya. Data ini dipakai untuk audit.</p></div></div><section class="panel">' + isi + "</section>";
  }

  /* ============================================================== render */

  const JUDUL_HALAMAN = { beranda: "Beranda", autentik: "Antrean konfirmasi", panggilan: "Panggilan", kartu: "Kartu bukti", "ringkasan-rs": "Ringkasan RS", riwayat: "Riwayat keputusan" };

  function gambar(tetap) {
    const y = window.scrollY;
    const r = rute();
    const akar = document.getElementById("akar");
    const sedangMengetik = document.activeElement && document.activeElement.dataset && document.activeElement.dataset.aksi === "catatan" ? document.activeElement.selectionStart : null;
    document.body.style.overflow = "";

    if (!S.masuk) {
      akar.innerHTML = lamanMasuk();
      return;
    }

    const antrean = '<a href="#/autentik">Autentik</a><span>/</span>';
    let isi, jejak;
    if (r.nama === "autentik") { isi = lamanAntrean(); jejak = antrean + "<b>Antrean konfirmasi</b>"; }
    else if (r.nama === "panggilan") { isi = lamanPanggilan(r.id); jejak = antrean + '<a href="#/autentik">Antrean konfirmasi</a><span>/</span><b>Panggilan</b>'; }
    else if (r.nama === "kartu") { isi = lamanKartu(r.id); jejak = antrean + '<a href="#/autentik">Antrean konfirmasi</a><span>/</span><b>Kartu bukti</b>'; }
    else if (r.nama === "ringkasan-rs") { isi = lamanRingkasanRs(); jejak = antrean + "<b>Ringkasan RS</b>"; }
    else if (r.nama === "riwayat") { isi = lamanRiwayat(); jejak = "<b>Riwayat keputusan</b>"; }
    else { isi = lamanBeranda(); jejak = "<b>Beranda</b>"; }

    /* Pemutar rekaman di kartu bukti dipertahankan lintas render ulang (buka-tutup transkrip, keputusan),
       jika tidak elemen audio baru menggantikannya dan rekaman yang sedang diputar berhenti. */
    const pemutarLama = document.querySelector(".pemutar audio");
    const mainLagi = !!pemutarLama && !pemutarLama.paused;
    akar.innerHTML = kerangka(r, isi, jejak) + (ui.wa ? modalWa() : "");
    const pemutarBaru = document.querySelector(".pemutar audio");
    if (pemutarLama && pemutarBaru && pemutarLama.getAttribute("src") === pemutarBaru.getAttribute("src")) {
      pemutarBaru.replaceWith(pemutarLama);
      if (mainLagi && pemutarLama.paused) pemutarLama.play().catch(() => { /* autoplay ditolak */ });
    }
    document.title = (JUDUL_HALAMAN[r.nama] || "Beranda") + " · Vedika Autentik";
    if (M.hidup && r.nama === "panggilan") {
      const tr = document.getElementById("transkrip");
      if (tr) tr.scrollTop = tr.scrollHeight;
    }
    window.scrollTo(0, tetap ? y : 0);
    const obrolan = ui.wa && document.querySelector("#modalWa .obrolan");
    if (obrolan) obrolan.scrollTop = obrolan.scrollHeight;
    if (sedangMengetik != null) {
      const kolom = document.querySelector('[data-aksi="catatan"]');
      if (kolom) { kolom.focus(); kolom.setSelectionRange(sedangMengetik, sedangMengetik); }
    }
  }

  function toast(pesan, tautan, teksTautan) {
    const w = document.getElementById("toast");
    const t = document.createElement("div");
    t.className = "toast";
    t.innerHTML = ikon("lencanaCek") + "<span>" + esc(pesan) + (tautan ? ' <a href="' + tautan + '">' + esc(teksTautan || "Buka") + "</a>" : "") + "</span>";
    w.appendChild(t);
    setTimeout(() => { t.style.transition = "opacity .3s"; t.style.opacity = "0"; setTimeout(() => t.remove(), 320); }, 4200);
  }

  /* ============================================================ sinkron API */

  const sigAntrean = (a) => JSON.stringify(Object.assign({}, a, { pengaturan: Object.assign({}, a.pengaturan, { waktu_server: null }) }));

  /* Toast seperti di simulasi: WA terkirim saat panggilan dimulai, dan hasil saat selesai. Status yang pertama kali
     terlihat (muat halaman, setelah reset) hanya dicatat, tidak di-toast. */
  function catatTransisi() {
    M.baris.forEach((b) => {
      const lama = M.lalu[b.id];
      if (lama !== undefined && lama === "antre" && b.status === "wa_terkirim") {
        toast("Pesan WA terkirim ke " + b.penerima.nama + ". Panggilan untuk " + b.pasien + " dimulai.", "#/panggilan/" + b.id, "Buka panggilan");
      } else if (lama !== undefined && !selesaiSt(lama) && selesaiSt(b.status)) {
        toast("Panggilan selesai: " + b.pasien + (b.label ? " · " + D.LABEL[b.label].nama : "") + ".", "#/kartu/" + b.id, "Buka kartu bukti");
      }
      M.lalu[b.id] = b.status;
    });
  }

  /* Hanya bila verifikator sedang menonton panggilannya: WA pemberitahuan muncul di ponsel saat terkirim, lalu
     pindah ke kartu bukti begitu selesai. S5: chat cadangan ditampilkan dulu sebelum pindah. */
  function catatTransisiDetail(d) {
    const r = rute();
    if (!(r.nama === "panggilan" && r.id === d.id)) return;
    if (d.status === "wa_terkirim" && !M.waDibuka[d.id]) { M.waDibuka[d.id] = true; bukaWa(d.id, "pemberitahuan", true); }
    if (!selesaiSt(d.status) || M.kartuDibuka[d.id]) return;
    if (!modeCoba(d)) { M.kartuDibuka[d.id] = true; ke("#/kartu/" + d.id); return; }
    if ((d.log || []).some((l) => l.status === "tidak_terhubung")) {
      M.kartuDibuka[d.id] = true;
      bukaWa(d.id, "cadangan", true);
      setTimeout(() => { const r2 = rute(); if (r2.nama === "panggilan" && r2.id === d.id) { tutupWa(); ke("#/kartu/" + d.id); } }, 5000);
    }
  }

  function terapkan(baru) {
    let berubah = false;
    const ubah = (kunci, nilai) => { const sig = kunci === "antrean" ? sigAntrean(nilai) : JSON.stringify(nilai); if (M.sig[kunci] === sig) return false; M.sig[kunci] = sig; berubah = true; return true; };
    M.waktuServer = baru.antrean.pengaturan.waktu_server;
    if (ubah("antrean", baru.antrean)) { M.antrean = baru.antrean; M.baris = baru.antrean.baris.map(A3.keBaris); catatTransisi(); }
    if (baru.detail && ubah("d:" + baru.detail.id, baru.detail)) { M.detail[baru.detail.id] = A3.kePasien(baru.detail); }
    if (baru.ringkasan && ubah("ringkasan", baru.ringkasan)) M.ringkasan = A3.keRingkasan(baru.ringkasan);
    if (baru.riwayat && ubah("riwayat", baru.riwayat)) M.riwayat = A3.keRiwayat(baru.riwayat);
    const r = rute();
    const d = (r.nama === "panggilan" || r.nama === "kartu") && r.id ? M.detail[r.id] : null;
    if (d && r.nama === "panggilan") { catatTransisiDetail(d); suaraApi(d); }
    if (berubah) gambar(true);
  }

  /* Satu putaran: antrean selalu, ditambah data layar yang sedang dibuka. Tiga kegagalan beruntun = API dianggap mati. */
  async function segarkan() {
    if (!M.hidup || M.sibuk) return;
    M.sibuk = true;
    try {
      const r = rute(), baru = {};
      baru.antrean = await A3.antrean();
      if ((r.nama === "panggilan" || r.nama === "kartu") && r.id) {
        try { baru.detail = await A3.panggilan(r.id); delete M.tidakAda[r.id]; } catch (e) { if (e.status === 404) M.tidakAda[r.id] = true; else throw e; }
      }
      if (r.nama === "ringkasan-rs") baru.ringkasan = await A3.ringkasanRs();
      if (r.nama === "riwayat") baru.riwayat = await A3.keputusan();
      M.gagal = 0;
      terapkan(baru);
    } catch (e) {
      M.gagal += 1;
      if (M.gagal >= 3) putusApi();
    } finally {
      M.sibuk = false;
    }
  }

  /* API terputus di tengah jalan: kembali ke simulasi dari data-v3.js, seperti bila API mati saat dimuat. */
  function putusApi() {
    clearInterval(M.timer);
    M.hidup = false;
    suaraHenti(); tutupWa();
    toast("API tidak terjangkau. Beralih ke simulasi lokal.");
    gambar(true);
  }

  const galatToast = (awal) => (e) => toast(awal + ": " + (e && e.message ? e.message : "tidak diketahui") + ".");

  function putuskanApi(id, isi) {
    A3.putuskan(id, isi).then((k) => {
      ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; ui.ubah = null;
      const nama = (M.detail[id] || barisApi(id) || {}).pasien || id;
      return segarkan().then(() => toast(D.TINDAKAN[k.tindakan].status + " · " + nama, "#/riwayat", "Lihat riwayat"));
    }).catch(galatToast("Keputusan gagal disimpan"));
  }

  /* ============================================================== peristiwa */

  const AKSI = {
    masuk() { S.masuk = true; simpan(); ke("#/beranda"); },
    menu() { ui.menuBuka = !ui.menuBuka; gambar(true); },
    "buka-baris"(el) { ke(el.dataset.tujuan); },
    wa(el) { bukaWa(el.dataset.id, el.dataset.jenis, false); },
    loncat(el) {
      const a = document.querySelector(".pemutar--ponsel audio");
      if (!a) return;
      a.currentTime = Number(el.dataset.detik);
      a.play().catch(() => { /* autoplay ditolak */ });
    },
    bisu() {
      ui.bisu = !ui.bisu;
      suara.klip.forEach((a) => { a.muted = ui.bisu; });
      document.querySelectorAll('[data-aksi="bisu"]').forEach((el) => { el.outerHTML = tombolBisu(); });
    },
    "ulang-demo"() {
      if (M.hidup) {
        A3.resetDemo().then(() => {
          tutupWa(); suaraHenti();
          Object.assign(ui, { filterRs: "", filterStatus: "", pilihLain: false, tindakanLain: null, catatan: null, rsBuka: null, menuBuka: false, ubah: null });
          M.detail = {}; M.lalu = {}; M.lihat = {}; M.terisi = {}; M.waDibuka = {}; M.kartuDibuka = {}; M.tidakAda = {}; M.sig = {}; M.ringkasan = null; M.riwayat = null;
          return segarkan();
        }).then(() => { ke("#/autentik"); toast("Demo dimulai ulang. Antrean dan ringkasan RS kembali ke keadaan awal."); }).catch(galatToast("Gagal memulai ulang demo"));
        return;
      }
      /* Hentikan panggilan yang sedang berjalan dan jadwal otomatis, lalu kosongkan semua hasil dan keputusan. */
      clearInterval(ui.timer); clearTimeout(ui.timerBerikut); tutupWa(); suaraHenti();
      const tetapMasuk = S.masuk;
      S = statusAwal(); S.masuk = tetapMasuk;
      Object.assign(ui, { filterRs: "", filterStatus: "", otomatis: false, jeda: false, aktif: null, pilihLain: false, tindakanLain: null, catatan: null, rsBuka: null, menuBuka: false });
      simpan();
      ke("#/autentik");
      toast("Demo dimulai ulang. Antrean dan ringkasan RS kembali ke keadaan awal.");
    },
    "lihat-kartu-rs"(el) { ui.rsBuka = ui.rsBuka === el.dataset.id ? null : el.dataset.id; gambar(true); },
    setujui(el) {
      if (M.hidup) { putuskanApi(el.dataset.id, { ikut_saran: true }); return; }
      putuskan(el.dataset.id, D.SARAN[tunggal(el.dataset.id).label], "", true);
    },
    "pilih-lain"() { ui.pilihLain = true; ui.tindakanLain = null; ui.catatan = ""; gambar(true); },
    "batal-lain"() { ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; gambar(true); },
    "simpan-lain"(el) {
      if (!alasanTerisi()) return;
      if (M.hidup) { putuskanApi(el.dataset.id, { ikut_saran: false, tindakan: ui.tindakanLain, alasan: ui.catatan.trim() }); return; }
      putuskan(el.dataset.id, ui.tindakanLain, ui.catatan.trim(), false);
    },
    /* API: "Ubah keputusan" hanya membuka pilihan; keputusan lama baru tergantikan saat yang baru disimpan. */
    "batal-putusan"(el) {
      if (M.hidup) { ui.ubah = el.dataset.id; ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; gambar(true); return; }
      delete S.keputusan[el.dataset.id]; simpan(); gambar(true);
    },
    "batal-ubah"() { ui.ubah = null; ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; gambar(true); },
    "tutup-wa"() { tutupWa(); },
    diam() { /* klik di dalam kartu tidak menutup latar */ },
    telepon(el) {
      if (!M.hidup) { mulaiPanggilan(el.dataset.id); return; }
      const id = el.dataset.id, b = barisApi(id);
      A3.mulai(id).then(() => {
        toast("Panggilan untuk " + (b ? b.pasien : id) + " ditandai Telepon sekarang. Agen mengambilnya sebentar lagi.", "#/panggilan/" + id, "Buka panggilan");
        return segarkan();
      }).catch(galatToast("Gagal memulai panggilan"));
    },
    otomatis() {
      if (M.hidup) {
        const nyala = !otomatisAktif();
        A3.ubahPengaturan({ mode_otomatis: nyala }).then(segarkan).then(() => { if (!nyala) toast("Panggilan otomatis dinonaktifkan."); }).catch(galatToast("Gagal mengubah mode otomatis"));
        return;
      }
      ui.otomatis = !ui.otomatis;
      ui.jeda = false;
      clearTimeout(ui.timerBerikut);
      gambar(true);
      if (ui.otomatis) lanjutOtomatis();
      else toast("Panggilan otomatis dinonaktifkan.");
    },
    jeda() {
      if (M.hidup) { A3.ubahPengaturan({ jeda: !jedaAktif() }).then(segarkan).catch(galatToast("Gagal mengubah jeda")); return; }
      ui.jeda = !ui.jeda;
      clearTimeout(ui.timerBerikut);
      gambar(true);
      if (!ui.jeda) lanjutOtomatis();
    }
  };

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-aksi]");
    if (!el || el.tagName === "SELECT" || el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && el.type !== "checkbox" && el.type !== "radio")) return;
    const f = AKSI[el.dataset.aksi];
    if (f) { if (el.tagName === "A") e.preventDefault(); f(el); }
    if (ui.menuBuka && !e.target.closest("#sisi") && el.dataset.aksi !== "menu") { ui.menuBuka = false; gambar(true); }
  });

  document.addEventListener("keydown", (e) => {
    if (e.altKey && e.code === "KeyL") { e.preventDefault(); lompatAkhir(); }
    else if (e.key === "Escape") tutupWa();
    else if ((e.key === "Enter" || e.key === " ") && e.target.dataset && e.target.dataset.aksi === "loncat") { e.preventDefault(); AKSI.loncat(e.target); }
  });

  document.addEventListener("change", (e) => {
    const a = e.target.dataset && e.target.dataset.aksi;
    if (a === "saring-rs") { ui.filterRs = e.target.value; gambar(true); }
    else if (a === "saring-status") { ui.filterStatus = e.target.value; gambar(true); }
    else if (a === "tindakan-lain") { ui.tindakanLain = e.target.value; gambar(true); }
  });

  /* Tombol simpan hanya menyala bila tindakan dipilih dan alasan terisi; diperbarui tanpa merender ulang agar kursor tetap. */
  document.addEventListener("input", (e) => {
    if (!e.target.dataset || e.target.dataset.aksi !== "catatan") return;
    ui.catatan = e.target.value;
    const simpanBtn = document.querySelector('[data-aksi="simpan-lain"]');
    if (simpanBtn) simpanBtn.disabled = !alasanTerisi();
  });

  window.addEventListener("hashchange", () => {
    ui.menuBuka = false; ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; ui.ubah = null;
    suaraSelaraskan(); gambar(false);
    if (M.hidup) segarkan();
  });

  /* Mulai: pakai API bila sehat dan antreannya bisa dibaca, selain itu simulasi dari data-v3.js. */
  async function mulaiApp() {
    if (A3 && await A3.sehat()) {
      M.hidup = true;
      await segarkan();
      if (M.antrean) M.timer = setInterval(segarkan, 1000); else M.hidup = false;
    }
    gambar(false);
  }
  mulaiApp();
})();
