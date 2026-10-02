**PRODUCT REQUIREMENT DOCUMENT  ·  BPJS KESEHATAN HEALTHKATHON 2026**

**Vedika Autentik**

*Lengkap belum tentu asli.*

ditenagai PRAMANA

Fitur tambahan di alur verifikasi klaim BPJS Kesehatan yang memeriksa **keaslian** berkas klaim fisioterapi: apakah berkasnya dipakai ulang, disunting, atau dibuat dengan AI, dan apakah isinya cocok dengan jumlah sesi yang ditagih.

| Item | Keterangan |
| :---- | :---- |
| **Kategori lomba** | Efisiensi Risiko pada Fasilitas Kesehatan |
| **Modus yang disasar** | Cloning (No. 5), phantom billing (No. 6), dan menagihkan tindakan yang tidak dilakukan (No. 14), menurut Permenkes 16/2019 |
| **Layanan MVP** | Fisioterapi rawat jalan |
| **Posisi** | Fitur baru di sistem yang sudah ada (JKN Drive dan Vedika), bukan aplikasi baru |
| **Versi** | v2.1 · 30 September 2026 · draf untuk proposal |
| **Data prototipe** | Sintetis dan formulir relawan. Tidak ada data peserta JKN yang nyata. |

| Satu kalimat untuk juri Berkas yang lengkap belum tentu asli. Vedika Autentik memeriksa keaslian berkas klaim sebelum klaim dibayar, lalu menunjukkan buktinya ke verifikator. |
| :---- |

# **1\. Ringkasan**

Hari ini rumah sakit mengunggah berkas klaim dalam bentuk PDF hasil scan ke JKN Drive. Verifikator BPJS memeriksa kelengkapan berkas dan kesesuaian kodenya. Belum ada alat yang memeriksa apakah berkas itu **asli**.

Celah ini sudah terbukti dipakai. Pada temuan KPK di tiga rumah sakit, 3.269 dari 4.341 tagihan fisioterapi tidak didukung rekam medis. Modusnya termasuk pemalsuan dokumen dan menyalin klaim pasien lain.

Vedika Autentik memeriksa setiap berkas fisioterapi begitu masuk, lalu memberi satu dari empat label: **Lolos**, **Scan ulang**, **Perlu dicek**, atau **Prioritas**. Setiap label disertai buktinya. Keputusan tetap di tangan verifikator.

## **Yang berubah untuk verifikator**

* Tidak perlu membuka ratusan PDF satu per satu untuk mencari yang janggal. Berkas yang perlu dicek sudah ada di urutan atas.

* Temuan bisa langsung dilihat: dua berkas berdampingan, bagian yang disunting diberi warna, dan satu kalimat yang menjelaskan masalahnya.

* Untuk kasus yang paling kuat, peserta ditanya langsung lewat WhatsApp resmi BPJS, sehingga ada saksi dari luar rumah sakit.

# **2\. Masalah**

## **2.1 Alur hari ini**

1. Rumah sakit melayani pasien, mengisi lembar bukti pelayanan fisioterapi, dan meminta tanda tangan pasien di setiap sesi.

2. Rumah sakit men-scan berkas dan mengunggahnya ke **JKN Drive**.

3. Verifikator BPJS memeriksa kelengkapan berkas dan kesesuaian koding dalam alur **Vedika** (Verifikasi Digital Klaim).

4. Klaim yang lengkap dibayar.

Yang belum diperiksa: apakah lembar Bu Siti sama persis dengan lembar Pak Budi, apakah angka di berkas pernah diedit, dan apakah berkasnya dibuat di aplikasi desain atau generator gambar AI. Membandingkan ribuan berkas lintas pasien dengan mata manusia hampir tidak mungkin.

## **2.2 Data pendukung**

| Fakta | Angka | Sumber |
| :---- | :---- | :---- |
| Tagihan fisioterapi di tiga RS yang diperiksa KPK, BPJS, Kemenkes, dan BPKP | 4.341 tagihan, hanya 1.072 didukung rekam medis. 3.269 (75,3%) diduga fiktif. | Itjen Kemenkes, Juli 2024 |
| Kerugian dari tiga RS tersebut | Rp35,1 miliar dari 25.011 kasus. Modusnya termasuk pemalsuan dokumen dan menyalin klaim pasien lain. | detikHealth, September 2024 |
| Cara data pasien diperoleh | KTP dan nomor peserta dikumpulkan lewat acara bakti sosial, lalu dipakai untuk klaim fiktif. Ada juga fisioterapi 2 kali yang ditagih 10 kali. | Katadata, Juli 2024 |
| Potensi fraud layanan kesehatan | Sekitar 10% belanja kesehatan, setara kira-kira Rp20 triliun per tahun (estimasi KPK) | Tempo, Januari 2025 |
| Volume berkas | Sekitar 650.000 berkas klaim per hari, sekitar 5% terindikasi berpotensi fraud (menurut pemberitaan, mengutip Direktur TI BPJS) | Bloomberg Technoz, Juni 2026 |
| Rekomendasi KPK | Perkuat verifikasi berlapis dan verifikasi pasca-klaim | Itjen Kemenkes, Juli 2024 |

## **2.3 Kenapa mendesak sekarang**

* **Dokumen palsu makin murah dibuat.** Maret 2025, generator gambar ChatGPT terbukti bisa membuat struk palsu yang realistis, lengkap dengan lipatan dan noda kertas. Formulir fisioterapi tidak lebih sulit dipalsukan daripada struk.

* **Industri asuransi sudah merasakan dampaknya.** Allianz UK dan LV= melaporkan kenaikan 300% klaim yang memuat gambar dan dokumen hasil manipulasi AI. Survei ACFE dan SAS (2026) menemukan hanya 7% profesional anti-fraud yang merasa organisasinya lebih dari cukup siap menghadapi fraud berbasis AI.

* **Verifikasi JKN masih bergantung pada berkas scan.** Peralihan ke klaim elektronik berbasis rekam medis elektronik (RME) baru dimulai Agustus 2026, dengan target "No RME, No Claim" secara nasional pada 2027\. Selama masa transisi, dan untuk audit arsip bertahun-tahun ke belakang, berkas scan tetap menjadi bukti utama.

# **3\. Posisi produk: fitur baru di sistem yang sudah ada**

Vedika Autentik tidak menambah aplikasi baru untuk rumah sakit dan tidak meminta dokumen baru. Fitur ini membaca berkas yang sudah diunggah, lalu menaruh hasilnya di layar yang sudah dipakai verifikator.

| Sistem yang ada | Fungsinya sekarang | Peran untuk Vedika Autentik |
| :---- | :---- | :---- |
| **V-Claim (BPJS)** | Cek kepesertaan dan menerbitkan SEP | Sumber nomor SEP dan identitas klaim |
| **E-Klaim INA-CBG (Kemenkes)** | Mengubah diagnosis dan tindakan menjadi tarif, lalu membuat file klaim | Sumber jumlah sesi dan nilai yang ditagih |
| **JKN Drive (BPJS)** | Rumah sakit mengunggah berkas klaim PDF, petugas BPJS membukanya untuk verifikasi | **Pemicu.** Setiap berkas baru langsung diperiksa. |
| **Vedika (BPJS)** | Alur verifikasi klaim oleh verifikator BPJS | **Tempat hasil dipakai.** Label dan kartu bukti membantu verifikator saat memeriksa klaim. |

## **Nama dan slogan**

| Bagian | Isi | Alasan |
| :---- | :---- | :---- |
| **Nama fitur** | Vedika Autentik | Verifikator sudah mengenal Vedika sebagai alur verifikasi klaim. Kata "Autentik" langsung menjelaskan fungsinya: memeriksa keaslian berkas, dan satu kata ini mencakup keenam pemeriksaan. |
| **Slogan** | Lengkap belum tentu asli. | Merangkum masalah utamanya. Pemeriksaan sekarang memastikan berkas lengkap, belum memastikan berkas asli. |
| **Mesin di baliknya** | PRAMANA | Nama tim dan nama mesin analisis. "Pramana" berarti alat bukti yang sah. |

Nama ini sengaja bernada netral. Sebagian besar rumah sakit jujur dan merupakan mitra BPJS, jadi nama fitur tidak boleh terdengar menuduh.

# **4\. Pengguna**

| Pengguna | Kebutuhan | Yang didapat dari Vedika Autentik |
| :---- | :---- | :---- |
| **Verifikator klaim BPJS** di kantor cabang (pengguna utama) | Memeriksa banyak berkas per hari tanpa melewatkan yang palsu | Antrean berkas yang sudah diurutkan dan kartu bukti per kasus |
| **Tim Pencegahan Kecurangan JKN** dan auditor | Bukti yang bisa dipertanggungjawabkan untuk telaah lanjut | Laporan temuan PDF lengkap dengan potongan bukti dan jejak keputusan |
| **Peserta JKN** (pendukung) | Namanya tidak dipakai untuk klaim palsu | Satu pertanyaan konfirmasi di WhatsApp resmi BPJS untuk kasus berprioritas |
| **Rumah sakit** | Klaim yang jujur tidak ikut tertahan | Tidak ada pekerjaan tambahan. Hanya diminta scan ulang atau klarifikasi kalau ada temuan. |

# **5\. Ruang lingkup MVP**

| Masuk lingkup | Di luar lingkup |
| :---- | :---- |
| Fisioterapi rawat jalan. Pada temuan KPK, 75% tagihan fisioterapi yang diperiksa diduga fiktif. Berkasnya juga berulang dan formatnya relatif seragam. Satu jenis berkas: lembar bukti pelayanan fisioterapi bertanda tangan pasien. File PDF, JPG, atau PNG. Cek kualitas scan, lalu enam pemeriksaan keaslian: kecocokan dengan klaim, berkas kembar, copy-paste, tempelan dari berkas lain, suntingan, dan tanda buatan AI. Konfirmasi peserta untuk kasus berlabel Prioritas. | Menolak atau menahan pembayaran secara otomatis. Menyatakan sebuah klaim sebagai fraud. Mengenali siapa orang yang menulis tanda tangan. Layanan lain seperti hemodialisis dan katarak (masuk roadmap). Pemeriksaan obat dan resep. Data peserta JKN yang nyata. |

# **6\. Alur utama**

| 1 Unggah berkas | 2 Cek kualitas scan | 3 Baca isi | 4 Periksa keaslian | 5 Beri label | 6 Tanya peserta | 7 Keputusan verifikator |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |

| Langkah | Siapa | Yang terjadi |
| :---- | :---- | :---- |
| **1\. Unggah** | Rumah sakit | Mengunggah berkas fisioterapi ke JKN Drive seperti biasa. Tidak ada langkah baru. |
| **2\. Cek kualitas scan** | Sistem | Berkas yang buram, miring, terpotong, atau halamannya kurang diberi label **Scan ulang**, lengkap dengan bagian yang tidak terbaca. Berkas ini tidak dinilai curang. |
| **3\. Baca isi** | Sistem | Membaca nama, nomor kartu, SEP, fasilitas kesehatan, tanggal tiap sesi, dan jumlah baris yang terisi. |
| **4\. Periksa** | Sistem | Menjalankan enam pemeriksaan: kecocokan dengan klaim, berkas kembar, copy-paste, tempelan dari berkas lain, suntingan, dan tanda buatan AI (lihat bagian 8). |
| **5\. Beri label** | Sistem | Lolos, Perlu dicek, atau Prioritas, masing-masing dengan alasan satu kalimat. |
| **6\. Tanya peserta** | Sistem | Khusus label Prioritas: satu pertanyaan netral dikirim lewat PANDAWA, WhatsApp resmi BPJS. |
| **7\. Putuskan** | Verifikator | Membuka kartu bukti dan memilih tindakan. Semua keputusan tercatat. |

# **7\. Fitur MVP**

| No | Fitur | Yang dilakukan | Contoh hasil | Prioritas |
| :---- | :---- | :---- | :---- | :---- |
| F1 | **Terima berkas** | Menerima PDF, JPG, dan PNG. Di demo lewat unggah manual, di produksi diambil otomatis dari JKN Drive. | \- | Wajib |
| F2 | **Cek kualitas scan** | Mengukur ketajaman, kemiringan, dan bagian yang terpotong | "Kolom tanda tangan baris 6–8 terpotong. Minta scan ulang." | Wajib |
| F3 | **Baca isi berkas** | Membaca teks dan tabel dengan OCR, memakai template letak kolom | "8 baris terisi, 4–28 Agustus 2026" | Wajib |
| F4 | **Cocokkan klaim dengan berkas** | Membandingkan jumlah dan tanggal sesi di klaim dengan isi berkas | "Ditagih 8 sesi, berkas hanya mendukung 5." | Wajib |
| F5 | **Cari berkas kembar** | Membuat sidik jari berkas setelah kolom identitas dan tanggal ditutup, lalu mencarinya di semua berkas lain | "Isi berkas 97% sama dengan berkas Pak Budi, SEP berbeda." | Wajib |
| F6 | **Cari bagian copy-paste** | Membandingkan baris layanan, stempel, dan tanda tangan di dalam satu berkas dan antarberkas | "8 tanda tangan identik sampai tingkat piksel." | Wajib |
| F7 | **Cari suntingan dan tanda buatan AI** | Memetakan area yang diedit, membaca metadata file, dan memeriksa ciri hasil scan | "Angka 8 di kolom jumlah sesi terdeteksi ditempel." | Wajib |
| F8 | **Konfirmasi peserta** | Mengirim pertanyaan netral lewat PANDAWA, khusus label Prioritas | "Peserta menjawab: hanya sebagian." | Sebaiknya |
| F9 | **Antrean dan kartu bukti** | Mengurutkan berkas menurut label, lalu menampilkan berkas berdampingan, area yang disorot, dan alasannya | \- | Wajib |
| F10 | **Keputusan dan laporan** | Menyediakan empat pilihan tindakan, mencatat setiap keputusan, dan membuat laporan temuan PDF | \- | Wajib |
| F11 | **Peta hubungan berkas** | Menunjukkan satu berkas dipakai oleh pasien atau bulan klaim mana saja | Lihat contoh di bawah | Sebaiknya |

**Contoh peta hubungan berkas (F11)**, visual utama saat demo:

Berkas \#A17 (lembar fisioterapi RS Melati Sehat)  
  ├── dipakai untuk klaim Bu Siti      SEP ...V447215   Agustus  
  ├── dipakai untuk klaim Pak Budi     SEP ...V578778   Agustus  
  └── dipakai lagi untuk Bu Siti       SEP ...V612004   September

# **8\. Jenis manipulasi dokumen yang diperiksa**

Manipulasi dokumen dipecah menjadi enam jenis. Setiap jenis punya cara pemeriksaan sendiri dan tingkat keyakinan yang berbeda.

| Jenis | Seperti apa di lapangan | Cara memeriksanya | Kekuatan sinyal |
| :---- | :---- | :---- | :---- |
| **1\. Tidak cocok dengan klaim** | Tagihan 8 sesi, berkas hanya berisi 5 baris | Isi berkas dibaca dengan OCR, lalu dibandingkan dengan data klaim memakai aturan sederhana | Kuat. Paling mudah dijelaskan. |
| **2\. Berkas dipakai ulang** | Lembar Bu Siti sama dengan lembar Pak Budi, atau dipakai lagi bulan berikutnya | Kolom identitas dan tanggal ditutup, lalu sidik jari gambar dan teks isi dibandingkan dengan semua berkas lain | Kuat |
| **3\. Copy-paste di dalam berkas** | Delapan tanda tangan, stempel, atau baris layanan identik | Setiap kotak dipotong sesuai template, diluruskan, lalu dibandingkan piksel demi piksel | Kuat, tetapi bisa berasal dari kelalaian administrasi. Butuh sinyal lain untuk jadi Prioritas. |
| **4\. Ditempel dari berkas lain** | Tanda tangan atau stempel diambil dari berkas pasien lain | Potongan dicocokkan dengan kumpulan potongan dari berkas lain, lalu tepi tempelan dan perbedaan kompresi diperiksa | Kuat, bila sumbernya ditemukan |
| **5\. Angka atau teks disunting** | Angka 5 diubah jadi 8, tanggal diganti | Model pendeteksi area suntingan menghasilkan peta area mencurigakan. Huruf dan ketebalan tinta yang tidak konsisten juga diperiksa. | Sedang |
| **6\. Dibuat dengan AI atau aplikasi desain** | Berkas terlihat seperti hasil scan, padahal dibuat di aplikasi desain atau generator gambar | Metadata file (aplikasi pembuat, jejak C2PA), ciri hasil scan (derau, bayangan kertas), dan detektor gambar AI | Sedang sampai lemah. Tidak pernah dipakai sendirian. |

| Batas yang dijaga Detektor gambar AI bisa salah, terutama untuk foto HP atau berkas yang di-scan berulang kali. Karena itu tanda "buatan AI" hanya menaikkan urutan pemeriksaan dan tidak pernah menjadi satu-satunya alasan label Prioritas. |
| :---- |

# **9\. Aturan label dan keputusan**

| Label | Kapan diberikan | Tindak lanjut |
| :---- | :---- | :---- |
| **Lolos** | Scan terbaca, isi cocok dengan klaim, dan tidak ada temuan | Lanjut verifikasi biasa |
| **Scan ulang** | Berkas tidak terbaca atau halamannya tidak lengkap | Rumah sakit diminta scan ulang. Tidak dihitung sebagai temuan. |
| **Perlu dicek** | Ada satu sinyal sedang, atau satu sinyal kuat yang masih mungkin kelalaian (misalnya tanda tangan identik tetapi isi cocok dengan klaim) | Verifikator membuka kartu bukti dan bisa meminta klarifikasi rumah sakit |
| **Prioritas** | Ada dua sinyal kuat, atau satu sinyal kuat ditambah sinyal lain | Peserta dikonfirmasi, lalu verifikator menelaahnya lebih dulu |

## **Prinsip keputusan**

* Sistem tidak pernah menolak klaim atau menahan pembayaran sendiri.

* Kalau proses gagal, misalnya OCR tidak terbaca atau terjadi error, label yang muncul adalah **Perlu dicek**, tidak pernah **Lolos**.

* Pilihan verifikator: **minta scan ulang**, **minta klarifikasi rumah sakit**, **teruskan ke telaah lanjut**, atau **tutup sebagai wajar**.

* Setiap keputusan mencatat siapa yang memutuskan, kapan, dan alasannya.

# **10\. Konfirmasi peserta**

Pertanyaan hanya dikirim untuk berkas berlabel Prioritas, lewat PANDAWA (WhatsApp resmi BPJS Kesehatan, 0811 8 165 165). Contoh pesannya:

| Halo Ibu Siti. BPJS Kesehatan ingin memastikan layanan yang tercatat atas nama Ibu. Apakah Ibu menjalani fisioterapi di RS Melati Sehat sebanyak 8 kali pada Agustus 2026? Balas 1 jika Ya, 2 jika Tidak pernah, atau 3 jika Hanya sebagian. |
| :---- |

* Pesan tidak memuat tautan, karena penipu sering menyamar sebagai BPJS lewat WhatsApp.

* Pesan tidak menyebut dugaan kecurangan atau nama pihak yang dicurigai.

* Setiap klaim hanya mendapat satu pesan.

* Jawaban "Tidak pernah" atau "Hanya sebagian" menaikkan urutan pemeriksaan, tetapi tidak otomatis menjadi vonis.

* Kalau peserta tidak menjawab, label tidak berubah.

# **11\. Layar utama**

| Layar | Isi |
| :---- | :---- |
| **1\. Antrean berkas** | Daftar berkas dengan label, alasan singkat, nilai klaim, dan filter per rumah sakit. Label Prioritas ada di urutan atas. |
| **2\. Kartu bukti** | Berkas yang diperiksa ditampilkan berdampingan dengan berkas pembanding. Area mencurigakan diberi warna, setiap temuan dijelaskan dalam satu kalimat, dan jawaban peserta serta tombol keputusan ada di layar yang sama. |
| **3\. Peta hubungan berkas** | Satu berkas dan semua klaim yang memakainya, lintas pasien dan bulan |
| **4\. Laporan temuan** | PDF berisi identitas klaim, temuan, potongan bukti, hash file asli, versi aturan, dan keputusan verifikator |

# **12\. Rancangan teknis**

Tujuannya membuat pemeriksaan yang benar-benar berjalan dengan komponen yang sederhana. Setiap hasil harus bisa ditunjukkan asal-usulnya.

| Bagian | Pilihan untuk MVP | Alasan |
| :---- | :---- | :---- |
| **Antarmuka** | Melanjutkan prototipe web yang sudah ada | Antrean, kartu bukti, dan panel keputusan sudah jadi |
| **Layanan analisis** | Satu layanan Python (FastAPI) | Semua pustaka pemrosesan gambar tersedia di Python |
| **Cek kualitas scan** | OpenCV: meluruskan halaman, mengukur ketajaman, dan mendeteksi bagian terpotong | Cepat dan tidak butuh GPU |
| **Baca isi** | PaddleOCR atau Tesseract, ditambah template letak kolom | Format lembar sudah diketahui, jadi tidak perlu model besar |
| **Berkas kembar** | Kolom identitas ditutup, lalu dibandingkan dengan perceptual hash per halaman dan per baris serta kemiripan teks. Hasil disimpan di PostgreSQL. | Bisa mencari di ribuan berkas dalam hitungan detik dan mudah dijelaskan |
| **Copy-paste** | Kotak dipotong sesuai template, lalu dibandingkan dengan SSIM atau korelasi piksel setelah diluruskan | Sederhana dan hasilnya bisa diperlihatkan |
| **Suntingan** | Error Level Analysis ditambah model pendeteksi area suntingan pra-latih, misalnya TruFor (lisensi perlu dicek sebelum produksi) | Menghasilkan peta area, bukan hanya skor |
| **Tanda buatan AI** | Membaca metadata dengan exiftool dan pypdf (aplikasi pembuat, jejak C2PA), memeriksa ciri hasil scan, dan detektor gambar AI sebagai sinyal lemah | Beberapa sinyal kecil lebih aman daripada satu model |
| **Konfirmasi peserta** | Disimulasikan di demo. Di produksi memakai WhatsApp Business API resmi BPJS. | Tidak butuh akses produksi untuk lomba |
| **Penyimpanan** | PostgreSQL dan penyimpanan file lokal | Cukup untuk skala uji |

## **Data minimal**

| Tabel | Kolom utama |
| :---- | :---- |
| **berkas** | id, sep, faskes, hash\_file, jumlah\_halaman, waktu\_unggah |
| **hasil\_cek** | berkas\_id, jenis\_cek, skor, area (koordinat kotak), penjelasan, versi\_aturan |
| **label** | berkas\_id, label, alasan, waktu |
| **konfirmasi** | sep, pertanyaan, jawaban, waktu\_kirim, waktu\_jawab |
| **keputusan** | berkas\_id, verifikator, tindakan, catatan, waktu |

## **Yang sengaja tidak dilakukan**

* Tidak melatih model besar dari nol.

* Tidak memakai LLM untuk memutuskan label. LLM boleh dipakai untuk merangkai kalimat temuan dari hasil yang sudah terstruktur.

* Tidak memakai blockchain atau arsitektur terdistribusi.

* Target kecepatan: di bawah 10 detik per berkas 1–2 halaman di CPU biasa.

# **13\. Cara menguji dan metrik keberhasilan**

## **Dataset uji**

* **Berkas asli:** formulir fisioterapi tiruan yang dicetak dan diisi tangan oleh 20–30 relawan, lalu di-scan dengan scanner dan difoto dengan HP. Tidak memakai data JKN.

* **Berkas palsu:** tim membuat versi palsu dari berkas asli tersebut dengan lima cara, yaitu dipakai ulang, tanda tangan ditempel, angka disunting, dibuat ulang di aplikasi desain, dan dibuat dengan generator gambar AI.

* **Berkas asli bermutu jelek:** buram, miring, dan terpotong, untuk menguji salah tangkap.

* Pengujian dilakukan buta: sistem tidak tahu label berkas.

| Metrik | Target MVP |
| :---- | :---- |
| Berkas kembar yang tertangkap | ≥ 95% |
| Tanda tangan atau stempel tempelan yang tertangkap | ≥ 90% |
| Angka atau teks disunting yang tertangkap | ≥ 70% (lebih sulit, hasil dilaporkan apa adanya) |
| Jumlah sesi yang terbaca benar dari berkas | ≥ 95% |
| Berkas asli yang keliru diberi label Prioritas | ≤ 5% |
| Berkas asli bermutu jelek yang diberi label Prioritas | 0 |
| Waktu verifikator memahami satu kartu bukti | ≤ 3 menit (diuji dengan 5 orang yang berperan sebagai verifikator) |

Semua angka di atas adalah target yang diukur pada dataset uji, bukan hasil di data BPJS.

# **14\. Privasi, keamanan, dan etika**

* Prototipe hanya memakai data sintetis dan formulir relawan, sesuai aturan Healthkathon 2026\.

* Di produksi, sistem berjalan di lingkungan BPJS dan berkas tidak pernah keluar.

* Kolom identitas ditutup sebelum berkas dibandingkan satu sama lain.

* Sesuai UU Pelindungan Data Pribadi: akses menurut peran, catatan setiap akses, dan batas waktu penyimpanan.

* Sistem memberi prioritas pemeriksaan, bukan vonis. Penetapan kecurangan tetap menjadi wewenang tim sesuai Permenkes 16/2019.

* Scan yang jelek tidak pernah dianggap sebagai tanda kecurangan.

* Rumah sakit selalu diberi kesempatan klarifikasi sebelum kasus dinaikkan.

# **15\. Risiko dan mitigasi**

| Risiko | Mitigasi |
| :---- | :---- |
| Tanda tangan identik karena pasien memang diminta tanda tangan sekali untuk semua sesi (kelalaian, bukan fraud) | Label maksimal Perlu dicek bila isi berkas cocok dengan klaim. Butuh sinyal lain untuk jadi Prioritas. |
| Detektor gambar AI salah menilai | Diperlakukan sebagai sinyal lemah, tidak pernah dipakai sendiri, dan tingkat keyakinannya ditampilkan |
| Format lembar berbeda antar rumah sakit | Template per rumah sakit, dimulai dari rumah sakit percontohan. Kalau template tidak ada, sistem memakai deteksi tabel otomatis. |
| Pelaku beradaptasi, misalnya menulis tanda tangan palsu satu per satu | Pemeriksaan kecocokan klaim, berkas kembar, dan konfirmasi peserta tetap menangkapnya. Pengenalan penulis masuk roadmap setelah diuji. |
| Klaim beralih ke RME pada 2027 | Tetap berlaku untuk dokumen pendukung yang masih berupa scan dan untuk audit arsip. Nantinya diperluas ke dokumen elektronik (tanda tangan elektronik dan riwayat edit). |
| Nama BPJS dipakai penipu di WhatsApp | Pesan hanya lewat nomor resmi, tanpa tautan, dan disertai edukasi di Mobile JKN |
| Beban verifikator malah bertambah | Ambang label disetel bersama BPJS agar jumlah Prioritas sesuai kapasitas verifikator |

# **16\. Perubahan dari prototipe v1**

| Dipertahankan | Diubah atau dibuang |
| :---- | :---- |
| Antrean klaim dan kartu bukti Tampilan dua berkas berdampingan dengan bagian yang disorot Panel keputusan verifikator Laporan temuan PDF Konfirmasi peserta | Skor yang sebelumnya disiapkan di data kini **dihitung dari berkas yang diunggah** Kuadran K1–K4 diganti empat label yang lebih mudah dipahami Pemeriksaan obat dan resep dikeluarkan dari MVP Tebakan jenis tinta diganti pemeriksaan suntingan dan tanda buatan AI Istilah teknis diganti bahasa sehari-hari |

# **17\. Skenario demo 3 menit**

1. **Berkas asli.** Unggah satu berkas fisioterapi asli. Hasilnya Lolos dalam beberapa detik.

2. **Berkas kembar.** Unggah berkas Pak Budi. Sistem langsung menemukan kembarannya, yaitu berkas Bu Siti, dan menampilkannya berdampingan.

3. **Angka disunting.** Unggah berkas yang angka 5-nya diubah jadi 8\. Sistem menampilkan peta area yang disunting dan pesan "Ditagih 8, berkas mendukung 5".

4. **Berkas buatan AI.** Unggah berkas yang dibuat dengan generator gambar. Metadata dan ciri hasil scan tidak cocok, sehingga labelnya Perlu dicek.

5. **Konfirmasi peserta.** Layar HP menampilkan pesan PANDAWA, lalu peserta menjawab "Hanya sebagian".

6. **Keputusan.** Verifikator memilih "Teruskan ke telaah lanjut" dan laporan PDF langsung terbit.

7. **Momen langsung bersama juri.** Juri menandatangani formulir lima kali, lalu formulirnya difoto dan diunggah. Hasilnya Lolos. Setelah itu satu tanda tangan ditempel lima kali, dan sistem langsung menangkapnya.

# **18\. Roadmap**

| Fase | Waktu | Isi |
| :---- | :---- | :---- |
| **MVP lomba** | Selama lomba | Fisioterapi, satu format lembar, dan dataset uji relawan |
| **Uji terbatas** | 3–6 bulan setelah lomba | Satu kantor cabang dengan berkas dari lingkungan uji JKN Drive, kalibrasi ambang dengan data nyata, dan penambahan format rumah sakit |
| **Perluasan** | 6–18 bulan | Hemodialisis dan katarak, rumah sakit bisa memeriksa berkasnya sendiri sebelum mengunggah, dan pemeriksaan dokumen elektronik seperti tanda tangan elektronik serta riwayat edit RME |

# **19\. Pertanyaan terbuka untuk BPJS**

* Seperti apa struktur folder dan penamaan berkas di JKN Drive, dan apakah ada API untuk memicu pemeriksaan saat berkas masuk?

* Bolehkah PANDAWA dipakai untuk mengirim pesan keluar kepada peserta?

* Berapa kapasitas verifikator per cabang? Angka ini menentukan seberapa ketat ambang label Prioritas.

* Seberapa banyak klaim fisioterapi yang masih memakai berkas scan selama masa transisi ke RME?

# **Sumber**

* [Itjen Kemenkes: tindak lanjut dan sanksi dugaan klaim fiktif di 3 RS swasta](https://itjen.kemkes.go.id/index.php/berita/detail/tindaklanjut-dan-pemberian-sanksi-atas-dugaan-klaim-fiktif-di-3-rs-swasta)

* [detikHealth: BPJS Kesehatan ungkap RS nakal, klaim palsu, dan overbilling](https://health.detik.com/berita-detikhealth/d-7548897/buka-bukaan-bpjs-kesehatan-banyak-rs-nakal-bikin-klaim-palsu-overbilling)

* [Katadata: KPK temukan fraud klaim BPJS di 3 RS, modus bakti sosial](https://katadata.co.id/berita/nasional/66a1dc20b49c6/kpk-temukan-fraud-klaim-bpjs-rp-34-m-di-3-rs-modus-bakti-sosial)

* [Tempo: verifikasi diperketat sesuai rekomendasi KPK](https://www.tempo.co/ekonomi/klaim-rumah-sakit-tertahan-bpjs-kesehatan-verifikasi-diperketat-sesuai-rekomendasi-kpk-untuk-cegah-fraud-1194553)

* [Bloomberg Technoz: AI mampu deteksi potensi fraud di BPJS Kesehatan](https://www.bloombergtechnoz.com/detail-news/111647/ai-mampu-deteksi-potensi-fraud-triliunan-di-bpjs-kesehatan)

* [Info INACBG: JKN Drive, inovasi baru proses klaim JKN](https://www.inacbg.web.id/2025/04/jkn-drive-inovasi-baru-proses-klaim-jkn.html)

* [Pusat KP-MAK UGM: Apa itu Vedika](https://pusatkpmak.fkkmk.ugm.ac.id/2017/05/01/apa-itu-vedika/)

* [Micromeet: perbedaan VClaim dan E-Klaim](https://www.micromeet.ai/en/glossary/e-klaim)

* [Bisnis.com: klaim elektronik mulai Agustus 2026, No RME No Claim 2027](https://finansial.bisnis.com/read/20260731/215/1992660/cegah-fraud-mulai-agustus-2026-rs-didorong-terapkan-klaim-elektronik)

* [TechCrunch: generator gambar ChatGPT bisa memalsukan struk](https://techcrunch.com/2025/03/31/chatgpts-new-image-generator-is-really-good-at-faking-receipts)

* [Insurance Thought Leadership: kenaikan 300% klaim dengan media manipulasi AI](https://www.insurancethoughtleadership.com/cyber/ai-deepfakes-drive-surge-insurance-fraud)

* [SAS via PR Newswire: insurers grapple with AI-generated images (2026)](https://www.prnewswire.com/news-releases/insurers-grapple-with-new-fraud-threat-ai-generated-images-302784735.html)

* [TruFor (CVPR 2023): deteksi dan lokalisasi pemalsuan gambar](https://grip-unina.github.io/TruFor/)

* [BPJS Kesehatan RI: layanan PANDAWA WhatsApp resmi](https://x.com/BPJSKesehatanRI/status/1948236420780323309)
