# Test Soruları ve Beklenen Davranışlar

Bu set iki amaca hizmet eder:

1. **Cevaplanabilir sorular** — bilgi belgelerde var, doğru yanıtlanmalı
2. **Cevaplanamaz sorular** — bilgi belgelerde yok, reddedilmeli
   (*"Elimdeki belgelerde bu bilgi yok."*)

İkincisi en az birincisi kadar önemlidir: bir üniversite asistanının
uydurduğu ücret veya staj bilgisi, hiç cevap vermemesinden daha zararlıdır.

---

## A. Staj — fakülteye göre değişen cevaplar

Bu grup projenin en zorlu kısmıdır: "staj kaç gün?" sorusunun tek bir doğru
cevabı yoktur, dokuz farklı doğru cevap vardır.

| # | Soru | Beklenen cevap | Kaynak |
|---|------|----------------|--------|
| A1 | İşletme bölümü öğrencisi kaç iş günü staj yapar? | 20 iş günü | EK 1, Madde 1 |
| A2 | Yönetim Bilişim Sistemleri stajı kaç iş günü? | 40 iş günü | EK 1, Madde 1 |
| A3 | Mühendislik öğrencisi kaç iş günü staj yapar? | Proje tabanlı müfredatta 60 (30+30), değilse 40 | EK 2, Madde 2-3 |
| A4 | Mühendislikte ÇAP yapan öğrenci kaç gün staj yapar? | Proje tabanlıysa 90, değilse 60 | EK 2 |
| A5 | Mimarlık öğrencisi stajını nasıl böler? | 30 iş günü şantiye + 30 iş günü ofis | EK 3, Madde 2 |
| A6 | İletişim Fakültesi zorunlu stajı kaç gün? | 20 iş günü | EK 5, Madde 3 |
| A7 | Hukuk Fakültesi'nde zorunlu staj var mı? | Hayır, yalnızca gönüllü staj | EK 4, Madde 1 |
| A8 | Gönüllü stajda sigorta kim tarafından yapılır? | Okul tarafından karşılanır | EK 4, Madde 2 |
| A9 | Staj başvurusu en geç ne zaman yapılmalı? | Başlama tarihinden en az 15 gün önce | EK 4, Madde 3 |
| A10 | Bir işyerinde en az kaç iş günü staj yapılabilir? | 15 iş günü (İnşaat Mühendisliği hariç) | EK 2 |

## B. Burs ve indirimler

| # | Soru | Beklenen cevap | Kaynak |
|---|------|----------------|--------|
| B1 | ÖSYM burslu yerleşen öğrenci öğrenim ücreti öder mi? | Hayır, ücret alınmaz | Lisans Burs Yönergesi, Madde 6 |
| B2 | ÖSYM bursu kaç yıl devam eder? | Lisansta en çok 5 yıl (10 yarıyıl), hazırlıkta en çok 2 yıl | Lisans Burs Yönergesi, Madde 6 |
| B3 | Burs Değerlendirme Komisyonu kimlerden oluşur? | Rektör Yrd., Genel Sekreter, Mali İşler Dir., Kampüste Yaşam Ofisi, iki öğretim üyesi, raportör | Lisans Burs Yönergesi, Madde 4 |

## C. Öğrenim ücretleri (2025-2026)

Sayısal veri en yüksek hata riski taşıyan gruptur; rakamlar birebir doğru olmalıdır.

| # | Soru | Beklenen cevap | Kaynak |
|---|------|----------------|--------|
| C1 | Hukuk Fakültesi 2025-2026 girişli tam ücret ne kadar? | 1.230.000,00 TL | Ücret tablosu |
| C2 | Psikoloji bölümü %50 indirimli ücreti (2025-2026 girişli)? | 650.000,00 TL | Ücret tablosu |
| C3 | Hazırlık sınıfı tam ücreti nedir? | 1.250.000,00 TL | Ücret tablosu |
| C4 | Bilgisayar Mühendisliği %25 indirimli ücreti (2025-2026 girişli)? | 975.000,00 TL | Ücret tablosu |
| C5 | Tiyatro bölümünde hangi indirim oranları var? | Yalnızca %50 İndirimli ve Ücretli | Ücret tablosu |

## D. Lisansüstü

| # | Soru | Beklenen cevap | Kaynak |
|---|------|----------------|--------|
| D1 | Doktora programına başvuru koşulları nelerdir? | Yönetmelikteki ilgili madde | Lisansüstü Yönetmelik |
| D2 | Yüksek lisans tez savunması nasıl yapılır? | Yönetmelikteki ilgili madde | Lisansüstü Yönetmelik |
| D3 | Lisansüstü öğrencilere hangi burs ve destekler var? | Yönergedeki kategoriler | Lisansüstü Burs Yönergesi |

## E. Reddedilmesi gereken sorular

Bu grupta **tek doğru davranış reddetmektir.** Model bu sorulara cevap
üretiyorsa uyduruyor demektir.

| # | Soru | Neden reddedilmeli |
|---|------|--------------------|
| E1 | 2030-2031 yılı öğrenim ücreti ne kadar? | Yalnızca 2025-2026 verisi var |
| E2 | Yemekhane kaçta açılıyor? | Belgelerde yok |
| E3 | Kütüphane hafta sonu açık mı? | Belgelerde yok |
| E4 | Üniversitenin rektörü kimdir? | Belgelerde yok |
| E5 | Erasmus başvurusu nasıl yapılır? | Belgelerde yok |
| E6 | Geçen yılın (2024-2025) yeni kayıt ücreti neydi? | Tabloda yalnızca mevcut öğrenciler için 2024-2025 girişli sütunu var; yeni kayıt ücreti yok |

---

## F. Uç durumlar

| # | Girdi | Beklenen davranış |
|---|-------|-------------------|
| F1 | Boş girdi (yalnızca Enter) | Yeniden sor, çökme yok |
| F2 | Tek kelime: "staj" | Anlamlı bir şey döndür veya bilgi iste |
| F3 | Çok genel: "Bana her şeyi anlat" | Belirsizliği belirt, uydurma yapma |
| F4 | İngilizce soru: "How many days is the internship?" | Tercihen Türkçe yanıt, doğru bilgi |

---

## Sonuçlar

Koşucu: `python tests/run_tests.py` (grup seçmek için: `... A E`)

| Model | Donanım | TOP_K | Geçen | Ortalama süre |
|---|---|---|---|---|
| qwen2.5-1.5b | CPU | 2 | 5/17 | 8.3 sn |
| phi-4-mini | CPU | 2 | 8/17 | 21.6 sn |
| qwen2.5-7b | CPU | 2 | 10/17 | 30.3 sn |
| qwen2.5-7b | GPU | 2 | — | 41–56 sn (VRAM taştı) |
| qwen2.5-1.5b | GPU | 2 | 9/17 | 1.9 sn |
| qwen2.5-1.5b | GPU | 4 | 14/17 | 2.0 sn |
| **qwen2.5-1.5b** | **GPU** | **4** | **16/17** | **2.3 sn** |

Son satır, ücret verisi "her satırda tek tutar" biçimine çevrildikten sonraki
durumdur ve iki bağımsız çalıştırmada da 16/17 verdi.

### Kalan tek hata

| # | Soru | Sorun |
|---|------|-------|
| A1 | İşletme bölümü staj süresi | Kaynak belgede İşletme (20 iş günü) ve Yönetim Bilişim Sistemleri (40 iş günü) **aynı maddenin içinde** geçiyor. Model bazen diğer bölümün ya da "bir işyerinde en az 15 iş günü" ifadesinin rakamını alıyor. Maddeyi bölmek kural ile koşulu ayıracağı için tercih edilmedi. |

### Ücret sorularında giriş yılı

Ücret, öğrencinin giriş yılına göre değişiyor. Soru giriş yılını belirtmezse
model beş tutardan birini seçiyor ve bu rastgele olabiliyor:

- *"Bilgisayar Mühendisliği %25 indirimli **2025-2026 girişli** ücreti?"*
  → **975.000 TL** (doğru)
- *"Psikoloji %50 indirimli ücreti ne kadar?"* (yıl yok)
  → 408.240 TL (2022-2023 girişli tutarı)

Prompt'a "yıl belirtilmemişse 2025-2026'yı varsay" kuralı eklemek denendi ama
skor 16/17'den 14/17'ye düştü: 1.5B modelde her ek talimat satırı diğer
kuralların takibini zayıflatıyor. Bu yüzden eklenmedi — soru giriş yılını
içermelidir.
