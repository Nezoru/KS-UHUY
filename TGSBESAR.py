import os
import time
import re
import requests
import pandas as pd
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import MaxNLocator
from collections import Counter
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from transformers import pipeline
from dotenv import load_dotenv

# ==========================================
# 1. KONFIGURASI & VARIABEL
# ==========================================
load_dotenv()
username_ig = os.getenv("IG_USER")
password_ig = os.getenv("IG_PASS")
HF_TOKEN = os.getenv("HF_TOKEN")

if not username_ig or not password_ig:
    print("Error: IG_USER atau IG_PASS tidak ditemukan di file .env")
    exit()

URL_BERITA = "https://money.kompas.com/read/2026/06/04/085746426/rupiah-tembus-rp-18000-per-dollar-as-terlemah-sepanjang-sejarah?page=all"
URL_IG = "https://www.instagram.com/p/DZJcFuDympN/"

# ==========================================
# 2. LOAD MODEL NLP (INDOBERT)
# ==========================================
device = 0 if torch.cuda.is_available() else -1
print("Memuat model IndoBERT...")
id_model = pipeline("text-classification", model="crypter70/IndoBERT-Sentiment-Analysis", token=HF_TOKEN, device=device)
label_map = {"LABEL_0": "negative", "LABEL_1": "positive"}

# ==========================================
# 3. SCRAPING ARTIKEL BERITA (KOMPAS)
# ==========================================
print("\n--- TAHAP 1: SCRAPING BERITA KOMPAS ---")
dataset = []

try:
    response = requests.get(URL_BERITA)
    soup = BeautifulSoup(response.content, 'html.parser')

    article_body = soup.find('div', class_='read__content')
    if article_body:
        paragraphs = article_body.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 20:
                dataset.append({"source": "Berita Kompas", "text": text})
        print(f"✅ Selesai: Berhasil mengekstrak {len(dataset)} paragraf dari artikel berita.")
    else:
        print("❌ Gagal menemukan body artikel.")
except Exception as e:
    print(f"❌ Error scraping berita: {e}")

# ==========================================
# 4. SCRAPING KOMENTAR INSTAGRAM (SELENIUM)
# ==========================================
print("\n--- TAHAP 2: SCRAPING KESELURUHAN KOMENTAR INSTAGRAM ---")
options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

all_valid_comments = set()

try:
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    try:
        user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        pass_input = driver.find_element(By.NAME, "password")
    except:
        user_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        pass_input = driver.find_element(By.NAME, "pass")

    user_input.send_keys(username_ig)
    pass_input.send_keys(password_ig + Keys.RETURN)

    print("\n" + "=" * 50)
    print("[!] Selesaikan reCAPTCHA/Login manual jika muncul di browser Chrome.")
    print("=" * 50)
    input("=> TEKAN ENTER JIKA SUDAH MASUK BERANDA IG... ")

    driver.get(URL_IG)
    time.sleep(5)

    scroll_selector = '.x5yr21d.xw2csxc.x1odjw0f.x1n2onr6'
    try:
        scroll_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, scroll_selector)))

        print("Memulai proses scroll agresif hingga akhir kolom komentar...")
        retries = 0
        last_milestone = 0
        previous_count = 0  # <--- Variabel pelacak jumlah data riil

        while True:
            # 1. Ekstrak data yang ada di layar saat ini
            soup_ig = BeautifulSoup(driver.page_source, 'html.parser')
            spans = soup_ig.find_all('span')

            for span in spans:
                text = span.get_text(strip=True)
                if len(text) > 2:
                    all_valid_comments.add(text)

            current_count = len(all_valid_comments)

            # 2. Print progres kelipatan 50
            if current_count >= last_milestone + 50:
                last_milestone = (current_count // 50) * 50
                print(f"  [Progress] Sedang scraping... {last_milestone} komentar unik telah diambil.")

            # 3. Scroll ke bawah wadah komentar
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
            time.sleep(4)  # Waktu tunggu wajib agar tidak kena limit IG

            # 4. Taktik Klik Tombol "Load More" (Jika ada ikon +)
            try:
                # Mencari SVG berbentuk tombol load more (Label bahasa Inggris atau Indonesia)
                load_more_btn = driver.find_element(By.CSS_SELECTOR,
                                                    "svg[aria-label='Load more comments'], svg[aria-label='Muat memuat komentar lainnya']")
                driver.execute_script("arguments[0].scrollIntoView();", load_more_btn)
                load_more_btn.click()
                time.sleep(2)
            except:
                pass  # Lanjutkan saja jika tidak menemukan tombolnya

            # 5. Logika Berhenti yang Lebih Cerdas (Berdasarkan jumlah set, bukan tinggi scroll)
            if current_count == previous_count:
                retries += 1
                print(f"  [Info] Data stuck/menunggu IG memuat... (Percobaan {retries}/5)")

                # Trik: Scroll sedikit ke atas lalu ke bawah lagi untuk memancing lazy-load
                driver.execute_script("arguments[0].scrollTop -= 300", scroll_div)
                time.sleep(1)
                driver.execute_script("arguments[0].scrollTop += 300", scroll_div)
                time.sleep(3)

                if retries >= 5:
                    print("  [Info] Scraping dihentikan (Mentok dasar / Dilimit IG).")
                    break
            else:
                retries = 0  # Reset percobaan jika berhasil dapat data baru
                previous_count = current_count

    except Exception as e:
        print(f"Mungkin tidak ada komentar atau perlu penyesuaian selector. Error: {e}")

    print(f"✅ Selesai: Total berhasil mengekstrak {len(all_valid_comments)} komentar unik dari Instagram.")

    for comment in list(all_valid_comments):
        dataset.append({"source": "Instagram", "text": comment})

finally:
    driver.quit()

# Tampilkan Rekapitulasi Data Sebelum Masuk NLP
print("\n" + "=" * 50)
print(f"📊 REKAPITULASI TOTAL DATA YANG AKAN DIANALISIS:")
print(f"   - Dari Berita Kompas : {len([d for d in dataset if d['source'] == 'Berita Kompas'])} data")
print(f"   - Dari Instagram     : {len([d for d in dataset if d['source'] == 'Instagram'])} data")
print(f"   - Total Keseluruhan  : {len(dataset)} data")
print("=" * 50)

# ==========================================
# 5. NLP: SENTIMEN & EKSTRAKSI KATA KUNCI
# ==========================================
print("\n--- TAHAP 3: ANALISIS SENTIMEN & KATA KUNCI ---")
stopwords_id = [
    "saya", "aku", "gue", "gw", "kamu", "lu", "lo", "dia", "mereka", "kita", "kami", "nya", "beliau", "anda", "kalian",
    "yang",
    "ku", "mu", "kau", "bro", "kak", "bang", "pak", "bapak", "bu", "ibu", "mas", "mbak", "si", "sang",
    "ini", "itu", "tersebut", "sini", "situ", "sana", "di", "ke", "dari", "pada", "dalam", "kepada", "bagi", "untuk",
    "buat", "oleh", "tentang", "terhadap", "sebagai",
    "dengan", "atas", "bawah", "antara", "pun", "kah", "lah", "toh",
    "dan", "atau", "serta", "karena", "sebab", "sehingga", "maka", "bahwa", "lalu", "kemudian", "terus",
    "kalau", "kalo", "jika", "jikalau", "bila", "apabila", "agar", "supaya", "seperti", "macam",
    "saat", "ketika", "sedang", "akan", "sudah", "telah", "baru", "pernah", "lagi", "bisa", "dapat", "adalah", "ialah",
    "merupakan", "yaitu", "yakni", "ada", "hal", "jadi",
    "juga", "cuma", "hanya", "memang", "selalu", "sempat", "mulai", "hari", "bulan", "tahun", "kali", "banyak",
    "beberapa",
    "yg", "aja", "saja", "deh", "dong", "sih", "kok", "kan", "tuh", "yah", "ya", "nih", "mah", "pas", "eh", "oh", "kek",
    "wkwk", "wkwkwk", "wk", "haha", "hehe", "hihi", "xixi", "hmm", "kata", "tidak", "persen", "berita", "kompas",
    "admin"
]

final_results = []
all_words_ig = []
all_words_news = []

for data in dataset:
    text = data["text"]
    source = data["source"]

    try:
        res = id_model(text)[0]
        sentiment = label_map.get(res["label"], res["label"].lower())
        confidence = round(res["score"], 4)
    except:
        sentiment = "neutral"
        confidence = 0.0

    clean_text = re.sub(r'[^\w\s]', '', text.lower())
    words = [w for w in clean_text.split() if w not in stopwords_id and len(w) > 3]

    if source == "Instagram":
        all_words_ig.extend(words)
    else:
        all_words_news.extend(words)

    final_results.append({
        "source": source,
        "text": text,
        "sentiment": sentiment,
        "confidence": confidence
    })

top_10_news = Counter(all_words_news).most_common(10)
top_10_ig = Counter(all_words_ig).most_common(10)

print(f"\nKata Kunci Berita (Top 10): {top_10_news}")
print(f"Kata Kunci Instagram (Top 10): {top_10_ig}")

# ==========================================
# 6. EXPORT CSV
# ==========================================
print("\n--- TAHAP 4: MENYIMPAN DATA ---")
df = pd.DataFrame(final_results)
df.to_csv("analisis_narasi_dollar_18k.csv", index=False, encoding="utf-8")
print(f"🎉 Total {len(df)} data berhasil disimpan di 'analisis_narasi_dollar_18k.csv'.")

# ==========================================
# 7. VISUALISASI GRAFIK (4 GRAFIK GRID 2x2)
# ==========================================
print("\n--- TAHAP 5: MEMBUAT VISUALISASI ---")
df_berita = df[df['source'] == 'Berita Kompas']
df_ig = df[df['source'] == 'Instagram']

sns.set_theme(style="whitegrid", palette="muted")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# --- GRAFIK 1: SENTIMEN ARTIKEL BERITA ---
sns.countplot(
    data=df_berita, x='sentiment', ax=axes[0, 0],
    order=['positive', 'neutral', 'negative'],
    palette={'positive': '#2ecc71', 'neutral': '#95a5a6', 'negative': '#e74c3c'}
)
axes[0, 0].set_title('Grafik 1: Sentimen Artikel Berita', fontsize=14, fontweight='bold')
axes[0, 0].set_xlabel('Kategori Sentimen', fontsize=12)
axes[0, 0].set_ylabel('Jumlah Paragraf', fontsize=12)
axes[0, 0].yaxis.set_major_locator(MaxNLocator(integer=True))
for p in axes[0, 0].patches:
    axes[0, 0].annotate(f'{int(p.get_height())}' if p.get_height() > 0 else '',
                        (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', xytext=(0, 8), textcoords='offset points')

# --- GRAFIK 2: SENTIMEN KOMENTAR INSTAGRAM ---
sns.countplot(
    data=df_ig, x='sentiment', ax=axes[0, 1],
    order=['positive', 'neutral', 'negative'],
    palette={'positive': '#2ecc71', 'neutral': '#95a5a6', 'negative': '#e74c3c'}
)
axes[0, 1].set_title('Grafik 2: Sentimen Publik (IG)', fontsize=14, fontweight='bold')
axes[0, 1].set_xlabel('Kategori Sentimen', fontsize=12)
axes[0, 1].set_ylabel('Jumlah Komentar', fontsize=12)
axes[0, 1].yaxis.set_major_locator(MaxNLocator(integer=True))
for p in axes[0, 1].patches:
    axes[0, 1].annotate(f'{int(p.get_height())}' if p.get_height() > 0 else '',
                        (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', xytext=(0, 8), textcoords='offset points')

# --- GRAFIK 3: TOP 10 KATA DOMINAN ARTIKEL ---
df_words_news = pd.DataFrame(top_10_news, columns=['Kata', 'Frekuensi'])
sns.barplot(data=df_words_news, x='Frekuensi', y='Kata', ax=axes[1, 0], palette='viridis')
axes[1, 0].set_title('Grafik 3: Top 10 Kata Dominan (Artikel)', fontsize=14, fontweight='bold')
axes[1, 0].set_xlabel('Jumlah Kemunculan', fontsize=12)
axes[1, 0].set_ylabel('Kata Kunci', fontsize=12)
axes[1, 0].xaxis.set_major_locator(MaxNLocator(integer=True))

# --- GRAFIK 4: TOP 10 KATA DOMINAN INSTAGRAM ---
df_words_ig = pd.DataFrame(top_10_ig, columns=['Kata', 'Frekuensi'])
sns.barplot(data=df_words_ig, x='Frekuensi', y='Kata', ax=axes[1, 1], palette='plasma')
axes[1, 1].set_title('Grafik 4: Top 10 Kata Dominan (Instagram)', fontsize=14, fontweight='bold')
axes[1, 1].set_xlabel('Jumlah Kemunculan', fontsize=12)
axes[1, 1].set_ylabel('Kata Kunci', fontsize=12)
axes[1, 1].xaxis.set_major_locator(MaxNLocator(integer=True))

# Simpan dan Tampilkan
plt.tight_layout(pad=3.0, h_pad=4.0, w_pad=3.0)
plt.savefig('grafik_analisis_narasi.png', dpi=300)
print("🎉 Grafik berhasil dibuat dan disimpan sebagai 'grafik_analisis_narasi.png'!")
plt.show()