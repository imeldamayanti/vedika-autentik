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
    telepon: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    awas: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    jeda: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    main: '<polygon points="6 3 20 12 6 21 6 3"/>',
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    pengguna: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    kunci: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
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
    otomatis: false, jeda: false, aktif: null, timer: null, timerBerikut: null, wa: null, transkripBuka: false,
    pilihLain: false, tindakanLain: null, catatan: null
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

  /* Durasi dipadatkan: panggilan nyata 1-2 menit berjalan sekitar 45 detik di layar.
     Jeda pesan WA ke panggilan (PRD R2.2, bawaan prototipe 1 menit) ikut dipadatkan. */
  const SIM = { sambung: 4, rekam: 6, rentang: 32, kartu: 4, jedaBerikut: 12000 };

  const tidakTerhubung = (p) => p.jawaban.status_panggilan === "tidak_terhubung";

  /* Titik waktu layar (detik sejak panggilan dimulai) untuk tiap tahap. S5 punya dua percobaan
     yang gagal lalu chat cadangan; skenario lain tersambung, merekam, lalu dibaca. */
  function titik(p) {
    if (tidakTerhubung(p)) return { coba1: 4, gagal1: 9, coba2: 12, gagal2: 17, chat: 19, kartu: 22, total: 24 };
    const akhir = SIM.rekam + SIM.rentang;
    return { sambung: SIM.sambung, rekam: SIM.rekam, akhir: akhir, kartu: akhir + SIM.kartu, total: akhir + SIM.kartu + 2 };
  }

  function statusSim(p, t) {
    const k = titik(p);
    if (tidakTerhubung(p)) return t >= k.chat ? "tidak_terhubung" : t >= k.coba1 ? "menelepon" : "wa";
    return t >= k.sambung ? "menelepon" : "wa";
  }

  function statusBaris(id) {
    if (D.LATAR[id]) return "selesai";
    if (S.hasil[id]) return tidakTerhubung(tunggal(id)) ? "tidak_terhubung" : "selesai";
    if (ui.aktif && ui.aktif.id === id) return ui.aktif.status;
    return "antre";
  }

  const labelBaris = (id) => (D.LATAR[id] || S.hasil[id] ? tunggal(id).label : null);

  /* Semua panggilan yang sudah selesai: 4 latar sebelum demo dan skenario yang sudah dijalankan. */
  const panggilanSelesai = () => Object.keys(D.LATAR).map((id) => D.LATAR[id]).concat(Object.keys(S.hasil).map((id) => D.SKENARIO[id]));

  function angka() {
    const selesai = panggilanSelesai();
    return {
      terpicu: D.PASIEN_TERPICU, aktif: D.PASIEN_AKTIF, ditelepon: selesai.length,
      tidakSesuai: selesai.filter((p) => p.label === "tidak_sesuai").length,
      rsKlarifikasi: D.ringkasanRs(selesai).filter((r) => r.status === "Perlu klarifikasi RS").length
    };
  }

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
    if (dilihat) perbaruiPanggilan(p, t);
  }

  function selesaikan(id) {
    const p = D.SKENARIO[id];
    clearInterval(ui.timer);
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
    const menunggu = panggilanSelesai().filter((p) => p.label === "tidak_sesuai" && !S.keputusan[p.id]).length;
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
  /* ============================================================== antrean */

  const penerimaTeks = (p) => (p.penerima.hubungan === "peserta" ? "Peserta" : esc(p.penerima.nama) + ' <span class="redup">(' + esc(p.penerima.hubungan) + ")</span>");

  function kartuAngka() {
    const a = angka();
    return '<div class="kartu-angka">' +
      "<div><b>" + a.terpicu + "</b><span>pasien terpicu dari " + a.aktif + " aktif</span></div>" +
      "<div><b>" + a.ditelepon + "</b><span>sudah ditelepon</span></div>" +
      '<div class="' + (a.tidakSesuai ? "peringatan" : "") + '"><b>' + a.tidakSesuai + "</b><span>tidak sesuai</span></div>" +
      '<div class="' + (a.rsKlarifikasi ? "waspada" : "") + '"><b>' + a.rsKlarifikasi + "</b><span>RS perlu klarifikasi</span></div>" +
    "</div>";
  }

  /* Tujuan klik baris: kartu bukti bila sudah selesai, layar panggilan bila skenario, kosong bila belum ada panggilan. */
  function tujuanBaris(p) {
    if (D.LATAR[p.id] || S.hasil[p.id]) return "#/kartu/" + p.id;
    if (D.SKENARIO[p.id]) return "#/panggilan/" + p.id;
    return null;
  }

  function barisAntrean() {
    return D.URUTAN_ANTREAN
      .map((id) => Object.assign({ st: statusBaris(id) }, tunggal(id)))
      .filter((p) => !ui.filterRs || p.rs === ui.filterRs)
      .filter((p) => !ui.filterStatus || p.st === ui.filterStatus);
  }

  function lamanAntrean() {
    const baris = barisAntrean().map((p) => {
      const tujuan = tujuanBaris(p), lab = labelBaris(p.id);
      const bisaTelepon = D.SKENARIO[p.id] && p.st === "antre";
      let aksi;
      if (bisaTelepon) {
        aksi = '<button class="btn btn--kecil btn--primer" type="button" data-aksi="telepon" data-id="' + p.id + '"' + (ui.aktif ? ' disabled title="Satu panggilan aktif pada satu waktu"' : "") + ">" + ikon("telepon") + "Telepon sekarang</button>";
      } else if (tujuan) {
        aksi = '<a class="btn btn--kecil" href="' + tujuan + '">Lihat</a>';
      } else {
        aksi = '<span class="redup">Belum ditelepon</span>';
      }
      return "<tr" + (tujuan ? ' class="bisa-klik" data-aksi="buka-baris" data-tujuan="' + tujuan + '"' : "") + ">" +
        '<td class="nama-berkas"><b>' + esc(p.pasien) + "</b><span>" + p.umur + " th</span></td>" +
        '<td class="sembunyi-hp">' + esc(D.namaRs(p.rs)) + "</td>" +
        '<td class="angka sembunyi-hp">' + p.ditagih + " sesi</td>" +
        '<td class="lebar-penuh"><div class="chip-ind-wadah">' + p.indikator.map((i) => '<span class="chip-ind" title="' + esc(D.INDIKATOR[i].arti) + '">' + D.INDIKATOR[i].nama + "</span>").join("") + "</div></td>" +
        '<td class="sembunyi-hp">' + penerimaTeks(p) + "</td>" +
        '<td><div class="sel-status"><span class="status-chip status-chip--' + p.st + '">' + STATUS[p.st] + "</span>" + (lab ? labelChip(lab) + "<small>" + (S.keputusan[p.id] ? D.TINDAKAN[S.keputusan[p.id].tindakan].status : "Belum diputuskan") + "</small>" : "") + "</div></td>" +
        '<td class="aksi lebar-penuh">' + aksi + "</td></tr>";
    }).join("");

    const keadaan = ui.jeda ? "Dijeda. Panggilan yang berjalan diselesaikan dulu." : ui.aktif ? "1 panggilan berjalan." : "Menyiapkan panggilan berikutnya.";

    return '<div class="kepala"><div><h1>Antrean konfirmasi · layanan ' + D.BULAN + "</h1>" +
        '<p class="keterangan-pemicu">Pasien masuk antrean jika dua indikator atau lebih aktif. Panggilan otomatis berjalan pukul 09.00–17.00 dan hanya satu panggilan aktif pada satu waktu.</p></div></div>' +
      kartuAngka() +
      '<section class="panel tabel-antrean"><div class="bar-antrean"><span class="kapital">Filter</span>' +
        '<select class="pilih" data-aksi="saring-rs" aria-label="Saring menurut rumah sakit"><option value="">Semua RS</option>' +
          D.RS.map((r) => '<option value="' + r.id + '"' + (ui.filterRs === r.id ? " selected" : "") + ">" + esc(r.nama) + "</option>").join("") + "</select>" +
        '<select class="pilih" data-aksi="saring-status" aria-label="Saring menurut status"><option value="">Semua status</option>' +
          Object.keys(STATUS).map((k) => '<option value="' + k + '"' + (ui.filterStatus === k ? " selected" : "") + ">" + STATUS[k] + "</option>").join("") + "</select>" +
        '<div class="kanan">' + (ui.otomatis ? '<span class="redup" style="font-size:12.5px">' + keadaan + "</span>" : "") +
          '<button class="btn btn--otomatis" type="button" data-aksi="otomatis" aria-pressed="' + ui.otomatis + '">' + ikon("telepon") + "Panggilan otomatis: <b>" + (ui.otomatis ? "AKTIF" : "NONAKTIF") + "</b></button>" +
          '<button class="btn" type="button" data-aksi="jeda"' + (ui.otomatis ? "" : " disabled") + ">" + ikon(ui.jeda ? "main" : "jeda") + (ui.jeda ? "Lanjutkan" : "Jeda") + "</button></div></div>" +
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
  const detikRekam = (p, t) => Math.max(0, Math.min(p.durasi, (t - SIM.rekam) / SIM.rentang * p.durasi));

  /* Jumlah baris transkrip yang sudah muncul pada detik layar t. */
  const barisTampil = (p, t) => (t == null ? 0 : p.transkrip.filter((l) => t >= SIM.rekam + l[1] * SIM.rentang / p.durasi).length);

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

  function htmlLangkah(p, t) {
    return langkahSim(p, t).map((l) => '<li class="' + l.state + '"><span class="ikon">' + (l.state === "selesai" ? ikon("cek") : l.state === "gagal" ? ikon("x") : "") + "</span>" +
      "<div><b>" + l.nama + "</b>" + (l.ket ? "<small>" + l.ket + "</small>" : "") + "</div><time>" + (l.state === "menunggu" ? "" : l.jam) + "</time></li>").join("");
  }

  function htmlTranskrip(p, t) {
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

  function nilaiIsian(p, k) {
    const j = p.jawaban;
    if (k === "penerima") return j.penerima === "peserta" ? "Peserta" : "Keluarga (" + j.hubungan + ")";
    if (k === "hadir") return j.hadir === true ? "Ya" : j.hadir === false ? "Tidak" : "Tidak dijawab";
    if (k === "jumlah") return j.jumlah_min == null ? "Tidak dijawab" : j.jumlah_min === j.jumlah_maks ? j.jumlah_min + " sesi" : j.jumlah_min + "–" + j.jumlah_maks + " sesi";
    if (k === "keyakinan") return j.keyakinan === "tinggi" ? "Tinggi" : j.keyakinan === "rendah" ? "Rendah" : "–";
    if (k === "libur") return !p.tanggalLibur.length ? "Tidak ditanyakan" : j.membantah_tanggal_libur === true ? "Membantah" : j.membantah_tanggal_libur === false ? "Mengakui" : "Tidak jelas";
    return j.tanda_bahaya.length ? j.tanda_bahaya.map((x) => TANDA_BAHAYA[x]).join(", ") : "Tidak ada";
  }

  /* Isian terisi bertahap menurut baris transkrip; setelah rekaman selesai semuanya terisi. */
  function terisi(p, t) {
    if (tidakTerhubung(p) || t == null) return [];
    const n = barisTampil(p, t), selesaiRekam = t >= titik(p).akhir;
    return ISIAN.map((x) => x[0]).filter((k) => selesaiRekam || (p.tangkap[k] != null && n > p.tangkap[k]));
  }

  function htmlIsian(p, t) {
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

  function isiPanggilan(p, t) {
    return '<div class="panggilan-grid" id="panggilan">' +
      '<section class="panel"><div class="panel-kepala"><h2>Progres</h2></div><ol class="progres">' + htmlLangkah(p, t) + "</ol>" +
        '<p class="catatan-simulasi">Simulasi: ' + (tidakTerhubung(p) ? "dua percobaan tanpa jawaban" : "panggilan nyata " + mmss(p.durasi)) + " dipadatkan menjadi sekitar " + (tidakTerhubung(p) ? "25" : "45") + " detik. Tidak ada suara yang diputar.</p></section>" +
      '<section class="panel"><div class="panel-kepala"><h2>' + (tidakTerhubung(p) ? "Log panggilan" : "Transkrip langsung") + '</h2></div><div class="transkrip" id="transkrip" aria-live="polite">' + htmlTranskrip(p, t) + "</div></section>" +
      '<section class="panel"><div class="panel-kepala"><h2>Yang ditangkap AI</h2></div><dl class="isian">' + htmlIsian(p, t) + "</dl></section>" +
    "</div>";
  }

  function lamanPanggilan(id) {
    const p = D.SKENARIO[id];
    if (!p) return kepala("Panggilan tidak ditemukan", "Hanya pasien di antrean yang punya panggilan simulasi.") + '<section class="panel"><div class="belum-mulai"><b>Tidak ada panggilan untuk ' + esc(id || "") + '</b><a class="btn btn--primer" href="#/autentik">Ke antrean konfirmasi</a></div></section>';
    const a = ui.aktif && ui.aktif.id === id;
    const t = a ? detikLayar() : null;
    const libur = p.tanggalLibur.length ? p.tanggalLibur.join(" dan ") + " " + D.BULAN_PENDEK : "tidak ada";
    const aksi = a ? '<span class="status-chip status-chip--' + ui.aktif.status + '">' + STATUS[ui.aktif.status] + "</span>"
      : S.hasil[id] ? "" : '<button class="btn btn--primer" type="button" data-aksi="telepon" data-id="' + id + '"' + (ui.aktif ? ' disabled title="Satu panggilan aktif pada satu waktu"' : "") + ">" + ikon("telepon") + "Telepon sekarang</button>";
    const kop = '<div class="kepala-panggilan"><div><h1>' + esc(p.pasien) + " · " + esc(D.namaRs(p.rs)) + " · " + D.BULAN + "</h1>" +
      '<div class="meta-panggilan"><span><b>Ditagih</b>' + p.ditagih + " sesi</span>" +
        '<span><b>Indikator</b><span class="chip-ind-wadah">' + p.indikator.map((i) => '<span class="chip-ind" title="' + esc(D.INDIKATOR[i].arti) + '">' + D.INDIKATOR[i].nama + "</span>").join("") + "</span></span>" +
        "<span><b>Tanggal libur</b>" + libur + "</span><span><b>Penerima</b>" + penerimaTeks(p) + "</span></div></div>" +
      '<div class="kepala-aksi">' + aksi + "</div></div>";
    if (S.hasil[id]) {
      return kop + '<section class="panel"><div class="belum-mulai"><b>Panggilan sudah selesai</b><p>Hasilnya ada di kartu bukti.</p><a class="btn btn--primer" href="#/kartu/' + id + '">Buka kartu bukti</a></div></section>';
    }
    return kop + isiPanggilan(p, t);
  }

  /* ================================================================ mockup WA */

  /* Menit (jam simulasi) saat panggilan dimulai, untuk cap waktu di gelembung. */
  const menitPanggilan = (id) => (ui.aktif && ui.aktif.id === id ? ui.aktif.menit : S.hasil[id] ? S.hasil[id].menit : menitSekarang());

  const gelembungWa = (teks, jam) => '<div class="gelembung dari-bpjs"><p>' + esc(teks) + "</p><small>" + jam + "</small></div>";

  /* Komponen ponsel dari v2. Pengirim hanya nomor tim (Simulasi), bukan nama atau logo BPJS. */
  function modalWa() {
    const p = D.SKENARIO[ui.wa.id], cadangan = ui.wa.jenis === "cadangan";
    const m = menitPanggilan(p.id);
    const obrolan = '<span class="tanggal-obrolan">Hari ini</span>' + gelembungWa(D.pesanPemberitahuan(p), formatJam(m)) +
      (cadangan ? '<div class="gelembung sistem">Panggilan suara tak terjawab · ' + formatJam(m + D.JEDA_PESAN_MENIT) + "</div>" +
        '<div class="gelembung sistem">Panggilan suara tak terjawab · ' + formatJam(m + D.JEDA_PESAN_MENIT + 3) + "</div>" +
        gelembungWa(D.pesanCadangan(p), formatJam(m + D.JEDA_PESAN_MENIT + 4)) : "");
    const petunjuk = cadangan ? "Penerima belum membalas. Jawaban 1–6 menggantikan panggilan." : "Penerima belum membalas. Pesan ini tanpa tautan.";
    const aturan = cadangan
      ? ["Dikirim setelah dua kali panggilan tidak diangkat (jeda 2 menit di prototipe, 2 jam di produksi).", "Satu pertanyaan, jawaban cukup dengan angka 1–6.", "Tanpa tautan, tidak meminta data pribadi atau pembayaran.", "Tidak dijawab bukan sinyal negatif: label tetap Tidak terhubung."]
      : ["Dikirim sebelum panggilan. Jeda " + D.JEDA_PESAN_MENIT + " menit di prototipe, 10 menit di produksi.", "Tanpa tautan, karena penipu sering menyamar sebagai BPJS.", "Tidak meminta data pribadi, kode OTP, atau pembayaran.", "Mengarahkan penerima mengecek ke Care Center 165."];
    return '<div class="modal-wa" id="modalWa" data-aksi="tutup-wa"><div class="modal-wa-kartu" data-aksi="diam" role="dialog" aria-modal="true" aria-label="Simulasi layar WhatsApp penerima">' +
      '<button class="modal-wa-tutup" type="button" data-aksi="tutup-wa" aria-label="Tutup">' + ikon("x") + "</button>" +
      '<div class="ponsel"><div class="ponsel-layar"><div class="ponsel-kepala"><span class="foto">' + ikon("pengguna") + "</span><div><b>" + D.NOMOR_PENELEPON + "</b><span>Nomor tim · Simulasi</span></div></div>" +
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
    const sig = [langkahSim(p, t).map((l) => l.state[0]).join(""), barisTampil(p, t), terisi(p, t).length, logPercobaan(p, t).length, t >= titik(p).akhir].join("|");
    const el = document.getElementById("panggilan");
    if (el && sig !== a.sig) {
      a.sig = sig;
      el.outerHTML = isiPanggilan(p, t);
      const tr = document.getElementById("transkrip");
      if (tr) tr.scrollTop = tr.scrollHeight;
    }
    const d = document.getElementById("durasiLive");
    if (d) d.textContent = mmss(detikRekam(p, t));
  }

  /* Pintasan tersembunyi Alt+L: lompat ke akhir panggilan yang sedang berjalan, hasilnya sama dengan menunggu. */
  function lompatAkhir() {
    if (!ui.aktif) return;
    ui.aktif.mulai = Date.now() - (titik(D.SKENARIO[ui.aktif.id]).total + 1) * 1000;
    tick();
  }
  /* ============================================================ kartu bukti */

  const daftarTanggal = (t) => t.join(" dan ") + " " + D.BULAN_PENDEK;

  function waktuPanggilan(p) {
    return D.LATAR[p.id] ? D.LATAR[p.id].waktu : "6 Okt 2026, " + formatJam(S.hasil[p.id].menit);
  }

  /* Versi penerima, selisih, dan keterangannya untuk tiga kartu. Yang tidak dihitung tampil "–". */
  function ringkasKartu(p) {
    const j = p.jawaban, dihitung = p.label === "tidak_sesuai" || p.label === "sesuai";
    let versi = "–", versiKet = "", gaya = "netral";
    if (p.label === "tidak_terhubung") versiKet = "Belum ada jawaban. Panggilan tidak diangkat 2 kali.";
    else if (p.label === "menolak") versiKet = "Penerima menolak menjawab. Tidak dihitung sebagai sinyal negatif.";
    else {
      versi = j.jumlah_min === j.jumlah_maks ? j.jumlah_min : j.jumlah_min + "–" + j.jumlah_maks;
      versiKet = p.label === "tidak_yakin" ? "Perkiraan saja, keyakinan rendah."
        : j.membantah_tanggal_libur === true ? "Membantah ada sesi pada " + daftarTanggal(p.tanggalLibur) + "."
        : !p.tanggalLibur.length ? "AI tidak menanyakan tanggal libur karena tidak ada." : "";
    }
    const sel = D.selisih(p);
    let selisihTeks = "–", selisihKet = "Tidak dihitung pada ringkasan RS.";
    if (dihitung) {
      selisihTeks = sel;
      selisihKet = "Toleransi salah ingat: " + D.TOLERANSI + " sesi. " + (sel > D.TOLERANSI ? "Selisih di atas toleransi." : "Masih dalam toleransi.");
      gaya = sel > D.TOLERANSI ? "beda" : "sama";
    }
    if (p.label === "tidak_yakin") selisihKet = "Tidak dihitung karena penerima tidak yakin.";
    return { versi: versi, versiKet: versiKet, selisih: selisihTeks, selisihKet: selisihKet, gaya: gaya, versiGaya: p.label === "tidak_sesuai" ? "beda" : p.label === "sesuai" ? "sama" : "netral" };
  }

  /* Keputusan (R5.3): setujui saran, atau pilih tindakan lain dengan alasan wajib. */
  const alasanTerisi = () => !!(ui.tindakanLain && ui.catatan && ui.catatan.trim());

  function aksiKeputusan(p) {
    if (!ui.pilihLain) {
      return '<div class="saran-tombol"><button class="btn btn--primer" type="button" data-aksi="setujui" data-id="' + p.id + '">' + ikon("cek") + "Setujui saran</button>" +
        '<button class="btn btn--hantu" type="button" data-aksi="pilih-lain">Pilih tindakan lain</button></div>';
    }
    const lain = D.PILIHAN_TINDAKAN.filter((x) => x !== D.SARAN[p.label]);
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
    const p = tunggal(id);
    if (!p || !(D.LATAR[id] || D.SKENARIO[id])) {
      return kepala("Kartu bukti tidak ditemukan", "Kartu bukti hanya ada untuk pasien yang sudah ditelepon.") + '<section class="panel"><div class="belum-mulai"><b>Tidak ada kartu untuk ' + esc(id || "") + '</b><a class="btn btn--primer" href="#/autentik">Ke antrean konfirmasi</a></div></section>';
    }
    if (D.SKENARIO[id] && !S.hasil[id]) {
      return kepala("Kartu bukti belum tersedia", p.pasien) + '<section class="panel"><div class="belum-mulai"><b>' + esc(p.pasien) + ' belum ditelepon</b><p>Kartu bukti dibuat setelah panggilan selesai.</p><a class="btn btn--primer" href="#/panggilan/' + id + '">Ke layar panggilan</a></div></section>';
    }
    const j = p.jawaban, rk = ringkasKartu(p), latar = !!D.LATAR[id];
    const saran = D.TINDAKAN[D.SARAN[p.label]];
    const rs = D.ringkasanRs(panggilanSelesai()).find((r) => r.id_rs === p.rs);
    const bahaya = j.tanda_bahaya.length;
    const simpanTeks = p.label === "tidak_sesuai" || p.label === "sesuai";

    const tanggal = '<div class="tanggal-sesi">' + p.tanggal.map((h) => {
      const tanda = p.tandaTanggal[h];
      return '<span class="tgl' + (tanda ? " tgl--tanda" : "") + '">' + h + (tanda ? "<small>" + tanda + "</small>" : "") + "</span>";
    }).join("") + "</div>";
    const nTanda = Object.keys(p.tandaTanggal).length;

    const durasi = tidakTerhubung(p) ? "2 percobaan, tidak diangkat" : "durasi " + mmss(p.durasi);
    const kop = '<div class="kepala-kartu"><div><h1>' + esc(p.pasien) + " · " + esc(D.namaRs(p.rs)) + "</h1>" +
      '<div class="meta-panggilan"><span><b>Layanan</b>Fisioterapi · ' + D.BULAN + "</span><span><b>Panggilan</b>" + waktuPanggilan(p) + " · " + durasi + "</span><span><b>Penerima</b>" + penerimaTeks(p) + "</span></div></div>" +
      labelChip(p.label, true) + "</div>";

    const peringatan = bahaya ? '<div class="tanda-bahaya" role="alert">' + ikon("awas") + "<div><b>Tanda bahaya: " + esc(j.tanda_bahaya.map((x) => TANDA_BAHAYA[x]).join(", ")) + "</b><p>" + esc(j.ringkasan) + "</p></div></div>" : "";

    const tiga = '<div class="tiga-kartu">' +
      '<section><span class="kapital">Ditagih rumah sakit</span><div class="besar">' + p.ditagih + "<small>sesi</small></div>" + tanggal +
        '<p class="ket">' + (nTanda ? nTanda + " tanggal jatuh di Minggu atau libur nasional (ditandai kuning)." : "Tidak ada sesi di hari Minggu atau libur nasional.") + "</p></section>" +
      '<section class="' + rk.versiGaya + '"><span class="kapital">Versi peserta</span><div class="besar">' + rk.versi + (rk.versi === "–" ? "" : "<small>sesi</small>") + '</div><p class="ket">' + esc(rk.versiKet) + "</p></section>" +
      '<section class="' + rk.gaya + '"><span class="kapital">Selisih</span><div class="besar">' + rk.selisih + (rk.selisih === "–" ? "" : "<small>sesi</small>") + '</div><p class="ket">' + esc(rk.selisihKet) + "</p></section>" +
    "</div>";

    let bukti;
    if (latar) bukti = '<p class="tanpa-rekaman">Riwayat latar sebelum demo: rekaman dan transkrip tidak tersedia di simulasi.</p>';
    else if (p.rekaman) bukti = '<div class="pemutar"><audio controls preload="none" src="' + p.rekaman + '">Peramban tidak mendukung pemutar audio.</audio><small>Rekaman placeholder untuk simulasi: nada pendek, bukan suara penerima.</small></div>';
    else bukti = '<p class="tanpa-rekaman">Tidak ada rekaman atau transkrip yang disimpan untuk label ' + D.LABEL[p.label].nama + ". Hanya status dan hasil terstruktur.</p>";
    const tombolTranskrip = simpanTeks && !latar
      ? '<div class="tombol-transkrip"><button class="btn btn--kecil" type="button" data-aksi="transkrip" aria-expanded="' + ui.transkripBuka + '">' + ikon("berkas") + (ui.transkripBuka ? "Sembunyikan transkrip lengkap" : "Transkrip lengkap") + "</button></div>" : "";
    const transkrip = ui.transkripBuka && simpanTeks && !latar
      ? '<div class="transkrip transkrip--tetap">' + p.transkrip.map((l) => '<div class="baris-trans baris-trans--' + (l[0] === "A" ? "ai" : "p") + '"><div class="peran">' + (l[0] === "A" ? "AI" : "Penerima") + "<time>" + mmss(l[1]) + "</time></div>" + esc(l[2]) + "</div>").join("") + "</div>" : "";

    const kutipan = '<section class="panel"><div class="panel-kepala"><h2>Kutipan kunci</h2></div>' +
      (j.kutipan_kunci ? '<blockquote class="kutipan">' + esc(j.kutipan_kunci) + '</blockquote><p class="kutipan-ringkasan">' + esc(j.ringkasan) + "</p>"
        : '<p class="kutipan-ringkasan" style="padding-top:16px">Tidak ada kutipan. ' + esc(j.ringkasan) + "</p>") +
      bukti + tombolTranskrip + transkrip +
      '<div class="catatan-bukti"><span>' + ikon("kunci") + esc(D.RETENSI[p.label]) + "</span><span>" + ikon("kunci") + "Identitas penerima tidak dibagikan ke rumah sakit.</span></div></section>";

    const konteks = '<div class="konteks"><span><b>' + esc(D.namaRs(p.rs)) + "</b>: " + rs.tidak_sesuai + " jawaban tidak sesuai dari " + rs.terjawab + " terjawab.</span>" +
      '<span>Status RS: <b>' + rs.status + "</b>. Perlu klarifikasi bila tidak sesuai ≥3 dan ≥10% dari terjawab.</span></div>";
    const keputusan = S.keputusan[id];
    const sarankan = '<section class="panel saran saran-kartu"><div class="saran-isi"><span class="kapital">Langkah yang disarankan</span><h3>' + saran.nama + "</h3>" +
      "<p>" + esc(p.alasan) + " " + esc(saran.akibat) + "</p>" + konteks + (keputusan ? "" : aksiKeputusan(p)) +
      '<p class="catatan-saran">Rekaman adalah bukti awal untuk klarifikasi, bukan satu-satunya dasar menolak klaim. Satu jawaban tidak mengubah status RS.</p></div>' +
      (keputusan ? putusanTerpilih(p, keputusan) : "") + "</section>";

    return kop + peringatan + tiga + '<div class="bukti-bawah">' + kutipan + "<div>" + sarankan + "</div></div>";
  }
  function lamanRingkasanRs() { return kepala("Ringkasan per rumah sakit", "Layanan Agustus 2026") + kosong("Ringkasan RS", "Diisi pada tiket UI-08."); }
  function lamanRiwayat() { return kepala("Riwayat keputusan", "Semua keputusan verifikator atas panggilan konfirmasi.") + kosong("Riwayat keputusan", "Diisi pada tiket UI-10."); }

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

    akar.innerHTML = kerangka(r, isi, jejak) + (ui.wa ? modalWa() : "");
    document.title = (JUDUL_HALAMAN[r.nama] || "Beranda") + " · Vedika Autentik";
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

  /* ============================================================== peristiwa */

  const AKSI = {
    masuk() { S.masuk = true; simpan(); ke("#/beranda"); },
    menu() { ui.menuBuka = !ui.menuBuka; gambar(true); },
    "buka-baris"(el) { ke(el.dataset.tujuan); },
    wa(el) { bukaWa(el.dataset.id, el.dataset.jenis, false); },
    transkrip() { ui.transkripBuka = !ui.transkripBuka; gambar(true); },
    setujui(el) { putuskan(el.dataset.id, D.SARAN[tunggal(el.dataset.id).label], "", true); },
    "pilih-lain"() { ui.pilihLain = true; ui.tindakanLain = null; ui.catatan = ""; gambar(true); },
    "batal-lain"() { ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; gambar(true); },
    "simpan-lain"(el) {
      if (!alasanTerisi()) return;
      putuskan(el.dataset.id, ui.tindakanLain, ui.catatan.trim(), false);
    },
    "batal-putusan"(el) { delete S.keputusan[el.dataset.id]; simpan(); gambar(true); },
    "tutup-wa"() { tutupWa(); },
    diam() { /* klik di dalam kartu tidak menutup latar */ },
    telepon(el) { mulaiPanggilan(el.dataset.id); },
    otomatis() {
      ui.otomatis = !ui.otomatis;
      ui.jeda = false;
      clearTimeout(ui.timerBerikut);
      gambar(true);
      if (ui.otomatis) lanjutOtomatis();
      else toast("Panggilan otomatis dinonaktifkan.");
    },
    jeda() {
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

  window.addEventListener("hashchange", () => { ui.menuBuka = false; ui.transkripBuka = false; ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; gambar(false); });

  gambar(false);
})();
