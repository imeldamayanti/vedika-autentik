# Evaluasi skor pola (`pola-v1`)

Dibuat otomatis oleh `ai-service/scripts/train_pattern_model.py` pada 2026-11-16. Jangan disunting tangan.

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

- AUC normal vs pelanggaran buatan pada 20% data tahan: **0,981** (50.000 + 50.000 sampel).
- Kelas pelanggaran dibuat dari aturan yang sama dengan yang diuji, jadi angka ini hanya menunjukkan model mempelajari manipulasi tersebut. Ini bukan akurasi deteksi.

## Tier A (agregat nasional 2024)

- Ambang `ambang_tinggi` = **0,878** (persentil berbobot 98,5 skor atas histogram nasional).
- Pangsa bulan-pasien nasional dengan skor ≥ ambang: **1,56%**.
- Histogram dipakai setelah sel di bawah 10 baris disembunyikan (1,53% bobot). Sel yang tersembunyi kebanyakan ada di ekor, termasuk semua bulan-pasien dengan sesi hari Minggu (0,44% nasional), yang skornya pasti di atas ambang. Pangsa nasional sebenarnya karena itu di antara kira-kira 1,5% dan 3,1%.

Rata-rata skor per kombinasi aturan (sel histogram yang tidak tersembunyi):

| Kombinasi | Rata-rata skor | Pangsa bobot |
|---|---|---|
| - | 0,064 | 79,84% |
| I1 | 0,048 | 0,66% |
| I1+I2 | 0,798 | 0,37% |
| I1+I2+I3 | 0,929 | 0,19% |
| I1+I3 | 0,106 | 0,37% |
| I2 | 0,911 | 1,27% |
| I2+I3 | 0,964 | 0,22% |
| I3 | 0,144 | 17,07% |

## Tier B (data demo vs `kunci_kebenaran_2026-08.csv`)

300 bulan-pasien Agustus 2026, 25 di antaranya digelembungkan (selisih ditagih dan sebenarnya lebih dari 2). Kunci kebenaran hanya dibaca di evaluasi offline ini.

- AUC skor pola: **0,997**.
- AUC `jumlah_indikator` (pembanding): **0,996**.
- Pemicu aturan (≥ 2 indikator, 30 bulan-pasien): presisi **0,833**, recall **1,000**.
- Presisi@30 skor pola: **0,833**.
- Skor ≥ ambang: 23 bulan-pasien, 22 di antaranya digelembungkan.
- Digelembungkan tetapi tidak terpicu aturan: 0; di antaranya **0** berskor ≥ ambang (tampil sebagai informasi, tidak ditelepon).

## Koefisien

Intersep: 5,8516. Skor = logistik(intersep + jumlah koefisien bin yang aktif).

| Fitur | Bin | Koefisien |
|---|---|---|
| `sesi` | 1 | -4,0941 |
| `sesi` | 2 | -2,9065 |
| `sesi` | 3 | 0,7908 |
| `sesi` | 4 | 1,0000 |
| `sesi` | 5 | 0,9606 |
| `sesi` | 6 | 1,3800 |
| `sesi` | 7 | 2,0408 |
| `sesi` | 8 | 2,2464 |
| `sesi` | 9 | 0,3675 |
| `sesi` | 10 | 0,8207 |
| `sesi` | 11 | 1,1417 |
| `sesi` | 12 | 1,1231 |
| `sesi` | 13+ | 0,6757 |
| `maks_minggu` | 1 | -3,9313 |
| `maks_minggu` | 2 | -3,5190 |
| `maks_minggu` | 3 | 0,8358 |
| `maks_minggu` | 4 | 6,2674 |
| `maks_minggu` | 5 | 5,8796 |
| `maks_minggu` | 6+ | 0,0141 |
| `ahad_libur` | 0 | -6,0635 |
| `ahad_libur` | 1 | 5,8161 |
| `ahad_libur` | 2+ | 5,7941 |
| `episode` | 1 | 0,5271 |
| `episode` | 2 | 0,0035 |
| `episode` | 3 | 0,1749 |
| `episode` | 4 | 0,8864 |
| `episode` | 5 | 1,2284 |
| `episode` | 6 | 1,5548 |
| `episode` | 7+ | 1,1715 |

## Batasan

- Skor berarti "mirip pola manipulasi yang dikenal, dibanding pola nasional 2024". Skor bukan peluang kecurangan dan bukan putusan.
- Kelas normal adalah data nyata apa adanya, jadi bisa memuat manipulasi yang tidak terdeteksi.
- Di data nyata 2024 tidak ada daftar libur, jadi `ahad_libur` dan I4 hanya menghitung hari Minggu.
- Semua sel histogram yang memuat sesi hari Minggu berisi kurang dari 10 baris dan tersembunyi. Kelas normal karenanya tidak punya sesi hari Minggu, dan koefisien `ahad_libur` sepenuhnya berasal dari manipulasi buatan.
- Data sampel tidak memuat identitas RS dan tidak memuat bulan sebelum Januari 2024.
- Skor hanya mengurutkan antrean. Pemicu panggilan, label, saran, dan status RS tetap dari aturan.
