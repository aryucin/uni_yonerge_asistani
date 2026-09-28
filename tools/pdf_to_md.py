"""PDF -> Markdown donusturucu.

Bir kereye mahsus hazirlik adimidir; RAG pipeline'i PDF gormez, sadece docs/*.md okur.
Boyle yaptik cunku chunk kalitesi dogrudan cevap kalitesini belirliyor ve PDF'ten
gelen ham metin (ozellikle ucret tablosu) chunk'lamaya uygun degil.

Iki ayri islem var:
  1. Yonergeler  -> pypdf ile metin, madde bazli baslıklandirma
  2. Ucret tablosu -> pdfplumber ile TABLO olarak; duz metne cevrilirse
     fakulte adlari kayboluyor ve geriye anonim rakam yiginI kaliyor.

Kullanim:  python tools/pdf_to_md.py
"""

import re
import sys
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import MD_DIZIN, PDF_DIZIN  # noqa: E402

UCRET_PDF = "2025-2026-Yeni-Kayit-ve-Kayit-Yenileme-Ucretleri-PDF-21.08.2025.pdf"

# Her PDF icin: (cikti adi, baslik, kategori, fakulte)
# Fakulte bilgisi metadata olarak yaziliyor cunku staj sureleri fakulteye gore
# degisiyor ve bot hangi kuralin hangi fakulteye ait oldugunu ayirt edebilmeli.
BELGE_BILGI = {
    "ek1-iktisadi-idari-ve-sosyal-bilimler-fakultesi-staj-uygulama-esaslari1.pdf": (
        "staj-iisbf", "İİSBF Staj Uygulama Esasları (EK 1)", "staj",
        "İktisadi, İdari ve Sosyal Bilimler Fakültesi"),
    "ek2-muhendislik-ve-doga-bilimleri-fakultesi-staj-uygulama-esaslari1.pdf": (
        "staj-muhendislik", "Mühendislik ve Doğa Bilimleri Fakültesi Staj Uygulama Esasları (EK 2)",
        "staj", "Mühendislik ve Doğa Bilimleri Fakültesi"),
    "ek3-sanat-ve-tasarim-fakultesi-staj-uygulama-esaslari1.pdf": (
        "staj-sanat-tasarim", "Sanat ve Tasarım Fakültesi Staj Uygulama Esasları (EK 3)",
        "staj", "Sanat ve Tasarım Fakültesi"),
    "ek4-hukuk-fakultesi-ve-iletisim-fakultesi-staj-uygulama-esaslari.pdf": (
        "staj-hukuk-iletisim-gonullu",
        "Hukuk ve İletişim Fakültesi Gönüllü Staj Uygulama Esasları (EK 4)",
        "staj", "Hukuk Fakültesi, İletişim Fakültesi"),
    "ek5-iletisim-fakultesi-staj-uygulama-esaslari-radyotelevizyon-ve-sinema-yeni-medya-ve-iletisim-reklamcilik-bolumleri.pdf": (
        "staj-iletisim-zorunlu",
        "İletişim Fakültesi (RTS / Yeni Medya / Reklamcılık) Zorunlu Staj Esasları (EK 5)",
        "staj", "İletişim Fakültesi"),
    "kadir-has-universitesi-lisans-burs-yonergesi13.pdf": (
        "lisans-burs-yonergesi", "KHAS Lisans Burs Yönergesi", "lisans-burs", "Tüm fakülteler"),
    "kadir-has-universitesi-lisans-egitim-ve-ogretim-yonetmeligi1.pdf": (
        "lisans-egitim-yonetmeligi", "KHAS Lisans Eğitim ve Öğretim Yönetmeliği",
        "lisans-egitim", "Tüm fakülteler"),
    "kadir-has-universitesi-lisansustu-burs-ve-destege-iliskin-yonerge2.pdf": (
        "lisansustu-burs-yonergesi", "KHAS Lisansüstü Burs ve Desteğe İlişkin Yönerge",
        "lisansustu-burs", "Lisansüstü Eğitim Enstitüsü"),
    "kadir-has-universitesi-lisansustu-egitim-ve-ogretim-yonetmeligi3.pdf": (
        "lisansustu-egitim-yonetmeligi", "KHAS Lisansüstü Eğitim ve Öğretim Yönetmeliği",
        "lisansustu-egitim", "Lisansüstü Eğitim Enstitüsü"),
}

# Giris yili sutun basliklari (ucret tablosunun 2-6. sutunlari)
GIRIS_YILLARI = [
    "2021-2022 ve öncesi girişli",
    "2022-2023 girişli",
    "2023-2024 girişli",
    "2024-2025 girişli",
    "2025-2026 girişli (yeni kayıt)",
]


def bosluk_duzelt(s: str) -> str:
    """PDF'ten gelen bozuk bosluklari temizler."""
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def oran_duzelt(s: str) -> str:
    """'% 6 5 İ n d i r i m l i' -> '%65 İndirimli'.

    Bu sutunun formati sabit oldugu icin tum bosluklari silip yeniden
    ayirmak guvenli.
    """
    yogun = re.sub(r"\s+", "", s or "")
    m = re.match(r"^%(\d+)İndirimli$", yogun, re.IGNORECASE)
    if m:
        return f"%{m.group(1)} İndirimli"
    if yogun.lower() == "ücretli":
        return "Ücretli (indirimsiz, tam ücret)"
    return bosluk_duzelt(s)


def ucret_tablosu_cevir(pdf_yolu: Path) -> str:
    """Ucret PDF'ini program bazli Markdown bolumlerine cevirir.

    Her fakulte/program grubu ayri bir '##' bolumu olur; boylece chunk'landiginda
    her parcada fakulte adi ve yil basliklari birlikte kalir.
    """
    gruplar: list[tuple[str, list[list[str]]]] = []
    with pdfplumber.open(pdf_yolu) as pdf:
        for page in pdf.pages:
            for tablo in page.extract_tables():
                for row in tablo:
                    hucre = [bosluk_duzelt(c) for c in row]
                    if not any(hucre):
                        continue  # ayirici bos satir
                    program, oran = hucre[0], oran_duzelt(hucre[1])
                    tutarlar = hucre[2:7]
                    if program:  # yeni grup basliyor
                        gruplar.append((program, []))
                    if not gruplar or not oran:
                        continue  # baslik satirlari
                    gruplar[-1][1].append([oran] + tutarlar)

    sat = [
        "# Kadir Has Üniversitesi — 2025-2026 Öğrenim Ücretleri",
        "",
        "Aşağıdaki tutarlar **KDV dahil nakit ödeme tutarları** olup Türk Lirası (TL) cinsindendir.",
        "Ücret, öğrencinin **hangi yıl üniversiteye giriş yaptığına** ve **burs/indirim oranına** göre değişir.",
        "Bu tablo yalnızca 2025-2026 eğitim yılı içindir; başka bir yıl için geçerli değildir.",
        "",
    ]
    # Markdown TABLOSU KULLANMIYORUZ. Denendi ve basarisiz oldu: chunk'lama
    # sirasinda baslik satiri ("## Hukuk Fakultesi") ayri bir parcaya, rakamlar
    # baska bir parcaya dusuyordu. Model elindeki tablonun hangi fakulteye ait
    # oldugunu goremedigi icin baska programin rakamini veriyordu
    # (Psikoloji %50 icin 650.000 yerine 615.000).
    #
    # Bunun yerine her satir kendi basina anlamli ve eksiksiz: program adi,
    # indirim orani, giris yili ve tek bir tutar. Parca nereden bolunurse
    # bolunsun baglam icinde kaliyor.
    for program, satirlar in gruplar:
        if not satirlar:
            continue
        sat.append(f"## {program} — 2025-2026 öğrenim ücreti")
        sat.append("")
        # HER YIL AYRI SATIR. Once bir satirda bes yilin tutarini birlikte
        # yaziyorduk; model dogru fakulteyi ve dogru indirim oranini buluyor
        # ama bes yakin rakam arasindan yanlisini seciyordu (Psikoloji %50
        # icin 650.000 yerine ayni satirdaki 499.583,70). Her satirda tek
        # rakam olunca karistiracak alternatif kalmiyor.
        for r in satirlar:
            oran = r[0]
            for yil, tutar in zip(GIRIS_YILLARI, r[1:6]):
                if not tutar:
                    continue
                sat.append(
                    f"**{program}** bölümünde **{oran}** öğrenciler için, "
                    f"**{yil}** öğrencinin 2025-2026 eğitim yılı öğrenim ücreti: "
                    f"**{tutar} TL** (KDV dahil nakit ödeme tutarı)."
                )
                sat.append("")
    return "\n".join(sat)


def yonerge_cevir(pdf_yolu: Path, baslik: str) -> str:
    """Yonerge PDF'ini madde yapisi korunacak sekilde Markdown'a cevirir.

    Madde tespiti iki kurala birden dayanir:
      1. Numara SATIR BASINDA olmali (PDF'te madde numaralari hep satir basindadir)
      2. Numara SIRADAKI beklenen numara olmali

    Ikinci kural sart: "...ogrenci 1. Sinifi tamamladiktan sonra..." gibi sira
    sayilari aksi halde madde numarasi sanilip maddeyi ortadan boluyor ve
    kural ile kosul birbirinden kopuyor.
    """
    okuyucu = PdfReader(pdf_yolu)
    ham = "\n".join((s.extract_text() or "") for s in okuyucu.pages)
    ham = re.sub(r"-\n", "", ham)  # satir sonu kelime bolunmeleri

    satirlar = []
    for s in ham.split("\n"):
        s = re.sub(r"[ \t]+", " ", s).strip()
        if s and not re.fullmatch(r"\d{1,3}", s):  # yalniz sayfa numarasi olan satirlar
            satirlar.append(s)

    bloklar: list[str] = []
    mevcut: list[str] = []
    beklenen = 1

    def blogu_kapat() -> None:
        if mevcut:
            bloklar.append(" ".join(mevcut).strip())
            mevcut.clear()

    for s in satirlar:
        m_madde = re.match(r"^(Madde\s+\d+)\s*[-–—]?\s*(.*)$", s, re.IGNORECASE)
        m_numara = re.match(r"^(\d{1,2})\.\s+(.+)$", s)

        if m_madde:
            blogu_kapat()
            mevcut.append(f"### {m_madde.group(1)}\n\n{m_madde.group(2)}")
        elif m_numara and int(m_numara.group(1)) == beklenen:
            blogu_kapat()
            mevcut.append(f"**{beklenen}.** {m_numara.group(2)}")
            beklenen += 1
        else:
            mevcut.append(s)
    blogu_kapat()

    return f"# {baslik}\n\n" + "\n\n".join(bloklar) + "\n"


def main() -> None:
    MD_DIZIN.mkdir(parents=True, exist_ok=True)
    uretilen = 0

    for pdf_ad, (cikti, baslik, kategori, fakulte) in BELGE_BILGI.items():
        kaynak = PDF_DIZIN / pdf_ad
        if not kaynak.exists():
            print(f"  ATLANDI (bulunamadi): {pdf_ad}")
            continue
        govde = yonerge_cevir(kaynak, baslik)
        onbilgi = (
            f"---\nkaynak: {baslik}\nkategori: {kategori}\n"
            f"fakulte: {fakulte}\ndosya: {pdf_ad}\n---\n\n"
        )
        (MD_DIZIN / f"{cikti}.md").write_text(onbilgi + govde, encoding="utf-8")
        print(f"  yazildi: {cikti}.md  ({len(govde)} karakter)")
        uretilen += 1

    ucret_kaynak = PDF_DIZIN / UCRET_PDF
    if ucret_kaynak.exists():
        govde = ucret_tablosu_cevir(ucret_kaynak)
        onbilgi = (
            "---\nkaynak: 2025-2026 Öğrenim Ücretleri\nkategori: ucret\n"
            f"fakulte: Tüm fakülteler\ndosya: {UCRET_PDF}\n---\n\n"
        )
        (MD_DIZIN / "ucretler-2025-2026.md").write_text(onbilgi + govde, encoding="utf-8")
        print(f"  yazildi: ucretler-2025-2026.md  ({len(govde)} karakter)")
        uretilen += 1
    else:
        print(f"  ATLANDI (bulunamadi): {UCRET_PDF}")

    print(f"\nToplam {uretilen} Markdown dosyasi uretildi -> {MD_DIZIN}")


if __name__ == "__main__":
    main()
