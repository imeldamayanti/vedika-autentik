/* Vedika Autentik: prototipe tab pemeriksaan keaslian berkas di aplikasi verifikasi klaim.

   Alur: masuk → beranda → Autentik (unggah berkas, antrean berlabel) → kartu bukti
   (temuan, saran tindakan, konfirmasi peserta, peta hubungan, jejak) → laporan temuan.

   Tidak ada AI yang berjalan di sini. Temuan dibaca dari ground truth dataset
   (dataset/manifest.js) dan labelnya dihitung ulang oleh DATA.hitungLabel. */

(function () {
  "use strict";

  const D = window.DATA;

  /* ================================================================== util */

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const rp = (n) => "Rp" + Number(n).toLocaleString("id-ID");
  /* Jam kerja simulasi: demo selalu terasa berlangsung pagi hari di kantor cabang. */
  const MULAI = Date.now();
  const jam = () => {
    const menit = 9 * 60 + 20 + Math.floor((Date.now() - MULAI) / 60000);
    return String(Math.floor(menit / 60)).padStart(2, "0") + "." + String(menit % 60).padStart(2, "0");
  };
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const koma = (n) => String(n).replace(".", ",");

  /* Ikon garis 24px, satu ketebalan untuk seluruh antarmuka. */
  const IKON = {
    perisai: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    rumah: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    berkas: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M9 15h6"/><path d="M9 11h6"/>',
    riwayat: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    tanya: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    ulang: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    unggah: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
    main: '<polygon points="6 3 20 12 6 21 6 3"/>',
    cek: '<path d="M20 6 9 17l-5-5"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    jeda: '<path d="M12 8v4"/><path d="M12 16h.01"/>',
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    pengguna: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    kunci: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    unduh: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
    cetak: '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6"/><rect x="6" y="14" width="12" height="8" rx="1"/>',
    kiri: '<path d="m15 18-6-6 6-6"/>',
    klik: '<path d="M14 4.1 12 6"/><path d="m5.1 8-2.9-.8"/><path d="m6 12-1.9 2"/><path d="M7.2 2.2 8 5.1"/><path d="M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z"/>',
    pesan: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    tautan: '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><path d="M8 12h8"/>',
    lencanaCek: '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>',
    kaca: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/>'
  };
  const ikon = (n) => '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + IKON[n] + "</svg>";
  const logoVeritas = '<img src="assets/veritas-mark.svg" alt="" aria-hidden="true">';

  const labelChip = (kunci, besar) => '<span class="label label--' + kunci + (besar ? " label--besar" : "") + '">' + D.LABEL[kunci].nama + "</span>";

  /* ================================================================ status */

  const KUNCI_SIMPAN = "vedika.autentik.v1";

  function statusAwal() {
    return {
      masuk: false,
      antrean: D.ANTREAN_AWAL.map((a) => ({ id: a[0], tanggal: a[1], jam: a[2] })),
      keputusan: {},
      jawaban: {},
      dibuka: [],
      turSelesai: false
    };
  }

  function muat() {
    try {
      const s = JSON.parse(localStorage.getItem(KUNCI_SIMPAN));
      if (s && Array.isArray(s.antrean)) return Object.assign(statusAwal(), s);
    } catch (e) { /* penyimpanan peramban tidak tersedia: mulai dari awal */ }
    return statusAwal();
  }

  let S = muat();
  const simpan = () => {
    try {
      localStorage.setItem(KUNCI_SIMPAN, JSON.stringify(Object.assign({}, S, { antrean: S.antrean.filter((a) => !a.luar) })));
    } catch (e) { /* diabaikan */ }
  };

  /* Status tampilan yang tidak perlu bertahan setelah halaman dimuat ulang. */
  const ui = {
    filter: "semua", faskes: "", q: "",
    asalUnggah: "", asalError: false, unggahMemeriksa: false,
    sorot: true, perbesar: false, fokus: null,
    pilihLain: false, tindakanLain: null, catatan: null, galat: "",
    proses: null, menuBuka: false, hash: {}, luarUrut: 0
  };

  const diAntrean = (id) => S.antrean.some((a) => a.id === id);
  const berkas = (id) => D.PETA[id];

  /* ============================================================== perute */

  function rute() {
    const bagian = (location.hash || "").replace(/^#\/?/, "").split("/").filter(Boolean);
    return { nama: bagian[0] || "beranda", id: bagian[1] || null, tab: bagian[2] || "bukti" };
  }
  const ke = (h) => { if (location.hash !== h) location.hash = h; else gambar(true); };

  /* ============================================================== kerangka */

  function kerangka(r, isi, jejak) {
    const prioritasBaru = S.antrean.filter((a) => berkas(a.id).label === "prioritas" && !S.keputusan[a.id]).length;
    const aktif = (nama) => (r.nama === nama || (nama === "autentik" && (r.nama === "berkas" || r.nama === "laporan")) ? ' aria-current="page"' : "");
    return '<div class="kerangka">' +
      '<aside class="sisi' + (ui.menuBuka ? " buka" : "") + '" id="sisi">' +
        '<a class="merek" href="#/beranda"><span class="merek-ikon">' + ikon("perisai") + "</span><span><b>VEDIKA</b><span>Verifikasi Digital Klaim</span></span></a>" +
        '<nav class="nav" aria-label="Menu utama">' +
          '<a href="#/beranda"' + aktif("beranda") + ">" + ikon("rumah") + "Beranda</a>" +
          '<span class="nav-judul kapital">Verifikasi</span>' +
          '<button class="mati" type="button" aria-disabled="true" title="Menu Vedika yang sudah ada, tidak termasuk prototipe">' + ikon("berkas") + "Verifikasi klaim<small>Sudah ada</small></button>" +
          '<a class="nav-autentik" href="#/autentik"' + aktif("autentik") + ">" + logoVeritas + "Autentik" +
            (prioritasBaru ? '<span class="lencana" title="Berkas Prioritas yang belum diputuskan">' + prioritasBaru + "</span>" : '<span class="lencana lencana--halus">Baru</span>') + "</a>" +
          '<a href="#/riwayat"' + aktif("riwayat") + ">" + ikon("riwayat") + "Riwayat keputusan</a>" +
        "</nav>" +
        '<div class="sisi-kaki nav">' +
          '<button type="button" data-aksi="tur-mulai">' + ikon("tanya") + "Panduan demo</button>" +
          '<button type="button" data-aksi="ulang-demo">' + ikon("ulang") + "Mulai ulang demo</button>" +
          '<p class="catatan-prototipe"><b>Prototipe Healthkathon 2026.</b> Semua data fiktif.</p>' +
        "</div>" +
      "</aside>" +
      '<div class="kolom">' +
        '<header class="atas">' +
          '<button class="tombol-menu" type="button" data-aksi="menu" aria-label="Buka menu">' + ikon("menu") + "</button>" +
          '<div class="jejak-rute">' + jejak + "</div>" +
          '<div class="atas-kanan"><span class="lencana-prototipe">Prototipe · data sintetis</span>' +
            '<div class="pengguna"><span class="avatar"><img src="assets/foto/verifikator.png" alt="" width="34" height="34"></span><div><b>' + D.VERIFIKATOR.nama + "</b><span>" + D.VERIFIKATOR.peran + " · " + D.VERIFIKATOR.kantor + "</span></div></div></div>" +
        "</header>" +
        '<main class="isi" id="isi">' + isi + "</main>" +
      "</div></div>";
  }

  /* ============================================================== masuk */

  function lamanMasuk() {
    return '<div class="masuk"><div class="masuk-bungkus">' +
      '<div class="merek-ikon">' + ikon("perisai") + "</div>" +
      "<h1>VEDIKA</h1><p>Verifikasi Digital Klaim</p>" +
      '<div class="masuk-kartu">' +
        "<h2>Otentikasi pengguna</h2>" +
        '<div class="medan"><span class="kapital">Username</span><div class="medan-isi">' + ikon("pengguna") + "rsantoso.kc0901</div></div>" +
        '<div class="medan"><span class="kapital">Kata sandi</span><div class="medan-isi">' + ikon("kunci") + "••••••••••</div></div>" +
        '<button class="btn btn--primer btn--lebar btn--kapital" type="button" data-aksi="masuk">Masuk sebagai verifikator demo</button>' +
        '<p class="masuk-catatan">Akun fiktif. Tidak ada data yang dikirim.</p>' +
      "</div>" +
      '<p class="masuk-versi">Prototipe Vedika Autentik · Healthkathon 2026</p>' +
    "</div></div>";
  }

  /* ============================================================== beranda */

  function lamanBeranda() {
    const total = D.BATCH.reduce((a, b) => ({ masuk: a.masuk + b.masuk, selesai: a.selesai + b.selesai, prioritas: a.prioritas + b.prioritas, ulang: a.ulang + b.ulang }), { masuk: 0, selesai: 0, prioritas: 0, ulang: 0 });
    const baris = D.BATCH.map((b) => {
      const persen = Math.round((b.selesai / b.masuk) * 100);
      return '<tr class="bisa-klik" data-aksi="buka-antrean" data-faskes="' + esc(b.faskes) + '">' +
        '<td class="nama-berkas lebar-penuh"><b>' + esc(b.faskes) + '</b><span class="mono">' + b.kode + "</span></td>" +
        '<td class="angka sembunyi-hp">' + b.masuk.toLocaleString("id-ID") + "</td>" +
        '<td class="sembunyi-hp"><div style="display:flex;align-items:center;gap:10px"><div class="batang"><i style="width:' + persen + '%"></i></div><span class="angka redup">' + persen + "%</span></div></td>" +
        '<td class="angka">' + (b.prioritas ? '<span class="label label--prioritas">' + b.prioritas + "</span>" : '<span class="redup">0</span>') + "</td>" +
        '<td class="angka sembunyi-hp">' + b.cek + "</td>" +
        '<td class="angka sembunyi-hp">' + b.ulang + "</td>" +
        '<td class="kanan sembunyi-hp"><span class="btn btn--kecil btn--hantu">Buka antrean</span></td></tr>';
    }).join("");

    return '<div class="kepala"><div><h1>Beranda</h1><p>' + D.HARI_INI + " · " + D.VERIFIKATOR.kantor + "</p></div></div>" +
      '<div class="pengumuman"><span class="merek-ikon merek-ikon--veritas">' + logoVeritas + "</span>" +
        "<div><b>Autentik sekarang aktif untuk klaim fisioterapi</b><p>Berkas dari JKN Drive diperiksa keasliannya lebih dulu. Keputusan tetap di tangan Anda.</p></div>" +
        '<a class="btn btn--primer" href="#/autentik">Buka Autentik</a></div>' +
      '<section class="panel"><div class="panel-kepala"><h2>Klaim fisioterapi masuk, 7 hari terakhir</h2><span class="kanan redup">Batas verifikasi 10 hari kerja</span></div>' +
        '<div class="ringkas">' +
          "<div><b>" + total.masuk.toLocaleString("id-ID") + "</b><span>Berkas masuk</span></div>" +
          "<div><b>" + total.selesai.toLocaleString("id-ID") + "</b><span>Sudah diverifikasi</span></div>" +
          "<div><b>" + total.prioritas + "</b><span>Label Prioritas</span></div>" +
          "<div><b>" + total.ulang + "</b><span>Diminta scan ulang</span></div>" +
        "</div>" +
        '<div class="tabel-bungkus"><table class="tabel tabel--kartu"><thead><tr><th>Fasilitas kesehatan</th><th>Berkas masuk</th><th>Progres verifikasi</th><th>Prioritas</th><th>Perlu dicek</th><th>Scan ulang</th><th></th></tr></thead><tbody>' + baris + "</tbody></table></div>" +
      "</section>";
  }

  /* ============================================================== autentik */

  function barisAntrean() {
    const q = ui.q.trim().toLowerCase();
    const urutJawaban = (id) => (S.jawaban[id] === "2" || S.jawaban[id] === "3" ? 0 : 1);
    return S.antrean
      .map((a, i) => Object.assign({ b: berkas(a.id), urut: i }, a))
      .filter((a) => ui.filter === "semua" || a.b.label === ui.filter)
      .filter((a) => !ui.faskes || a.b.klaim.faskes === ui.faskes)
      .filter((a) => !q || (a.b.klaim.peserta + " " + a.b.klaim.sep + " " + a.id).toLowerCase().includes(q))
      .sort((x, y) => D.LABEL[x.b.label].urut - D.LABEL[y.b.label].urut || urutJawaban(x.id) - urutJawaban(y.id) || y.urut - x.urut);
  }

  function alasanSingkat(b) {
    if (b.label === "lolos") return "Semua pemeriksaan bersih.";
    const utama = b.temuan.find((t) => t.kekuatan === "kuat") || b.temuan[0];
    return utama ? utama.kalimat.split(". ")[0].replace(/\.$/, "") + "." : "";
  }

  function panelUnggah() {
    const jalan = !!(ui.proses && !ui.proses.selesai);
    const kartu = D.DEMO.map((d) => {
      const b = berkas(d.id);
      const ada = diAntrean(d.id);
      const dibuka = S.dibuka.includes(d.id);
      const ket = !ada ? "Belum diunggah" : dibuka ? "Sudah dibuka" : "Buka kartu bukti";
      return '<button type="button" data-aksi="skenario" data-id="' + d.id + '"' + (jalan ? " disabled" : "") + ">" +
        '<span class="gambar"><img src="' + b.jpg + '" alt="" loading="lazy">' + (dibuka ? '<span class="centang">' + ikon("cek") + "</span>" : "") + "</span>" +
        '<span class="keterangan"><b>' + d.judul + "</b><span>" + ket + "</span></span></button>";
    }).join("");
    const semuaAda = D.DEMO.every((d) => diAntrean(d.id));

    return '<section class="panel unggah" id="panelUnggah">' +
      '<div class="unggah-manual"><div class="asal-unggah">' +
        '<label for="faskesUnggah">Rumah sakit pengirim <span>untuk berkas di luar dataset</span></label>' +
        '<select id="faskesUnggah" data-aksi="asal-unggah" aria-describedby="asalUnggahBantu"' + (ui.asalError ? ' aria-invalid="true"' : '') + '>' +
          '<option value="">Pilih rumah sakit</option>' + D.BATCH.map((r) => '<option value="' + esc(r.faskes) + '"' + (ui.asalUnggah === r.faskes ? ' selected' : '') + '>' + esc(r.faskes) + '</option>').join("") + '</select>' +
        '<p id="asalUnggahBantu">Pilihan manual bukan bukti asal dokumen.</p>' +
        (ui.asalError ? '<p class="galat" role="alert">Pilih rumah sakit sebelum mengunggah berkas di luar dataset.</p>' : '') +
      '</div>' +
      '<label class="unggah-jatuh" id="jatuh" for="pilihBerkas">' + ikon("unggah") +
        "<b>Tarik berkas klaim ke sini</b><p>PDF, JPG, atau PNG</p>" +
        '<span class="btn btn--kecil">Pilih berkas</span>' +
        '<input class="sr" type="file" id="pilihBerkas" accept=".pdf,.jpg,.jpeg,.png" multiple></label></div>' +
      '<div class="unggah-demo">' +
        '<div class="unggah-demo-kepala"><div><b>Coba lima berkas contoh</b><p>Satu berkas untuk tiap jenis hasil</p></div>' +
          '<button class="btn btn--primer" type="button" id="tombolDemo" data-aksi="demo"' + (jalan ? " disabled" : "") + ">" + ikon("main") + (semuaAda ? "Jalankan ulang demo" : "Jalankan demo") + "</button></div>" +
        '<div class="skenario">' + kartu + "</div>" +
      "</div>" +
      (ui.proses ? tampilanProses() : "") +
    "</section>";
  }

  function tampilanProses() {
    const p = ui.proses;
    const antre = p.daftar.map((d, i) => {
      const b = berkas(d.id);
      const kelas = i === p.aktif && !p.selesai ? "aktif" : d.selesai ? "selesai" : "";
      return '<div class="' + kelas + '"><span class="mono">' + d.id + "</span>" + (d.selesai ? labelChip(b.label) : "") + "</div>";
    }).join("");
    if (p.selesai) {
      const hasil = p.daftar.map((d) => {
        const x = berkas(d.id);
        return "<li>" + labelChip(x.label) + '<div><a href="#/berkas/' + d.id + '">' + esc(x.klaim.peserta) + "</a> <span>" + esc(alasanSingkat(x)) + "</span></div></li>";
      }).join("");
      return '<div class="proses" id="proses" aria-live="polite"><div class="proses-antre"><span class="kapital">Berkas masuk</span>' + antre + "</div>" +
        '<div><p style="font-weight:700;margin-bottom:10px">' + p.daftar.length + ' berkas selesai diperiksa. Klik nama untuk membuka kartu bukti.</p><ul class="ringkas-hasil">' + hasil + "</ul></div></div>";
    }
    const b = berkas(p.daftar[p.aktif].id);
    const daftar = D.langkah(b);
    const langkah = daftar.map((l, j) => {
      const kelas = j < p.langkah || p.daftar[p.aktif].selesai ? l.status : j === p.langkah ? "jalan" : "menunggu";
      const tanda = kelas === "ok" ? ikon("cek") : kelas === "temuan" ? ikon("jeda") : kelas === "henti" ? ikon("jeda") : "";
      const hasil = kelas === "menunggu" ? "" : kelas === "jalan" ? "Memeriksa…" : esc(l.hasil);
      return '<li class="' + kelas + '"><span class="ikon">' + tanda + "</span><b>" + l.nama + '</b><span class="hasil">' + hasil + "</span></li>";
    }).join("");
    const judul = "Memeriksa " + b.klaim.peserta + " · " + b.klaim.faskes + " · " + b.id;
    return '<div class="proses" id="proses" aria-live="polite"><div class="proses-antre"><span class="kapital">Berkas masuk</span>' + antre + "</div>" +
      '<div><p style="font-weight:700;margin-bottom:8px">' + esc(judul) + '</p><ol class="langkah">' + langkah + "</ol></div></div>";
  }

  function lamanAutentik() {
    const semua = S.antrean.map((a) => berkas(a.id));
    const hitung = (k) => semua.filter((b) => b.label === k).length;
    const segmen = [["semua", "Semua", semua.length, ""], ["prioritas", "Prioritas", hitung("prioritas"), "var(--prioritas)"], ["cek", "Perlu dicek", hitung("cek"), "var(--cek)"],
      ["ulang", "Scan ulang", hitung("ulang"), "var(--ulang)"], ["lolos", "Lolos", hitung("lolos"), "var(--lolos)"]]
      .map((s) => '<button type="button" data-aksi="saring" data-nilai="' + s[0] + '" aria-pressed="' + (ui.filter === s[0]) + '">' +
        (s[3] ? '<i class="titik" style="background:' + s[3] + '"></i>' : "") + s[1] + " <b>" + s[2] + "</b></button>").join("");
    const faskes = [...new Set(semua.map((b) => b.klaim.faskes))].sort();
    const lolosTerbuka = S.antrean.filter((a) => berkas(a.id).label === "lolos" && !S.keputusan[a.id]).length;

    const baris = barisAntrean().map((a) => {
      const b = a.b, k = S.keputusan[a.id];
      const jawab = S.jawaban[a.id];
      const sesi = b.label === "ulang" ? '<span class="redup">Belum terbaca</span>'
        : b.klaim.sesi_ditagih + " / " + (b.isi_lembar ? b.isi_lembar.baris_asli : "–");
      return '<tr class="bisa-klik' + (a.baru ? " baru" : "") + '" data-aksi="buka-berkas" data-id="' + a.id + '">' +
        "<td>" + labelChip(b.label) + "</td>" +
        '<td class="nama-berkas"><b>' + esc(b.klaim.peserta) + (a.baru ? '<span class="tanda-baru">BARU</span>' : "") + '</b><span class="mono">' + a.id + "</span></td>" +
        '<td class="alasan lebar-penuh">' + esc(alasanSingkat(b)) + (jawab ? ' <b style="color:var(--prioritas-fg)">Peserta: ' + D.JAWABAN[jawab].teks + ".</b>" : "") + "</td>" +
        '<td class="sembunyi-hp">' + esc(b.klaim.faskes) + "</td>" +
        '<td class="mono sembunyi-hp">' + esc(b.klaim.sep) + "</td>" +
        '<td class="angka sembunyi-hp" title="Sesi ditagih / sesi yang didukung berkas">' + sesi + "</td>" +
        '<td class="angka kanan sembunyi-hp">' + (b.klaim.nilai_klaim ? rp(b.klaim.nilai_klaim) : "–") + "</td>" +
        '<td class="sembunyi-hp redup">' + a.tanggal + ", " + a.jam + "</td>" +
        '<td class="lebar-penuh">' + (k ? '<span class="status-keputusan">' + ikon("cek") + D.TINDAKAN[k.tindakan].status + "</span>" : '<span class="redup">Belum diputuskan</span>') + "</td>" +
      "</tr>";
    }).join("");

    return '<div class="kepala"><div><h1>Autentik</h1><p>Pemeriksaan keaslian berkas fisioterapi dari JKN Drive</p></div></div>' +
      panelUnggah() +
      '<section class="panel tabel-antrean"><div class="saringan"><div class="segmen" role="group" aria-label="Saring menurut label">' + segmen + "</div>" +
        '<select class="pilih" data-aksi="saring-faskes" aria-label="Saring menurut fasilitas kesehatan"><option value="">Semua rumah sakit</option>' +
          faskes.map((f) => "<option" + (ui.faskes === f ? " selected" : "") + ">" + esc(f) + "</option>").join("") + "</select>" +
        '<div class="kanan"><input class="cari" type="search" data-aksi="cari" placeholder="Cari nama, SEP, atau ID berkas" value="' + esc(ui.q) + '" aria-label="Cari berkas">' +
          (lolosTerbuka ? '<button class="btn btn--kecil" type="button" data-aksi="setujui-lolos">' + ikon("cek") + "Setujui " + lolosTerbuka + " yang lolos</button>" : "") + "</div></div>" +
        (baris
          ? '<div class="tabel-bungkus"><table class="tabel tabel--kartu"><thead><tr><th>Label</th><th>Peserta</th><th>Alasan</th><th>Rumah sakit</th><th>SEP</th><th>Sesi</th><th class="kanan">Nilai klaim</th><th>Masuk</th><th>Keputusan</th></tr></thead><tbody>' + baris + "</tbody></table></div>"
          : '<div class="kosong"><b>Tidak ada berkas yang cocok</b>Ubah saringan atau kosongkan pencarian.</div>') +
      "</section>";
  }

  /* ============================================================ kartu bukti */

  const persen = (region, ukuran) => "left:" + (region[0] / ukuran[0] * 100) + "%;top:" + (region[1] / ukuran[1] * 100) + "%;width:" + (region[2] / ukuran[0] * 100) + "%;height:" + (region[3] / ukuran[1] * 100) + "%";

  function kotakSorot(b, hanyaCek) {
    return b.temuan.map((t, i) => {
      if (!t.region || (hanyaCek && !hanyaCek.includes(t.cek))) return "";
      const kotak = t.area && t.area.length > 1 ? t.area : [t.region];
      return kotak.map((r, j) => '<span class="sorot sorot--' + t.kekuatan + (ui.fokus === i ? " fokus" : "") + '" data-temuan="' + i + '" style="' + persen(r, b.ukuran) + '">' +
        (j === 0 ? '<span class="sorot-nomor">' + (i + 1) + "</span>" : "") + "</span>").join("");
    }).join("");
  }

  function penampil(b) {
    const kembar = b.temuan.find((t) => t.cek === "berkas_kembar");
    const gambarLembar = (x, sorotan) => x.jpg
      ? '<div class="lembar"><img src="' + x.jpg + '" alt="Halaman berkas ' + esc(x.id) + '" width="' + x.ukuran[0] + '" height="' + x.ukuran[1] + '">' + sorotan + "</div>"
      : '<div class="lembar" style="aspect-ratio:1240/1754;display:grid;place-items:center;color:var(--muted-fg)">Pratinjau tidak tersedia untuk berkas ini</div>';
    let isi;
    if (kembar) {
      const p = berkas(kembar.pasangan);
      const cekSama = ["berkas_kembar", "tempelan"];
      isi = '<div class="halaman-berkas dua">' +
        '<div><p class="lembar-judul">Berkas ini <span>' + esc(b.klaim.peserta) + " · SEP " + esc(b.klaim.sep) + "</span></p>" + gambarLembar(b, kotakSorot(b)) + "</div>" +
        '<div><p class="lembar-judul">Berkas pembanding <span>' + esc(p.klaim.peserta) + " · SEP " + esc(p.klaim.sep) + "</span></p>" + gambarLembar(p, kotakSorot(b, cekSama)) + "</div>" +
      "</div>";
    } else {
      isi = '<div class="halaman-berkas">' + gambarLembar(b, kotakSorot(b)) + "</div>";
    }
    return '<section class="panel penampil' + (ui.sorot ? "" : " tanpa-sorot") + (ui.perbesar ? " perbesar" : "") + '">' +
      '<div class="penampil-alat"><label class="saklar"><input type="checkbox" data-aksi="saklar-sorot"' + (ui.sorot ? " checked" : "") + "> Tampilkan sorotan</label>" +
        '<div class="kanan"><button class="btn btn--kecil" type="button" data-aksi="perbesar">' + ikon("kaca") + (ui.perbesar ? "Muat di layar" : "Ukuran asli") + "</button>" +
        (b.pdf ? '<a class="btn btn--kecil" href="' + b.pdf + '" target="_blank" rel="noopener">' + ikon("berkas") + "PDF asli</a>" : "") + "</div></div>" +
      isi + "</section>";
  }

  function daftarTemuan(b) {
    const jawab = S.jawaban[b.id];
    let li = b.temuan.map((t, i) => {
      const fokus = t.region ? ' data-aksi="fokus" data-i="' + i + '" data-fokus' : "";
      return '<li class="' + (ui.fokus === i ? "fokus" : "") + '"' + fokus + ">" +
        '<span class="nomor nomor--' + t.kekuatan + '">' + (i + 1) + "</span>" +
        '<div><div class="atas-temuan"><b>' + D.CEK[t.cek] + '</b><span class="kekuatan kekuatan--' + t.kekuatan + '">' + D.KEKUATAN[t.kekuatan] + "</span>" +
          (t.region ? "" : '<span class="redup" style="font-size:12px">seluruh berkas</span>') + "</div><p>" + esc(t.kalimat) + "</p></div></li>";
    }).join("");
    if (jawab) {
      li += '<li><span class="nomor nomor--tanpa">P</span><div><div class="atas-temuan"><b>Konfirmasi peserta</b></div><p>Peserta menjawab: <b>' +
        D.JAWABAN[jawab].teks + "</b>. " + esc(D.JAWABAN[jawab].akibat) + "</p></div></li>";
    }
    if (!b.temuan.length) li = '<li class="bersih">' + ikon("lencanaCek") + "<span>Enam pemeriksaan keaslian bersih. Tidak ada temuan.</span></li>";
    return '<section class="panel"><div class="panel-kepala"><h3>Temuan</h3><span class="kanan redup">' + (b.label === "ulang" ? "Belum dinilai" : b.temuan.filter((t) => t.kekuatan !== "info").length + " sinyal") + "</span></div>" +
      '<ul class="daftar-temuan">' + li + "</ul></section>";
  }

  function tabelBanding(b) {
    if (b.luar && !b.dariApi) return "";
    const isi = b.isi_lembar, k = b.klaim;
    const ulang = b.label === "ulang";
    const mendukung = b.temuan.some((t) => t.cek === "kecocokan_klaim") ? isi.baris_asli : isi.baris_terisi;
    const sesiBeda = mendukung < k.sesi_ditagih;
    const ttd = isi.kemiripan_ttd_rerata;
    const baris = [
      ["Peserta", esc(k.peserta)],
      ["SEP", '<span class="mono">' + esc(k.sep) + "</span>"],
      ["Sesi ditagih", k.sesi_ditagih + " sesi · " + rp(k.nilai_klaim)],
      ["Sesi di berkas", ulang ? '<span class="redup">Belum terbaca</span>'
        : '<span class="' + (sesiBeda ? "beda" : "sama") + '">' + mendukung + " sesi" + (sesiBeda ? ", kurang " + (k.sesi_ditagih - mendukung) : ", cocok") + "</span>"],
      ["Tanda tangan pasien", ulang ? '<span class="redup">Belum terbaca</span>'
        : ttd > 0.97 ? '<span class="beda">Identik (kemiripan ' + koma(ttd.toFixed(2)) + ")</span>" : '<span class="sama">Bervariasi wajar (' + koma(ttd.toFixed(2)) + ")</span>"],
      ["Pembuat berkas", esc(b.metadata_file.Creator || "–") + (b.metadata_file.ModDate ? '<br><span class="redup">Diubah ' + esc(b.metadata_file.ModDate.replace("T", " ").slice(0, 16)) + "</span>" : "")]
    ];
    return '<section class="panel"><div class="panel-kepala"><h3>Klaim dan isi berkas</h3></div><table class="banding"><tbody>' +
      baris.map((r) => "<tr><th>" + r[0] + "</th><td>" + r[1] + "</td></tr>").join("") + "</tbody></table></section>";
  }

  function ringkasCatatan(b) {
    const cek = b.temuan.filter((t) => t.kekuatan !== "info").map((t) => D.CEK[t.cek].toLowerCase());
    const unik = cek.filter((v, i) => cek.indexOf(v) === i);
    const jawab = S.jawaban[b.id];
    return "Temuan: " + (unik.join(", ") || "tidak ada") + ". Peserta: " + (jawab ? "menjawab " + D.JAWABAN[jawab].teks.toLowerCase() : "belum menjawab") + ".";
  }

  function kartuSaran(b) {
    const k = S.keputusan[b.id];
    const saranKey = D.SARAN[b.label];
    const saran = D.TINDAKAN[saranKey];
    const jawab = S.jawaban[b.id];

    if (k) {
      const t = D.TINDAKAN[k.tindakan];
      return '<section class="panel saran"><div class="saran-isi"><span class="kapital">Langkah yang disarankan</span><h3>' + saran.nama + "</h3></div>" +
        '<div class="putusan"><b>' + ikon("lencanaCek") + t.status + "</b>" +
        "<p>" + esc(k.oleh) + " memilih <b>" + t.nama.toLowerCase() + "</b> pada " + esc(k.waktu) + (k.ikutSaran ? ", sesuai saran sistem." : ", berbeda dari saran sistem.") + "</p>" +
        (k.catatan ? "<blockquote>" + esc(k.catatan) + "</blockquote>" : "") +
        '<div class="aksi">' + (t.laporan ? '<a class="btn btn--primer btn--kecil" href="#/laporan/' + b.id + '">' + ikon("berkas") + "Buka laporan temuan</a>" : "") +
          '<button class="btn btn--kecil" type="button" data-aksi="batal-putusan">Ubah keputusan</button></div></div></section>';
    }

    const catatan = ui.catatan != null ? ui.catatan : saran.laporan ? ringkasCatatan(b) : "";
    const lain = Object.keys(D.TINDAKAN).filter((x) => x !== saranKey);
    const pesertaInfo = b.label === "prioritas"
      ? '<p style="margin-top:10px;font-size:12.5px"><a href="#/berkas/' + b.id + '/peserta">Konfirmasi peserta</a>: ' + (jawab ? "menjawab <b>" + D.JAWABAN[jawab].teks + "</b>" : "terkirim, menunggu jawaban") + "</p>"
      : "";

    let bawah;
    if (!ui.pilihLain) {
      bawah = (saran.laporan
        ? '<label class="catatan-medan" style="display:block;margin-top:14px"><span class="kapital">Catatan untuk tim telaah</span><textarea data-aksi="catatan" rows="3">' + esc(catatan) + "</textarea></label>"
        : "") +
        '<div class="saran-tombol"><button class="btn btn--primer" type="button" data-aksi="setujui">' + ikon("cek") + "Setujui saran</button>" +
        '<button class="btn btn--hantu" type="button" data-aksi="pilih-lain">Pilih tindakan lain</button></div>';
    } else {
      bawah = '<div class="pilihan-lain" role="radiogroup" aria-label="Tindakan lain">' +
        lain.map((x) => '<label class="' + (ui.tindakanLain === x ? "dipilih" : "") + '"><input type="radio" name="tindakan" data-aksi="tindakan-lain" value="' + x + '"' + (ui.tindakanLain === x ? " checked" : "") + ">" +
          "<span><b>" + D.TINDAKAN[x].nama + "</b><span>" + D.TINDAKAN[x].akibat + "</span></span></label>").join("") +
        '<label class="catatan-medan"><span class="kapital">Alasan tidak mengikuti saran</span><textarea data-aksi="catatan" rows="3" placeholder="Contoh: pasien memang tanda tangan sekali untuk semua sesi, sudah dikonfirmasi ke RS.">' + esc(catatan) + "</textarea>" +
          (ui.galat ? '<p class="galat" role="alert">' + esc(ui.galat) + "</p>" : "") + "</label>" +
        '<div class="saran-tombol"><button class="btn btn--primer" type="button" data-aksi="simpan-lain">Simpan keputusan</button>' +
        '<button class="btn btn--hantu" type="button" data-aksi="batal-lain">Kembali ke saran</button></div></div>';
    }

    return '<section class="panel saran"><div class="saran-isi"><span class="kapital">Langkah yang disarankan</span>' +
      "<h3>" + saran.nama + "</h3><p>" + D.ALASAN_SARAN[b.label] + " " + saran.akibat + "</p>" + pesertaInfo + bawah + "</div></section>";
  }

  function tabBerkas(b, tab) {
    const keluarga = D.keluargaBerkas(b.id);
    const daftar = [["bukti", "Bukti"]];
    if (keluarga) daftar.push(["peta", "Peta hubungan berkas"]);
    if (b.label === "prioritas") daftar.push(["peserta", "Konfirmasi peserta"]);
    daftar.push(["jejak", "Jejak keputusan"]);
    return '<nav class="tab" aria-label="Bagian kartu bukti">' + daftar.map((d) =>
      '<a href="#/berkas/' + b.id + "/" + d[0] + '"' + (tab === d[0] ? ' aria-current="page"' : "") + ">" + d[1] +
      (d[0] === "peserta" && !S.jawaban[b.id] ? '<i class="titik-merah" title="Menunggu jawaban"></i>' : "") + "</a>").join("") + "</nav>";
  }

  function lamanBerkas(id, tab) {
    const b = berkas(id);
    if (!b || !diAntrean(id)) {
      return '<div class="kosong"><b>Berkas belum ada di antrean</b>Unggah berkasnya dulu dari halaman Autentik.<br><br><a class="btn btn--primer" href="#/autentik">Ke Autentik</a></div>';
    }
    const a = S.antrean.find((x) => x.id === id);
    const kepala = '<div class="berkas-kepala"><div>' +
      '<div class="berkas-judul">' + labelChip(b.label, true) + "<h1>" + esc(b.klaim.peserta) + '</h1><span class="mono redup">' + b.id + "</span></div>" +
      '<div class="berkas-meta"><span><b>SEP</b><span class="mono">' + esc(b.klaim.sep) + "</span></span><span><b>Rumah sakit</b>" + esc(b.klaim.faskes) + (b.luar ? ' <small class="redup">(dipilih saat unggah)</small>' : '') + "</span>" +
        "<span><b>Periode</b>" + esc(b.klaim.periode) + "</span><span><b>Nilai klaim</b>" + (b.klaim.nilai_klaim ? rp(b.klaim.nilai_klaim) : "–") + "</span>" +
        "<span><b>Masuk</b>" + a.tanggal + ", " + a.jam + "</span></div>" +
      '<p class="berkas-alasan">' + esc(b.ringkasan) + "</p></div></div>";

    let isi;
    if (tab === "peta" && D.keluargaBerkas(b.id)) isi = tabPeta(b);
    else if (tab === "peserta" && b.label === "prioritas") isi = tabPeserta(b);
    else if (tab === "jejak") isi = tabJejak(b, a);
    else isi = '<div class="bukti">' + penampil(b) + '<div class="samping">' + kartuSaran(b) + daftarTemuan(b) + tabelBanding(b) + "</div></div>";
    return kepala + tabBerkas(b, tab) + isi;
  }

  function tabPeta(b) {
    const kel = D.keluargaBerkas(b.id);
    const akar = berkas(kel.akar);
    const pasien = new Set(kel.anggota.map((x) => x.klaim.peserta)).size;
    const bulan = new Set(kel.anggota.map((x) => x.klaim.periode)).size;
    const cabang = kel.anggota.map((x) => {
      const dipakai = x.id === kel.akar ? "Lembar asli, masuk lebih dulu" : "Memakai lembar " + kel.akar;
      const ada = diAntrean(x.id);
      return '<li><a class="peta-simpul' + (x.id === b.id ? " ini" : "") + '" href="' + (ada ? "#/berkas/" + x.id : "#/berkas/" + b.id + "/peta") + '">' +
        "<b>" + esc(x.klaim.peserta) + (x.id === b.id ? ' <span class="redup" style="font-weight:600">· berkas ini</span>' : "") + "</b>" +
        '<span><span class="mono">SEP ' + esc(x.klaim.sep) + "</span> · " + esc(x.klaim.periode) + " · " + dipakai + "</span>" + labelChip(x.label) + "</a></li>";
    }).join("");
    return '<section class="panel"><div class="panel-kepala"><h3>Satu lembar, ' + kel.anggota.length + " klaim</h3><span class=\"kanan redup\">" + pasien + " peserta · " + bulan + " periode</span></div>" +
      '<div class="peta"><div class="peta-akar"><img src="' + akar.jpg + '" alt="Lembar ' + akar.id + '">' +
        "<div><b>Lembar " + akar.id + "</b><p>Lembar bukti pelayanan fisioterapi " + esc(akar.klaim.faskes) + ". Setelah kolom identitas dan tanggal ditutup, isinya sama dengan setiap klaim di bawah ini.</p></div></div>" +
        '<ul class="peta-cabang">' + cabang + "</ul></div></section>";
  }

  function tabPeserta(b) {
    const p = D.pesanPeserta(b);
    const jawab = S.jawaban[b.id];
    const inisial = p.sapaan === "Bapak" ? "Pak" : "Bu";
    const obrolan = '<span class="tanggal-obrolan">Hari ini</span>' +
      '<div class="gelembung dari-bpjs"><p>' + esc(p.teks) + "</p><p>" + esc(p.tanya) + "</p><p>" + esc(p.pilihan) + "</p><small>09.14</small></div>" +
      (jawab ? '<div class="gelembung dari-peserta"><p>' + jawab + "</p><small>" + jam() + " ✓✓</small></div>" +
        '<div class="gelembung dari-bpjs"><p>Terima kasih, ' + p.sapaan + ". Jawaban " + p.sapaan + " sudah kami catat.</p><small>" + jam() + "</small></div>" : "");
    const balas = jawab
      ? '<div class="ponsel-balas"><button type="button" data-aksi="hapus-jawaban" style="grid-column:1/-1">Ulangi simulasi jawaban</button></div>'
      : '<div class="ponsel-balas"><span class="petunjuk">Simulasikan jawaban peserta</span>' +
        ["1", "2", "3"].map((n) => '<button type="button" data-aksi="jawab" data-nilai="' + n + '">' + n + " · " + D.JAWABAN[n].teks + "</button>").join("") + "</div>";

    const status = jawab
      ? '<div class="jawaban-kartu"><span class="kapital">Jawaban peserta</span><b>' + jawab + " · " + D.JAWABAN[jawab].teks + "</b><p>" + D.JAWABAN[jawab].akibat + "</p></div>"
      : '<div class="jawaban-kartu"><span class="kapital">Status</span><b>Terkirim otomatis pukul 09.14</b><p>Menunggu jawaban. Label tidak berubah kalau tidak dijawab.</p></div>';

    return '<div class="peserta"><div class="ponsel" aria-label="Simulasi layar WhatsApp peserta"><div class="ponsel-layar">' +
      '<div class="ponsel-kepala"><span class="foto">BPJS</span><div><b>BPJS Kesehatan ' + ikon("lencanaCek") + "</b><span>PANDAWA · 0811 8 165 165</span></div></div>" +
      '<div class="obrolan">' + obrolan + "</div>" + balas + "</div></div>" +
      '<div class="peserta-info"><div><h2 style="font-size:18px;font-weight:800">Konfirmasi ke ' + inisial + " " + esc(b.klaim.peserta.split(" ")[0]) + '</h2><p class="redup" style="margin-top:4px">Hanya untuk label Prioritas</p></div>' +
        status +
        '<section class="panel"><div class="panel-kepala"><h3>Aturan pesan</h3></div><div class="panel-isi"><ul class="aturan">' +
          ["Lewat PANDAWA, WhatsApp resmi BPJS.", "Tanpa tautan, karena penipu sering menyamar sebagai BPJS.", "Tidak menyebut dugaan kecurangan.", "Jawaban menaikkan urutan pemeriksaan, bukan vonis."]
            .map((t) => "<li>" + ikon("cek") + "<span>" + t + "</span></li>").join("") +
        "</ul></div></section>" +
        '<p class="redup" style="font-size:12.5px">Jawaban peserta disimulasikan di prototipe ini.</p>' +
      "</div></div>";
  }

  function tabJejak(b, a) {
    const k = S.keputusan[b.id];
    const jawab = S.jawaban[b.id];
    const langkah = D.langkah(b);
    const item = [
      { waktu: a.jam, judul: b.luar ? "Diunggah manual untuk demo" : "Diunggah rumah sakit ke JKN Drive", teks: b.klaim.faskes + (b.luar ? " (dipilih saat unggah)" : "") + " · " + (b.berkas ? b.berkas.pdf : b.nama) },
      { waktu: a.jam, judul: "Diperiksa Vedika Autentik", teks: langkah.length + " langkah selesai. Label " + D.LABEL[b.label].nama + ". " + (b.temuan.length ? b.temuan.length + " temuan." : "Tanpa temuan.") }
    ];
    if (b.label === "prioritas") {
      item.push({ waktu: "09.14", judul: "Pertanyaan dikirim ke peserta lewat PANDAWA", teks: "Satu pesan netral tanpa tautan." });
      item.push(jawab ? { waktu: "Hari ini", judul: "Peserta menjawab: " + D.JAWABAN[jawab].teks, teks: D.JAWABAN[jawab].akibat }
        : { menunggu: true, waktu: "", judul: "Menunggu jawaban peserta", teks: "Label tidak berubah." });
    }
    if (k) {
      item.push({ waktu: k.waktu.split(", ")[1] || k.waktu, judul: k.oleh + ": " + D.TINDAKAN[k.tindakan].nama, teks: (k.ikutSaran ? "Sesuai saran sistem." : "Berbeda dari saran sistem.") + (k.catatan ? " Catatan: " + k.catatan : "") });
      if (D.TINDAKAN[k.tindakan].laporan) item.push({ waktu: k.waktu.split(", ")[1] || k.waktu, judul: "Laporan temuan terbit", teks: '<a href="#/laporan/' + b.id + '">Buka laporan</a>', html: true });
    } else {
      item.push({ menunggu: true, waktu: "", judul: "Menunggu keputusan verifikator", teks: "Saran sistem: " + D.TINDAKAN[D.SARAN[b.label]].nama.toLowerCase() + "." });
    }
    return '<section class="panel"><div class="panel-kepala"><h3>Jejak keputusan</h3><span class="kanan redup">Siapa, kapan, dan alasannya</span></div><ol class="linimasa">' +
      item.map((x) => '<li class="' + (x.menunggu ? "menunggu" : "") + '"><time>' + esc(x.waktu) + '</time><span class="bulat">' + (x.menunggu ? "" : ikon("cek")) + "</span><div><b>" + esc(x.judul) + "</b><p>" + (x.html ? x.teks : esc(x.teks)) + "</p></div></li>").join("") +
      "</ol></section>";
  }

  /* ============================================================== laporan */

  function nomorLaporan(b) { return "LT-VA/" + b.id.replace("VA-", "").replace("-", "") + "/X/2026"; }

  function lamanLaporan(id) {
    const b = berkas(id);
    if (!b || !diAntrean(id)) return '<div class="kosong"><b>Laporan belum tersedia</b>Berkas ini belum ada di antrean.</div>';
    const k = S.keputusan[id];
    const jawab = S.jawaban[id];
    const hash = ui.hash[id];
    if (hash === undefined) hitungHash(b);

    const potongan = b.temuan.filter((t) => t.region).map((t, i) =>
      '<figure><canvas data-potong="' + b.id + '" data-region="' + t.region.join(",") + '" width="10" height="10"></canvas><figcaption>' + (i + 1) + ". " + D.CEK[t.cek] + "</figcaption></figure>").join("");

    return '<div class="laporan-alat"><a class="btn" href="#/berkas/' + id + '">' + ikon("kiri") + "Kartu bukti</a>" +
        '<button class="btn btn--primer" type="button" data-aksi="unduh-pdf" data-id="' + id + '">' + ikon("unduh") + "Unduh PDF</button>" +
        '<button class="btn" type="button" data-aksi="cetak">' + ikon("cetak") + "Cetak</button></div>" +
      '<article class="kertas-laporan">' +
        '<header><span class="merek-ikon merek-ikon--veritas">' + logoVeritas + "</span><div><b>VEDIKA AUTENTIK</b><span>" + D.VERIFIKATOR.kantor + ' · Tim Pencegahan Kecurangan JKN</span></div><div class="kanan"><span>' + D.HARI_INI + "</span></div></header>" +
        "<h2>LAPORAN TEMUAN KEASLIAN BERKAS KLAIM</h2>" +
        '<p class="nomor-laporan">Nomor ' + nomorLaporan(b) + (k ? "" : " · DRAF, belum ada keputusan verifikator") + "</p>" +
        "<h3>Identitas klaim</h3><dl>" +
          "<dt>Peserta</dt><dd>" + esc(b.klaim.peserta) + " · No. kartu " + esc(b.klaim.no_kartu) + "</dd>" +
          '<dt>Nomor SEP</dt><dd class="mono">' + esc(b.klaim.sep) + "</dd>" +
          "<dt>Fasilitas kesehatan</dt><dd>" + esc(b.klaim.faskes) + " (" + esc(b.klaim.kode_faskes) + ")</dd>" +
          "<dt>Layanan</dt><dd>" + esc(b.klaim.layanan) + ", " + esc(b.klaim.periode) + "</dd>" +
          "<dt>Ditagihkan</dt><dd>" + b.klaim.sesi_ditagih + " sesi · " + rp(b.klaim.nilai_klaim) + "</dd>" +
          '<dt>ID berkas</dt><dd class="mono">' + b.id + "</dd></dl>" +
        "<h3>Hasil pemeriksaan</h3><p>" + labelChip(b.label) + " " + esc(b.ringkasan) + "</p>" +
        "<h3>Temuan</h3>" + (b.temuan.length ? "<ol>" + b.temuan.map((t) => "<li><b>" + D.CEK[t.cek] + "</b> (" + D.KEKUATAN[t.kekuatan].toLowerCase() + "). " + esc(t.kalimat) + "</li>").join("") + "</ol>" : "<p>Tidak ada temuan.</p>") +
        (potongan ? "<h3>Potongan bukti</h3><div class=\"potongan\">" + potongan + "</div>" : "") +
        (b.label === "prioritas" ? "<h3>Konfirmasi peserta</h3><p>" + (jawab ? "Peserta menjawab <b>" + D.JAWABAN[jawab].teks + "</b> melalui PANDAWA." : "Pertanyaan terkirim melalui PANDAWA, belum ada jawaban.") + "</p>" : "") +
        "<h3>Jejak berkas</h3><dl>" +
          '<dt>SHA-256 berkas asli</dt><dd class="mono">' + (hash ? esc(hash) : hash === null ? "Tersedia saat prototipe dibuka lewat server" : "Menghitung…") + "</dd>" +
          "<dt>Pembuat berkas</dt><dd>" + esc([b.metadata_file.Creator, b.metadata_file.Producer].filter(Boolean).join(" · ")) + "</dd>" +
          "<dt>Versi aturan</dt><dd>VA-aturan 2026.09 (PRD bagian 9)</dd></dl>" +
        "<h3>Keputusan verifikator</h3>" + (k
          ? "<dl><dt>Tindakan</dt><dd><b>" + D.TINDAKAN[k.tindakan].nama + "</b>" + (k.ikutSaran ? ", sesuai saran sistem" : ", berbeda dari saran sistem") + "</dd><dt>Oleh</dt><dd>" + esc(k.oleh) + ", " + esc(k.waktu) + "</dd>" + (k.catatan ? "<dt>Catatan</dt><dd>" + esc(k.catatan) + "</dd>" : "") + "</dl>"
          : "<p class=\"redup\">Belum ada keputusan.</p>") +
        '<div class="ttd-laporan"><div>Verifikator<span></span><b>' + D.VERIFIKATOR.nama + "</b></div><div>Kepala Bidang Penjaminan Manfaat<span></span><b>......................................</b></div></div>" +
        '<p class="kaki-laporan">Laporan ini berisi prioritas pemeriksaan beserta buktinya, bukan penetapan kecurangan. Rumah sakit berhak memberi klarifikasi sebelum kasus dinaikkan. Penetapan tetap wewenang Tim Pencegahan dan Penanganan Kecurangan JKN sesuai Permenkes 16/2019. Prototipe Healthkathon 2026, seluruh data sintetis.</p>' +
      "</article>";
  }

  async function hitungHash(b) {
    ui.hash[b.id] = "";
    try {
      const data = await fetch(b.pdf).then((r) => { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); });
      const hasil = await crypto.subtle.digest("SHA-256", data);
      ui.hash[b.id] = [...new Uint8Array(hasil)].map((x) => x.toString(16).padStart(2, "0")).join("");
    } catch (e) {
      ui.hash[b.id] = null;
    }
    if (rute().nama === "laporan") gambar(true);
  }

  /* Potong area temuan dari halaman berkas ke kanvas, untuk laporan dan PDF. */
  function muatGambar(src) {
    return new Promise((ok, gagal) => { const img = new Image(); img.onload = () => ok(img); img.onerror = gagal; img.src = src; });
  }

  async function potong(b, region, lebarMaks) {
    const img = await muatGambar(b.jpg);
    const pad = 12;
    const x = Math.max(0, region[0] - pad), y = Math.max(0, region[1] - pad);
    const w = Math.min(img.naturalWidth - x, region[2] + pad * 2), h = Math.min(img.naturalHeight - y, region[3] + pad * 2);
    const skala = Math.min(1, lebarMaks / w);
    const c = document.createElement("canvas");
    c.width = Math.round(w * skala); c.height = Math.round(h * skala);
    c.getContext("2d").drawImage(img, x, y, w, h, 0, 0, c.width, c.height);
    return c;
  }

  async function isiPotongan() {
    const kanvas = document.querySelectorAll("canvas[data-potong]");
    for (const k of kanvas) {
      try {
        const c = await potong(berkas(k.dataset.potong), k.dataset.region.split(",").map(Number), 600);
        k.width = c.width; k.height = c.height;
        k.getContext("2d").drawImage(c, 0, 0);
      } catch (e) { /* gambar gagal dimuat: kanvas dibiarkan kosong */ }
    }
  }

  const bersihPdf = (s) => String(s).replace(/[—–]/g, "-").replace(/[“”]/g, '"').replace(/[‘’]/g, "'").replace(/…/g, "...").replace(/·/g, "-");

  async function unduhPdf(id) {
    const b = berkas(id);
    if (!window.jspdf) { toast("Pembuat PDF belum termuat. Periksa koneksi, lalu coba lagi."); return; }
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: "mm", format: "a4" });
    const L = 18, R = 192, lebar = R - L;
    let y = 18;
    const baru = (perlu) => { if (y + perlu > 278) { doc.addPage(); y = 18; } };
    const teks = (t, o) => {
      o = o || {};
      doc.setFont("helvetica", o.tebal ? "bold" : "normal"); doc.setFontSize(o.ukuran || 9.5); doc.setTextColor(o.warna || "#1a1a19");
      doc.splitTextToSize(bersihPdf(t), o.lebar || lebar).forEach((baris) => { baru(6); doc.text(baris, o.x || L, y, { align: o.align || "left" }); y += (o.ukuran || 9.5) * 0.45 + 1.2; });
    };
    const judul = (t) => { y += 4; baru(12); teks(t.toUpperCase(), { tebal: true, ukuran: 8, warna: "#6b6a66" }); doc.setDrawColor("#e4e4e0"); doc.line(L, y - 1, R, y - 1); y += 3; };
    const kv = (p) => p.forEach((r) => { baru(6); doc.setFont("helvetica", "bold"); doc.setFontSize(8.5); doc.setTextColor("#6b6a66"); doc.text(bersihPdf(r[0]), L, y);
      doc.setFont("helvetica", "normal"); doc.setTextColor("#1a1a19"); const isi = doc.splitTextToSize(bersihPdf(r[1]), 118); doc.text(isi, L + 52, y); y += 5.2 * isi.length; });

    const k = S.keputusan[id], jawab = S.jawaban[id];
    doc.setFillColor("#2b6f7c"); doc.rect(0, 0, 210, 3, "F");
    teks("VEDIKA AUTENTIK", { tebal: true, ukuran: 12 });
    teks(D.VERIFIKATOR.kantor + " - Tim Pencegahan Kecurangan JKN", { ukuran: 8.5, warna: "#6b6a66" });
    y += 6;
    teks("LAPORAN TEMUAN KEASLIAN BERKAS KLAIM", { tebal: true, ukuran: 12, x: 105, align: "center" });
    teks("Nomor " + nomorLaporan(b) + (k ? "" : " - DRAF"), { ukuran: 8.5, warna: "#6b6a66", x: 105, align: "center" });

    judul("Identitas klaim");
    kv([["Peserta", b.klaim.peserta + " - No. kartu " + b.klaim.no_kartu], ["Nomor SEP", b.klaim.sep], ["Fasilitas kesehatan", b.klaim.faskes + " (" + b.klaim.kode_faskes + ")"],
      ["Layanan", b.klaim.layanan + ", " + b.klaim.periode], ["Ditagihkan", b.klaim.sesi_ditagih + " sesi - " + rp(b.klaim.nilai_klaim)], ["ID berkas", b.id]]);
    judul("Hasil pemeriksaan");
    teks("Label " + D.LABEL[b.label].nama + ". " + b.ringkasan);
    judul("Temuan");
    if (!b.temuan.length) teks("Tidak ada temuan.");
    b.temuan.forEach((t, i) => teks((i + 1) + ". " + D.CEK[t.cek] + " (" + D.KEKUATAN[t.kekuatan].toLowerCase() + "). " + t.kalimat));

    const berregion = b.temuan.filter((t) => t.region);
    if (berregion.length) {
      judul("Potongan bukti");
      for (let i = 0; i < berregion.length; i++) {
        try {
          const c = await potong(b, berregion[i].region, 900);
          const w = Math.min(lebar, 80 * (c.width / c.height)), h = w * (c.height / c.width);
          const tinggi = Math.min(h, 90), lebarAkhir = tinggi * (c.width / c.height);
          baru(tinggi + 8);
          doc.addImage(c.toDataURL("image/jpeg", 0.85), "JPEG", L, y, lebarAkhir, tinggi);
          y += tinggi + 3;
          teks((i + 1) + ". " + D.CEK[berregion[i].cek], { ukuran: 8, warna: "#6b6a66" });
          y += 2;
        } catch (e) {
          teks("Potongan bukti hanya tersedia saat prototipe dibuka lewat server.", { ukuran: 8.5, warna: "#6b6a66" });
          break;
        }
      }
    }
    if (b.label === "prioritas") { judul("Konfirmasi peserta"); teks(jawab ? "Peserta menjawab " + D.JAWABAN[jawab].teks + " melalui PANDAWA." : "Pertanyaan terkirim melalui PANDAWA, belum ada jawaban."); }
    judul("Jejak berkas");
    kv([["SHA-256 berkas asli", ui.hash[id] || "tidak tersedia"], ["Pembuat berkas", [b.metadata_file.Creator, b.metadata_file.Producer].filter(Boolean).join(" - ")], ["Versi aturan", "VA-aturan 2026.09"]]);
    judul("Keputusan verifikator");
    if (k) kv([["Tindakan", D.TINDAKAN[k.tindakan].nama + (k.ikutSaran ? ", sesuai saran sistem" : ", berbeda dari saran sistem")], ["Oleh", k.oleh + ", " + k.waktu]].concat(k.catatan ? [["Catatan", k.catatan]] : []));
    else teks("Belum ada keputusan.", { warna: "#6b6a66" });
    y += 4;
    teks("Laporan ini berisi prioritas pemeriksaan beserta buktinya, bukan penetapan kecurangan. Penetapan tetap wewenang Tim Pencegahan dan Penanganan Kecurangan JKN sesuai Permenkes 16/2019. Prototipe Healthkathon 2026, seluruh data sintetis.", { ukuran: 8, warna: "#6b6a66" });

    doc.save("Laporan-Temuan-" + id + ".pdf");
    toast("Laporan " + id + " diunduh.");
  }

  /* ============================================================== riwayat */

  function lamanRiwayat() {
    const daftar = Object.keys(S.keputusan).map((id) => Object.assign({ id: id, b: berkas(id) }, S.keputusan[id])).filter((x) => x.b);
    const isi = daftar.length
      ? '<div class="tabel-bungkus"><table class="tabel tabel--kartu"><thead><tr><th>Waktu</th><th>Peserta</th><th>Label</th><th>Tindakan</th><th>Saran sistem</th><th>Catatan</th></tr></thead><tbody>' +
        daftar.reverse().map((x) => '<tr class="bisa-klik" data-aksi="buka-berkas" data-id="' + x.id + '"><td class="redup">' + esc(x.waktu) + '</td><td class="nama-berkas"><b>' + esc(x.b.klaim.peserta) + '</b><span class="mono">' + x.id + "</span></td><td>" + labelChip(x.b.label) + "</td><td><b>" + D.TINDAKAN[x.tindakan].nama + '</b></td><td class="sembunyi-hp">' + (x.ikutSaran ? "Diikuti" : '<b style="color:var(--cek-fg)">Tidak diikuti</b>') + '</td><td class="alasan lebar-penuh">' + esc(x.catatan || "–") + "</td></tr>").join("") +
        "</tbody></table></div>"
      : '<div class="riwayat-kosong"><b>Belum ada keputusan</b><p>Setiap keputusan di kartu bukti tercatat di sini, lengkap dengan waktu, tindakan, dan alasannya.</p><a class="btn btn--primer" href="#/autentik">Buka antrean Autentik</a></div>';
    return '<div class="kepala"><div><h1>Riwayat keputusan</h1><p>Semua keputusan verifikator atas berkas Autentik. Data ini yang dipakai untuk audit dan kalibrasi ambang label.</p></div></div><section class="panel">' + isi + "</section>";
  }

  /* ============================================================== proses */

  async function jalankan(ids) {
    if (ui.proses && !ui.proses.selesai) return;
    ids.forEach((id) => { S.antrean = S.antrean.filter((a) => a.id !== id); delete S.keputusan[id]; delete S.jawaban[id]; });
    ui.proses = { daftar: ids.map((id) => ({ id: id, selesai: false })), aktif: 0, langkah: 0, selesai: false };
    if (rute().nama !== "autentik") ke("#/autentik"); else gambar(true);
    for (let i = 0; i < ids.length; i++) {
      ui.proses.aktif = i;
      const jumlah = D.langkah(berkas(ids[i])).length;
      for (let j = 0; j < jumlah; j++) { ui.proses.langkah = j; perbaruiProses(); await tunggu(260); }
      ui.proses.langkah = jumlah;
      ui.proses.daftar[i].selesai = true;
      S.antrean.push({ id: ids[i], tanggal: "6 Okt", jam: jam(), baru: true, luar: berkas(ids[i]).luar });
      simpan();
      gambar(true);
      await tunggu(380);
    }
    ui.proses.selesai = true;
    gambar(true);
    document.dispatchEvent(new CustomEvent("demo-selesai"));
    const prioritas = ids.filter((id) => berkas(id).label === "prioritas").length;
    toast(ids.length + " berkas diperiksa" + (prioritas ? ", " + prioritas + " berlabel Prioritas." : "."));
  }

  /* Perbarui hanya bagian proses supaya halaman tidak berkedip setiap langkah. */
  function perbaruiProses() {
    const el = document.getElementById("proses");
    if (el) el.outerHTML = tampilanProses();
    else gambar(true);
  }

  /* Berkas di luar dataset tidak bisa dinilai prototipe: gagal-aman menjadi Perlu dicek. */
  function berkasLuar(file, asal) {
    ui.luarUrut += 1;
    const id = "UNGGAH-" + String(ui.luarUrut).padStart(2, "0");
    const gambarUrl = /^image\//.test(file.type) ? URL.createObjectURL(file) : null;
    const b = {
      id: id, luar: true, nama: file.name, jpg: gambarUrl, pdf: null, ukuran: [1240, 1754],
      berkas: { pdf: file.name }, ringkasan: "Prototipe hanya mengenali berkas dari folder dataset. Berkas lain tidak pernah diberi label Lolos.",
      klaim: { peserta: file.name.replace(/\.[^.]+$/, ""), sep: "Tidak terbaca", faskes: asal.faskes, periode: "–", sesi_ditagih: 0, nilai_klaim: 0, no_kartu: "–", kode_faskes: asal.kode, layanan: "Fisioterapi rawat jalan" },
      isi_lembar: null, kualitas_scan: { status: "baik", catatan: "Berkas diterima." },
      temuan: [{ cek: "kualitas_scan", kekuatan: "info", region: null, kalimat: "Isi berkas tidak bisa dibaca oleh prototipe. Sesuai prinsip gagal-aman, berkas yang gagal diproses ditandai Perlu dicek." }],
      metadata_file: { Creator: file.type || "tidak diketahui" }
    };
    b.label = "cek";
    D.PETA[id] = b;
    return id;
  }

  async function berkasDariApi(file, asal) {
    try {
      const id = await window.API.unggah(file, asal.kode);
      return await window.API.muatKeFe(id, { file: file, faskes: asal.faskes, kode: asal.kode });
    } catch (e) { return null; }
  }

  async function idDataset(file) {
    const cocok = /^((?:VA-(?:ASL|KMB|DST|AI|BRM)-\d{2}))\.(PDF|JPG|JPEG|PNG)$/i.exec(file.name);
    if (!cocok) return null;
    const id = cocok[1].toUpperCase(), contoh = berkas(id);
    if (!contoh || contoh.luar) return null;
    const ekstensi = cocok[2].toLowerCase() === "jpeg" ? "jpg" : cocok[2].toLowerCase();
    try {
      const respons = await fetch("dataset/" + contoh.folder + "/" + id + "." + ekstensi);
      if (!respons.ok) return null;
      const [asli, unggahan] = await Promise.all([respons.arrayBuffer(), file.arrayBuffer()]);
      if (asli.byteLength !== unggahan.byteLength) return null;
      const a = new Uint8Array(asli), b = new Uint8Array(unggahan);
      return a.every((nilai, i) => nilai === b[i]) ? id : null;
    } catch (e) { return null; }
  }

  async function terimaBerkas(files) {
    const daftar = [...files];
    if (!daftar.length) return;
    if (ui.unggahMemeriksa || (ui.proses && !ui.proses.selesai)) {
      toast("Tunggu pemeriksaan sebelumnya selesai, lalu unggah berkas berikutnya.");
      return;
    }
    ui.unggahMemeriksa = true;
    const asalDipilih = ui.asalUnggah;
    try {
      toast("Mencocokkan berkas dengan data contoh…");
      const dikenal = await Promise.all(daftar.map(idDataset));
      const asal = D.BATCH.find((r) => r.faskes === asalDipilih);
      if (dikenal.some((id) => !id) && !asal) {
        ui.asalError = true;
        gambar(true);
        document.querySelector("#faskesUnggah")?.focus();
        return;
      }
      ui.asalError = false;
      /* Berkas di luar dataset dikirim ke mesin pemeriksa bila API sehat. Bila tidak, jatuh ke jalur cadangan. */
      const apiSiap = dikenal.some((id) => !id) && window.API ? await window.API.sehat() : false;
      if (apiSiap) toast("Mengirim berkas ke mesin pemeriksa…");
      const ids = [];
      for (let i = 0; i < daftar.length; i++) {
        ids.push(dikenal[i] || (apiSiap && await berkasDariApi(daftar[i], asal)) || berkasLuar(daftar[i], asal));
      }
      jalankan([...new Set(ids)]);
    } finally { ui.unggahMemeriksa = false; }
  }

  /* ============================================================== keputusan */

  function putuskan(id, tindakan, catatan, ikutSaran) {
    S.keputusan[id] = { tindakan: tindakan, catatan: catatan, ikutSaran: ikutSaran, oleh: D.VERIFIKATOR.nama, waktu: "6 Okt 2026, " + jam() };
    ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; ui.galat = "";
    simpan();
    gambar(true);
    const t = D.TINDAKAN[tindakan];
    toast(t.status + " · " + id, t.laporan ? "#/laporan/" + id : null);
  }

  /* ============================================================== panduan */

  const TUR = [
    { tengah: true, judul: "Selamat datang di Vedika Autentik",
      teks: "Anda verifikator di KC Jakarta Pusat. Fitur ini memeriksa keaslian berkas fisioterapi sebelum klaim dibayar." },
    { rute: "#/autentik", sel: "#panelUnggah", posisi: "bawah", coba: "#tombolDemo", tungguDemo: true, judul: "Masukkan lima berkas contoh",
      teks: "Anggap rumah sakit baru mengunggah lima berkas ke JKN Drive. Hasilnya masuk antrean, Prioritas di atas.", cobaTeks: "Tekan Jalankan demo" },
    { rute: "#/berkas/VA-KMB-01/bukti", sel: ".penampil", posisi: "kanan", siap: () => { pastikanDemo(); bukaBerkas("VA-KMB-01"); }, judul: "Buktinya langsung terlihat",
      teks: "Berkas Pak Budi ternyata lembar milik Bu Siti. Kotak merah menandai bagian yang sama persis." },
    { rute: "#/berkas/VA-KMB-01/peserta", sel: ".ponsel", posisi: "kanan", coba: ".ponsel-balas button", judul: "Peserta ditanya langsung",
      teks: "Satu pertanyaan netral lewat PANDAWA. Peserta menjadi saksi dari luar rumah sakit.", cobaTeks: "Pilih salah satu jawaban" },
    { rute: "#/berkas/VA-KMB-01/bukti", sel: ".saran", posisi: "kiri", coba: '[data-aksi="setujui"]', judul: "Sistem menyarankan, Anda memutuskan",
      teks: "Setujui dengan satu klik, atau pilih tindakan lain dengan alasan tertulis. Tersisa empat berkas contoh untuk dicoba sendiri.", cobaTeks: "Tekan Setujui saran" }
  ];

  const tur = { aktif: false, i: 0, dengar: false };

  function pastikanDemo() {
    D.DEMO.forEach((d, i) => { if (!diAntrean(d.id)) S.antrean.push({ id: d.id, tanggal: "6 Okt", jam: jam(), baru: true }); void i; });
    simpan();
  }
  function bukaBerkas(id) { if (!S.dibuka.includes(id)) { S.dibuka.push(id); simpan(); } }

  function turMulai() { tur.aktif = true; ui.menuBuka = false; turKe(0); }
  function turSelesai() {
    tur.aktif = false; S.turSelesai = true; simpan(); turBersih();
  }
  function turKe(i) {
    if (i < 0) return;
    if (i >= TUR.length) { turSelesai(); return; }
    tur.i = i;
    const s = TUR[i];
    if (s.siap) s.siap();
    if (s.rute && location.hash !== s.rute) location.hash = s.rute;
    else gambar(true);
  }
  function turBersih() { document.querySelectorAll(".tur-tirai,.tur-sorot,.tur-kartu").forEach((e) => e.remove()); }

  function turGambar() {
    turBersih();
    if (!tur.aktif) return;
    const s = TUR[tur.i];
    const el = s.sel ? document.querySelector(s.sel) : null;
    if (s.sel && !el) return;
    if (el) {
      const r0 = el.getBoundingClientRect();
      if (r0.top < 70 || r0.top > window.innerHeight - 120) window.scrollTo(0, window.scrollY + r0.top - 90);
    }
    const kartu = document.createElement("div");
    kartu.className = "tur-kartu" + (s.tengah || !el ? " tur-kartu--tengah" : "");
    kartu.setAttribute("role", "dialog");
    kartu.setAttribute("aria-label", "Panduan demo, langkah " + (tur.i + 1) + " dari " + TUR.length);
    const akhir = tur.i === TUR.length - 1;
    const menungguDemo = s.tungguDemo && ui.proses && !ui.proses.selesai;
    kartu.innerHTML =
      '<span class="hitung">Langkah ' + (tur.i + 1) + " dari " + TUR.length + "</span><h3>" + esc(s.judul) + "</h3><p>" + esc(s.teks) + "</p>" +
      (s.cobaTeks ? '<span class="coba">' + ikon("klik") + esc(menungguDemo ? "Tunggu sampai kelima berkas selesai diperiksa" : s.cobaTeks) + "</span>" : "") +
      '<div class="tur-kaki">' + (akhir ? "" : '<button class="tur-lewati" type="button" data-aksi="tur-tutup">Lewati panduan</button>') +
        '<span class="kanan">' + (tur.i > 0 ? '<button class="btn btn--kecil" type="button" data-aksi="tur-mundur">Kembali</button>' : "") +
        '<button class="btn btn--kecil' + (s.coba ? "" : " btn--primer") + '" type="button" data-aksi="tur-maju"' + (menungguDemo ? " disabled" : "") + ">" +
          (akhir ? "Selesai" : tur.i === 0 ? "Mulai" : s.coba ? "Lewati" : "Lanjut") + "</button></span></div>" +
      '<div class="tur-titik">' + TUR.map((_, j) => "<i" + (j === tur.i ? ' class="ini"' : "") + "></i>").join("") + "</div>";
    document.body.appendChild(kartu);

    const tirai = (gaya) => { const d = document.createElement("div"); d.className = "tur-tirai"; d.style.cssText = gaya; document.body.appendChild(d); };
    if (!el || s.tengah) { tirai("inset:0"); return; }

    const r = el.getBoundingClientRect(), p = 6;
    const atas = Math.max(0, r.top - p), bawah = Math.min(window.innerHeight, r.bottom + p);
    tirai("top:0;left:0;right:0;height:" + atas + "px");
    tirai("top:" + bawah + "px;left:0;right:0;bottom:0");
    tirai("top:" + atas + "px;left:0;width:" + Math.max(0, r.left - p) + "px;height:" + (bawah - atas) + "px");
    tirai("top:" + atas + "px;left:" + (r.right + p) + "px;right:0;height:" + (bawah - atas) + "px");
    const sorot = document.createElement("div");
    sorot.className = "tur-sorot";
    sorot.style.cssText = "top:" + atas + "px;left:" + (r.left - p) + "px;width:" + (r.width + p * 2) + "px;height:" + (bawah - atas) + "px";
    document.body.appendChild(sorot);

    const W = kartu.offsetWidth, H = kartu.offsetHeight, M = 16, vw = window.innerWidth, vh = window.innerHeight;
    let top, left;
    if (s.posisi === "kanan" && r.right + 16 + W < vw) { left = r.right + 16; top = r.top; }
    else if (s.posisi === "kiri" && r.left - 16 - W > 0) { left = r.left - 16 - W; top = r.top; }
    else if (s.posisi === "atas" && r.top - 16 - H > M) { top = r.top - 16 - H; left = r.left; }
    else if (r.bottom + 16 + H < vh) { top = r.bottom + 16; left = r.left; }
    else { top = vh - H - M; left = vw - W - M; }
    kartu.style.top = Math.max(M, Math.min(top, vh - H - M)) + "px";
    kartu.style.left = Math.max(M, Math.min(left, vw - W - M)) + "px";
  }

  function turDengar(e) {
    if (!tur.aktif) return;
    const s = TUR[tur.i];
    if (!s.coba || s.tungguDemo || !e.target.closest || !e.target.closest(s.coba)) return;
    const i = tur.i;
    setTimeout(() => { if (tur.aktif && tur.i === i) turKe(i + 1); }, 650);
  }

  /* ============================================================== render */

  function gambar(tetap) {
    const y = window.scrollY;
    const r = rute();
    const akar = document.getElementById("akar");
    document.body.style.overflow = "";

    if (!S.masuk) {
      akar.innerHTML = lamanMasuk();
      turBersih();
      return;
    }

    let isi, jejak;
    const b = r.id ? berkas(r.id) : null;
    if (r.nama === "autentik") { isi = lamanAutentik(); jejak = "<b>Autentik</b>"; }
    else if (r.nama === "berkas") {
      if (b && diAntrean(r.id)) bukaBerkas(r.id);
      isi = lamanBerkas(r.id, r.tab);
      jejak = '<a href="#/autentik">Autentik</a><span>/</span><b>' + esc(b ? b.klaim.peserta : "Berkas") + "</b>";
    } else if (r.nama === "laporan") {
      isi = lamanLaporan(r.id);
      jejak = '<a href="#/autentik">Autentik</a><span>/</span><a href="#/berkas/' + esc(r.id) + '">' + esc(b ? b.klaim.peserta : "Berkas") + "</a><span>/</span><b>Laporan temuan</b>";
    } else if (r.nama === "riwayat") { isi = lamanRiwayat(); jejak = "<b>Riwayat keputusan</b>"; }
    else { isi = lamanBeranda(); jejak = "<b>Beranda</b>"; }

    akar.innerHTML = kerangka(r, isi, jejak);
    document.title = (r.nama === "beranda" ? "Beranda" : r.nama === "riwayat" ? "Riwayat keputusan" : b ? b.klaim.peserta : "Autentik") + " · Vedika Autentik";
    window.scrollTo(0, tetap ? y : 0);
    if (r.nama === "laporan") isiPotongan();
    if (ui.fokus != null) { const f = document.querySelector(".sorot.fokus"); if (f && !tetap) f.scrollIntoView({ block: "center" }); }
    requestAnimationFrame(turGambar);
  }

  function toast(pesan, tautan) {
    const w = document.getElementById("toast");
    const t = document.createElement("div");
    t.className = "toast";
    t.innerHTML = ikon("lencanaCek") + "<span>" + esc(pesan) + (tautan ? ' <a href="' + tautan + '">Buka laporan</a>' : "") + "</span>";
    w.appendChild(t);
    setTimeout(() => { t.style.transition = "opacity .3s"; t.style.opacity = "0"; setTimeout(() => t.remove(), 320); }, 4200);
  }

  /* ============================================================== peristiwa */

  const AKSI = {
    masuk() { S.masuk = true; simpan(); ke("#/beranda"); if (!S.turSelesai) setTimeout(turMulai, 350); },
    menu() { ui.menuBuka = !ui.menuBuka; gambar(true); },
    "buka-antrean"(el) {
      const ada = S.antrean.some((a) => berkas(a.id).klaim.faskes === el.dataset.faskes);
      ui.faskes = ada ? el.dataset.faskes : "";
      ui.asalUnggah = el.dataset.faskes;
      if (!ada) toast("Belum ada berkas Autentik dari " + el.dataset.faskes + " di antrean demo.");
      ke("#/autentik");
    },
    "buka-berkas"(el) { ui.fokus = null; ke("#/berkas/" + el.dataset.id); },
    saring(el) { ui.filter = el.dataset.nilai; gambar(true); },
    demo() { jalankan(D.DEMO.map((d) => d.id)); },
    skenario(el) { const id = el.dataset.id; if (diAntrean(id)) ke("#/berkas/" + id); else jalankan([id]); },
    "setujui-lolos"() {
      const ids = S.antrean.filter((a) => berkas(a.id).label === "lolos" && !S.keputusan[a.id]).map((a) => a.id);
      ids.forEach((id) => { S.keputusan[id] = { tindakan: "wajar", catatan: "Disetujui bersama: semua pemeriksaan bersih.", ikutSaran: true, oleh: D.VERIFIKATOR.nama, waktu: "6 Okt 2026, " + jam() }; });
      simpan(); gambar(true); toast(ids.length + " berkas lolos dikembalikan ke verifikasi biasa.");
    },
    fokus(el) { const i = Number(el.dataset.i); ui.fokus = ui.fokus === i ? null : i; ui.sorot = true; gambar(true); const f = document.querySelector(".sorot.fokus"); if (f) f.scrollIntoView({ block: "center", behavior: "smooth" }); },
    perbesar() { ui.perbesar = !ui.perbesar; gambar(true); },
    setujui() {
      const r = rute(), b = berkas(r.id), saran = D.SARAN[b.label];
      const catatan = D.TINDAKAN[saran].laporan ? (ui.catatan != null ? ui.catatan : ringkasCatatan(b)) : "";
      putuskan(b.id, saran, catatan.trim(), true);
    },
    "pilih-lain"() { ui.pilihLain = true; ui.catatan = ""; ui.galat = ""; gambar(true); },
    "batal-lain"() { ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; ui.galat = ""; gambar(true); },
    "simpan-lain"() {
      if (!ui.tindakanLain) { ui.galat = "Pilih salah satu tindakan dulu."; gambar(true); return; }
      if (!ui.catatan || !ui.catatan.trim()) { ui.galat = "Tulis alasan singkat. Catatan ini masuk ke jejak keputusan dan laporan."; gambar(true); return; }
      putuskan(rute().id, ui.tindakanLain, ui.catatan.trim(), false);
    },
    "batal-putusan"() { delete S.keputusan[rute().id]; simpan(); gambar(true); },
    jawab(el) { const id = rute().id; S.jawaban[id] = el.dataset.nilai; ui.catatan = null; simpan(); gambar(true); toast("Jawaban peserta tercatat: " + D.JAWABAN[el.dataset.nilai].teks + "."); },
    "hapus-jawaban"() { delete S.jawaban[rute().id]; simpan(); gambar(true); },
    "unduh-pdf"(el) { unduhPdf(el.dataset.id); },
    cetak() { window.print(); },
    "tur-mulai"() { turMulai(); },
    "tur-maju"() { turKe(tur.i + 1); },
    "tur-mundur"() { turKe(tur.i - 1); },
    "tur-tutup"() { turSelesai(); },
    "ulang-demo"() {
      const tetapMasuk = S.masuk;
      S = statusAwal(); S.masuk = tetapMasuk; S.turSelesai = true;
      ui.proses = null; ui.filter = "semua"; ui.faskes = ""; ui.q = ""; ui.asalUnggah = ""; ui.asalError = false; ui.fokus = null; ui.pilihLain = false; ui.catatan = null;
      simpan(); ke("#/autentik"); toast("Demo dimulai ulang. Antrean kembali ke keadaan awal.");
    }
  };

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-aksi]");
    if (!el || el.tagName === "SELECT" || el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && el.type !== "checkbox" && el.type !== "radio")) return;
    const f = AKSI[el.dataset.aksi];
    if (f) { if (el.tagName === "A") e.preventDefault(); f(el); }
    if (ui.menuBuka && !e.target.closest("#sisi") && el.dataset.aksi !== "menu") { ui.menuBuka = false; gambar(true); }
  });

  document.addEventListener("change", (e) => {
    const a = e.target.dataset && e.target.dataset.aksi;
    if (a === "saring-faskes") { ui.faskes = e.target.value; gambar(true); }
    else if (a === "asal-unggah") { ui.asalUnggah = e.target.value; ui.asalError = false; gambar(true); document.querySelector("#faskesUnggah")?.focus(); }
    else if (a === "saklar-sorot") { ui.sorot = e.target.checked; gambar(true); }
    else if (a === "tindakan-lain") { ui.tindakanLain = e.target.value; ui.galat = ""; gambar(true); }
    else if (e.target.id === "pilihBerkas" && e.target.files.length) { const files = [...e.target.files]; e.target.value = ""; terimaBerkas(files); }
  });

  document.addEventListener("input", (e) => {
    const a = e.target.dataset && e.target.dataset.aksi;
    if (a === "catatan") ui.catatan = e.target.value;
    else if (a === "cari") {
      ui.q = e.target.value;
      const pos = e.target.selectionStart;
      gambar(true);
      const baru = document.querySelector('[data-aksi="cari"]');
      if (baru) { baru.focus(); baru.setSelectionRange(pos, pos); }
    }
  });

  ["dragenter", "dragover"].forEach((t) => document.addEventListener(t, (e) => {
    const z = e.target.closest && e.target.closest("#jatuh");
    if (!z) return;
    e.preventDefault(); z.classList.add("aktif");
  }));
  document.addEventListener("dragleave", (e) => { const z = e.target.closest && e.target.closest("#jatuh"); if (z) z.classList.remove("aktif"); });
  document.addEventListener("drop", (e) => {
    const z = e.target.closest && e.target.closest("#jatuh");
    if (!z) return;
    e.preventDefault(); z.classList.remove("aktif");
    if (e.dataTransfer && e.dataTransfer.files.length) terimaBerkas(e.dataTransfer.files);
  });

  document.addEventListener("click", turDengar, true);
  document.addEventListener("demo-selesai", () => { if (tur.aktif && TUR[tur.i].tungguDemo) setTimeout(() => turKe(tur.i + 1), 500); });
  document.addEventListener("keydown", (e) => {
    if (!tur.aktif) return;
    if (e.key === "Escape") turSelesai();
    else if (e.key === "ArrowRight" && !TUR[tur.i].tungguDemo) turKe(tur.i + 1);
    else if (e.key === "ArrowLeft") turKe(tur.i - 1);
  });
  window.addEventListener("hashchange", () => { ui.pilihLain = false; ui.tindakanLain = null; ui.catatan = null; ui.galat = ""; ui.fokus = null; ui.menuBuka = false; gambar(false); });
  window.addEventListener("resize", () => { if (tur.aktif) turGambar(); });
  window.addEventListener("scroll", () => { if (tur.aktif) turGambar(); }, { passive: true });

  gambar(false);
})();
