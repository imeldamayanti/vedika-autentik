/* Klien API Vedika Autentik (Kontrak A, docs/api-contract.md).

   Dipakai untuk berkas di luar dataset. Berkas dataset tetap lewat jalur demo (manifest.js), jadi
   demo berjalan walau API mati. Bila API atau mesin tidak sehat, pemanggil jatuh ke perilaku lama.

   Alamat API: window.VEDIKA_API_BASE bila diisi; di localhost http://localhost:8000; di produksi
   kosong (satu origin, Vercel meneruskan /api/* ke API). */

(function (global) {
  "use strict";

  const lokal = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  const BASE = global.VEDIKA_API_BASE != null ? global.VEDIKA_API_BASE : (lokal ? "http://localhost:8000" : "");
  const url = (p) => BASE + p;
  const IDS = /^(VA-(?:ASL|KMB|DST|AI|BRM)-\d{2})/i;
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));

  /* Sehat berarti API, database, dan mesin semuanya ok. Selain itu, pakai jalur cadangan. */
  async function sehat() {
    try {
      const r = await fetch(url("/api/v1/kesehatan"), { signal: AbortSignal.timeout(2500) });
      if (!r.ok) return false;
      const j = await r.json();
      return j.api === "ok" && j.db === "ok" && j.mesin === "ok";
    } catch (e) { return false; }
  }

  async function unggah(file, kodeFaskes) {
    const f = new FormData();
    f.append("file", file);
    f.append("kode_faskes", kodeFaskes);
    const r = await fetch(url("/api/v1/berkas"), { method: "POST", body: f });
    if (!r.ok) throw new Error("unggah " + r.status);
    return (await r.json()).id;
  }

  async function ambil(id) {
    const r = await fetch(url("/api/v1/berkas/" + id));
    if (!r.ok) throw new Error("ambil " + r.status);
    return r.json();
  }

  async function tungguSelesai(id, batasMs) {
    const mulai = Date.now();
    for (;;) {
      const d = await ambil(id);
      if (d.status !== "diproses") return d;
      if (Date.now() - mulai > (batasMs || 60000)) throw new Error("batas waktu");
      await tunggu(700);
    }
  }

  /* Pratinjau: gambar dari API bila ada, foto yang diunggah, atau gambar dataset bila namanya dikenal. */
  function jpgDataset(nama) {
    const m = IDS.exec(nama || "");
    const b = m && global.DATA.PETA[m[1].toUpperCase()];
    return b && !b.luar ? b.jpg : null;
  }

  /* Mengubah detail API menjadi bentuk yang sama dengan entri dataset/manifest.js, supaya layar yang ada tidak berubah. */
  function keBentukFe(d, opsi) {
    const nama = (d.berkas && d.berkas.nama) || (opsi.file && opsi.file.name) || d.id;
    const isi = d.isi_lembar || null;
    const klaim = d.klaim || {
      peserta: (isi && isi.nama) || nama.replace(/\.[^.]+$/, ""), sep: (isi && isi.no_sep) || "Tidak terbaca",
      faskes: opsi.faskes || "–", periode: (isi && isi.periode) || "–", sesi_ditagih: 0, nilai_klaim: 0,
      no_kartu: (isi && isi.no_kartu) || "–", kode_faskes: opsi.kode || "–", layanan: "Fisioterapi rawat jalan"
    };
    const gambarLokal = opsi.file && /^image\//.test(opsi.file.type) ? URL.createObjectURL(opsi.file) : null;
    return {
      id: d.id, luar: true, dariApi: d.status === "selesai", nama: nama,
      jpg: (d.berkas && d.berkas.jpg ? url(d.berkas.jpg) : null) || gambarLokal || jpgDataset(nama),
      pdf: d.berkas && d.berkas.pdf ? url(d.berkas.pdf) : null,
      ukuran: d.ukuran || [1240, 1754], berkas: { pdf: nama },
      ringkasan: d.ringkasan || "", klaim: klaim, isi_lembar: isi,
      kualitas_scan: d.kualitas_scan || { status: "baik", catatan: "Berkas diterima." },
      temuan: (d.temuan || []).map((t) => ({ cek: t.cek, kekuatan: t.kekuatan, kalimat: t.kalimat, region: t.region || null, area: t.area, pasangan: t.pasangan, skor: t.skor })),
      metadata_file: d.metadata_file || {}, label: d.label
    };
  }

  /* Menunggu hasil, mendaftarkannya ke DATA.PETA beserta berkas kerabatnya (kembar, pasangan tempelan). */
  async function muatKeFe(id, opsi) {
    const d = await tungguSelesai(id);
    const b = keBentukFe(d, opsi);
    global.DATA.PETA[id] = b;
    const kerabat = new Set((d.keluarga ? d.keluarga.anggota : []).concat((d.temuan || []).map((t) => t.pasangan).filter(Boolean)));
    await Promise.all([...kerabat].filter((x) => x !== id && !global.DATA.PETA[x]).map(async (x) => {
      try {
        const dx = await ambil(x);
        global.DATA.PETA[x] = keBentukFe(dx, { faskes: dx.klaim && dx.klaim.faskes });
      } catch (e) { /* kerabat gagal dimuat: ditangani di bawah */ }
    }));
    b.temuan.forEach((t) => { if (t.pasangan && !global.DATA.PETA[t.pasangan]) delete t.pasangan; });
    return id;
  }

  global.API = { sehat, unggah, muatKeFe, url };
})(window);
