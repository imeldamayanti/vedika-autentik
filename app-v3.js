/* Vedika Autentik v3: simulasi konfirmasi suara peserta di aplikasi verifikasi klaim.

   Alur: masuk → beranda → Autentik (antrean konfirmasi) → panggilan berlangsung →
   kartu bukti → keputusan verifikator → ringkasan rumah sakit → riwayat.

   Tidak ada telepon atau AI yang berjalan di sini. Semua panggilan adalah simulasi
   dari data tulisan tangan di data-v3.js. */

(function () {
  "use strict";

  const D = window.DATA3;

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
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    pengguna: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    kunci: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    lencanaCek: '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>'
  };
  const ikon = (n) => '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + IKON[n] + "</svg>";
  const logoVeritas = '<img src="assets/veritas-mark.svg" alt="" aria-hidden="true">';

  /* ================================================================ status */

  const KUNCI_SIMPAN = "vedika.konfirmasi.v1";

  function statusAwal() {
    return { masuk: false };
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
  const ui = { menuBuka: false };

  /* ============================================================== perute */

  /* #/beranda, #/autentik, #/panggilan/:id, #/kartu/:id, #/ringkasan-rs, #/riwayat */
  function rute() {
    const bagian = (location.hash || "").replace(/^#\/?/, "").split("/").filter(Boolean);
    return { nama: bagian[0] || "beranda", id: bagian[1] || null };
  }
  const ke = (h) => { if (location.hash !== h) location.hash = h; else gambar(true); };

  /* ============================================================== kerangka */

  function kerangka(r, isi, jejak) {
    const dalamAutentik = r.nama === "autentik" || r.nama === "panggilan" || r.nama === "kartu";
    const aktif = (ya) => (ya ? ' aria-current="page"' : "");
    return '<div class="kerangka">' +
      '<aside class="sisi' + (ui.menuBuka ? " buka" : "") + '" id="sisi">' +
        '<a class="merek" href="#/beranda"><span class="merek-ikon">' + ikon("perisai") + "</span><span><b>VEDIKA</b><span>Verifikasi Digital Klaim</span></span></a>" +
        '<nav class="nav" aria-label="Menu utama">' +
          '<a href="#/beranda"' + aktif(r.nama === "beranda") + ">" + ikon("rumah") + "Beranda</a>" +
          '<span class="nav-judul kapital">Verifikasi</span>' +
          '<button class="mati" type="button" aria-disabled="true" title="Menu Vedika yang sudah ada, tidak termasuk prototipe">' + ikon("berkas") + "Verifikasi klaim<small>Sudah ada</small></button>" +
          '<a class="nav-autentik induk" href="#/autentik">' + logoVeritas + "Autentik</a>" +
          '<div class="nav-sub">' +
            '<a href="#/autentik"' + aktif(dalamAutentik) + ">Antrean konfirmasi</a>" +
            '<a href="#/ringkasan-rs"' + aktif(r.nama === "ringkasan-rs") + ">Ringkasan RS</a>" +
          "</div>" +
          '<a href="#/riwayat"' + aktif(r.nama === "riwayat") + ">" + ikon("riwayat") + "Riwayat keputusan</a>" +
        "</nav>" +
        '<div class="sisi-kaki nav">' +
          '<p class="catatan-prototipe"><b>Simulasi Healthkathon 2026.</b> Semua data fiktif.</p>' +
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

  function lamanBeranda() { return kepala("Beranda", D.HARI_INI + " · " + D.VERIFIKATOR.kantor) + kosong("Beranda v3", "Diisi pada tiket UI-09."); }
  function lamanAntrean() { return kepala("Antrean konfirmasi", "Layanan Agustus 2026") + kosong("Antrean konfirmasi", "Diisi pada tiket UI-03."); }
  function lamanPanggilan(id) { return kepala("Panggilan berlangsung", id) + kosong("Panggilan", "Diisi pada tiket UI-04."); }
  function lamanKartu(id) { return kepala("Kartu bukti", id) + kosong("Kartu bukti", "Diisi pada tiket UI-06."); }
  function lamanRingkasanRs() { return kepala("Ringkasan per rumah sakit", "Layanan Agustus 2026") + kosong("Ringkasan RS", "Diisi pada tiket UI-08."); }
  function lamanRiwayat() { return kepala("Riwayat keputusan", "Semua keputusan verifikator atas panggilan konfirmasi.") + kosong("Riwayat keputusan", "Diisi pada tiket UI-10."); }

  /* ============================================================== render */

  const JUDUL_HALAMAN = { beranda: "Beranda", autentik: "Antrean konfirmasi", panggilan: "Panggilan", kartu: "Kartu bukti", "ringkasan-rs": "Ringkasan RS", riwayat: "Riwayat keputusan" };

  function gambar(tetap) {
    const y = window.scrollY;
    const r = rute();
    const akar = document.getElementById("akar");
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

    akar.innerHTML = kerangka(r, isi, jejak);
    document.title = (JUDUL_HALAMAN[r.nama] || "Beranda") + " · Vedika Autentik";
    window.scrollTo(0, tetap ? y : 0);
  }

  function toast(pesan, tautan, teksTautan) {
    const w = document.getElementById("toast");
    const t = document.createElement("div");
    t.className = "toast";
    t.innerHTML = ikon("lencanaCek") + "<span>" + esc(pesan) + (tautan ? ' <a href="' + tautan + '">' + esc(teksTautan || "Buka") + "</a>" : "") + "</span>";
    w.appendChild(t);
    setTimeout(() => { t.style.transition = "opacity .3s"; t.style.opacity = "0"; setTimeout(() => t.remove(), 320); }, 4200);
  }

  /* ============================================================== peristiwa */

  const AKSI = {
    masuk() { S.masuk = true; simpan(); ke("#/beranda"); },
    menu() { ui.menuBuka = !ui.menuBuka; gambar(true); }
  };

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-aksi]");
    if (!el || el.tagName === "SELECT" || el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && el.type !== "checkbox" && el.type !== "radio")) return;
    const f = AKSI[el.dataset.aksi];
    if (f) { if (el.tagName === "A") e.preventDefault(); f(el); }
    if (ui.menuBuka && !e.target.closest("#sisi") && el.dataset.aksi !== "menu") { ui.menuBuka = false; gambar(true); }
  });

  window.addEventListener("hashchange", () => { ui.menuBuka = false; gambar(false); });

  gambar(false);
})();
