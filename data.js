/* Vedika Autentik: data dan aturan prototipe.

   Berkas dan temuannya dibaca dari dataset/manifest.js (window.VEDIKA_BERKAS), yaitu
   ground truth yang sama dengan dataset uji. Label TIDAK disalin dari ground truth:
   label dihitung ulang dari temuan memakai aturan PRD bagian 9, lalu dicocokkan
   dengan label yang diharapkan sebagai uji mandiri saat halaman dimuat.

   Seluruh nama, nomor kartu, SEP, dan rumah sakit bersifat fiktif. */

(function (global) {
  "use strict";

  const MANIFEST = global.VEDIKA_BERKAS || [];

  /* ---------- aturan label (PRD bagian 9) ---------- */

  const LABEL = {
    prioritas: { nama: "Prioritas", urut: 0 },
    cek: { nama: "Perlu dicek", urut: 1 },
    ulang: { nama: "Scan ulang", urut: 2 },
    lolos: { nama: "Lolos", urut: 3 }
  };

  function hitungLabel(berkas) {
    if (berkas.kualitas_scan.status === "scan_ulang") return "ulang";
    const sinyal = berkas.temuan.filter((t) => t.kekuatan !== "info");
    if (!sinyal.length) return "lolos";
    const kuat = sinyal.filter((t) => t.kekuatan === "kuat").length;
    /* Tanda buatan AI hanya menaikkan urutan, tidak pernah jadi satu-satunya alasan Prioritas. */
    const selainAi = sinyal.filter((t) => t.cek !== "tanda_ai").length;
    if (selainAi && (kuat >= 2 || (kuat >= 1 && sinyal.length >= 2))) return "prioritas";
    return "cek";
  }

  /* ---------- nama pemeriksaan untuk verifikator ---------- */

  const CEK = {
    kualitas_scan: "Kualitas scan",
    kecocokan_klaim: "Cocok dengan klaim",
    berkas_kembar: "Berkas kembar",
    copy_paste: "Copy-paste dalam berkas",
    tempelan: "Tempelan dari berkas lain",
    suntingan: "Suntingan",
    tanda_ai: "Tanda buatan AI"
  };

  const KEKUATAN = { kuat: "Kuat", sedang: "Sedang", lemah: "Lemah", info: "Info" };

  /* ---------- tindakan verifikator (PRD bagian 9) ---------- */

  const TINDAKAN = {
    scanUlang: {
      nama: "Minta scan ulang",
      akibat: "Rumah sakit diminta mengunggah ulang lewat JKN Drive. Tidak dicatat sebagai temuan.",
      status: "Menunggu scan ulang"
    },
    klarifikasi: {
      nama: "Minta klarifikasi rumah sakit",
      akibat: "Rumah sakit diminta menjelaskan temuan. Klaim menunggu jawaban.",
      status: "Menunggu klarifikasi RS"
    },
    telaah: {
      nama: "Teruskan ke telaah lanjut",
      akibat: "Kasus diteruskan ke Tim Pencegahan Kecurangan JKN beserta laporan temuan.",
      status: "Diteruskan ke telaah lanjut",
      laporan: true
    },
    wajar: {
      nama: "Tutup sebagai wajar",
      akibat: "Klaim kembali ke verifikasi biasa: administrasi, koding, dan medis.",
      status: "Lanjut verifikasi biasa"
    }
  };

  const SARAN = { lolos: "wajar", ulang: "scanUlang", cek: "klarifikasi", prioritas: "telaah" };

  const ALASAN_SARAN = {
    lolos: "Semua pemeriksaan bersih dan isi berkas cocok dengan klaim.",
    ulang: "Berkas belum bisa dinilai. Hasil scan yang jelek bukan tanda kecurangan.",
    cek: "Ada sinyal yang masih mungkin kelalaian administrasi. Beri rumah sakit kesempatan menjelaskan.",
    prioritas: "Ada lebih dari satu sinyal kuat. Tim telaah perlu melihat kasus ini lebih dulu."
  };

  /* ---------- waktu dan antrean ---------- */

  const HARI_INI = "Selasa, 6 Oktober 2026";
  const VERIFIKATOR = { nama: "R. Santoso", peran: "Verifikator", kantor: "KC Jakarta Pusat" };

  /* Berkas yang sudah diperiksa sebelum demo dimulai. Lima berkas demo menyusul lewat unggahan. */
  const ANTREAN_AWAL = [
    ["VA-KMB-00", "29 Sep", "08.12"], ["VA-ASL-02", "30 Sep", "10.41"], ["VA-ASL-03", "1 Okt", "09.05"],
    ["VA-ASL-04", "1 Okt", "13.37"], ["VA-KMB-03", "2 Okt", "08.56"], ["VA-DST-02", "2 Okt", "14.20"],
    ["VA-DST-03", "5 Okt", "09.18"], ["VA-AI-02", "5 Okt", "11.02"], ["VA-AI-03", "5 Okt", "15.44"],
    ["VA-BRM-02", "6 Okt", "07.51"], ["VA-BRM-03", "6 Okt", "08.03"], ["VA-KMB-02", "6 Okt", "08.30"]
  ];

  const DEMO = [
    { id: "VA-ASL-01", judul: "Berkas asli" },
    { id: "VA-KMB-01", judul: "Berkas kembar" },
    { id: "VA-DST-01", judul: "Angka disunting" },
    { id: "VA-AI-01", judul: "Dibuat dengan AI" },
    { id: "VA-BRM-01", judul: "Scan buram" }
  ];

  /* ---------- ringkasan batch untuk beranda (angka agregat sintetis) ---------- */

  const BATCH = [
    { faskes: "RS Melati Sehat", kode: "0901R014", masuk: 412, selesai: 268, prioritas: 6, cek: 11, ulang: 9 },
    { faskes: "RS Cipta Medika", kode: "0901R027", masuk: 355, selesai: 301, prioritas: 2, cek: 7, ulang: 4 },
    { faskes: "RSU Bakti Mulia", kode: "0901R041", masuk: 287, selesai: 159, prioritas: 4, cek: 9, ulang: 12 },
    { faskes: "RS Harapan Bunda", kode: "0901R008", masuk: 198, selesai: 198, prioritas: 0, cek: 3, ulang: 2 }
  ];

  /* ---------- turunan per berkas ---------- */

  const PETA = {};
  MANIFEST.forEach((b) => {
    b.label = hitungLabel(b);
    b.jpg = "dataset/" + b.folder + "/" + b.berkas.jpg;
    b.pdf = "dataset/" + b.folder + "/" + b.berkas.pdf;
    PETA[b.id] = b;
  });

  const selisihLabel = MANIFEST.filter((b) => LABEL[b.label].nama !== b.label_diharapkan);
  if (selisihLabel.length) console.warn("Label tidak sesuai ground truth:", selisihLabel.map((b) => b.id));

  const tglPendek = (t) => String(parseInt(t.split("/")[0], 10));

  /* Hasil tiap langkah pemeriksaan, ditulis untuk dibaca verifikator dalam sekali lirik. */
  function langkah(b) {
    if (b.luar && !b.dariApi) {
      return [
        { nama: "Terima berkas", hasil: b.nama, status: "ok" },
        { nama: "Baca isi berkas", hasil: "Isi tidak terbaca oleh prototipe. Berkas ditandai Perlu dicek.", status: "henti" }
      ];
    }
    const isi = b.isi_lembar, klaim = b.klaim;
    const temuan = (cek) => b.temuan.filter((t) => t.cek === cek);
    const ulang = b.kualitas_scan.status === "scan_ulang";
    const tgl = isi.tanggal_sesi;
    const rentang = tgl.length ? tglPendek(tgl[0]) + "–" + tglPendek(tgl[tgl.length - 1]) + " " + isi.periode : "tanpa tanggal";
    const ttd = isi.kemiripan_ttd_rerata;

    const daftar = [
      { nama: "Terima berkas", hasil: "PDF 1 halaman dari JKN Drive", status: "ok" },
      { nama: "Cek kualitas scan", status: ulang ? "henti" : "ok",
        hasil: ulang ? b.kualitas_scan.catatan + " Pemeriksaan keaslian dihentikan." : b.kualitas_scan.catatan }
    ];
    if (ulang) return daftar;

    const cocok = temuan("kecocokan_klaim");
    const kembar = temuan("berkas_kembar").concat(temuan("tempelan"));
    const salin = temuan("copy_paste");
    const sunting = temuan("suntingan").concat(temuan("tanda_ai"));
    const pembuat = b.metadata_file.Creator || b.metadata_file.Producer || "tidak tercatat";
    const jenisSunting = sunting.map((t) => CEK[t.cek].toLowerCase()).filter((v, i, a) => a.indexOf(v) === i);

    daftar.push(
      { nama: "Baca isi berkas", hasil: isi.baris_terisi + " baris terisi, " + rentang, status: "ok" },
      { nama: "Cocokkan dengan klaim", status: cocok.length ? "temuan" : "ok",
        hasil: "Ditagih " + klaim.sesi_ditagih + " sesi, berkas mendukung " + (cocok.length ? isi.baris_asli : isi.baris_terisi) },
      { nama: "Cari berkas kembar", status: kembar.length ? "temuan" : "ok",
        hasil: kembar.length ? "Kembar dengan " + kembar[0].pasangan + " milik " + PETA[kembar[0].pasangan].klaim.peserta : "Tidak ada berkas serupa di arsip" },
      { nama: "Cari copy-paste", status: salin.length ? "temuan" : "ok",
        hasil: salin.length ? salin[0].kalimat.split(". ")[0]
          : ttd > 0.97 ? "Tanda tangan identik" : "Tanda tangan bervariasi wajar, kemiripan " + ttd.toFixed(2).replace(".", ",") },
      { nama: "Cari suntingan dan tanda AI", status: sunting.length ? "temuan" : "ok",
        hasil: sunting.length ? sunting.length + " sinyal: " + jenisSunting.join(", ") : "Tidak ada suntingan. Dibuat oleh " + pembuat }
    );
    return daftar;
  }

  /* Pesan PANDAWA (PRD bagian 10): netral, tanpa tautan, tanpa menyebut dugaan. */
  function pesanPeserta(b) {
    const nama = b.klaim.peserta.split(" ")[0];
    const sapaan = /^(Budi|Hartono|Agus|Bambang|Joko|Rudi|Fajar)$/.test(nama) ? "Bapak" : "Ibu";
    return {
      sapaan: sapaan,
      teks: "Halo " + sapaan + " " + nama + ". BPJS Kesehatan ingin memastikan layanan yang tercatat atas nama " + sapaan + ".",
      tanya: "Apakah " + sapaan + " menjalani fisioterapi di " + b.klaim.faskes + " sebanyak " + b.klaim.sesi_ditagih + " kali pada " + b.klaim.periode + "?",
      pilihan: "Balas 1 jika Ya, 2 jika Tidak pernah, atau 3 jika Hanya sebagian."
    };
  }

  const JAWABAN = {
    1: { teks: "Ya", akibat: "Peserta mengonfirmasi layanan. Temuan pada berkas tetap perlu ditelaah." },
    2: { teks: "Tidak pernah", akibat: "Peserta menyatakan tidak pernah menjalani layanan ini. Berkas naik ke urutan teratas." },
    3: { teks: "Hanya sebagian", akibat: "Peserta menyatakan hanya sebagian sesi dijalani. Berkas naik ke urutan teratas." }
  };

  /* Semua klaim yang memakai lembar yang sama, untuk peta hubungan berkas. */
  function keluargaBerkas(id) {
    const b = PETA[id];
    const kembar = b.temuan.find((t) => t.cek === "berkas_kembar");
    const akar = kembar ? kembar.pasangan : id;
    const anggota = Object.values(PETA).filter((x) => x.id === akar || x.temuan.some((t) => t.cek === "berkas_kembar" && t.pasangan === akar));
    return anggota.length > 1 ? { akar: akar, anggota: anggota } : null;
  }

  global.DATA = {
    MANIFEST, PETA, LABEL, CEK, KEKUATAN, TINDAKAN, SARAN, ALASAN_SARAN, JAWABAN,
    HARI_INI, VERIFIKATOR, ANTREAN_AWAL, DEMO, BATCH,
    hitungLabel, langkah, pesanPeserta, keluargaBerkas
  };
})(window);
