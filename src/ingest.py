"""Veri hazirlama: Markdown -> chunk -> embedding -> SQLite.

Kapsamin Week 3 adimi. Calistirmadan once Foundry Local'da embedding modeli
yuklu olmali:
    foundry model load qwen3-embedding-0.6b

Kullanim:
    python src/ingest.py                 # degisen/eksik belgeleri indeksler
    python src/ingest.py --tam           # her seyi silip bastan indeksler
    python src/ingest.py --dosya a.md    # yalnizca belirtilen dosyalari
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

from openai import OpenAI

from config import (
    API_KEY,
    DB_YOLU,
    EMBEDDING_MODELI,
    FOUNDRY_URL,
    MAKS_CHUNK_KARAKTER,
    MD_DIZIN,
    VERI_DIZIN,
)

# Embedding istegi basina gonderilecek chunk sayisi.
# CPU'da calistigi icin cok buyuk parti bellek baskisi yaratiyor.
PARTI_BOYU = 16


def onbilgi_ayir(metin: str) -> tuple[dict, str]:
    """Markdown basindaki '---' bloklarindan metadata'yi ayirir."""
    if not metin.startswith("---"):
        return {}, metin
    _, ustbilgi, govde = metin.split("---", 2)
    veri = {}
    for satir in ustbilgi.strip().splitlines():
        if ":" in satir:
            anahtar, deger = satir.split(":", 1)
            veri[anahtar.strip()] = deger.strip()
    return veri, govde.strip()


def madde_no_bul(blok: str) -> str:
    """Chunk'in hangi maddeden geldigini cikarir (kaynak gostermek icin)."""
    m = re.match(r"^###\s*(Madde\s+\d+)", blok)
    if m:
        return m.group(1)
    m = re.match(r"^\*\*(\d{1,2})\.\*\*", blok)
    if m:
        return f"Madde {m.group(1)}"
    m = re.match(r"^##\s*(.+?)\s*—", blok)  # ucret tablosu basliklari
    if m:
        return m.group(1)[:80]
    return ""


def uzun_blogu_bol(blok: str, sinir: int) -> list[str]:
    """Sinirdan uzun bloklari cumle sinirindan boler.

    Cumle ortasindan bolmuyoruz; yonergelerde kosul ile sonuc ayni cumlede
    oldugu icin ortadan bolmek yanlis cevaba yol aciyor.
    """
    if len(blok) <= sinir:
        return [blok]

    cumleler = re.split(r"(?<=[.!?])\s+", blok)
    parcalar, mevcut = [], ""
    for c in cumleler:
        if mevcut and len(mevcut) + len(c) + 1 > sinir:
            parcalar.append(mevcut.strip())
            mevcut = c
        else:
            mevcut = f"{mevcut} {c}".strip()
    if mevcut:
        parcalar.append(mevcut.strip())
    return parcalar


def chunklari_uret(dosyalar: list[Path] | None = None) -> list[dict]:
    """Markdown dosyalarini okuyup chunk listesi uretir.

    dosyalar verilmezse docs/ altindaki tum .md dosyalari islenir.
    """
    chunklar = []
    for md_yolu in sorted(dosyalar if dosyalar is not None else MD_DIZIN.glob("*.md")):
        onbilgi, govde = onbilgi_ayir(md_yolu.read_text(encoding="utf-8"))
        kaynak = onbilgi.get("kaynak", md_yolu.stem)
        kategori = onbilgi.get("kategori", "")
        fakulte = onbilgi.get("fakulte", "")

        bloklar = [b.strip() for b in govde.split("\n\n") if b.strip()]
        for blok in bloklar:
            if blok.startswith("# "):      # dosya basligi, icerik tasimaz
                continue
            if len(blok) < 40:             # tek satirlik aciklama/ayirici
                continue
            madde = madde_no_bul(blok)
            for parca in uzun_blogu_bol(blok, MAKS_CHUNK_KARAKTER):
                # Her chunk'in basina kaynak bilgisi yaziliyor: retrieval sirasinda
                # parca baglamindan koptugu icin fakulte bilgisi metnin icinde de
                # bulunmali, yoksa "hangi fakulte" ayrimi kayboluyor.
                baslik = f"[{kaynak}"
                if fakulte:
                    baslik += f" | {fakulte}"
                if madde:
                    baslik += f" | {madde}"
                baslik += "]"
                chunklar.append({
                    "icerik": f"{baslik}\n{parca}",
                    "kaynak": kaynak,
                    "kategori": kategori,
                    "fakulte": fakulte,
                    "madde": madde,
                    "dosya": md_yolu.name,
                })
    return chunklar


def embedding_al(istemci: OpenAI, metinler: list[str]) -> list[list[float]]:
    yanit = istemci.embeddings.create(model=EMBEDDING_MODELI, input=metinler)
    return [d.embedding for d in yanit.data]


def veritabani_kur(baglanti: sqlite3.Connection, sifirla: bool = False) -> None:
    """Tablolari olusturur. sifirla=True ise once mevcut veriyi siler."""
    if sifirla:
        baglanti.execute("DROP TABLE IF EXISTS chunklar")
        baglanti.execute("DROP TABLE IF EXISTS ayarlar")

    baglanti.execute("""
        CREATE TABLE IF NOT EXISTS chunklar (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            icerik    TEXT NOT NULL,
            embedding TEXT NOT NULL,   -- JSON dizisi olarak saklanan vektor
            kaynak    TEXT NOT NULL,
            kategori  TEXT,
            fakulte   TEXT,
            madde     TEXT,
            dosya     TEXT,
            imza      TEXT             -- kaynak dosyanin icerik ozeti
        )
    """)
    baglanti.execute("CREATE INDEX IF NOT EXISTS idx_kategori ON chunklar(kategori)")
    baglanti.execute("CREATE INDEX IF NOT EXISTS idx_dosya ON chunklar(dosya)")
    baglanti.execute("""
        CREATE TABLE IF NOT EXISTS ayarlar (
            anahtar TEXT PRIMARY KEY,
            deger   TEXT
        )
    """)
    baglanti.commit()


def dosya_imzasi(md_yolu: Path) -> str:
    """Dosya iceriginin kisa ozeti; degisip degismedigini anlamak icin."""
    return hashlib.sha256(md_yolu.read_bytes()).hexdigest()[:16]


def kurulum_imzasi() -> str:
    """Chunk boyutu + embedding modeli imzasi.

    Bunlardan biri degisirse eski vektorler yenileriyle karsilastirilabilir
    olmaktan cikar (farkli model = farkli vektor uzayi) ya da parca boyutlari
    tutarsizlasir. O yuzden imza degistiginde artimli indeksleme yapmiyor,
    her seyi bastan kuruyoruz.
    """
    return f"{EMBEDDING_MODELI}|{MAKS_CHUNK_KARAKTER}"


def mevcut_imzalar(baglanti: sqlite3.Connection) -> dict[str, str]:
    try:
        satirlar = baglanti.execute(
            "SELECT dosya, imza FROM chunklar GROUP BY dosya"
        ).fetchall()
    except sqlite3.Error:
        return {}
    return {d: i for d, i in satirlar if d}


def kayitli_kurulum(baglanti: sqlite3.Connection) -> str | None:
    try:
        satir = baglanti.execute(
            "SELECT deger FROM ayarlar WHERE anahtar = 'kurulum'"
        ).fetchone()
    except sqlite3.Error:
        return None
    return satir[0] if satir else None


def vektorlestir(istemci: OpenAI, chunklar: list[dict]) -> list[list[float]]:
    """Chunk'lari partiler halinde vektore cevirir."""
    vektorler: list[list[float]] = []
    baslangic = time.time()
    for i in range(0, len(chunklar), PARTI_BOYU):
        parti = chunklar[i:i + PARTI_BOYU]
        vektorler.extend(embedding_al(istemci, [c["icerik"] for c in parti]))
        print(f"  {min(i + PARTI_BOYU, len(chunklar))}/{len(chunklar)} "
              f"({time.time() - baslangic:.0f}s)", flush=True)
    return vektorler


def dosyalari_yaz(
    baglanti: sqlite3.Connection,
    chunklar: list[dict],
    vektorler: list[list[float]],
    imzalar: dict[str, str],
) -> None:
    """Chunk'lari yazar; ayni dosyanin eski kayitlarini once siler.

    Silme sart: dosya guncellenmisse eski parcalar durmaya devam eder ve ayni
    bilgi iki kez baglama girer.
    """
    for dosya in {c["dosya"] for c in chunklar}:
        baglanti.execute("DELETE FROM chunklar WHERE dosya = ?", (dosya,))

    baglanti.executemany(
        "INSERT INTO chunklar (icerik, embedding, kaynak, kategori, fakulte,"
        " madde, dosya, imza) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (c["icerik"], json.dumps(v), c["kaynak"], c["kategori"],
             c["fakulte"], c["madde"], c["dosya"], imzalar.get(c["dosya"], ""))
            for c, v in zip(chunklar, vektorler)
        ],
    )
    baglanti.commit()


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="Belgeleri indeksler.")
    ayristirici.add_argument("--tam", action="store_true",
                             help="her seyi silip bastan indeksle")
    ayristirici.add_argument("--dosya", nargs="*", default=None,
                             help="yalnizca bu .md dosyalarini indeksle")
    secenek = ayristirici.parse_args()

    if not MD_DIZIN.exists():
        sys.exit(f"HATA: {MD_DIZIN} yok. Once 'python tools/pdf_to_md.py' calistirin.")

    tum_md = sorted(MD_DIZIN.glob("*.md"))
    if not tum_md:
        sys.exit(f"HATA: {MD_DIZIN} icinde .md dosyasi yok.")

    VERI_DIZIN.mkdir(parents=True, exist_ok=True)
    yeni_kurulum = kurulum_imzasi()

    with sqlite3.connect(DB_YOLU) as baglanti:
        veritabani_kur(baglanti)
        eski_kurulum = kayitli_kurulum(baglanti)
        onceki = mevcut_imzalar(baglanti)

    # Chunk boyutu veya embedding modeli degistiyse artimli calismak guvensiz:
    # eski vektorler farkli bir uzaya ait olur, skorlar karsilastirilamaz.
    kurulum_degisti = eski_kurulum is not None and eski_kurulum != yeni_kurulum
    tam_mi = secenek.tam or kurulum_degisti or not onceki

    if kurulum_degisti:
        print("Chunk boyutu veya embedding modeli degismis -> tam yeniden indeksleme")

    if secenek.dosya:
        istenen = []
        for ad in secenek.dosya:
            yol = MD_DIZIN / Path(ad).name
            if not yol.exists():
                sys.exit(f"HATA: {yol} bulunamadi.")
            istenen.append(yol)
        hedef = istenen
        tam_mi = False
    elif tam_mi:
        hedef = tum_md
    else:
        # Yalnizca yeni eklenen veya icerigi degisen dosyalar
        hedef = [md for md in tum_md if onceki.get(md.name) != dosya_imzasi(md)]

    # docs/ altindan silinmis belgelerin kayitlarini temizle.
    # Yapilmazsa bot artik var olmayan bir belgeden cevap vermeye devam eder;
    # hata vermez, sadece yanlis kaynak gosterir.
    guncel_adlar = {md.name for md in tum_md}
    silinecek = [ad for ad in onceki if ad not in guncel_adlar] if not tam_mi else []
    if silinecek:
        with sqlite3.connect(DB_YOLU) as baglanti:
            for ad in silinecek:
                baglanti.execute("DELETE FROM chunklar WHERE dosya = ?", (ad,))
            baglanti.commit()
        print(f"Silinen belge temizlendi: {', '.join(silinecek)}")

    if not hedef:
        if not silinecek:
            print("Degisen belge yok; indeksleme atlandi.")
        with sqlite3.connect(DB_YOLU) as baglanti:
            adet = baglanti.execute("SELECT COUNT(*) FROM chunklar").fetchone()[0]
        print(f"Veritabaninda {adet} chunk var.")
        return

    kip = "TAM" if tam_mi else "ARTIMLI"
    print(f"Indeksleme kipi: {kip} | islenecek dosya: {len(hedef)}/{len(tum_md)}")
    for md in hedef:
        print(f"  - {md.name}")

    print("\nChunk'lar uretiliyor...")
    chunklar = chunklari_uret(hedef)
    if not chunklar:
        sys.exit("HATA: hic chunk uretilmedi.")

    uzunluklar = [len(c["icerik"]) for c in chunklar]
    print(f"  {len(chunklar)} chunk | ortalama {sum(uzunluklar)//len(uzunluklar)} "
          f"karakter | en uzun {max(uzunluklar)}")

    istemci = OpenAI(base_url=FOUNDRY_URL, api_key=API_KEY)
    print(f"\nEmbedding uretiliyor (model: {EMBEDDING_MODELI})...")
    baslangic = time.time()
    vektorler = vektorlestir(istemci, chunklar)

    imzalar = {md.name: dosya_imzasi(md) for md in hedef}
    print(f"\nSQLite'a yaziliyor -> {DB_YOLU}")
    with sqlite3.connect(DB_YOLU) as baglanti:
        veritabani_kur(baglanti, sifirla=tam_mi)
        dosyalari_yaz(baglanti, chunklar, vektorler, imzalar)
        baglanti.execute(
            "INSERT INTO ayarlar (anahtar, deger) VALUES ('kurulum', ?)"
            " ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger",
            (yeni_kurulum,),
        )
        baglanti.commit()
        adet = baglanti.execute("SELECT COUNT(*) FROM chunklar").fetchone()[0]
        dagilim = baglanti.execute(
            "SELECT kategori, COUNT(*) FROM chunklar GROUP BY kategori ORDER BY 2 DESC"
        ).fetchall()

    print(f"\nTamam: {len(chunklar)} chunk yazildi ({time.time() - baslangic:.0f}s)")
    print(f"Veritabani toplami: {adet} chunk")
    print("Kategori dagilimi:")
    for kategori, sayi in dagilim:
        print(f"  {kategori or '(bos)':<22} {sayi}")


if __name__ == "__main__":
    main()
