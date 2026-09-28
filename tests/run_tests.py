"""Test kosucusu: questions.md'deki senaryolari otomatik calistirir.

Kapsamin Week 5 adimi (System Testing & Evaluation).

Kullanim:
    python tests/run_tests.py           # tum testler
    python tests/run_tests.py A         # sadece A grubu (staj)
    python tests/run_tests.py A B E     # secili gruplar
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from answer import answer_query  # noqa: E402

# (grup, id, soru, beklenen_anahtarlar, yasakli_ifadeler)
#
# beklenen bos liste  = soru reddedilmeli
# yasakli             = cevapta gecerse test KALIR (yanlis bilgi isareti)
#
# Yasakli listesi sart: onceki surumde "gonullu" anahtarini ararken model
# "zorunlu staj VAR" dedigi halde test geciyordu, cunku kaynak adi
# "Gonullu Staj Esaslari" idi. Ayni sekilde "on" ararken "Yonergesi"
# kelimesinin icindeki "on" eslesiyordu. Artik kelime siniri da araniyor.
TESTLER = [
    ("A", "A1", "İşletme bölümü öğrencisi kaç iş günü staj yapar?", ["20"], ["40", "60"]),
    ("A", "A2", "Yönetim Bilişim Sistemleri stajı kaç iş günü?", ["40"], ["60", "20"]),
    ("A", "A3", "Mühendislik Fakültesi öğrencisi kaç iş günü staj yapar?", ["40"], ["20 iş günü"]),
    ("A", "A5", "Mimarlık öğrencisi stajını nasıl böler?", ["şantiye"], []),
    ("A", "A6", "İletişim Fakültesi zorunlu stajı kaç iş günü?", ["20"], ["40", "60"]),
    ("A", "A7", "Hukuk Fakültesi'nde zorunlu staj var mı?", ["yok", "gönüllü staj"], ["zorunlu staj var"]),
    ("A", "A9", "Staj başvurusu en geç ne zaman yapılmalı?", ["15"], []),

    ("B", "B1", "ÖSYM burslu yerleşen öğrenci öğrenim ücreti öder mi?",
     ["alınmaz", "ödemez", "ödemeyecek", "ücretsiz"], ["ücreti öder", "öder."]),
    ("B", "B2", "ÖSYM bursu lisans düzeyinde kaç yıl devam eder?",
     ["beş yıl", "5 yıl", "on yarıyıl", "10 yarıyıl"], ["dört yıl", "4 yıl"]),

    ("C", "C1", "Hukuk Fakültesi 2025-2026 girişli öğrenci için tam öğrenim ücreti ne kadar?",
     ["1.230.000"], []),
    ("C", "C2", "Psikoloji bölümü %50 indirimli ücreti 2025-2026 girişli için ne kadar?",
     ["650.000"], ["615.000"]),
    ("C", "C3", "Hazırlık sınıfı tam ücreti ne kadar?", ["1.250.000"], []),

    ("D", "D1", "Doktora programının amacı nedir?", ["araştırma"], []),

    ("E", "E1", "2030-2031 yılı öğrenim ücreti ne kadar?", [], []),
    ("E", "E2", "Yemekhane kaçta açılıyor?", [], []),
    ("E", "E4", "Üniversitenin rektörü kimdir?", [], []),
    ("E", "E5", "Erasmus başvurusu nasıl yapılır?", [], []),
]

RED_IFADELERI = ["bilgi yok", "bilgi bulunm", "bulunmamakta", "yer almam", "mevcut degil", "mevcut değil"]


def normalize(s: str) -> str:
    s = s.lower()
    for a, b in [("ı", "i"), ("i̇", "i"), ("ş", "s"), ("ğ", "g"),
                 ("ü", "u"), ("ö", "o"), ("ç", "c"), ("â", "a")]:
        s = s.replace(a, b)
    return s


def _gecer_mi(metin: str, anahtar: str) -> bool:
    """Kelime siniri arayarak eslesme; alt dizi yanlis pozitiflerini onler.

    "on" ararken "yonergesi" icindeki "on"a takilmamak icin sart.
    """
    return re.search(rf"(?<![0-9a-zçğıöşü]){re.escape(anahtar)}(?![0-9a-zçğıöşü])", metin) is not None


def degerlendir(cevap: str, beklenen: list[str], yasakli: list[str]) -> tuple[bool, str]:
    d = normalize(cevap)
    reddetti = any(r in d for r in (normalize(x) for x in RED_IFADELERI))

    if not beklenen:                      # reddedilmesi gereken soru
        return (reddetti, "reddetti" if reddetti else "UYDURDU")

    # Yanlis bilgi kontrolu once: dogru anahtar da gecse yanlis rakam varsa kalir
    carpik = [y for y in yasakli if _gecer_mi(d, normalize(y))]
    if carpik:
        return (False, f"YANLIS BILGI: {', '.join(carpik)}")

    # Model bazen once cevabi verip sonra cekince belirtiyor; bunu basarisiz
    # saymiyoruz, dogru bilgiyi vermis olmasi yeterli.
    bulunan = [k for k in beklenen if _gecer_mi(d, normalize(k))]
    if bulunan:
        return (True, f"eslesen: {', '.join(bulunan)}")
    return (False, "GEREKSIZ RED" if reddetti else "ANAHTAR YOK")


def main() -> None:
    gruplar = [a.upper() for a in sys.argv[1:]] or None
    secili = [t for t in TESTLER if not gruplar or t[0] in gruplar]

    print(f"{len(secili)} test calistiriliyor...\n")
    gecen, sureler, basarisizlar = 0, [], []

    for grup, tid, soru, beklenen, yasakli in secili:
        t0 = time.time()
        try:
            cevap, chunklar = answer_query(soru)
        except Exception as hata:  # noqa: BLE001
            print(f"[{tid}] HATA: {hata}")
            basarisizlar.append((tid, soru, str(hata)))
            continue
        sure = time.time() - t0
        sureler.append(sure)

        ok, aciklama = degerlendir(cevap, beklenen, yasakli)
        gecen += ok
        print(f"[{tid}] {'GECTI' if ok else 'KALDI'} ({sure:.1f}s) — {aciklama}")
        print(f"   S: {soru}")
        print(f"   C: {cevap[:220]}")
        if not ok:
            kaynaklar = ", ".join(f"{c['kaynak'][:30]}/{c['madde'] or '-'}" for c in chunklar[:3])
            print(f"   getirilen: {kaynaklar}")
            basarisizlar.append((tid, soru, cevap[:150]))
        print()

    print("=" * 66)
    print(f"SONUC: {gecen}/{len(sureler)} gecti | ortalama {sum(sureler)/len(sureler):.1f}s"
          if sureler else "SONUC: test calistirilamadi")
    if basarisizlar:
        print("\nBasarisiz olanlar:")
        for tid, soru, detay in basarisizlar:
            print(f"  [{tid}] {soru}\n        -> {detay}")


if __name__ == "__main__":
    main()
