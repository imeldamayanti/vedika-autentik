-- Skema Supabase Vedika Autentik. Salinan migrasi "skema_awal_vedika_autentik"
-- (project vedika-autentik). Kontrak: docs/api-contract.md, bagian "Skema database".
-- RLS aktif tanpa policy: hanya API (service role) yang boleh mengakses.

create table public.berkas (
  id text primary key,
  sep text,
  kode_faskes text not null,
  faskes text,
  nama_file text not null,
  path_storage text,
  sha256 text,
  jumlah_halaman int not null default 1,
  status text not null default 'diproses' check (status in ('diproses','selesai','gagal')),
  ringkasan text,
  klaim jsonb,
  isi_lembar jsonb,
  kualitas_scan jsonb,
  metadata_file jsonb,
  ukuran int[],
  sidik_jari jsonb,
  sidik_jari_halaman text,
  sidik_jari_teks text,
  versi_mesin text,
  versi_aturan text,
  galat text,
  diunggah_oleh text,
  waktu_unggah timestamptz not null default now(),
  waktu_selesai timestamptz
);
create index berkas_kode_faskes_idx on public.berkas (kode_faskes);
create index berkas_status_idx on public.berkas (status);
create index berkas_sidik_halaman_idx on public.berkas (sidik_jari_halaman);
create index berkas_waktu_unggah_idx on public.berkas (waktu_unggah desc);

create table public.hasil_cek (
  id bigint generated always as identity primary key,
  berkas_id text not null references public.berkas(id) on delete cascade,
  cek text not null check (cek in ('kualitas_scan','kecocokan_klaim','berkas_kembar','copy_paste','tempelan','suntingan','tanda_ai')),
  kekuatan text not null check (kekuatan in ('kuat','sedang','lemah','info')),
  skor numeric,
  region int[],
  area jsonb,
  pasangan_id text references public.berkas(id) on delete set null,
  kalimat text not null,
  versi_mesin text,
  versi_aturan text
);
create index hasil_cek_berkas_idx on public.hasil_cek (berkas_id);

create table public.label (
  berkas_id text primary key references public.berkas(id) on delete cascade,
  label text not null check (label in ('prioritas','cek','ulang','lolos')),
  alasan text,
  waktu timestamptz not null default now()
);
create index label_label_idx on public.label (label);

create table public.konfirmasi (
  berkas_id text primary key references public.berkas(id) on delete cascade,
  pertanyaan text not null,
  jawaban smallint check (jawaban in (1,2,3)),
  waktu_kirim timestamptz not null default now(),
  waktu_jawab timestamptz
);

create table public.keputusan (
  id bigint generated always as identity primary key,
  berkas_id text not null references public.berkas(id) on delete cascade,
  verifikator text not null,
  tindakan text not null check (tindakan in ('scanUlang','klarifikasi','telaah','wajar')),
  catatan text,
  waktu timestamptz not null default now(),
  dibatalkan boolean not null default false
);
create index keputusan_berkas_idx on public.keputusan (berkas_id);

create table public.akses_log (
  id bigint generated always as identity primary key,
  waktu timestamptz not null default now(),
  pengguna text not null,
  aksi text not null,
  berkas_id text references public.berkas(id) on delete set null
);
create index akses_log_berkas_idx on public.akses_log (berkas_id);

-- Antrean kerja. Worker mengambil dengan: select ... for update skip locked.
create table public.job (
  id bigint generated always as identity primary key,
  berkas_id text not null references public.berkas(id) on delete cascade,
  status text not null default 'menunggu' check (status in ('menunggu','jalan','selesai','gagal')),
  percobaan int not null default 0,
  galat text,
  dibuat timestamptz not null default now(),
  diambil timestamptz,
  selesai timestamptz
);
create index job_menunggu_idx on public.job (dibuat) where status = 'menunggu';

alter table public.berkas enable row level security;
alter table public.hasil_cek enable row level security;
alter table public.label enable row level security;
alter table public.konfirmasi enable row level security;
alter table public.keputusan enable row level security;
alter table public.akses_log enable row level security;
alter table public.job enable row level security;
