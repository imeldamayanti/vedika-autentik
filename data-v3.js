/* Vedika Autentik v3: data demo konfirmasi suara.

   Seluruh isi ditulis tangan mengikuti PRD v3 dan folder data-uji-konfirmasi
   (skenario_uji.json, transkrip_uji, rumah_sakit.csv, riwayat_panggilan_2026-08.json,
   expected_ringkasan_rs.json), tidak dihitung dari CSV. Label tiap skenario ditulis
   langsung, lalu diperiksa ulang dengan aturan PRD bagian F4 sebagai uji mandiri saat
   halaman dimuat (selisih label muncul di konsol).

   Nama, rumah sakit, dan nomor bersifat fiktif. */

(function (global) {
  "use strict";

  /* ---------- waktu, verifikator, dan nomor ---------- */

  const HARI_INI = "Selasa, 6 Oktober 2026";
  const VERIFIKATOR = { nama: "R. Santoso", peran: "Verifikator", kantor: "KC Jakarta Pusat" };
  const BULAN = "Agustus 2026";
  const BULAN_PENDEK = "Agustus";
  /* Awalan 0800 tidak bisa ditelepon (README data uji). Mode presentasi (?presentasi=1, hanya untuk rekaman video
     demo): label Simulasi disembunyikan dan pemanggil tampil sebagai Care Center 165, seperti produk akhir. */
  const PRESENTASI = new URLSearchParams(location.search).get("presentasi") === "1";
  const NOMOR_PENELEPON = PRESENTASI ? "165" : "0800-0000-0165";
  const JEDA_PESAN_MENIT = 1;

  /* ---------- label hasil panggilan (PRD F4) ---------- */

  /* Lima label dari aturan.py (API dan backend tetap memakai kelimanya). Di layar hanya tiga: Tidak yakin, Tidak terhubung,
     dan Menolak tampil sebagai "Tidak ada jawaban" dengan alasan kecil, karena tindakannya sama dan ketiganya tidak dihitung. */
  const LABEL = {
    tidak_sesuai: { nama: "Tidak sesuai" },
    sesuai: { nama: "Sesuai" },
    tidak_yakin: { nama: "Tidak ada jawaban", alasan: "tidak yakin jumlahnya" },
    tidak_terhubung: { nama: "Tidak ada jawaban", alasan: "tidak diangkat" },
    menolak: { nama: "Tidak ada jawaban", alasan: "menolak menjawab" }
  };

  /* Tindakan verifikator (PRD R5.3). "Pantau" hanya muncul sebagai saran, bukan pilihan lain. */
  const TINDAKAN = {
    pantau: {
      nama: "Pantau",
      akibat: "Tidak ada tindakan ke rumah sakit. Panggilan ini tidak dihitung pada ringkasan RS.",
      status: "Dipantau"
    },
    tutup: {
      nama: "Tutup kasus",
      akibat: "Kasus selesai. Klaim kembali ke verifikasi biasa.",
      status: "Kasus ditutup"
    },
    klarifikasi: {
      nama: "Minta klarifikasi RS",
      akibat: "Rumah sakit diminta menjelaskan selisih. Bukti disimpan sampai klarifikasi selesai.",
      status: "Menunggu klarifikasi RS"
    },
    teruskan: {
      nama: "Teruskan ke Tim PK-JKN",
      akibat: "Kasus diteruskan ke Tim Pencegahan Kecurangan JKN beserta kartu bukti.",
      status: "Diteruskan ke Tim PK-JKN"
    }
  };
  const PILIHAN_TINDAKAN = ["tutup", "klarifikasi", "teruskan"];

  /* Langkah yang disarankan per label (tabel F4). */
  const SARAN = { tidak_terhubung: "pantau", menolak: "pantau", tidak_sesuai: "klarifikasi", tidak_yakin: "pantau", sesuai: "tutup" };

  const RETENSI = {
    tidak_sesuai: "Rekaman dan transkrip disimpan terenkripsi sampai klarifikasi ke RS selesai.",
    sesuai: "Rekaman dan transkrip dihapus otomatis setelah 30 hari. Hasil terstruktur tetap disimpan.",
    tidak_yakin: "Hanya status yang disimpan. Tidak ada rekaman atau transkrip.",
    tidak_terhubung: "Hanya status yang disimpan. Tidak ada rekaman atau transkrip.",
    menolak: "Hanya status yang disimpan. Tidak ada rekaman atau transkrip."
  };

  /* ---------- indikator (PRD F1) ---------- */

  const INDIKATOR = {
    /* nama = arti singkat yang langsung terbaca di chip, tanpa hover (audit S-11). */
    I1: { nama: "Lebih dari 8 sesi/bulan", arti: "Sesi ditagih lebih dari 8 dalam sebulan" },
    I2: { nama: "3 sesi dalam seminggu", arti: "Ada satu minggu dengan 3 sesi atau lebih" },
    I3: { nama: "6 bulan berturut-turut", arti: "Ada sesi di 6 bulan berturut-turut" },
    I4: { nama: "Sesi di hari libur", arti: "Ada sesi di hari Minggu atau libur nasional" }
  };

  /* ---------- rumah sakit (rumah_sakit.csv, expected_ringkasan_rs.json) ----------
     funnel: pasien dipilih (aturan ATAU model) dibanding harapan menurut umur pasiennya (anomali_demo.json). */

  const RS = [
    { id: "RS01", nama: "RS Melati Sehat", aktif: 68, terpicu: 27, persen: 39.7,
      funnel: {"patient_months": 68, "selected": 27, "expected": 2.3, "z": 10.34, "position": "above_99_8"} },
    { id: "RS02", nama: "RSU Bakti Mulia", aktif: 65, terpicu: 1, persen: 1.5,
      funnel: {"patient_months": 65, "selected": 1, "expected": 2.3, "z": -0.54, "position": "within"} },
    { id: "RS03", nama: "RS Cempaka Asri", aktif: 60, terpicu: 1, persen: 1.7,
      funnel: {"patient_months": 60, "selected": 2, "expected": 2.1, "z": -0.05, "position": "within"} },
    { id: "RS04", nama: "RSU Nusa Sejahtera", aktif: 53, terpicu: 0, persen: 0.0,
      funnel: {"patient_months": 53, "selected": 0, "expected": 1.8, "z": -0.85, "position": "within"} },
    { id: "RS05", nama: "RS Kenanga Medika", aktif: 56, terpicu: 1, persen: 1.8,
      funnel: {"patient_months": 56, "selected": 2, "expected": 1.9, "z": 0.05, "position": "within"} }
  ];
  const PASIEN_AKTIF = 302;
  const PASIEN_TERPICU = 30;

  /* ---------- pengaturan (halaman Pengaturan) ----------
     Bentuknya sengaja sama dengan PUT /pengaturan supaya nanti tinggal disambung ke API. Selama backend belum
     menerimanya, app-v3.js menyimpannya di localStorage dan memberi tahu modul ini lewat ubahPengaturan. */

  /* Bagian pesan yang tidak bisa diubah verifikator: melindungi peserta dari penipuan, dan pilihan jawaban 1–6
     yang dibaca otomatis oleh sistem. Selalu ditempel di belakang templat yang diedit. */
  const KUNCI_WA = "Ini bukan tagihan. Kami tidak akan meminta NIK, kode OTP, nomor rekening, atau pembayaran. Ragu pesan ini asli? Hubungi Care Center 165.";
  const KUNCI_CADANGAN = "Balas dengan angka: 1) 1–2 kali  2) 3–4 kali  3) 5–8 kali  4) lebih dari 8 kali  5) tidak ingat  6) tidak pernah terapi di sana.";

  const PENGATURAN_BAWAAN = {
    nomor_penelepon: NOMOR_PENELEPON,
    nomor_uji: "0812-0000-0000",
    saluran: "wa",
    templat_wa: "Halo {{nama}}, kami dari BPJS Kesehatan. Sekitar {{menit}} menit lagi kami akan menelepon dari nomor {{nomor}} untuk konfirmasi singkat layanan fisioterapi {{pasien}} di {{rs}} bulan {{bulan}}. Teleponnya sekitar 2 menit, mohon diangkat.",
    templat_cadangan: "Kami belum berhasil menelepon. Kira-kira berapa kali {{pasien}} menjalani fisioterapi di {{rs}} bulan {{bulan}}?",
    jam_mulai: "08:00", jam_selesai: "16:00", hari: "senin_jumat", batas_harian: 40,
    jeda_wa_menit: JEDA_PESAN_MENIT, jeda_percobaan_menit: 3, percobaan_maks: 2,
    indikator_min: 2, indikator_aktif: ["I1", "I2", "I3", "I4"], sertakan_model: true
  };
  let pengaturanAktif = Object.assign({}, PENGATURAN_BAWAAN, { indikator_aktif: PENGATURAN_BAWAAN.indikator_aktif.slice() });
  const pengaturan = () => pengaturanAktif;
  function ubahPengaturan(patch) {
    pengaturanAktif = Object.assign({}, pengaturanAktif, patch);
    return pengaturanAktif;
  }
  const nomorPenelepon = () => pengaturanAktif.nomor_penelepon;
  const jedaWa = () => pengaturanAktif.jeda_wa_menit;

  /* Placeholder yang boleh dipakai di templat, dengan arti singkatnya untuk chip di editor. */
  const PLACEHOLDER = {
    nama: "Nama penerima", menit: "Menit sebelum telepon", nomor: "Nomor penelepon",
    pasien: "Nama pasien", rs: "Rumah sakit", bulan: "Bulan layanan"
  };
  /* Placeholder yang wajib ada: tanpa ini peserta tidak tahu siapa menelepon, kapan, dan soal siapa. */
  const WAJIB = { wa: ["nomor", "menit", "pasien"], cadangan: ["pasien"] };
  const BATAS_KARAKTER = { wa: 600, cadangan: 400 };
  const RE_PLACEHOLDER = /\{\{\s*([a-z_]+)\s*\}\}/gi;

  function isiTemplat(teks, data) {
    return teks.replace(RE_PLACEHOLDER, (utuh, k) => (data[k.toLowerCase()] != null ? data[k.toLowerCase()] : utuh));
  }

  /* Galat templat yang diedit (bagian yang bisa diubah saja), dalam kalimat yang langsung bisa dipahami. */
  function cekTemplat(teks, jenis) {
    const galat = [];
    const dipakai = [];
    String(teks).replace(RE_PLACEHOLDER, (utuh, k) => { dipakai.push(k.toLowerCase()); return utuh; });
    dipakai.filter((k, i) => !PLACEHOLDER[k] && dipakai.indexOf(k) === i).forEach((k) => galat.push("Placeholder {{" + k + "}} tidak dikenal."));
    WAJIB[jenis].filter((k) => dipakai.indexOf(k) < 0).forEach((k) => galat.push("Placeholder {{" + k + "}} wajib ada (" + PLACEHOLDER[k].toLowerCase() + ")."));
    if (/https?:|www\.|\b[a-z0-9-]+\.(com|id|net|org)\b/i.test(teks)) galat.push("Pesan tidak boleh berisi tautan.");
    if (String(teks).length > BATAS_KARAKTER[jenis]) galat.push("Terlalu panjang: " + String(teks).length + " dari " + BATAS_KARAKTER[jenis] + " karakter.");
    return galat;
  }

  const jumlahSms = (n) => (n > 0 ? Math.ceil(n / 160) : 0);

  function cekNomor(nomor) {
    const n = String(nomor).trim();
    const angka = n.replace(/\D/g, "");
    if (!/^[+()\d\s-]+$/.test(n) || angka.length < 3 || angka.length > 15) return "Nomor hanya berisi angka, spasi, tanda hubung, atau +, sepanjang 3–15 angka.";
    return "";
  }

  const keMenit = (h) => { const [j, m] = String(h).split(":").map(Number); return j * 60 + m; };
  function cekAturanPanggilan(a) {
    const galat = [];
    const bulat = (x, min, maks) => x !== "" && Number.isInteger(Number(x)) && Number(x) >= min && Number(x) <= maks;
    if (!/^\d{2}:\d{2}$/.test(a.jam_mulai) || !/^\d{2}:\d{2}$/.test(a.jam_selesai)) galat.push("Jam panggilan: isi jam mulai dan jam selesai.");
    else if (keMenit(a.jam_mulai) >= keMenit(a.jam_selesai)) galat.push("Jam panggilan: jam mulai harus lebih awal dari jam selesai.");
    if (!bulat(a.jeda_wa_menit, 1, 10)) galat.push("Jeda pesan ke telepon: 1–10 menit.");
    if (!bulat(a.jeda_percobaan_menit, 1, 30)) galat.push("Jeda antar percobaan: 1–30 menit.");
    if (!bulat(a.percobaan_maks, 1, 3)) galat.push("Percobaan telepon: 1–3 kali.");
    if (!bulat(a.batas_harian, 1, 500)) galat.push("Batas panggilan per hari: 1–500.");
    if (!bulat(a.indikator_min, 1, 4)) galat.push("Minimal indikator: 1–4.");
    if (!a.indikator_aktif.length && !a.sertakan_model) galat.push("Pilih minimal satu indikator atau sertakan model anomali.");
    return galat;
  }

  /* Berapa pasien di data contoh yang dipilih untuk ditelepon menurut aturan pemicu: indikator aktif yang
     terpenuhi minimal indikator_min, ATAU (bila model disertakan) model anomali menandainya. */
  function hitungDipilih(aturan) {
    const a = Object.assign({}, PENGATURAN_BAWAAN, aturan || {});
    const semua = Object.keys(SEMUA).map((id) => SEMUA[id]).concat(TIDAK_DIPICU);
    return semua.filter((p) => {
      const kena = p.indikator.filter((i) => a.indikator_aktif.indexOf(i) >= 0).length;
      return kena >= a.indikator_min || (a.sertakan_model && !!(p.anomali && p.anomali.ditandai));
    }).length;
  }

  /* ---------- teks WhatsApp (PRD Lampiran B), dari templat di Pengaturan ---------- */

  const dataPesan = (p) => ({ nama: p.penerima.nama, menit: jedaWa(), nomor: nomorPenelepon(), pasien: p.pasien, rs: namaRs(p.rs), bulan: BULAN_PENDEK });

  function pesanPemberitahuan(p, templat) {
    return isiTemplat(templat != null ? templat : pengaturanAktif.templat_wa, dataPesan(p)) + "\n\n" + KUNCI_WA;
  }

  function pesanCadangan(p, templat) {
    return isiTemplat(templat != null ? templat : pengaturanAktif.templat_cadangan, dataPesan(p)) + " " + KUNCI_CADANGAN;
  }

  function namaRs(id) { return RS.find((r) => r.id === id).nama; }

  /* ---------- pembuka percakapan yang sama di semua transkrip ---------- */

  const BUKA = (sapa) => "Selamat siang, saya asisten otomatis dari BPJS Kesehatan. Panggilan ini direkam untuk konfirmasi layanan. Ini bukan tagihan, dan saya tidak akan meminta data pribadi, kode OTP, atau pembayaran apa pun. Apakah benar saya bicara dengan " + sapa + "?";

  /* ---------- 8 skenario (skenario_uji.json) ----------

     transkrip: [pembicara, detik ke-n pada panggilan nyata, kalimat], pembicara A = AI, P = penerima.
     tangkap: indeks baris transkrip tempat tiap isian "Yang ditangkap AI" terisi.
     jawaban: skema keluaran pembaca jawaban (README data uji). */

  const SKENARIO = {
    S1: {
      id: "S1", pasien: "Andi Pratama", umur: 54, rs: "RS01",
      ditagih: 11, tanggal: [3, 4, 6, 10, 11, 13, 16, 17, 20, 24, 27], tandaTanggal: { 16: "Minggu", 17: "Libur nasional" },
      indikator: ["I1", "I2", "I4"], tanggalLibur: [16, 17],
      penerima: { nama: "Andi Pratama", hubungan: "peserta" },
      durasi: 63.4, rekaman: "assets/rekaman/S1.mp3", suara_langsung: "assets/rekaman/S1",
      jawaban: {
        status_panggilan: "terjawab", penerima: "peserta", hubungan: null, hadir: true, jumlah_min: 3, jumlah_maks: 3, keyakinan: "tinggi",
        tanda_bahaya: [], membantah_tanggal_libur: true,
        kutipan_kunci: "Tiga kali... Nggak pernah. Hari Minggu kan tutup.",
        ringkasan: "Peserta menjalani 3 sesi di bulan Agustus dan tidak pernah terapi di hari Minggu atau 17 Agustus."
      },
      label: "tidak_sesuai",
      alasan: "Ditagih 11 sesi, versi penerima paling banyak 3 sesi (selisih 8).",
      transkrip: [
        ["A", 0.0, BUKA("Bapak Andi Pratama")],
        ["P", 19.4, "Iya, saya sendiri."],
        ["A", 21.4, "Terima kasih, Pak Andi. Saya mau konfirmasi singkat soal fisioterapi Bapak di RS Melati Sehat bulan Agustus. Apakah Bapak menjalani fisioterapi di sana bulan Agustus?"],
        ["P", 33.5, "Iya, betul."],
        ["A", 35.1, "Kira-kira berapa kali Bapak datang terapi di bulan Agustus?"],
        ["P", 39.4, "Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan."],
        ["A", 43.7, "Baik, tiga kali. Satu lagi, Pak. Apakah Bapak pernah terapi di hari Minggu tanggal 16 Agustus atau tanggal 17 Agustus?"],
        ["P", 53.0, "Nggak pernah. Hari Minggu kan tutup."],
        ["A", 55.5, "Terima kasih, Pak Andi. Jawaban Bapak sudah kami catat dan tidak memengaruhi layanan atau iuran Bapak. Selamat siang."]
      ],
      tangkap: { penerima: 1, hadir: 3, jumlah: 5, keyakinan: 5, libur: 7, bahaya: 8 }
    },

    S2: {
      id: "S2", pasien: "Siti Rahmawati", umur: 67, rs: "RS01",
      ditagih: 10, tanggal: [1, 3, 5, 7, 12, 14, 19, 23, 26, 28], tandaTanggal: { 23: "Minggu" },
      indikator: ["I1", "I2", "I3", "I4"], tanggalLibur: [23],
      penerima: { nama: "Dewi Rahmawati", hubungan: "anak" },
      durasi: 72.3, rekaman: "assets/rekaman/S2.mp3", suara_langsung: "assets/rekaman/S2",
      jawaban: {
        status_panggilan: "terjawab", penerima: "keluarga", hubungan: "anak", hadir: true, jumlah_min: 2, jumlah_maks: 2, keyakinan: "tinggi",
        tanda_bahaya: ["tanda_tangan_tanpa_layanan"], membantah_tanggal_libur: true,
        kutipan_kunci: "Dua kali aja. Tapi waktu itu Ibu disuruh tanda tangan di beberapa lembar sekaligus.",
        ringkasan: "Menurut anak, Ibu Siti menjalani 2 sesi dan diminta menandatangani beberapa lembar sekaligus."
      },
      label: "tidak_sesuai",
      alasan: "Ada pernyataan berisiko: tanda tangan tanpa layanan.",
      transkrip: [
        ["A", 0.0, BUKA("keluarga Ibu Siti Rahmawati")],
        ["P", 19.6, "Iya, saya Dewi, anaknya."],
        ["A", 22.5, "Terima kasih, Bu Dewi. Saya mau konfirmasi singkat soal fisioterapi Ibu Siti di RS Melati Sehat bulan Agustus. Apakah Ibu Siti menjalani fisioterapi di sana bulan Agustus?"],
        ["P", 34.7, "Iya, saya yang nganter."],
        ["A", 37.0, "Kira-kira berapa kali Ibu Siti terapi di bulan Agustus?"],
        ["P", 41.3, "Dua kali aja. Tapi waktu itu Ibu disuruh tanda tangan di beberapa lembar sekaligus, katanya buat jadwal berikutnya."],
        ["A", 51.1, "Baik, dua kali, dan Ibu Siti diminta tanda tangan beberapa lembar sekaligus. Apakah Ibu Siti pernah terapi di hari Minggu, tanggal 23 Agustus?"],
        ["P", 61.8, "Nggak, Minggu kami di rumah."],
        ["A", 64.1, "Terima kasih, Bu Dewi. Jawaban Ibu sudah kami catat dan tidak memengaruhi layanan atau iuran keluarga. Selamat siang."]
      ],
      tangkap: { penerima: 1, hadir: 3, jumlah: 5, keyakinan: 5, libur: 7, bahaya: 5 }
    },

    S3: {
      id: "S3", pasien: "Budi Santoso", umur: 45, rs: "RS02",
      ditagih: 9, tanggal: [1, 3, 6, 10, 13, 18, 21, 25, 28], tandaTanggal: {},
      indikator: ["I1", "I3"], tanggalLibur: [],
      penerima: { nama: "Budi Santoso", hubungan: "peserta" },
      durasi: 55.0, rekaman: "assets/rekaman/S3.mp3", suara_langsung: "assets/rekaman/S3",
      jawaban: {
        status_panggilan: "terjawab", penerima: "peserta", hubungan: null, hadir: true, jumlah_min: 9, jumlah_maks: 10, keyakinan: "tinggi",
        tanda_bahaya: [], membantah_tanggal_libur: null,
        kutipan_kunci: "Rutin, seminggu dua kali. Agustus berarti sembilan atau sepuluh kali.",
        ringkasan: "Peserta menjalani 9-10 sesi di bulan Agustus, sesuai tagihan."
      },
      label: "sesuai",
      alasan: "Ditagih 9 sesi, versi penerima 9–10 sesi. Masih dalam toleransi.",
      transkrip: [
        ["A", 0.0, BUKA("Bapak Budi Santoso")],
        ["P", 18.8, "Iya, betul."],
        ["A", 20.4, "Terima kasih, Pak Budi. Saya mau konfirmasi singkat soal fisioterapi Bapak di RSU Bakti Mulia bulan Agustus. Apakah Bapak menjalani fisioterapi di sana bulan Agustus?"],
        ["P", 33.1, "Iya betul."],
        ["A", 34.6, "Kira-kira berapa kali Bapak datang terapi di bulan Agustus?"],
        ["P", 38.9, "Rutin, seminggu dua kali. Agustus berarti sembilan atau sepuluh kali."],
        ["A", 44.4, "Baik, sekitar sembilan sampai sepuluh kali. Terima kasih, Pak Budi. Jawaban Bapak sudah kami catat dan tidak memengaruhi layanan atau iuran Bapak. Selamat siang."]
      ],
      tangkap: { penerima: 1, hadir: 3, jumlah: 5, keyakinan: 5, libur: 6, bahaya: 6 }
    },

    S4: {
      id: "S4", pasien: "Karti Lestari", umur: 72, rs: "RS01",
      ditagih: 9, tanggal: [4, 6, 11, 13, 16, 18, 20, 25, 27], tandaTanggal: { 16: "Minggu" },
      indikator: ["I1", "I2", "I4"], tanggalLibur: [16],
      penerima: { nama: "Bayu Lestari", hubungan: "anak" },
      durasi: 62.3, rekaman: null, suara_langsung: "assets/rekaman/S4",
      jawaban: {
        status_panggilan: "terjawab", penerima: "keluarga", hubungan: "anak", hadir: true, jumlah_min: 5, jumlah_maks: 6, keyakinan: "rendah",
        tanda_bahaya: [], membantah_tanggal_libur: null,
        kutipan_kunci: "Saya kurang tahu persis. Mungkin lima atau enam kali.",
        ringkasan: "Keluarga tidak yakin jumlah sesi; perkiraan 5-6 kali."
      },
      label: "tidak_yakin",
      alasan: "Penerima tidak ingat jumlah sesi dengan yakin. Tidak dihitung.",
      transkrip: [
        ["A", 0.0, BUKA("keluarga Ibu Karti Lestari")],
        ["P", 19.6, "Iya, saya Bayu, anaknya."],
        ["A", 21.6, "Terima kasih, Pak Bayu. Saya mau konfirmasi singkat soal fisioterapi Ibu Karti di RS Melati Sehat bulan Agustus. Apakah Ibu Karti menjalani fisioterapi di sana bulan Agustus?"],
        ["P", 34.3, "Iya."],
        ["A", 35.6, "Kira-kira berapa kali Ibu Karti terapi di bulan Agustus?"],
        ["P", 39.8, "Waduh, saya kurang tahu persis. Mungkin lima atau enam kali, yang nganter kadang adik saya."],
        ["A", 45.5, "Tidak apa-apa, Pak. Apakah Ibu Karti pernah terapi di hari Minggu, tanggal 16 Agustus?"],
        ["P", 52.3, "Kurang tahu juga, Mbak."],
        ["A", 54.1, "Baik, terima kasih, Pak Bayu. Jawaban Bapak sudah kami catat dan tidak memengaruhi layanan atau iuran keluarga. Selamat siang."]
      ],
      tangkap: { penerima: 1, hadir: 3, jumlah: 5, keyakinan: 5, libur: 7, bahaya: 8 }
    },

    S5: {
      id: "S5", pasien: "Joko Prasetyo", umur: 39, rs: "RS03",
      ditagih: 10, tanggal: [3, 4, 5, 10, 12, 17, 19, 24, 26, 31], tandaTanggal: { 17: "Libur nasional" },
      indikator: ["I1", "I2", "I4"], tanggalLibur: [17],
      penerima: { nama: "Joko Prasetyo", hubungan: "peserta" },
      durasi: 0, rekaman: null,
      jawaban: {
        status_panggilan: "tidak_terhubung", penerima: null, hubungan: null, hadir: null, jumlah_min: null, jumlah_maks: null, keyakinan: null,
        tanda_bahaya: [], membantah_tanggal_libur: null, kutipan_kunci: "",
        ringkasan: "Panggilan tidak diangkat 2 kali."
      },
      label: "tidak_terhubung",
      alasan: "Panggilan tidak diangkat setelah 2 kali percobaan.",
      transkrip: [],
      tangkap: {}
    },

    S6: {
      id: "S6", pasien: "Slamet Riyadi", umur: 58, rs: "RS01",
      ditagih: 8, tanggal: [3, 5, 7, 9, 12, 19, 24, 26], tandaTanggal: { 9: "Minggu" },
      indikator: ["I2", "I4"], tanggalLibur: [9],
      penerima: { nama: "Slamet Riyadi", hubungan: "peserta" },
      durasi: 54.8, rekaman: "assets/rekaman/S6.mp3", suara_langsung: "assets/rekaman/S6",
      jawaban: {
        status_panggilan: "terjawab", penerima: "peserta", hubungan: null, hadir: true, jumlah_min: 2, jumlah_maks: 2, keyakinan: "tinggi",
        tanda_bahaya: [], membantah_tanggal_libur: true,
        kutipan_kunci: "Cuma dua kali kok. Wong kakinya udah enakan.",
        ringkasan: "Peserta menjalani 2 sesi lalu berhenti karena sudah membaik; membantah terapi hari Minggu."
      },
      label: "tidak_sesuai",
      alasan: "Ditagih 8 sesi, versi penerima paling banyak 2 sesi (selisih 6).",
      transkrip: [
        ["A", 0.0, BUKA("Bapak Slamet Riyadi")],
        ["P", 19.5, "Iya, saya."],
        ["A", 21.1, "Terima kasih, Pak Slamet. Saya mau konfirmasi singkat soal fisioterapi Bapak di RS Melati Sehat bulan Agustus. Apakah Bapak menjalani fisioterapi di sana bulan Agustus?"],
        ["P", 33.7, "Iya mas, cuma dua kali kok. Wong kakinya udah enakan, ya udah nggak balik lagi."],
        ["A", 38.5, "Baik, dua kali. Apakah Bapak pernah terapi di hari Minggu, tanggal 9 Agustus?"],
        ["P", 44.7, "Lho, Minggu ya libur to mas."],
        ["A", 46.8, "Terima kasih, Pak Slamet. Jawaban Bapak sudah kami catat dan tidak memengaruhi layanan atau iuran Bapak. Selamat siang."]
      ],
      tangkap: { penerima: 1, hadir: 3, jumlah: 3, keyakinan: 3, libur: 5, bahaya: 6 }
    },

    S8: {
      id: "S8", pasien: "Hendra Wijaya", umur: 50, rs: "RS05",
      ditagih: 10, tanggal: [1, 3, 5, 10, 12, 18, 20, 24, 26, 31], tandaTanggal: {},
      indikator: ["I1", "I3"], tanggalLibur: [],
      penerima: { nama: "Hendra Wijaya", hubungan: "peserta" },
      durasi: 50.6, rekaman: null, suara_langsung: "assets/rekaman/S8",
      jawaban: {
        status_panggilan: "menolak", penerima: "peserta", hubungan: null, hadir: null, jumlah_min: null, jumlah_maks: null, keyakinan: null,
        tanda_bahaya: [], membantah_tanggal_libur: null,
        kutipan_kunci: "Nggak, saya nggak mau. Nanti saya telepon 165 aja.",
        ringkasan: "Penerima curiga penipuan dan memilih tidak menjawab."
      },
      label: "menolak",
      alasan: "Penerima tidak bersedia menjawab. Tidak dihitung sebagai sinyal negatif.",
      transkrip: [
        ["A", 0.0, BUKA("Bapak Hendra Wijaya")],
        ["P", 19.4, "Ini penipuan ya? BPJS kok nelpon."],
        ["A", 22.1, "Wajar Bapak waspada. Saya tidak akan meminta data pribadi, kode OTP, atau uang. Bapak bisa memastikan panggilan ini lewat Care Center 165 atau aplikasi Mobile JKN. Apakah Bapak bersedia menjawab dua pertanyaan singkat soal fisioterapi bulan Agustus?"],
        ["P", 42.5, "Nggak, saya nggak mau. Nanti saya telepon 165 aja."],
        ["A", 46.3, "Baik, Pak, tidak apa-apa. Terima kasih atas waktunya. Selamat siang."]
      ],
      tangkap: { penerima: 1, hadir: 3, jumlah: 3, keyakinan: 3, libur: 3, bahaya: 4 }
    }
  };

  /* S7 (Rina Marlina, RSU Nusa Sejahtera, 4 sesi, hanya I3) tidak dipicu dan tidak ditelepon,
     jadi tidak ada di SKENARIO maupun di antrean. Dicatat di sini untuk uji mandiri. */
  const TIDAK_DIPICU = [{ id: "S7", pasien: "Rina Marlina", rs: "RS04", ditagih: 4, indikator: ["I3"] }];

  /* ---------- 4 panggilan latar yang dianggap sudah terjadi (riwayat_panggilan_2026-08.json) ----------

     Penerima mengikuti aturan R1.3 (anak di bawah 13 tahun ditelepon lewat orang tuanya), sehingga
     berbeda dari kolom penerima di berkas riwayat sintetis. Rekaman dan transkrip tidak ada. */

  const LATAR = {
    R1: {
      id: "R1", pasien: "Bayu Utami", umur: 5, rs: "RS01",
      ditagih: 11, tanggal: [6, 7, 8, 12, 17, 20, 24, 25, 26, 29, 31], tandaTanggal: { 17: "Libur nasional" },
      indikator: ["I1", "I2", "I4"], tanggalLibur: [17],
      penerima: { nama: "Wahyu Gunawan", hubungan: "orang tua" },
      waktu: "5 Okt 2026, 09.42", durasi: 84,
      jawaban: {
        status_panggilan: "terjawab", penerima: "keluarga", hubungan: "orang tua", hadir: true, jumlah_min: 1, jumlah_maks: 1, keyakinan: "tinggi",
        tanda_bahaya: [], membantah_tanggal_libur: null,
        kutipan_kunci: "Seingat saya cuma 1 kali.",
        ringkasan: "Jumlah sesi versi peserta jauh di bawah tagihan."
      },
      label: "tidak_sesuai", alasan: "Ditagih 11 sesi, versi penerima paling banyak 1 sesi (selisih 10)."
    },
    R2: {
      id: "R2", pasien: "Yuni Setiawan", umur: 35, rs: "RS01",
      ditagih: 9, tanggal: [1, 3, 8, 14, 19, 21, 22, 27, 28], tandaTanggal: {},
      indikator: ["I1", "I2"], tanggalLibur: [],
      penerima: { nama: "Yuni Setiawan", hubungan: "peserta" },
      waktu: "5 Okt 2026, 10.05", durasi: 71,
      jawaban: {
        status_panggilan: "terjawab", penerima: "peserta", hubungan: null, hadir: true, jumlah_min: 3, jumlah_maks: 3, keyakinan: "tinggi",
        tanda_bahaya: [], membantah_tanggal_libur: null,
        kutipan_kunci: "Seingat saya cuma 3 kali.",
        ringkasan: "Jumlah sesi versi peserta jauh di bawah tagihan."
      },
      label: "tidak_sesuai", alasan: "Ditagih 9 sesi, versi penerima paling banyak 3 sesi (selisih 6)."
    },
    R3: {
      id: "R3", pasien: "Ani Siregar", umur: 28, rs: "RS01",
      ditagih: 9, tanggal: [1, 4, 7, 10, 15, 19, 22, 24, 29], tandaTanggal: {},
      indikator: ["I1", "I3"], tanggalLibur: [],
      penerima: { nama: "Ani Siregar", hubungan: "peserta" },
      waktu: "5 Okt 2026, 10.31", durasi: 66,
      jawaban: {
        status_panggilan: "terjawab", penerima: "peserta", hubungan: null, hadir: true, jumlah_min: 8, jumlah_maks: 10, keyakinan: "tinggi",
        tanda_bahaya: [], membantah_tanggal_libur: null,
        kutipan_kunci: "Kurang lebih 9 kali.",
        ringkasan: "Jumlah sesi sesuai tagihan."
      },
      label: "sesuai", alasan: "Ditagih 9 sesi, versi penerima 8–10 sesi. Masih dalam toleransi."
    },
    R4: {
      id: "R4", pasien: "Ratna Handayani", umur: 8, rs: "RS01",
      ditagih: 11, tanggal: [1, 6, 7, 10, 12, 14, 20, 22, 27, 29, 31], tandaTanggal: {},
      indikator: ["I1", "I2"], tanggalLibur: [],
      penerima: { nama: "Dimas Rahayu", hubungan: "orang tua" },
      waktu: "5 Okt 2026, 11.18", durasi: 74,
      jawaban: {
        status_panggilan: "terjawab", penerima: "keluarga", hubungan: "orang tua", hadir: true, jumlah_min: 10, jumlah_maks: 12, keyakinan: "tinggi",
        tanda_bahaya: [], membantah_tanggal_libur: null,
        kutipan_kunci: "Kurang lebih 11 kali.",
        ringkasan: "Jumlah sesi sesuai tagihan."
      },
      label: "sesuai", alasan: "Ditagih 11 sesi, versi penerima 10–12 sesi. Masih dalam toleransi."
    }
  };

  /* ---------- pasien lain yang masih mengantre (tidak ada skenario, belum ditelepon) ----------
     A1–A3 terpicu aturan. M1 dan M2 tidak terpicu aturan (kurang dari dua indikator), tetapi ditandai model anomali.
     Polanya dua pola "hanya model" yang paling sering di data sampel BPJS 2023–2024: M1 sebagian kunjungan tanpa
     rujukan FKTP dan dari kab/kota lain, M2 dua sesi hari Minggu. Keduanya ada di data uji (P-M1, P-M2). */

  const MENGANTRE = {
    A1: { id: "A1", pasien: "Sri Kurniawan", umur: 26, rs: "RS01", ditagih: 10, indikator: ["I1", "I2"], penerima: { nama: "Sri Kurniawan", hubungan: "peserta" } },
    A2: { id: "A2", pasien: "Tuti Hidayat", umur: 71, rs: "RS01", ditagih: 9, indikator: ["I1", "I2", "I4"], penerima: { nama: "Bayu Firmansyah", hubungan: "anak" } },
    A3: { id: "A3", pasien: "Sri Gunawan", umur: 69, rs: "RS01", ditagih: 9, indikator: ["I1", "I2", "I4"], penerima: { nama: "Bayu Handayani", hubungan: "anak" } },
    M1: { id: "M1", pasien: "Sari Wulandari", umur: 49, rs: "RS03", ditagih: 6, indikator: [], penerima: { nama: "Sari Wulandari", hubungan: "peserta" } },
    M2: { id: "M2", pasien: "Agus Setiadi", umur: 41, rs: "RS05", ditagih: 6, indikator: ["I4"], penerima: { nama: "Agus Setiadi", hubungan: "peserta" } }
  };

  /* ---------- model anomali anomali-v2 (disalin dari data-uji-konfirmasi/referensi-pola/anomali_demo.json) ----------

     Pasien ditelepon bila aturan ATAU model menandainya. dipilih: "keduanya", "aturan", atau "model".
     urut = id panggilan di API, penentu urutan bila hasil model sama.
     Rujukan per kunjungan dari klaim_sesi.csv (rujukan_fktp, perujuk_luar_wilayah); umur dari peserta.csv.
     Model menilai seberapa jarang pola tagihan di antara pasien seusia.
     Di 302 pasien demo: 21 dipilih keduanya, 9 hanya aturan, 2 hanya model (M1, M2). */

  const VERSI_ANOMALI = "anomali-v2";
  const PASIEN_HANYA_MODEL = 2;
  const ANOMALI = {
    S1: {"urut": "CALL-P-S1-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["4 sesi atau lebih dalam satu minggu: hanya 0,1% tagihan bulanan pasien 40–59 tahun.", "2 sesi atau lebih hari Minggu: hanya 0,2% tagihan bulanan pasien 40–59 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan, 4 sesi atau lebih dalam satu minggu, 2 sesi atau lebih hari Minggu, dan 3–5 bulan berturut-turut muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    S2: {"urut": "CALL-P-S2-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["1 sesi hari Minggu: hanya 0,4% tagihan bulanan pasien 60 tahun ke atas.", "9–12 sesi sebulan: hanya 2,3% tagihan bulanan pasien 60 tahun ke atas."], "gabungan": "Gabungan 9–12 sesi sebulan, 3 sesi dalam satu minggu, 1 sesi hari Minggu, dan 6 bulan atau lebih berturut-turut muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    S3: {"urut": "CALL-P-S3-2026-08", "dipilih": "aturan", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": 5.2497, "ditandai": false, "langka": false, "alasan": ["9–12 sesi sebulan: hanya 2,5% tagihan bulanan pasien 40–59 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan dan 6 bulan atau lebih berturut-turut muncul pada 0,5% tagihan bulanan fisioterapi pasien 40–59 tahun di data sampel BPJS 2023–2024."},
    S4: {"urut": "CALL-P-S4-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["1 sesi hari Minggu: hanya 0,4% tagihan bulanan pasien 60 tahun ke atas.", "9–12 sesi sebulan: hanya 2,3% tagihan bulanan pasien 60 tahun ke atas."], "gabungan": "Gabungan 9–12 sesi sebulan, 3 sesi dalam satu minggu, dan 1 sesi hari Minggu muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    S5: {"urut": "CALL-P-S5-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["1 sesi hari Minggu: hanya 0,6% tagihan bulanan pasien 18–39 tahun.", "9–12 sesi sebulan: hanya 1,7% tagihan bulanan pasien 18–39 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan, 3 sesi dalam satu minggu, dan 1 sesi hari Minggu muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    S6: {"urut": "CALL-P-S6-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["4 sesi atau lebih dalam satu minggu: hanya 0,1% tagihan bulanan pasien 40–59 tahun.", "1 sesi hari Minggu: hanya 0,4% tagihan bulanan pasien 40–59 tahun."], "gabungan": "Gabungan 5–8 sesi sebulan, 4 sesi atau lebih dalam satu minggu, dan 1 sesi hari Minggu muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    S8: {"urut": "CALL-P-S8-2026-08", "dipilih": "aturan", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": 5.2497, "ditandai": false, "langka": false, "alasan": ["9–12 sesi sebulan: hanya 2,5% tagihan bulanan pasien 40–59 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan dan 6 bulan atau lebih berturut-turut muncul pada 0,5% tagihan bulanan fisioterapi pasien 40–59 tahun di data sampel BPJS 2023–2024."},
    A1: {"urut": "CALL-P0007-2026-08", "dipilih": "aturan", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": 5.2871, "ditandai": false, "langka": false, "alasan": ["9–12 sesi sebulan: hanya 1,7% tagihan bulanan pasien 18–39 tahun.", "3 sesi dalam satu minggu: hanya 3,1% tagihan bulanan pasien 18–39 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan dan 3 sesi dalam satu minggu muncul pada 0,5% tagihan bulanan fisioterapi pasien 18–39 tahun di data sampel BPJS 2023–2024."},
    A2: {"urut": "CALL-P0010-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["1 sesi hari Minggu: hanya 0,4% tagihan bulanan pasien 60 tahun ke atas.", "9–12 sesi sebulan: hanya 2,3% tagihan bulanan pasien 60 tahun ke atas."], "gabungan": "Gabungan 9–12 sesi sebulan, 3 sesi dalam satu minggu, dan 1 sesi hari Minggu muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    A3: {"urut": "CALL-P0011-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["1 sesi hari Minggu: hanya 0,4% tagihan bulanan pasien 60 tahun ke atas.", "9–12 sesi sebulan: hanya 2,3% tagihan bulanan pasien 60 tahun ke atas."], "gabungan": "Gabungan 9–12 sesi sebulan, 3 sesi dalam satu minggu, 1 sesi hari Minggu, dan 3–5 bulan berturut-turut muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    R1: {"urut": "CALL-P0002-2026-08", "dipilih": "keduanya", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": null, "ditandai": true, "langka": true, "alasan": ["1 sesi hari Minggu: hanya kurang dari 0,1% tagihan bulanan pasien di bawah 18 tahun.", "4 sesi atau lebih dalam satu minggu: hanya 0,7% tagihan bulanan pasien di bawah 18 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan, 4 sesi atau lebih dalam satu minggu, dan 1 sesi hari Minggu muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024."},
    R2: {"urut": "CALL-P0003-2026-08", "dipilih": "aturan", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": 6.1271, "ditandai": false, "langka": false, "alasan": ["9–12 sesi sebulan: hanya 1,7% tagihan bulanan pasien 18–39 tahun.", "3 sesi dalam satu minggu: hanya 3,1% tagihan bulanan pasien 18–39 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan, 3 sesi dalam satu minggu, dan 3–5 bulan berturut-turut muncul pada 0,2% tagihan bulanan fisioterapi pasien 18–39 tahun di data sampel BPJS 2023–2024."},
    R3: {"urut": "CALL-P0012-2026-08", "dipilih": "aturan", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": 5.5549, "ditandai": false, "langka": false, "alasan": ["9–12 sesi sebulan: hanya 1,7% tagihan bulanan pasien 18–39 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan dan 6 bulan atau lebih berturut-turut muncul pada 0,4% tagihan bulanan fisioterapi pasien 18–39 tahun di data sampel BPJS 2023–2024."},
    R4: {"urut": "CALL-P0065-2026-08", "dipilih": "aturan", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": 6.2045, "ditandai": false, "langka": false, "alasan": ["9–12 sesi sebulan: hanya 1,6% tagihan bulanan pasien di bawah 18 tahun.", "3 sesi dalam satu minggu: hanya 2,4% tagihan bulanan pasien di bawah 18 tahun."], "gabungan": "Gabungan 9–12 sesi sebulan, 3 sesi dalam satu minggu, dan 3–5 bulan berturut-turut muncul pada 0,2% tagihan bulanan fisioterapi pasien di bawah 18 tahun di data sampel BPJS 2023–2024."},
    M1: {"urut": "CALL-P-M1-2026-08", "dipilih": "model", "rujukan": {"tanpa_rujukan": 0.5, "lintas_wilayah": 0.5}, "skor": 7.8631, "ditandai": true, "langka": false, "alasan": ["Sebagian dirujuk dari kab/kota lain: hanya 0,2% tagihan bulanan pasien 40–59 tahun.", "Sebagian kunjungan tanpa rujukan FKTP: hanya 0,6% tagihan bulanan pasien 40–59 tahun."], "gabungan": "Gabungan 5–8 sesi sebulan, 3–5 bulan berturut-turut, sebagian kunjungan tanpa rujukan FKTP, dan sebagian dirujuk dari kab/kota lain muncul pada kurang dari 0,1% tagihan bulanan fisioterapi pasien 40–59 tahun di data sampel BPJS 2023–2024."},
    M2: {"urut": "CALL-P-M2-2026-08", "dipilih": "model", "rujukan": {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}, "skor": 8.1243, "ditandai": true, "langka": false, "alasan": ["2 sesi atau lebih hari Minggu: hanya 0,2% tagihan bulanan pasien 40–59 tahun."], "gabungan": "Gabungan 5–8 sesi sebulan dan 2 sesi atau lebih hari Minggu muncul pada kurang dari 0,1% tagihan bulanan fisioterapi pasien 40–59 tahun di data sampel BPJS 2023–2024."}
  };

  /* Urutan baris antrean, sama dengan API: yang belum ditelepon menurut model anomali (pola langka dulu, lalu skor
     tertinggi, lalu id panggilan), kemudian riwayat. */
  const kunciAntre = (id) => {
    const a = ANOMALI[id];
    return [a.langka ? 0 : 1, a.skor == null ? 1 : 0, -(a.skor || 0), a.urut];
  };
  const bandingKunci = (x, y) => { for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1; return 0; };
  const URUTAN_ANTREAN = ["S1", "S2", "S3", "S4", "S5", "S6", "S8", "A1", "A2", "A3", "M1", "M2"]
    .sort((a, b) => bandingKunci(kunciAntre(a), kunciAntre(b)))
    .concat(["R1", "R2", "R3", "R4"]);

  /* ---------- aturan label (PRD F4) dan ringkasan RS (R5.4) ---------- */

  /* Toleransi salah ingat: selisih ditagih dan jumlah_maks sampai 2 sesi masih Sesuai. */
  const TOLERANSI = 2;

  function hitungLabel(j, ditagih) {
    if (j.status_panggilan === "tidak_terhubung") return "tidak_terhubung";
    if (j.status_panggilan === "menolak") return "menolak";
    if (j.hadir === false) return "tidak_sesuai";
    if (j.tanda_bahaya.length) return "tidak_sesuai";
    if (j.jumlah_maks == null || j.keyakinan === "rendah") return "tidak_yakin";
    if (ditagih - j.jumlah_maks > TOLERANSI) return "tidak_sesuai";
    return "sesuai";
  }

  const selisih = (p) => (p.jawaban.jumlah_maks == null ? null : Math.max(0, p.ditagih - p.jawaban.jumlah_maks));

  /* Status RS dari jumlah jawaban. Yang terjawab hanya Sesuai + Tidak sesuai; Tidak yakin,
     Tidak terhubung, dan Menolak tidak dihitung.
     - Belum cukup jawaban: terjawab < 3. RS yang belum diperiksa tidak boleh tampak "Normal" (audit S-01).
     - Perlu klarifikasi RS: tidak sesuai >= 3 DAN >= 10% dari terjawab (PRD R5.4).
     - Normal: selain itu.
     TODO: pindah ke aturan_v3.py di backend, lalu UI cukup membaca status dari API. */
  const RS_MIN_TERJAWAB = 3, RS_MIN_TIDAK_SESUAI = 3, RS_MIN_RASIO = 0.1;
  const STATUS_RS = { belum: "Belum cukup jawaban", klarifikasi: "Perlu klarifikasi RS", normal: "Normal" };

  function statusRs(c) {
    const terjawab = c.terjawab || 0, tidakSesuai = c.tidak_sesuai || 0;
    if (terjawab < RS_MIN_TERJAWAB) return STATUS_RS.belum;
    return tidakSesuai >= RS_MIN_TIDAK_SESUAI && tidakSesuai / terjawab >= RS_MIN_RASIO ? STATUS_RS.klarifikasi : STATUS_RS.normal;
  }

  /* Jarak ke ambang dalam satu kalimat pendek, untuk baris RS dan kartu bukti (audit S-02). */
  function progresRs(c) {
    const terjawab = c.terjawab || 0, tidakSesuai = c.tidak_sesuai || 0;
    const status = statusRs(c);
    if (status === STATUS_RS.belum) return terjawab + " dari " + RS_MIN_TERJAWAB + " jawaban minimal";
    if (status === STATUS_RS.normal) return tidakSesuai >= RS_MIN_TIDAK_SESUAI ? "di bawah 10% dari jawaban" : "baru " + tidakSesuai + " dari " + RS_MIN_TIDAK_SESUAI + " yang dibutuhkan";
    return "";
  }

  function ringkasanRs(daftarPanggilan) {
    return RS.map((r) => {
      const c = { id_rs: r.id, sesuai: 0, tidak_sesuai: 0, tidak_yakin: 0, tidak_terhubung: 0, menolak: 0 };
      daftarPanggilan.filter((p) => p.rs === r.id).forEach((p) => { c[p.label] += 1; });
      c.terjawab = c.sesuai + c.tidak_sesuai;
      c.rasio = c.terjawab ? c.tidak_sesuai / c.terjawab : 0;
      c.status = statusRs(c);
      return c;
    });
  }

  /* ---------- turunan dan uji mandiri ---------- */

  const SEMUA = Object.assign({}, SKENARIO, LATAR, MENGANTRE);
  Object.keys(SEMUA).forEach((id) => {
    Object.assign(SEMUA[id], {
      kunciPeserta: id,
      dipilih: ANOMALI[id].dipilih,
      anomali: Object.assign({ versi: VERSI_ANOMALI }, ANOMALI[id])
    });
  });

  const UJI = (function () {
    const salah = [];
    const cek = (kondisi, pesan) => { if (!kondisi) salah.push(pesan); };
    const harapan = { S1: "tidak_sesuai", S2: "tidak_sesuai", S3: "sesuai", S4: "tidak_yakin", S5: "tidak_terhubung", S6: "tidak_sesuai", S8: "menolak" };
    Object.keys(harapan).forEach((id) => {
      const p = SKENARIO[id];
      cek(p.label === harapan[id], id + ": label tertulis " + p.label + ", seharusnya " + harapan[id]);
      cek(hitungLabel(p.jawaban, p.ditagih) === p.label, id + ": aturan F4 menghasilkan " + hitungLabel(p.jawaban, p.ditagih));
      cek(p.tanggal.length === p.ditagih, id + ": daftar tanggal tidak sama dengan sesi ditagih");
    });
    Object.keys(LATAR).forEach((id) => {
      const p = LATAR[id];
      cek(hitungLabel(p.jawaban, p.ditagih) === p.label, id + ": aturan F4 menghasilkan " + hitungLabel(p.jawaban, p.ditagih));
      cek(p.tanggal.length === p.ditagih, id + ": daftar tanggal tidak sama dengan sesi ditagih");
    });
    cek(SKENARIO.S1.ditagih === 11 && SKENARIO.S1.jawaban.jumlah_maks === 3 && selisih(SKENARIO.S1) === 8, "S1 harus 11 ditagih, 3 versi peserta, selisih 8");
    cek(URUTAN_ANTREAN.every((id) => SEMUA[id]) && URUTAN_ANTREAN.indexOf("S7") < 0, "antrean memuat id yang tidak ada atau S7");
    cek(TIDAK_DIPICU[0].indikator.length < 2, "S7 harus kurang dari 2 indikator");
    cek(RS.reduce((a, r) => a + r.aktif, 0) === PASIEN_AKTIF && RS.reduce((a, r) => a + r.terpicu, 0) === PASIEN_TERPICU, "jumlah pasien aktif atau terpicu per RS tidak cocok");
    const sebelum = ringkasanRs(Object.keys(LATAR).map((id) => LATAR[id]))[0];
    const sesudah = ringkasanRs(Object.keys(LATAR).map((id) => LATAR[id]).concat([SKENARIO.S1]))[0];
    cek(sebelum.tidak_sesuai === 2 && sebelum.terjawab === 4 && sebelum.status === "Normal", "RS Melati sebelum S1 harus Normal 2 dari 4");
    cek(sesudah.tidak_sesuai === 3 && sesudah.terjawab === 5 && sesudah.status === "Perlu klarifikasi RS", "RS Melati sesudah S1 harus Perlu klarifikasi RS 3 dari 5");
    const rsKosong = ringkasanRs(Object.keys(LATAR).map((id) => LATAR[id])).filter((c) => c.terjawab === 0);
    cek(rsKosong.every((c) => c.status === STATUS_RS.belum), "RS tanpa jawaban harus Belum cukup jawaban, bukan Normal");
    cek(!/https?:|www\./i.test(pesanPemberitahuan(SKENARIO.S1) + pesanCadangan(SKENARIO.S5)), "pesan WA tidak boleh berisi tautan");
    if (salah.length) console.warn("Data v3 tidak konsisten dengan PRD:", salah);
    return salah;
  })();

  /* Uji mandiri model anomali: sumber pemilihan cocok dengan aturan (≥ 2 indikator) dan penanda model. */
  const UJI_ANOMALI = (function () {
    const salah = [];
    const cek = (kondisi, pesan) => { if (!kondisi) salah.push(pesan); };
    Object.keys(SEMUA).forEach((id) => {
      const p = SEMUA[id], aturan = p.indikator.length >= 2, model = p.anomali.ditandai;
      const harapan = aturan && model ? "keduanya" : aturan ? "aturan" : model ? "model" : null;
      cek(p.dipilih === harapan, id + ": dipilih " + p.dipilih + ", seharusnya " + harapan);
      cek(!/fraud|curang/i.test(JSON.stringify(p.anomali)), id + ": teks model anomali memuat kata terlarang");
    });
    cek(SEMUA.M1.dipilih === "model" && SEMUA.M2.dipilih === "model", "M1 dan M2 harus hanya dipilih model");
    cek(RS[0].funnel.position === "above_99_8" && RS.slice(1).every((r) => r.funnel.position === "within"), "hanya RS Melati di atas batas corong");
    const antre = URUTAN_ANTREAN.filter((id) => !LATAR[id]).map(kunciAntre);
    cek(antre.every((k, i) => i === 0 || bandingKunci(antre[i - 1], k) <= 0), "antrean harus terurut menurut model anomali");
    if (salah.length) console.warn("Model anomali data v3 tidak konsisten:", salah);
    return salah;
  })();

  global.DATA3 = {
    HARI_INI, VERIFIKATOR, BULAN, BULAN_PENDEK, PRESENTASI, NOMOR_PENELEPON, JEDA_PESAN_MENIT,
    LABEL, TINDAKAN, PILIHAN_TINDAKAN, SARAN, RETENSI, INDIKATOR, TOLERANSI,
    RS, PASIEN_AKTIF, PASIEN_TERPICU, PASIEN_HANYA_MODEL, VERSI_ANOMALI,
    SKENARIO, LATAR, MENGANTRE, SEMUA, URUTAN_ANTREAN, TIDAK_DIPICU,
    PENGATURAN_BAWAAN, PLACEHOLDER, KUNCI_WA, KUNCI_CADANGAN, BATAS_KARAKTER, pengaturan, ubahPengaturan, nomorPenelepon, jedaWa,
    isiTemplat, cekTemplat, cekNomor, cekAturanPanggilan, jumlahSms, hitungDipilih, dataPesan,
    pesanPemberitahuan, pesanCadangan, namaRs, hitungLabel, selisih, ringkasanRs, statusRs, progresRs, STATUS_RS, RS_MIN_TERJAWAB, UJI, UJI_ANOMALI
  };
})(window);
