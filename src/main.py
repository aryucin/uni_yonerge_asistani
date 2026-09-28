"""KHAS Yönerge Asistanı - komut satırı arayüzü.

Kullanim:
    python src/main.py

Onkosullar:
    foundry server start
    foundry model load qwen2.5-1.5b-instruct-cuda-gpu
    foundry model load qwen3-embedding-0.6b-generic-cpu
    python tools/pdf_to_md.py   (belgeler degistiyse)
    python src/ingest.py        (belgeler degistiyse)

Gunluk kullanim icin proje kokundeki baslat.bat yeterlidir.
"""

import sys
import time

from answer import answer_query
from config import DB_YOLU, SOHBET_MODELI

KARSILAMA = """
======================================================================
  KHAS Yönerge Asistanı  (tamamen çevrimdışı çalışır)
======================================================================
  Staj, burs, öğrenim ücreti ve eğitim yönetmeliği sorularını
  resmi KHAS belgelerine dayanarak yanıtlar.

  Örnek sorular:
    - Mühendislik öğrencisi kaç iş günü staj yapar?
    - ÖSYM bursu kaç yıl devam eder?
    - Hukuk Fakültesi tam ücreti ne kadar?
    - Doktora programına başvuru koşulları nelerdir?

  Çıkmak için: q  |  Enter'a basmadan önce sorunuzu yazın.
======================================================================
"""

UYARI = (
    "Not: Bu bir eğitim projesidir. Bağlayıcı bilgi için khas.edu.tr\n"
    "     adresindeki resmi belgeleri esas alınız.\n"
)


def main() -> None:
    if not DB_YOLU.exists():
        sys.exit(
            f"HATA: veritabani yok ({DB_YOLU}).\n"
            "Once su iki komutu calistirin:\n"
            "  python tools/pdf_to_md.py\n"
            "  python src/ingest.py"
        )

    print(KARSILAMA)
    print(UYARI)

    while True:
        try:
            soru = input("Soru> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGörüşürüz.")
            break

        if not soru:
            continue
        if soru.lower() in {"q", "quit", "exit", "cikis", "çıkış"}:
            print("Görüşürüz.")
            break

        baslangic = time.time()
        try:
            cevap, chunklar = answer_query(soru)
        except Exception as hata:  # noqa: BLE001 - kullaniciya anlasilir mesaj
            print(f"\n[HATA] {hata}\n")
            print("Foundry Local calisiyor mu? Kontrol: foundry server status\n")
            continue

        print(f"\nCevap: {cevap}")

        sure = time.time() - baslangic
        print(f"\n\n  Kullanılan belgeler ({sure:.1f} sn):")
        for c in chunklar:
            etiket = f"{c['kaynak']}"
            if c["madde"]:
                etiket += f", {c['madde']}"
            print(f"    - {etiket}  (benzerlik {c['skor']:.3f})")
        print()


if __name__ == "__main__":
    main()
