# 📊 Analisis Kesenjangan Narasi: Media Massa vs Opini Publik (Studi Kasus Dollar Rp18.000)

Repositori KS-UHUY ini memuat source code lengkap untuk mengekstraksi, menganalisis, dan memvisualisasikan perbedaan narasi antara pemberitaan media massa resmi (Kompas) dan opini publik di media sosial (Instagram). 

Proyek ini dibangun menggunakan teknik Web Scraping (Selenium & BeautifulSoup) dan Natural Language Processing (NLP) menggunakan model IndoBERT untuk analisis sentimen berbahasa Indonesia.

Persyaratan Sistem (Prerequisites)
Pastikan komputer Anda sudah terinstal perangkat lunak berikut:
1. Buka Pycharm dengan versi lebih baru.
2. Google Chrome (Browser).
3. Pastikan telah membuat file .csv
4. Akun Instagram (Disarankan menggunakan akun *dummy*/cadangan).
5. Saat kodenya di run terminal meminta klik "ENTER" saat instagram baru dibuka untuk melanjutkan scraping data
6. Tunggu Scraping data sampai selesai agar memaksimalkan keselurahan scraping
7. file .csv akan tertera di PyCharm dengan penamaan "analisis_narasi_dollar 18k.csv" sejajar dengan kodenya
8. Scraping data telah selesai

.env file berisi:
HF_TOKEN=token_huggingface_kamu
IG_USER=username_instagram_kamu
IG_PASS=password_instagram_kamu
