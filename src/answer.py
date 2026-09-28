"""Cevap uretimi: bulunan chunk'lari yerel LLM'e baglam olarak verir.

Prompt bicimi olcumle secildi (bkz. README "Model ve prompt secimi"): belgeler
once, talimatlar sonra. Bu bicim test setinde 4/4 dogru sonuc verdi ve kaynak
gosterimini duzgun yapti.
"""

import re
from collections.abc import Iterator

from openai import OpenAI

from config import (
    API_KEY,
    BENZERLIK_ESIGI,
    FOUNDRY_URL,
    MAX_TOKEN,
    SICAKLIK,
    SOHBET_MODELI,
    TOP_K,
)
from retrieve import get_top_chunks

# Prompt'taki her 100 karakter CPU'da yaklasik 1 saniye demek (olculdu).
# Bu yuzden sistem mesaji ve talimat mumkun oldugunca kisa tutuldu.
SISTEM_MESAJI = "KHAS yönerge asistanısın. Yalnızca verilen belgelere dayanarak Türkçe yanıtla."

# Talimatlar belgelerden SONRA geliyor: kucuk modeller son okuduklari
# talimata daha sadik kaliyor.
TALIMAT = """Kurallar:
- TEK CÜMLE yaz, en fazla 25 kelime. Ek açıklama, liste, giriş cümlesi yapma.
- Soruda fakülte/bölüm geçiyorsa yalnızca o fakülteye ait parçayı kullan.
- Koşula bağlı kuralda koşulu da yaz (örn: "proje tabanlıysa 60, değilse 40 iş günü").
- Sonuna kaynağı yaz: köşeli parantezteki belge adı ve madde.
- Belgelerde yoksa sadece şunu yaz: "Elimdeki belgelerde bu bilgi yok."
- Tahmin yürütme, belgelerde olmayan bilgi ekleme."""


_istemci: OpenAI | None = None


def istemci_al() -> OpenAI:
    global _istemci
    if _istemci is None:
        _istemci = OpenAI(base_url=FOUNDRY_URL, api_key=API_KEY)
    return _istemci


def baglam_kur(chunklar: list[dict]) -> str:
    """Belge parcalarini baglam metnine cevirir.

    Parcalari 'BELGE 1', 'BELGE 2' diye numaralandirmiyoruz: olcumde model
    kaynak olarak bu numaralari yaziyordu ("(Belge 1)") ve hatta uydurma
    markdown linki uretiyordu ("[BELGE 1](#)"). Numara yerine dogrudan
    kaynak adini basliga koyunca dogru atif yapiyor.
    """
    parcalar = []
    for c in chunklar:
        etiket = c["kaynak"]
        if c["madde"]:
            etiket += f", {c['madde']}"
        parcalar.append(f"--- KAYNAK: {etiket} ---\n{c['icerik']}")
    return "\n\n".join(parcalar)


def mesajlari_kur(soru: str, chunklar: list[dict]) -> list[dict]:
    return [
        {"role": "system", "content": SISTEM_MESAJI},
        {"role": "user", "content": f"{baglam_kur(chunklar)}\n\nSORU: {soru}\n\n{TALIMAT}"},
    ]


BILGI_YOK = "Elimdeki belgelerde bu bilgi yok."



# Modelin cevaba ekledigi "belge hakkinda konusma" kaliplari. 1.5B model
# TEK CUMLE talimatina her zaman uymuyor ve cevabin ardina soyle seyler
# ekliyor: "Belgedeki aciklamalari goz onunde bulundurarak, bu bilginin
# dogru oldugu kesin olarak belirtilemez ama...". Bilgi tasimayan bu
# cumleleri atiyoruz; cevabin kendisine ve kaynak satirina dokunmuyoruz.
META_KALIPLAR = (
    "belgedeki aciklama",
    "belgenin kaynak",
    "kaynak bilgisini",
    "kesin olarak belirtilemez",
    "goz onunde bulundur",
    "belirtildigi gibi",
    "belgesel",
    "[link]",
    "belgenin belirtilmesi",
    "belgeden sonra",
    "unutmayin",
    "unutma",
    "gozlemleyip",
    "ekleyelim",
    "bulalim",
)

# Modelin cevabin ardina ekledigi ozet basliklari. "Belge:" ve "Kaynak:"
# BILINCLI olarak bu listede degil -- onlar kaynak gosterimi, korunmali.
OZET_BASLIKLARI = ("sonuc:", "ozet:", "aciklama:", "not:", "cevap:")

# Cevabin tasiyabilecegi en fazla cumle sayisi. Kosullu kurallar iki cumle
# olabiliyor ("Proje tabanliysa 60 is gunu. Degilse 40 is gunu."), bu yuzden
# tek cumleye indirmiyoruz.
MAKS_CUMLE = 3


def _meta_mi(cumle: str) -> bool:
    d = cumle.lower()
    for a, b in (("ı", "i"), ("i̇", "i"), ("ş", "s"), ("ğ", "g"),
                 ("ü", "u"), ("ö", "o"), ("ç", "c"), ("â", "a")):
        d = d.replace(a, b)
    return any(k in d for k in META_KALIPLAR)


# Kaynak gosterimi baslangiclari. Bunlar noktalama olmadan bitse bile
# yarim sayilmaz -- "Belge: IISBF Staj Esaslari, Madde 1" gecerli bir
# kaynak satiridir, kesilmis cumle degil.
KAYNAK_BASLANGICLARI = ("belge:", "kaynak:", "(kaynak", "[kaynak")


def _yarim_mi(cumle: str) -> bool:
    """Cumle token siniri yuzunden ortada kesilmis mi?

    Noktalama ile bitmiyorsa ve kisa kaliyorsa yarim kabul ediyoruz.
    Parantezle biten kaynak gosterimleri ("(EK 4), Madde 1") saglam sayilir.
    """
    son = cumle.rstrip()
    if son.endswith((".", "!", "?", ")", "]", "\"", "'")):
        return False
    if son.lower().startswith(KAYNAK_BASLANGICLARI):
        return False
    # Rakamla biten kaynak satirlari ("... Madde: 1") da saglamdir
    if re.search(r"(madde|md\.?)\s*:?\s*\d+\s*$", son, re.IGNORECASE):
        return False
    return len(son.split()) <= 6


def cevabi_sadelestir(metin: str) -> str:
    """Modelin ekledigi bilgi tasimayan ve yarim kalan kisimlari ayiklar.

    Ilk cumle her zaman korunur (asil cevap odur). Sonrakiler yalnizca
    meta-konusma ya da ozet basligi degilse tutulur.

    Cumle bolerken iki ayiricya bakiyoruz: noktalama + buyuk harf, ve satir
    sonu. Ikincisi sart, cunku model ozeti genellikle yeni satirda basliyor
    ("...Madde: 1\nSonuc: Gonullu st") ve noktalama ile ayrilmiyor.
    Sayilardaki nokta (1.230.000,00) bolme noktasi sayilmaz.
    """
    metin = (metin or "").strip()
    if not metin:
        return metin

    parcalar = [
        c.strip()
        for c in re.split(r"(?:(?<=[.!?])\s+|\n+)(?=[A-ZÇĞİÖŞÜ])", metin)
        if c.strip()
    ]
    if not parcalar:
        return metin

    tutulan = [parcalar[0]]
    for c in parcalar[1:]:
        if len(tutulan) >= MAKS_CUMLE:
            break
        dusuk = c.lower()
        if any(dusuk.startswith(b) for b in OZET_BASLIKLARI):
            continue
        if _meta_mi(c):
            continue
        tutulan.append(c)

    # Token siniri yuzunden yarim kalan son parcayi at -- ama elde baska
    # parca varsa. Tek parcalik cevabi atarsak geriye hicbir sey kalmaz.
    while len(tutulan) > 1 and _yarim_mi(tutulan[-1]):
        tutulan.pop()

    sonuc = " ".join(tutulan).strip()
    return re.sub(r"[\s,;:]+$", "", sonuc)


def alakasiz_mi(chunklar: list[dict]) -> bool:
    """En iyi parca bile yeterince yakin degilse soru belgelerin disindadir."""
    return not chunklar or chunklar[0]["skor"] < BENZERLIK_ESIGI


def answer_query(
    soru: str, k: int = TOP_K, kaynaklar: list[str] | None = None
) -> tuple[str, list[dict]]:
    """Soruyu yanitlar. (cevap, kullanilan_chunklar) dondurur."""
    chunklar = get_top_chunks(soru, k=k, kaynaklar=kaynaklar)
    if alakasiz_mi(chunklar):
        return BILGI_YOK, chunklar

    yanit = istemci_al().chat.completions.create(
        model=SOHBET_MODELI,
        messages=mesajlari_kur(soru, chunklar),
        max_tokens=MAX_TOKEN,
        temperature=SICAKLIK,
    )
    ham = (yanit.choices[0].message.content or "").strip()
    return cevabi_sadelestir(ham), chunklar


def answer_query_stream(
    soru: str, k: int = TOP_K, kaynaklar: list[str] | None = None
) -> tuple[Iterator[str], list[dict]]:
    """Streaming surumu.

    Su an kullanilmiyor: GPU'ya gecince yanit ~2 saniyeye indi ve akisin
    kazandirdigi bir sey kalmadi. Ayrica cevabi_sadelestir() tum metni
    gerektirdigi icin akisla birlikte calismiyor. CPU'ya donulmesi
    gerekirse (bkz. README "Model secimi ve GPU") tekrar devreye alinabilir.
    """
    chunklar = get_top_chunks(soru, k=k, kaynaklar=kaynaklar)
    if alakasiz_mi(chunklar):
        return iter([BILGI_YOK]), chunklar

    akis = istemci_al().chat.completions.create(
        model=SOHBET_MODELI,
        messages=mesajlari_kur(soru, chunklar),
        max_tokens=MAX_TOKEN,
        temperature=SICAKLIK,
        stream=True,
    )

    def parcalar() -> Iterator[str]:
        for olay in akis:
            if olay.choices and olay.choices[0].delta.content:
                yield olay.choices[0].delta.content

    return parcalar(), chunklar
