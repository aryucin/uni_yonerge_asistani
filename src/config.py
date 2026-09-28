"""Proje genelinde kullanilan sabitler.

Tum ayarlar tek yerde toplandi ki model degistirmek veya top-K denemek icin
kodun icinde arama yapmak gerekmesin.
"""

import os
from pathlib import Path

# --- Dizinler ---------------------------------------------------------------
PROJE_KOK = Path(__file__).resolve().parent.parent
PDF_DIZIN = PROJE_KOK / "khas-docs"   # kaynak PDF'ler (elle indirildi)
MD_DIZIN = PROJE_KOK / "docs"         # PDF'lerden uretilen Markdown
VERI_DIZIN = PROJE_KOK / "data"
DB_YOLU = VERI_DIZIN / "khas.db"

# --- Foundry Local ----------------------------------------------------------
# Port 'auto' birakilirsa her yeniden baslatmada degisiyor; 5273'e sabitlendi:
#   foundry config set port 5273 --force
FOUNDRY_URL = "http://127.0.0.1:5273/v1"
API_KEY = "none"  # yerel calisiyor, kimlik dogrulama yok

# Model id'leri 'foundry model list' ciktisindaki tam adlardir.
# Kullanmadan once bellege yuklenmeleri gerekir:
#   foundry model load qwen2.5-1.5b-instruct-cuda-gpu
#   foundry model load qwen3-embedding-0.6b-generic-cpu
# KHAS_MODEL ortam degiskeniyle gecici olarak degistirilebilir; model
# karsilastirmasi yaparken config dosyasini kurcalamamak icin.
#
# GPU (CUDA) varyanti kullaniliyor. Bu makinede GPU'yu acmak icin Foundry
# Local'in execution provider'larini bir kez kaydetmek gerekti; ayrintisi
# ve nedeni README "GPU nasil devreye alindi" bolumunde.
#
# Olcum (17 soruluk test seti):
#   qwen2.5-7b      CPU  TOP_K=2 -> 10/17, 30.3 sn
#   phi-4-mini      CPU  TOP_K=2 ->  8/17, 21.6 sn (5 kez yanlis bilgi)
#   qwen2.5-1.5b    GPU  TOP_K=4 -> 14/17,  2.0 sn   <-- secildi
#
# 1.5B model CPU'da yetersizdi (baglami yok sayip uydururdu). GPU'da ise
# baglam neredeyse bedava oldugu icin TOP_K'yi 4'e cikarabildik; model ayni
# kalmasina ragmen daha genis baglamla dogru cevap veriyor.
SOHBET_MODELI = os.environ.get("KHAS_MODEL", "qwen2.5-1.5b-instruct-cuda-gpu")
EMBEDDING_MODELI = "qwen3-embedding-0.6b-generic-cpu"

# --- RAG parametreleri ------------------------------------------------------
# Kac chunk baglama eklenecek.
#
# CPU'da her ek chunk ~15 saniye getiriyordu, bu yuzden 2'de tutuyorduk.
# GPU'ya gecince prefill 110 karakter/sn'den ~1750 karakter/sn'ye cikti ve
# baglam neredeyse bedava oldu; bu fazlayi dogruluga cevirdik.
#
# Olcum (qwen2.5-1.5b GPU):
#   TOP_K=2 ->  9/17, 1.9 sn
#   TOP_K=4 -> 14/17, 2.0 sn   <-- secildi
#   TOP_K=5 -> 11/17, 2.0 sn
#   TOP_K=6 -> 10/17, 2.2 sn
# 4'ten sonra dusuyor: fazla baglam modeli karistiriyor, hiz sorunu degil.
TOP_K = int(os.environ.get("KHAS_TOPK", "4"))
# Cevap uzunlugu siniri.
#
# CPU doneminde 80'e cekilmisti (uretim 4.6 token/sn, her 100 token ~22 sn).
# GPU'da uretim ~16 token/sn oldugu icin bu sinir artik gereksiz dar kaliyordu
# ve cevaplar cumlenin ortasinda kesiliyordu ("...Sonuc: Gonullu st").
# 160'a cikarildi; yarim kalan cumleler ayrica cevabi_sadelestir() icinde
# ayikleniyor.
MAX_TOKEN = 160
SICAKLIK = 0.0     # yonerge sorulari icin belirlenimci cevap istiyoruz

# En iyi chunk'in benzerlik skoru bu esigin altindaysa modele hic gitmiyoruz.
#
# Iki sebep:
#  1. Guvenlik: uydurmalarin hepsi ayni desendeydi -- soru belgelerle alakasiz
#     (rektor kim, Erasmus nasil), retrieval mecburen alakasiz bir parca
#     getiriyor, model onunla bir seyler uyduruyordu.
#  2. Hiz: alakasiz sorular LLM cagrisi yapilmadan ~1 saniyede yanitlaniyor.
#
# Esik olcumle secildi (18 soruluk ornek):
#   alakali sorular  : 0.544 - 0.826  (en dusuk 0.544)
#   alakasiz sorular : 0.284 - 0.646  (kalan 7'si 0.49 altinda)
# Bu deger belge kumesine ozgudur; belgeler degisirse yeniden olculmelidir.
BENZERLIK_ESIGI = 0.50

# Chunk'lama: yonergeler madde bazli bolunur; bolmek gerekirse cumle
# sinirindan bolunur, cumle ortasindan asla.
#
# Bu sinir dogrudan yanit suresini belirliyor. Olcum: CPU'da prompt'un her
# 100 karakteri yaklasik 1 saniye ekliyor (bkz. README). 1800 ile chunk'lar
# 2200 karaktere kadar cikiyordu ve tek soru 60 saniyeyi asiyordu.
# 500'e cektik: bagalm kisaldi, sure dustu, chunk'lar daha hedefli oldu.
#
# Neden 700 degil de 500: sure toplam karakterle belirlendigi icin, kucuk
# chunk + daha cok chunk ayni butceye daha genis kapsama sigdiriyor.
# 700/TOP_K=2 kurulumunda "YBS staji kac gun" sorusunda dogru madde (Madde 1)
# 3. siraya dusup baglama hic girmiyordu; 500/TOP_K=3 ile ayni surede giriyor.
MAKS_CHUNK_KARAKTER = 500

# --- Kategoriler ------------------------------------------------------------
# Her chunk bir kategoriye ait; cevapta kaynak gosterirken kullanilir.
KATEGORILER = {
    "staj": "Staj Uygulama Esaslari",
    "lisans-burs": "Lisans Burs ve Indirim",
    "lisans-egitim": "Lisans Egitim-Ogretim",
    "lisansustu-burs": "Lisansustu Burs ve Destek",
    "lisansustu-egitim": "Lisansustu Egitim-Ogretim",
    "ucret": "Ogrenim Ucretleri",
}
