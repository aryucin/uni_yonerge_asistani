"""Anlamsal arama: sorguya en yakin chunk'lari SQLite'tan bulur.

Kapsamin onerdigi yontem: tum vektorleri bellege al, Python'da cosine
similarity hesapla, en yuksek K taneyi dondur. Veri kumemiz kucuk oldugu icin
(birkac yuz chunk) bu yaklasim milisaniyeler suruyor; ayri bir vektor
veritabanina gerek yok.
"""

import json
import sqlite3

import numpy as np
from openai import OpenAI

from config import API_KEY, DB_YOLU, EMBEDDING_MODELI, FOUNDRY_URL, TOP_K

_istemci: OpenAI | None = None
_onbellek: tuple[np.ndarray, list[dict]] | None = None


def istemci_al() -> OpenAI:
    global _istemci
    if _istemci is None:
        _istemci = OpenAI(base_url=FOUNDRY_URL, api_key=API_KEY)
    return _istemci


def chunklari_yukle() -> tuple[np.ndarray, list[dict]]:
    """Tum chunk'lari ve vektorlerini bellege alir (bir kez).

    Onbellek kullaniyoruz cunku her soruda diskten okuyup JSON cozmek
    gereksiz; veri ingestion disinda degismiyor.
    """
    global _onbellek
    if _onbellek is not None:
        return _onbellek

    if not DB_YOLU.exists():
        raise FileNotFoundError(
            f"{DB_YOLU} bulunamadi. Once 'python src/ingest.py' calistirin."
        )

    with sqlite3.connect(DB_YOLU) as baglanti:
        satirlar = baglanti.execute(
            "SELECT id, icerik, embedding, kaynak, kategori, fakulte, madde FROM chunklar"
        ).fetchall()

    if not satirlar:
        raise ValueError("Veritabani bos. 'python src/ingest.py' calistirin.")

    kayitlar = [
        {"id": r[0], "icerik": r[1], "kaynak": r[3],
         "kategori": r[4], "fakulte": r[5], "madde": r[6]}
        for r in satirlar
    ]
    matris = np.array([json.loads(r[2]) for r in satirlar], dtype=np.float32)
    # Normalize edilmis vektorlerde cosine similarity = ic carpim.
    # Bir kez normalize edip her sorguda bolme isleminden kurtuluyoruz.
    matris /= np.linalg.norm(matris, axis=1, keepdims=True)

    _onbellek = (matris, kayitlar)
    return _onbellek


def onbellegi_temizle() -> None:
    """Bellekteki vektor onbellegini bosaltir.

    Indeksleme ayri bir surecte calisip veritabanini gunceller; bu surecteki
    onbellek ise eski kalir. Arayuz, indeksleme bittikten sonra bunu cagirmazsa
    yeni yuklenen belgeyi goremez ve "bu bilgi yok" demeye devam eder.
    """
    global _onbellek
    _onbellek = None


def sorgu_vektoru(soru: str) -> np.ndarray:
    yanit = istemci_al().embeddings.create(model=EMBEDDING_MODELI, input=[soru])
    v = np.array(yanit.data[0].embedding, dtype=np.float32)
    return v / np.linalg.norm(v)


def _sadelestir(s: str) -> str:
    """Turkce karakterleri sadelestirir; kelime eslesmesi icin."""
    s = s.lower()
    for a, b in [("ı", "i"), ("i̇", "i"), ("ş", "s"), ("ğ", "g"),
                 ("ü", "u"), ("ö", "o"), ("ç", "c"), ("â", "a")]:
        s = s.replace(a, b)
    return s


def leksikal_bonus(soru: str, kayit: dict) -> float:
    """Sorudaki ayirt edici kelimeler chunk'ta geciyorsa 0..1 arasi puan.

    Neden gerekli: embedding "staj suresi" kavramini yakaliyor ama "hangi
    fakulte" ayrimini yapamiyor. Olcumde uc farkli fakultenin staj maddesi
    0.652 / 0.648 / 0.647 gibi neredeyse esit skor aldi ve dogru olan
    ucuncu siraya dustu. Fakulte adi leksikal olarak nettir; kucuk bir
    kelime eslesme puani bu ayrimi yapiyor.
    """
    # Uzunluk filtresi var cunku "ne", "icin" gibi dolgu kelimeler ayirt edici
    # degil. Ama sayi ve oran iceren kisa tokenlar ("%50", "20", "tam") tam
    # tersine en ayirt edici ipuclar: onceki surumde bunlar atiliyordu ve
    # "Psikoloji %50 indirimli ucreti" sorusunda oran bilgisi kayboldugu icin
    # yanlis satir getiriliyordu.
    kelimeler = {
        k for k in _sadelestir(soru).split()
        if len(k) > 4 or any(c.isdigit() for c in k) or k.startswith("%")
    }
    if not kelimeler:
        return 0.0
    hedef = _sadelestir(f"{kayit['icerik']} {kayit['fakulte']} {kayit['kaynak']}")
    return sum(1 for k in kelimeler if k in hedef) / len(kelimeler)


# Leksikal puanin toplam skora katkisi. Cosine farklari cok kucuk oldugu icin
# (0.005 mertebesinde) bu agirlik siralamayi belirleyici sekilde etkiliyor,
# ama anlamsal aramanin yerini almiyor.
LEKSIKAL_AGIRLIK = 0.10


def get_top_chunks(
    soru: str,
    k: int = TOP_K,
    kaynaklar: list[str] | None = None,
) -> list[dict]:
    """Soruya en yakin k chunk'i dondurur (anlamsal + leksikal skor).

    kaynaklar verilirse yalnizca o belgelerde aranir. Varsayilan None, yani
    tum havuzda arama -- arayuzdeki belge secimi icin opsiyonel bir daraltma,
    varsayilan davranis degismiyor.
    """
    matris, kayitlar = chunklari_yukle()
    anlamsal = matris @ sorgu_vektoru(soru)

    bonuslar = np.array([leksikal_bonus(soru, r) for r in kayitlar], dtype=np.float32)
    toplam = anlamsal + LEKSIKAL_AGIRLIK * bonuslar

    if kaynaklar:
        secili = set(kaynaklar)
        maske = np.array([r["kaynak"] in secili for r in kayitlar])
        toplam = np.where(maske, toplam, -np.inf)

    en_iyi = np.argsort(toplam)[::-1][:k]
    en_iyi = [i for i in en_iyi if np.isfinite(toplam[i])]
    return [
        {**kayitlar[i], "skor": float(toplam[i]),
         "anlamsal": float(anlamsal[i]), "leksikal": float(bonuslar[i])}
        for i in en_iyi
    ]


if __name__ == "__main__":
    # Hizli dogrulama: birkac ornek soruyla ne getirdigine bakalim
    ornekler = [
        "Mühendislik öğrencisi kaç iş günü staj yapar?",
        "Yönetim Bilişim Sistemleri stajı kaç gün?",
        "Hukuk Fakültesi 2025-2026 tam ücret ne kadar?",
        "ÖSYM bursu kaç yıl devam eder?",
        "Doktora tez savunması nasıl yapılır?",
    ]
    for soru in ornekler:
        print(f"\n{'=' * 70}\nSORU: {soru}")
        for i, c in enumerate(get_top_chunks(soru, k=3), 1):
            onizleme = c["icerik"].replace("\n", " ")[:150]
            print(f"  {i}. [{c['skor']:.3f}] {c['kaynak']} / {c['madde'] or '-'}")
            print(f"     {onizleme}...")
