# Uji dengan HP nyata

Daftar periksa untuk tim, dijalankan dengan HP saluran dan HP penguji (`NOMOR_PENGUJI`). Belum pernah dijalankan:
seluruh kode di tiket ini diuji dengan HP palsu (`SALURAN_ADB=palsu`) dan uji unit. Pasang dulu menurut
[STASIUN.md](STASIUN.md).

Isi kotak `[ ]` dengan `L` (lulus) atau `G` (gagal). Untuk tiap yang gagal, catat apa yang terjadi.

| | |
|---|---|
| Tanggal | |
| Penguji | |
| HP saluran (model, Android) | |
| Operator SIM | |
| Mode audio | speaker / kabel |
| Mode Meta | log / teks / template |

## A. Hari pertama: pemeriksaan ADB (tanpa sistem)

Jalankan di terminal laptop stasiun, HP tercolok. Ganti `08xx` dengan `NOMOR_PENGUJI`.

| # | Langkah | Yang diharapkan | Hasil |
|---|---|---|---|
| A1 | `adb devices` | Tepat satu baris, status `device` | [ ] |
| A2 | `adb shell getprop ro.product.model` dan `adb shell getprop gsm.sim.state` | Model HP; keadaan SIM memuat `READY` | [ ] |
| A3 | `adb shell dumpsys telephony.registry \| grep mCallState` | Semua `mCallState=0` (satu baris per SIM) | [ ] |
| A4 | `adb shell am start -a android.intent.action.CALL -d tel:08xx` | HP langsung menelepon, tanpa pemilih SIM dan tanpa dialog; HP penguji berdering | [ ] |
| A5 | Selama berdering dan setelah diangkat: ulangi A3 | Ada `mCallState=2` | [ ] |
| A6 | `adb shell input keyevent KEYCODE_ENDCALL` | Panggilan putus; A3 kembali semua `0` | [ ] |
| A7 | Ulangi A6 saat tidak ada panggilan | Tidak terjadi apa-apa yang mengganggu (catat bila layar HP mati atau terkunci) | [ ] |
| A8 | Telepon lagi (A4), angkat, nyalakan speakerphone HP saluran. Bicara di HP penguji | Suara penguji terdengar jelas dari speaker HP saluran | [ ] |
| A9 | Bicara ke arah HP saluran dari jarak laptop | Terdengar jelas di HP penguji | [ ] |
| A10 | Tutup, telepon lagi (A4) | Catat: apakah speakerphone masih menyala tanpa disentuh? | [ ] |
| A11 | Telepon (A4), tutup dari HP penguji | A3 kembali `0` dalam 2 detik | [ ] |
| A12 | Telepon (A4), jangan diangkat sampai putus sendiri | Catat berapa detik sampai putus, dan apa yang terdengar (nada sibuk, pengumuman) | [ ] |
| A13 | Pesan uji Meta (mode `teks`/`template` saja): dari halaman API Setup Meta kirim pesan contoh ke HP penguji | Pesan masuk di WhatsApp HP penguji | [ ] |

Bila A4 gagal (muncul pemilih SIM, dialog izin, atau layar terkunci), perbaiki dulu menurut STASIUN.md bagian 2.

## B. Stasiun menyala

| # | Langkah | Yang diharapkan | Hasil |
|---|---|---|---|
| B1 | `./stasiun.sh` | Empat baris pemeriksaan (HP, SIM, Audio, Meta), lalu "Stasiun siap." | [ ] |
| B2 | Jendela "Stasiun saluran Vedika" | Stasiun: "siap, menunggu tugas"; HP dan SIM terisi; Audio menyebut mode dan perangkat | [ ] |
| B3 | Website → Autentik | Strip status hijau/biru; chip "Saluran telepon siap (model HP)" | [ ] |
| B4 | Cabut kabel USB, tunggu 10 detik | Website: "Saluran telepon belum siap: HP tidak terhubung ke laptop" | [ ] |
| B5 | Colok lagi | Kembali siap dalam 10 detik, tanpa menyentuh laptop | [ ] |
| B6 | Tutup jendela halaman agen, tunggu 35 detik | Website: "Saluran telepon terputus sejak HH.MM". Jalankan ulang `./stasiun.sh` | [ ] |

## C. Skenario S1–S8

Persiapan: jam panggilan aktif (atau lebarkan jam, lihat STASIUN.md bagian 4), lalu tekan **Mulai ulang demo**.
Mode otomatis menyala sendiri dan antrean berjalan berurutan S1, S2, S3, S4, S5, S6, S8; tidak perlu menekan apa pun.
Penguji memegang HP penguji dan menjawab menurut naskah (`data-uji-konfirmasi/skenario_uji.json`, kalimat lengkap di
`data-uji-konfirmasi/transkrip_uji/`). Tunggu AI selesai bicara sebelum menjawab.

Yang diperiksa di tiap panggilan terjawab:

- pesan WA masuk sebelum telepon (mode `teks`/`template`), tanpa tautan, isinya Lampiran B;
- telepon masuk sekitar `jeda_wa_menit` setelahnya, dari nomor SIM stasiun;
- AI menyebut dirinya asisten otomatis, bilang panggilan direkam dan bukan tagihan; tidak meminta NIK, OTP, rekening,
  atau uang; tidak memakai kata "curang" atau "fraud";
- setelah AI berpamitan, telepon ditutup sendiri oleh stasiun dalam beberapa detik;
- website pindah ke kartu bukti dengan label yang diharapkan.

| Skenario | Peran penguji | Yang diucapkan penguji | Label diharapkan | Ringkasan RS sesudahnya | Hasil |
|---|---|---|---|---|---|
| **S1** Andi Pratama, RS Melati Sehat, ditagih 11 | Andi Pratama (peserta) | Akui terapi di RS Melati Sehat bulan Agustus. Jumlah: "Tiga kali, awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan." Hari Minggu/17 Agustus: "Nggak pernah. Hari Minggu kan tutup." | **Tidak sesuai**, kartu 11 vs 3, selisih 8. Rekaman dan transkrip tersimpan | RS01: 3 tidak sesuai dari 5 terjawab → **Perlu klarifikasi RS** (sebelumnya 2 dari 4, Normal) | [ ] |
| **S2** Siti Rahmawati, RS Melati Sehat, ditagih 10 | Dewi, anak Ibu Siti | Ibu memang terapi di sana, saya yang mengantar. Jumlah: "Dua kali aja. Tapi waktu itu Ibu disuruh tanda tangan di beberapa lembar sekaligus, katanya buat jadwal berikutnya." Minggu 23 Agustus: "Nggak, Minggu kami di rumah." | **Tidak sesuai** + tanda bahaya "Tanda tangan tanpa layanan" | RS01: 4 dari 6, Perlu klarifikasi RS | [ ] |
| **S3** Budi Santoso, RSU Bakti Mulia, ditagih 9 | Budi Santoso (peserta) | "Iya betul. Rutin, seminggu dua kali. Agustus berarti sembilan atau sepuluh kali." (AI tidak bertanya tanggal libur.) | **Sesuai**. Rekaman tersimpan 30 hari | RS02: 0 dari 1, Normal. RS01 tetap 4 dari 6 | [ ] |
| **S4** Karti Lestari, RS Melati Sehat, ditagih 9 | Bayu, anak Ibu Karti | Jumlah: "Waduh, saya kurang tahu persis. Mungkin lima atau enam kali, yang nganter kadang adik saya." Minggu 16 Agustus: "Kurang tahu juga, Mbak." | **Tidak yakin**. Tanpa rekaman dan transkrip | RS01: tidak yakin 1; tetap 4 dari 6 (tidak dihitung) | [ ] |
| **S5** Joko Prasetyo, RS Cempaka Asri, ditagih 10 | Joko Prasetyo | **Jangan angkat** panggilan pertama. Tunggu sekitar 2 menit, **jangan angkat** panggilan kedua. Cek WhatsApp. | **Tidak terhubung** setelah 2 percobaan; chat cadangan (pilihan 1–6) masuk di WhatsApp; layar: "Chat cadangan terkirim" | RS03: tidak terhubung 1, terjawab 0, Normal | [ ] |
| **S6** Slamet Riyadi, RS Melati Sehat, ditagih 8 | Slamet Riyadi, bicara santai berlogat | Jumlah: "Iya mas, cuma dua kali kok. Wong kakinya udah enakan, ya udah nggak balik lagi." Minggu 9 Agustus: "Lho, Minggu ya libur to mas." | **Tidak sesuai**, 8 vs 2, selisih 6 | RS01: 5 dari 7, Perlu klarifikasi RS | [ ] |
| **S7** Rina Marlina, RSU Nusa Sejahtera | (tidak ada panggilan) | Pastikan Rina Marlina **tidak muncul** di antrean (hanya 1 indikator) dan HP penguji tidak ditelepon untuknya | Tidak pernah masuk antrean | Tidak berubah | [ ] |
| **S8** Hendra Wijaya, RS Kenanga Medika, ditagih 10 | Hendra Wijaya | Setelah salam pembuka: "Ini penipuan ya? BPJS kok nelpon." Setelah AI menjelaskan: "Nggak, saya nggak mau. Nanti saya telepon 165 aja." | **Menolak**. Tanpa rekaman. AI menyebut Care Center 165 dan tidak memaksa | RS05: menolak 1, terjawab 0, Normal | [ ] |

Ringkasan RS akhir (harus sama dengan `data-uji-konfirmasi/expected_ringkasan_rs.json`):

| RS | Sesuai | Tidak sesuai | Tidak yakin | Tidak terhubung | Menolak | Terjawab | Status | Hasil |
|---|---|---|---|---|---|---|---|---|
| RS01 Melati Sehat | 2 | 5 | 1 | 0 | 0 | 7 | Perlu klarifikasi RS | [ ] |
| RS02 Bakti Mulia | 1 | 0 | 0 | 0 | 0 | 1 | Normal | [ ] |
| RS03 Cempaka Asri | 0 | 0 | 0 | 1 | 0 | 0 | Normal | [ ] |
| RS05 Kenanga Medika | 0 | 0 | 0 | 0 | 1 | 0 | Normal | [ ] |

Setelah S8 antrean lanjut ke pasien bukan skenario. Tekan **Jeda** atau matikan Panggilan otomatis bila uji selesai,
supaya HP penguji tidak terus ditelepon.

## D. Pengumuman operator dan kasus tepi

Tekan Mulai ulang demo, lalu matikan Panggilan otomatis supaya hanya pasien yang didahulukan yang ditelepon.

| # | Langkah | Yang diharapkan | Hasil |
|---|---|---|---|
| D1 | **Nomor mati.** Matikan HP penguji (atau mode pesawat). Tekan Dahulukan pada satu pasien | Operator memutar pengumuman ("Nomor yang Anda tuju…"). Panggilan **tidak pernah** berstatus Tersambung, AI tidak membacakan pembuka, stasiun menutup telepon, baris menjadi "Coba lagi m:ss". Log halaman agen: "pengumuman operator, bukan jawaban". Catat kalimat pengumuman persisnya | [ ] |
| D2 | Biarkan percobaan ke-2 juga kena pengumuman | Tidak terhubung, chat cadangan dikirim | [ ] |
| D3 | **Ditolak.** Dahulukan pasien lain, tekan tolak di HP penguji | Percobaan gagal dalam beberapa detik (bukan menunggu 40 detik); "Coba lagi m:ss" | [ ] |
| D4 | **Penerima menutup di tengah.** Angkat, jawab satu pertanyaan, tutup telepon | Dalam 2 detik stasiun berhenti, hasil diunggah, kartu bukti muncul (label mengikuti isi percakapan, biasanya Tidak yakin) | [ ] |
| D5 | **Penerima diam.** Angkat, bilang "Halo", lalu diam | Sekitar 10 detik setelah AI selesai bicara, stasiun menutup telepon dan mengunggah hasil | [ ] |
| D6 | **Batalkan.** Saat panggilan berjalan lebih dari 60 detik, atau setelah menutup jendela halaman agen, tekan "Batalkan panggilan" di website | Konfirmasi muncul; setelah disetujui panggilan dihitung satu percobaan gagal, HP saluran menutup telepon, antrean lanjut | [ ] |
| D7 | **Macet.** Tutup jendela halaman agen di tengah panggilan, jangan sentuh website | Dalam 30 detik: "Saluran telepon terputus". Setelah 5 menit panggilan dilepas sendiri (log: "Terputus, dilepas otomatis") | [ ] |
| D8 | **Dahulukan.** Tekan Dahulukan pada pasien di tengah daftar saat panggilan lain berjalan | Pasien itu pindah ke urutan berikutnya dan ditelepon setelah panggilan sekarang selesai | [ ] |
| D9 | **Di luar jam.** Kembalikan jam ke 09.00–17.00 dan uji di luar jam itu | Strip: "Di luar jam panggilan (09.00–17.00 WIB)…"; tidak ada panggilan keluar | [ ] |
| D10 | **Meta gagal.** Isi `META_WA_TOKEN` dengan nilai salah, mode `teks`, jalankan satu panggilan | Layar: "Pesan WA gagal terkirim"; telepon tetap masuk setelah jeda | [ ] |

## E. Yang dicatat

- [ ] Tangkapan layar: strip status (siap, sedang menelepon, terputus), layar panggilan dengan transkrip, kartu bukti S1
      (11 vs 3), ringkasan RS akhir, jendela halaman agen.
- [ ] Tangkapan layar WhatsApp HP penguji: pesan pemberitahuan dan chat cadangan.
- [ ] Foto susunan HP dan laptop (jarak, arah speaker).
- [ ] Untuk tiap panggilan terjawab: jeda dari "Halo" penguji sampai AI mulai bicara (detik), dan apakah AI pernah
      memotong atau menjawab suaranya sendiri.
- [ ] Kalimat pengumuman operator yang terdengar (D1, A12), persis seperti di transkrip halaman agen.

### Akurasi transkrip (R3.6, batas lulus ≥ 90%)

Untuk tiap skenario terjawab, bandingkan transkrip di kartu bukti (atau halaman agen untuk label tanpa transkrip)
dengan yang benar-benar diucapkan penguji. Hitung per field kunci, bukan per kata:

| Skenario | Penerima benar | Hadir benar | Jumlah sesi benar | Keyakinan benar | Tanggal libur benar | Tanda bahaya benar | Benar / 6 |
|---|---|---|---|---|---|---|---|
| S1 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| S2 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| S3 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| S4 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| S6 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| S8 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

Akurasi = jumlah benar / 36. Lulus bila ≥ 90% (paling banyak 3 field salah) **dan** label ketujuh skenario sama dengan
yang diharapkan. Bila gagal karena suara (bukan pembaca jawaban), ulangi dengan mode kabel dan catat keduanya.

## F. Kesimpulan

| | |
|---|---|
| Bagian A lulus semua | ya / tidak |
| Label S1–S8 sesuai | /8 |
| Ringkasan RS akhir sesuai | ya / tidak |
| Akurasi field kunci | % |
| Yang perlu diperbaiki | |
