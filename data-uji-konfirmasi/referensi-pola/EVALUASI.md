# Evaluasi skor pola (`pola-v1`)

Dibuat otomatis oleh `ai-service/scripts/train_pattern_model.py` pada 2026-11-17. Jangan disunting tangan.

Angka di bawah dilaporkan per tingkat bukti dan tidak digabung. Tier A = agregat data sampel BPJS 2024 (nyata). Tier B = data sintetis (metode dan demo), bukan bukti kinerja di lapangan.

## Cek kecocokan fitur (sebelum melatih)

Pangsa bulan-pasien di bin teratas: RS demo jujur (RS02 sampai RS05, Agustus 2026, Tier B) dibanding nasional 2024 (Tier A). Fitur dibuang bila pangsa demo lebih dari 3 kali nasional.

| Fitur | Bin teratas | Demo jujur | Nasional | Keputusan |
|---|---|---|---|---|
| `sesi` | 13+ | 0,00% | 0,12% | dipakai |
| `maks_minggu` | 4 | 0,00% | 0,13% | dipakai |
| `ahad_libur` | 2+ | 0,00% | 0,13% | dipakai |
| `episode` | 7+ | 0,00% | 14,26% | dipakai |

Fitur yang dibuang: tidak ada. Fitur model: sesi, maks_minggu, ahad_libur, episode.

## Tier B (sintetis, hanya uji kewajaran metode)

- AUC normal vs pelanggaran buatan pada 20% data tahan: **0,978** (50.000 + 50.000 sampel).
- Kelas pelanggaran dibuat dari aturan yang sama dengan yang diuji, jadi angka ini hanya menunjukkan model mempelajari manipulasi tersebut. Ini bukan akurasi deteksi.

## Tier A (agregat nasional 2024)

- Ambang `ambang_tinggi` = **0,898** (persentil berbobot 98,5 skor atas histogram nasional).
- Pangsa bulan-pasien nasional dengan skor ≥ ambang: **1,61%**.
- Histogram bertingkat: sel di bawah 10 baris digabung ke rentang yang lebih kasar (batas rentang tepat di ambang aturan), dan hanya sisa yang tetap di bawah 10 baris di tingkat terkasar yang disembunyikan (0,10% bobot). Bulan-pasien dengan sesi hari Minggu (0,44% nasional) ikut masuk kelas normal lewat sel kasar. Pangsa nasional sebenarnya di antara kira-kira 1,6% dan 1,7%.

Rata-rata skor per kombinasi aturan (sel histogram yang tidak tersembunyi):

| Kombinasi | Rata-rata skor | Pangsa bobot |
|---|---|---|
| - | 0,065 | 78,70% |
| I1 | 0,042 | 0,65% |
| I1+I2 | 0,744 | 0,79% |
| I1+I2+I3 | 0,882 | 0,27% |
| I1+I3 | 0,095 | 0,36% |
| I2 | 0,869 | 1,68% |
| I2+I3 | 0,946 | 0,29% |
| I3 | 0,144 | 16,83% |
| I3+I4 | 0,909 | 0,11% |
| I4 | 0,833 | 0,32% |

### Perilaku pada data nyata

Model diterapkan ke semua 22.457 bulan-pasien nyata 2024 di laptop (data mentah tidak di-commit; hanya agregat di `ai-service/data/reference/pola-2024/perilaku-nyata.json`). Ini perilaku, bukan akurasi: data sampel tidak punya label kecurangan, dan kelas normal model berasal dari data yang sama.

- Pola tidak biasa: **1,82%** bulan-pasien (berbobot); pemicu aturan 1,88%.
- Per bulan (tak berbobot): 1,6% sampai 2,3%.
- Terpicu aturan dan pola tidak biasa: 168 (0,59%). Terpicu tetapi skor di bawah ambang: 278 (1,29%).
- Pola tidak biasa tanpa pemicu aturan: 270 (1,23%), yaitu I2 saja 200, I4 saja 70.
- Dari 446 bulan-pasien terpicu, 11 tampil dengan skor 1,00.
- 216 kelompok RS sejenis (≥ 30 bulan-pasien): 143 tanpa satu pun pola tidak biasa; 10% kelompok teratas memuat 66% bulan-pasien berpola tidak biasa.

## Tier B (data demo vs `kunci_kebenaran_2026-08.csv`)

302 bulan-pasien Agustus 2026, 26 di antaranya digelembungkan (selisih ditagih dan sebenarnya lebih dari 2). Kunci kebenaran hanya dibaca di evaluasi offline ini.

- AUC skor pola: **0,990**.
- AUC `jumlah_indikator` (pembanding): **0,974**.
- Pemicu aturan (≥ 2 indikator, 30 bulan-pasien): presisi **0,833**, recall **0,962**.
- Presisi@30 skor pola: **0,833**.
- Skor ≥ ambang: 23 bulan-pasien, 21 di antaranya digelembungkan.
- Digelembungkan tetapi tidak terpicu aturan: 1; di antaranya **0** berskor ≥ ambang (tampil sebagai informasi, tidak ditelepon).

## Koefisien

Intersep: 4,0541. Skor = logistik(intersep + jumlah koefisien bin yang aktif).

| Fitur | Bin | Koefisien |
|---|---|---|
| `sesi` | 1 | -5,8398 |
| `sesi` | 2 | -1,2085 |
| `sesi` | 3 | 0,7694 |
| `sesi` | 4 | 0,9261 |
| `sesi` | 5 | 0,7958 |
| `sesi` | 6 | 1,2820 |
| `sesi` | 7 | 1,9108 |
| `sesi` | 8 | 2,1367 |
| `sesi` | 9 | 0,1667 |
| `sesi` | 10 | 0,6143 |
| `sesi` | 11 | 0,9020 |
| `sesi` | 12 | 0,7546 |
| `sesi` | 13+ | 0,3073 |
| `maks_minggu` | 1 | -4,0270 |
| `maks_minggu` | 2 | -3,6165 |
| `maks_minggu` | 3 | 0,3762 |
| `maks_minggu` | 4 | 4,8318 |
| `maks_minggu` | 5 | 5,8049 |
| `maks_minggu` | 6+ | 0,1481 |
| `ahad_libur` | 0 | -3,8272 |
| `ahad_libur` | 1 | 3,3454 |
| `ahad_libur` | 2+ | 3,9993 |
| `episode` | 1 | 0,2918 |
| `episode` | 2 | -0,1613 |
| `episode` | 3 | -0,0374 |
| `episode` | 4 | 0,4817 |
| `episode` | 5 | 0,7675 |
| `episode` | 6 | 1,2694 |
| `episode` | 7+ | 0,9058 |

## Batasan

- Skor berarti "mirip pola manipulasi yang dikenal, dibanding pola nasional 2024". Skor bukan peluang kecurangan dan bukan putusan.
- Kelas normal adalah data nyata apa adanya, jadi bisa memuat manipulasi yang tidak terdeteksi.
- Di data nyata 2024 tidak ada daftar libur, jadi `ahad_libur` dan I4 hanya menghitung hari Minggu.
- Sel kasar dipecah ke bin halus memakai marginal nasional, dengan anggapan fitur saling bebas di dalam sel itu. Sesi hari Minggu di data nyata hanya muncul di sel kasar dengan paling banyak 2 sesi seminggu; Minggu bersama 3 sesi atau lebih seminggu tetap tersembunyi.
- Data sampel tidak memuat identitas RS dan tidak memuat bulan sebelum Januari 2024.
- Skor hanya mengurutkan antrean. Pemicu panggilan, label, saran, dan status RS tetap dari aturan.
