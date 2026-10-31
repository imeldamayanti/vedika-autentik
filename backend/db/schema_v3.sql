-- Skema v3 Vedika Autentik: konfirmasi suara (PRD v3.0, F1-F5).
-- Tambahan, bukan pengganti: tabel v2 (berkas, hasil_cek, label, ...) di schema.sql tidak disentuh.
-- RLS aktif tanpa policy: hanya API (service role) yang boleh mengakses.
-- Idempoten: aman dijalankan berulang (if not exists, on conflict do nothing, enable RLS berulang tidak berefek).
-- Kolom baru di tabel yang sudah diterapkan ke database harus lewat alter table ... add column if not exists,
-- karena create table if not exists tidak mengubah tabel yang sudah ada.

create table if not exists public.rumah_sakit (
  id_rs text primary key,
  nama_rs text not null,
  tipe text,
  wilayah text
);

create table if not exists public.peserta (
  id_peserta text primary key,
  nama text not null,
  tanggal_lahir date,
  umur int,
  jenis_kelamin text check (jenis_kelamin in ('L','P')),
  no_hp text,
  kontak_keluarga text,
  hubungan_keluarga text,
  no_hp_keluarga text,
  -- R1.3: ya jika usia >= 60 atau < 13 dan ada kontak keluarga
  hubungi_keluarga boolean not null default false,
  catatan text
);

create table if not exists public.klaim_sesi (
  id_klaim text primary key,
  id_peserta text not null references public.peserta(id_peserta),
  id_rs text not null references public.rumah_sakit(id_rs),
  tanggal date not null,
  kode_cbg text,
  kode_icd10 text,
  diagnosis text,
  tarif int
);
create index if not exists klaim_sesi_pasien_idx on public.klaim_sesi (id_peserta, id_rs, tanggal);
create index if not exists klaim_sesi_rs_bulan_idx on public.klaim_sesi (id_rs, tanggal);

create table if not exists public.libur_nasional (
  tanggal date primary key,
  nama text not null
);

-- F1: hasil indikator per pasien, per RS, per bulan layanan (aturan: tools/aturan.py)
create table if not exists public.indikator_bulanan (
  id_peserta text not null references public.peserta(id_peserta),
  id_rs text not null references public.rumah_sakit(id_rs),
  bulan text not null check (bulan ~ '^[0-9]{4}-[0-9]{2}$'),
  sesi_ditagih int not null,
  maks_sesi_seminggu int not null,
  i1_lebih_8_sebulan boolean not null,
  i2_3x_seminggu boolean not null,
  i3_episode_6_bulan boolean not null,
  i4_hari_libur boolean not null,
  tanggal_libur date[] not null default '{}',
  jumlah_indikator int not null,
  dipicu boolean not null,
  primary key (id_peserta, id_rs, bulan)
);
create index if not exists indikator_dipicu_idx on public.indikator_bulanan (bulan) where dipicu;

-- F2-F5: satu baris per pasien-RS-bulan yang ditelepon. Antrean = indikator dipicu yang belum punya baris di sini.
create table if not exists public.panggilan (
  id text primary key,
  id_peserta text not null references public.peserta(id_peserta),
  id_rs text not null references public.rumah_sakit(id_rs),
  bulan_layanan text not null,
  sesi_ditagih int not null,
  penerima text not null check (penerima in ('peserta','keluarga')),
  nama_penerima text,
  hubungan text,
  status text not null default 'antre'
    check (status in ('antre','wa_terkirim','menelepon','tersambung','merekam','membaca_jawaban','selesai','tidak_terhubung')),
  percobaan int not null default 0,
  jeda_wa_menit int not null default 1,
  jawaban jsonb,                       -- keluaran pembaca jawaban (skema di README data uji)
  label text check (label in ('Sesuai','Tidak sesuai','Tidak yakin','Tidak terhubung','Menolak')),
  alasan text,
  rekaman_path text,
  transkrip jsonb,                     -- [{waktu, pembicara, teks}]
  waktu_wa timestamptz,
  waktu_mulai timestamptz,
  waktu_selesai timestamptz,
  -- R5.5: Sesuai = selesai + 30 hari; Tidak sesuai disimpan sampai klarifikasi selesai (null); lainnya tanpa rekaman
  hapus_pada timestamptz,
  sumber text not null default 'panggilan' check (sumber in ('panggilan','sintetis-riwayat')),
  -- Nomor yang ditelepon. Prototipe: NOMOR_PENGUJI dari .env, bukan nomor peserta atau keluarga.
  no_tujuan text,
  -- R3.5: setelah 2 percobaan gagal, chat WA berisi pilihan jumlah sesi dikirim (S5); jawaban_chat = balasan peserta.
  chat_cadangan_terkirim boolean not null default false,
  jawaban_chat text,
  -- R4.3: pesan galat jika JSON pembaca jawaban tidak valid setelah diulang (label jadi Tidak yakin).
  galat_pembaca text,
  -- R5.5: terisi saat klarifikasi RS selesai; memicu penghapusan rekaman dan transkrip berlabel Tidak sesuai.
  klarifikasi_selesai_pada timestamptz,
  dibuat timestamptz not null default now(),
  unique (id_peserta, id_rs, bulan_layanan)
);
-- Kolom susulan, lewat alter supaya database yang sudah menerapkan versi sebelumnya ikut mendapatkannya.
-- R3.5: percobaan ke-2 baru boleh diambil agen setelah waktu ini (percobaan ke-1 gagal + jeda_percobaan_menit).
alter table public.panggilan add column if not exists coba_lagi_setelah timestamptz;
-- R1.5: "Telepon sekarang", diambil agen di giliran berikutnya walau mode otomatis mati.
alter table public.panggilan add column if not exists prioritas boolean not null default false;
create index if not exists panggilan_status_idx on public.panggilan (status);
create index if not exists panggilan_rs_idx on public.panggilan (id_rs, bulan_layanan);

-- R2.2, R3.5, R3.7: jejak status panggilan bertahap (jeda WA, tiap percobaan, jam di layar Panggilan).
create table if not exists public.panggilan_log (
  id bigint generated always as identity primary key,
  panggilan_id text not null references public.panggilan(id) on delete cascade,
  status text not null
    check (status in ('antre','wa_terkirim','menelepon','tersambung','merekam','membaca_jawaban','selesai','tidak_terhubung')),
  waktu timestamptz not null default now(),
  percobaan int,
  catatan text
);
create index if not exists panggilan_log_panggilan_idx on public.panggilan_log (panggilan_id);
create index if not exists panggilan_log_waktu_idx on public.panggilan_log (waktu);

-- R5.3: siapa, kapan, apa, alasan. Alasan wajib jika bukan mengikuti saran.
create table if not exists public.keputusan_panggilan (
  id bigint generated always as identity primary key,
  panggilan_id text not null references public.panggilan(id) on delete cascade,
  verifikator text not null,
  tindakan text not null check (tindakan in ('tutup_kasus','minta_klarifikasi_rs','teruskan_pk_jkn')),
  ikut_saran boolean not null,
  alasan text,
  waktu timestamptz not null default now(),
  check (ikut_saran or coalesce(btrim(alasan), '') <> '')
);
create index if not exists keputusan_panggilan_idx on public.keputusan_panggilan (panggilan_id);

-- R1.5 dan R2.2: mode otomatis, jeda WA, jeda percobaan.
create table if not exists public.pengaturan (
  kunci text primary key,
  nilai jsonb not null
);
insert into public.pengaturan (kunci, nilai) values
  ('mode_otomatis', 'false'::jsonb),
  ('jam_mulai', '"09:00"'::jsonb),
  ('jam_selesai', '"17:00"'::jsonb),
  ('jeda_wa_menit', '1'::jsonb),
  ('jeda_percobaan_menit', '2'::jsonb)
on conflict do nothing;

alter table public.rumah_sakit enable row level security;
alter table public.peserta enable row level security;
alter table public.klaim_sesi enable row level security;
alter table public.libur_nasional enable row level security;
alter table public.indikator_bulanan enable row level security;
alter table public.panggilan enable row level security;
alter table public.panggilan_log enable row level security;
alter table public.keputusan_panggilan enable row level security;
alter table public.pengaturan enable row level security;
