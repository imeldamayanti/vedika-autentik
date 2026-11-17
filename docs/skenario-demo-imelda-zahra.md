# Skenario demo panggilan langsung: Imelda dan Zahra

Dua panggilan sungguhan saat presentasi. Saat **Panggilan otomatis** dinyalakan, AI menelepon Imelda dulu, lalu Zahra.
Kedua skenario sengaja berbeda hasilnya: satu RS menagih dengan benar, satu RS menagih lebih.

| | Imelda | Zahra |
|---|---|---|
| Pasien | **Bapak Hartono** (72 th), ayah Imelda. Karena pasien lansia, yang ditelepon kontak keluarganya: Imelda (anak) | **Zahra** sendiri (44 th) |
| Klaim | RS Melati Sehat, Agustus 2026, **8 sesi**, termasuk libur 17 Agustus. Dipilih karena 3 kali seminggu dan hari libur | RS Melati Sehat, Agustus 2026, **11 sesi**, termasuk Minggu 16 dan libur 17 Agustus |
| Kenyataan | 8 kali: **RS benar** | 4 kali: **RS salah** |
| Yang dijawab | Awalnya "empat kali", AI cek ulang, lalu Imelda mengoreksi jadi **8** | "Empat kali", AI cek ulang, Zahra tetap **4** |
| Hasil yang diharapkan | **Sesuai**: "Ditagih 8 sesi, versi penerima 8-8 sesi. Masih dalam toleransi." | **Tidak sesuai**: "Ditagih 11 sesi, versi penerima paling banyak 4 sesi (selisih 7)." |
| Saran tindakan | Tutup kasus | Minta klarifikasi RS |

## Cek ulang yang tidak menggiring

Bila jumlah dari penerima jauh dari tagihan (lebih dari 2 sesi, ke arah mana pun), AI bertanya **satu kali**:

> "Apakah empat kali itu sudah pas, atau mau diingat-ingat sebentar?"

- AI hanya mengulang angka dari penerima sendiri. AI **tidak pernah** menyebut angka tagihan, tidak berkata "lebih" atau
  "kurang", dan tidak berkata jawabannya berbeda dari catatan.
- Apa pun jawaban berikutnya, berubah atau tetap, AI menerimanya dan tidak bertanya ulang lagi.
- Di demo, cek ulang muncul di **kedua** panggilan. Imelda mengoreksi, Zahra tetap. Ini yang perlu ditekankan ke juri:
  AI membantu penerima mengingat, bukan menggiring ke angka tagihan.

## Persiapan (15 menit sebelum tampil)

1. Laptop stasiun: hentikan proses lain di port 8000, jalankan `./stasiun.sh`, pastikan strip status hijau.
2. Website: klik **Mulai ulang demo**. Antrean hanya berisi Hartono (penerima Imelda) lalu Zahra. Panggilan otomatis mati.
3. **Pengaturan**: jam mulai 00:00, jam selesai 23:59, **Jeda WA ke telepon = 1** menit. AI menelepon 1 menit setelah
   pesan WA terkirim. Pakai menit itu untuk membuka "Lihat pesan" dan menjelaskan pemberitahuan WA. Jangan isi 0:
   pesan WA akan berbunyi "Dalam 0 menit kami akan menelepon".
4. HP Imelda dan Zahra: nada dering nyala, baterai cukup, sinyal bagus. Angkat dalam 20 detik.
   Bila tidak diangkat, AI mencoba lagi setelah 2 menit.
5. Menjawab di ruangan yang tenang, tanpa speaker, supaya suara AI tidak terekam balik.

## Aturan umum untuk penerima

- Tunggu AI selesai bicara, baru jawab. Jawab singkat, satu kalimat, jelas.
- Kalimat AI di bawah adalah perkiraan. Kata-katanya bisa sedikit berbeda, urutannya sama:
  pembuka, memastikan penerima, hadir atau tidak, berapa kali, cek ulang, tanggal libur, penutup.
- Jangan menyebut angka lain selain yang ada di naskah. Setelah mengoreksi, jawab dengan yakin, tanpa "kayaknya".
- Bila AI bertanya hal yang tidak ada di naskah, jawab sesuai inti skenario: Imelda "delapan kali, tanggal 17 tetap
  terapi", Zahra "empat kali, tidak datang tanggal 16 dan 17".
- Panggilan selesai sendiri setelah AI berkata "Terima kasih atas waktunya." Tidak perlu menutup duluan.

## Skenario 1: Imelda untuk Bapak Hartono (Sesuai, mengoreksi setelah cek ulang)

| Giliran | Pembicara | Ucapan |
|---|---|---|
| 1 | AI | Pembuka: asisten otomatis BPJS Kesehatan, panggilan direkam, bukan tagihan, tidak meminta NIK, OTP, rekening, atau uang. "Apakah saya terhubung dengan keluarga Bapak Hartono?" |
| 2 | Imelda | "Iya, saya Imelda, anaknya." |
| 3 | AI | "Apakah Bapak Hartono menjalani fisioterapi di RS Melati Sehat bulan Agustus?" |
| 4 | Imelda | "Iya, Bapak terapi di sana. Saya yang antar." |
| 5 | AI | "Kira-kira berapa kali Bapak Hartono terapi di bulan Agustus?" |
| 6 | Imelda | "Empat kali." |
| 7 | AI | Cek ulang: "Apakah empat kali itu sudah pas, atau mau diingat-ingat sebentar?" |
| 8 | Imelda | "Hmm, sebentar. Bukan, maaf. Delapan kali, saya ingat sekarang." |
| 9 | AI | "Baik, jadi delapan kali, ya?" |
| 10 | Imelda | "Iya, delapan kali." |
| 11 | AI | "Apakah Bapak Hartono terapi pada tanggal 17 Agustus?" |
| 12 | Imelda | "Iya, tanggal tujuh belas Bapak tetap terapi." |
| 13 | AI | Mengulang jawaban penting, berterima kasih, jawaban tidak memengaruhi layanan atau iuran. "Terima kasih atas waktunya." |

Yang ditunjukkan di layar:
- Antrean: penerima "Imelda (anak)", karena pasien lansia dihubungi lewat keluarga.
- Transkrip berjalan: cek ulang AI tidak menyebut angka 8.
- Kartu hasil: **Sesuai**, saran **Tutup kasus**. Sistem tidak menuduh RS yang menagih dengan benar,
  walaupun klaimnya dipilih aturan dan model.

## Skenario 2: Zahra (Tidak sesuai, tetap pada jawabannya)

| Giliran | Pembicara | Ucapan |
|---|---|---|
| 1 | AI | Pembuka yang sama. "Apakah benar saya bicara dengan Ibu Zahra?" |
| 2 | Zahra | "Iya, saya sendiri." |
| 3 | AI | "Apakah Ibu menjalani fisioterapi di RS Melati Sehat bulan Agustus?" |
| 4 | Zahra | "Iya, saya terapi di sana." |
| 5 | AI | "Kira-kira berapa kali Ibu terapi di bulan Agustus?" |
| 6 | Zahra | "Empat kali." |
| 7 | AI | Cek ulang: "Apakah empat kali itu sudah pas, atau mau diingat-ingat sebentar?" |
| 8 | Zahra | "Iya, sudah pas. Empat kali." |
| 9 | AI | "Apakah Ibu terapi pada tanggal 16 dan 17 Agustus?" |
| 10 | Zahra | "Nggak, tanggal enam belas sama tujuh belas saya di rumah." |
| 11 | AI | Mengulang jawaban penting, berterima kasih. "Terima kasih atas waktunya." |

Yang ditunjukkan di layar:
- AI menerima jawaban "empat kali" tanpa mendesak lagi.
- Kartu hasil: **Tidak sesuai**, selisih 7 sesi, tanggal libur dibantah, saran **Minta klarifikasi RS**.
- Ringkasan RS: RS Melati Sehat bertambah satu jawaban tidak sesuai.

## Bila tidak sesuai rencana

| Kejadian | Yang dilakukan |
|---|---|
| HP tidak diangkat | AI mencoba lagi setelah 2 menit. Bila dua kali tidak diangkat, hasilnya Tidak ada jawaban dan antrean lanjut ke Zahra. |
| AI tidak melakukan cek ulang | Lanjutkan saja dengan angka akhir: Imelda langsung bilang "Eh, bukan, delapan kali." Hasilnya tetap Sesuai. |
| AI salah dengar atau mengulang pertanyaan | Jawab lagi dengan kalimat yang sama, lebih pelan. |
| Penerima diam lebih dari 10 detik | AI bertanya apakah penerima masih tersambung, lalu mengulang pertanyaan. Jawab seperti biasa. |
| Hasil berbeda dari harapan | Jelaskan apa adanya: verifikator yang memutuskan, AI hanya mencatat jawaban. |
| Perlu mengulang dari awal | Klik **Mulai ulang demo**, lalu nyalakan Panggilan otomatis. Nomor HP dan Pengaturan tidak berubah. |
