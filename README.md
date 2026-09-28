# KHAS Yönerge Asistanı

Kadir Has Üniversitesi'nin resmi yönergelerine dayanarak **staj**, **burs**,
**öğrenim ücreti** ve **lisansüstü koşullar** hakkındaki soruları yanıtlayan,
tamamen çevrimdışı çalışan bir soru-cevap asistanı.

`Python 3.11+` · `Microsoft Foundry Local` · `SQLite` · `Streamlit` ·
`Windows` · **16/17 test** · **~2 sn yanıt**

Microsoft **Foundry Local** ile cihaz üstünde çalışan bir dil modeli ve
**RAG (Retrieval-Augmented Generation)** deseni kullanır. İnternet bağlantısı
gerekmez; hiçbir veri cihazdan dışarı çıkmaz.

> **Not:** Bu bir eğitim projesidir. Bağlayıcı bilgi için
> [khas.edu.tr](https://www.khas.edu.tr) adresindeki resmi belgeleri esas alınız.

---

## Ne yapar?

Kullanıcı doğal dilde bir soru sorar. Sistem:

1. Soruyu bir **embedding** modeliyle vektöre çevirir
2. SQLite'ta saklanan belge parçaları arasında **anlamsal olarak en yakın**
   olanları bulur (cosine similarity)
3. Bulunan parçaları **bağlam** olarak yerel dil modeline verir
4. Model yalnızca bu bağlama dayanarak yanıt üretir ve **kaynağını gösterir**

Bilgi belgelerde yoksa uydurmaz; *"Elimdeki belgelerde bu bilgi yok."* der.

### Örnek

```
Soru> Mühendislik öğrencisi kaç iş günü staj yapar?

Cevap: Proje tabanlı bir müfredata bağlı öğrenciler için toplam 60 iş günü
(30+30), proje tabanlı değilse 40 iş günüdür.
(Mühendislik ve Doğa Bilimleri Fakültesi Staj Uygulama Esasları, Madde 2)
```

---

## Neden çevrimdışı?

Proje hiçbir veriyi dışarı göndermez; model de belgeler de bu bilgisayarda
durur. Bu bir kısıtlama değil, bilinçli bir tercih:

**Gizlilik.** Öğrenci soruları kişisel olabiliyor: "bursum kesilir mi",
"stajımı geç yaparsam ne olur". Bulut tabanlı bir asistanda bu sorular üçüncü
bir şirketin sunucusuna gider ve orada işlenir. Burada hiçbir soru bilgisayarı
terk etmiyor — KVKK açısından da en güvenli konum bu.

**Maliyet.** API ücreti yok. Kaç soru sorulursa sorulsun ek maliyet çıkmıyor;
bir üniversitede binlerce öğrenciye açılacaksa bu belirleyici bir fark.

**Kesintisizlik.** İnternet kesintisinde, kampüs ağı çöktüğünde veya sağlayıcı
servisi kapattığında çalışmaya devam eder. Sunum/demo günü internete bağlı
olmak zorunda değilsiniz.

**Tekrarlanabilirlik.** Bulut modelleri habersiz güncellenir; aynı soru üç ay
sonra farklı yanıt verebilir. Buradaki model dosyası sabit, dolayısıyla
test sonuçları (16/17) zamanla geçersizleşmiyor.

**Kurumsal onay.** "Veri dışarı çıkmıyor" diyebilmek, bir üniversitede bu tür
bir aracın hayata geçmesini kolaylaştıran en önemli cümledir.

Bunun bedeli donanım: yanıtlar bulut modellerinden yavaş (~2 saniye) ve
kullanılabilecek model boyutu ekran kartının belleğiyle sınırlı.

---

## Mimari

```
Kullanıcı sorusu
      │
      ▼
┌─────────────────┐   sorgu vektörü   ┌──────────────────────┐
│  retrieve.py    │ ────────────────► │  Foundry Local       │
│  cosine arama   │                   │  qwen3-embedding(CPU)│
└────────┬────────┘ ◄──────────────── └──────────────────────┘
         │  en yakın K parça
         ▼
┌─────────────────┐                   ┌──────────────────────┐
│   SQLite        │                   │  Foundry Local       │
│   data/khas.db  │                   │  qwen2.5-1.5b (GPU)  │
└────────┬────────┘                   └──────────┬───────────┘
         │  belge parçaları                      │
         └──────────► answer.py ─────────────────┘
                          │  bağlam + talimat
                          ▼
                      Yanıt + kaynak
```

Her şey tek makinede, tek süreçte çalışır. Ağ trafiği yoktur.

---

## Günlük kullanım

Kurulum bir kez yapılır. Sonrasında her gün tek adım:

**`baslat.bat` dosyasına çift tıklayın.**

Bu dosya Foundry Local sunucusunu başlatır, modelleri belleğe yükler ve
tarayıcıda arayüzü açar. Tarayıcı kendiliğinden açılmazsa
`http://localhost:8501` adresine gidin.

Kapatmak için: açılan siyah pencerede `Ctrl+C`, sonra pencereyi kapatın.

**Belge eklemek/güncellemek için** arayüzdeki sol panelden PDF yükleyip
"Yükle ve indeksle" düğmesine basın — yalnızca yeni belge işlenir (~10 saniye).

---

## Gereksinimler

| | |
|---|---|
| İşletim sistemi | Windows (başlatıcılar `.bat`; kod kendisi platform bağımsız) |
| Python | 3.11 veya üzeri |
| Microsoft Foundry Local | Kurulu ve `foundry` komutu PATH'te |
| Ekran kartı | NVIDIA + CUDA önerilir (4 GB yeterli). GPU yoksa çalışır ama ~15 kat yavaştır |
| Disk | Modeller için ~5 GB |

Model dosyaları büyük olduğu için `foundry config set cache-directory` ile
bol alanı olan bir diski göstermek işe yarar.

---

## Kurulum

### 1. Foundry Local — port

```bash
foundry config set port 5273 --force
```

Port `auto` bırakılırsa her yeniden başlatmada değişir ve uygulama bağlanamaz.

### 2. GPU'yu devreye alın (önemli)

Foundry Local varsayılan kurulumda modelleri **sessizce CPU'da** çalıştırır ve
katalog GPU varyantlarını hiç göstermez. Hata veya uyarı da vermez. Bu adım
atlanırsa proje çalışır ama ~15 kat yavaş olur.

```bash
py -3.12 -m venv .gpu-venv
```

```bash
.gpu-venv\Scripts\python -m pip install foundry-local-sdk
```

```bash
.gpu-venv\Scripts\python tools\enable_gpu.py
```

Ayrı bir sanal ortam gerekiyor çünkü SDK Anaconda içinde başlamıyor
(`WinError 1114`); ayrıntısı [tools/enable_gpu.py](tools/enable_gpu.py)
başındaki notta.

Doğrulama — GPU satırları görünmeli:

```bash
foundry model list --variants
```

### 3. Modelleri yükleyin

```bash
foundry model download qwen2.5-1.5b-instruct-cuda-gpu
```

```bash
foundry model load qwen2.5-1.5b-instruct-cuda-gpu
```

```bash
foundry model load qwen3-embedding-0.6b-generic-cpu
```

Sohbet modeli GPU'da, embedding CPU'da çalışır. Sebebi VRAM: bu makinede kart
4 GB ve ikisi birlikte sığmıyor (denendiğinde taşma yüzünden yavaşladı).

### 4. Python bağımlılıkları

```bash
pip install -r requirements.txt
```

### 5. Belgeleri temin edin

> **Belgeler bu depoda yer almıyor.** KHAS'ın resmi yönergeleri kurumun kendi
> dokümanlarıdır; yeniden yayımlamak yerine nereden alınacağını belirtiyoruz.

PDF'leri [khas.edu.tr](https://www.khas.edu.tr) üzerinden indirip
`khas-docs/` klasörüne koyun. Projenin beklediği on belge:

| Belge | Dosya adı (beklenen) |
|---|---|
| İİSBF Staj Uygulama Esasları | `ek1-iktisadi-idari-ve-sosyal-bilimler-fakultesi-staj-uygulama-esaslari1.pdf` |
| Mühendislik ve Doğa Bilimleri Staj Esasları | `ek2-muhendislik-ve-doga-bilimleri-fakultesi-staj-uygulama-esaslari1.pdf` |
| Sanat ve Tasarım Staj Esasları | `ek3-sanat-ve-tasarim-fakultesi-staj-uygulama-esaslari1.pdf` |
| Hukuk ve İletişim Gönüllü Staj Esasları | `ek4-hukuk-fakultesi-ve-iletisim-fakultesi-staj-uygulama-esaslari.pdf` |
| İletişim Zorunlu Staj Esasları | `ek5-iletisim-fakultesi-staj-uygulama-esaslari-...-bolumleri.pdf` |
| Lisans Burs Yönergesi | `kadir-has-universitesi-lisans-burs-yonergesi13.pdf` |
| Lisans Eğitim ve Öğretim Yönetmeliği | `kadir-has-universitesi-lisans-egitim-ve-ogretim-yonetmeligi1.pdf` |
| Lisansüstü Burs ve Destek Yönergesi | `kadir-has-universitesi-lisansustu-burs-ve-destege-iliskin-yonerge2.pdf` |
| Lisansüstü Eğitim ve Öğretim Yönetmeliği | `kadir-has-universitesi-lisansustu-egitim-ve-ogretim-yonetmeligi3.pdf` |
| 2025-2026 Öğrenim Ücretleri | `2025-2026-Yeni-Kayit-ve-Kayit-Yenileme-Ucretleri-PDF-21.08.2025.pdf` |

Dosya adları [tools/pdf_to_md.py](tools/pdf_to_md.py) içindeki `BELGE_BILGI`
sözlüğünde tanımlı; başka adla kaydederseniz orayı güncelleyin.

Sonra Markdown'a çevirin:

```bash
python tools/pdf_to_md.py
```

**Başka belgelerle çalıştırmak** isterseniz: PDF'leri `khas-docs/` içine koyup
`BELGE_BILGI` sözlüğüne birer satır ekleyin (çıktı adı, başlık, kategori,
fakülte). Ücret tablosu dışındaki tüm belgeler madde bazlı yönerge olarak
işlenir.

### 6. Veritabanını oluşturun

```bash
python src/ingest.py
```

Bu komut **artımlı** çalışır: yalnızca yeni eklenen veya içeriği değişen
belgeleri işler. Hiçbir şey değişmemişse saniyeler içinde biter.

Her şeyi baştan indekslemek için:

```bash
python src/ingest.py --tam
```

Tek bir belgeyi indekslemek için:

```bash
python src/ingest.py --dosya ucretler-2025-2026.md
```

### 7. Çalıştırın

Web arayüzü (önerilen):

```bash
streamlit run src/app.py
```

Komut satırı:

```bash
python src/main.py
```

---

## Arayüz

`streamlit run src/app.py` ile açılan web arayüzü üç bölümden oluşur:

- **Üst şerit** — indekslenmiş PDF sayısı, chunk sayısı, veritabanı durumu ve
  modelin hangi cihazda çalıştığı (GPU/CPU)
- **Sol panel** — PDF yükleme ve indeksleme, indekslenmiş belgelerin listesi.
  Belge seçmek aramayı o belgelerle sınırlar; hiçbiri seçilmezse tüm havuzda
  aranır (varsayılan davranış). Seçili belgeler **"Seçilenleri sistemden sil"**
  ile kaldırılabilir — onay istenir ve belge üç yerden birden silinir:
  kaynak PDF, üretilen Markdown ve veritabanı kayıtları. Bellekteki vektör
  önbelleği de temizlenir, yoksa arama silinmiş belgeyle çalışmaya devam eder.
- **Sağ panel** — cevap kartı, cevabın dayandığı belge parçaları (kaynak adı,
  madde ve benzerlik skoruyla), soru girişi ve Top K ayarı

Kaynak parçalarının gösterilmesi bilinçli bir tercih: kullanıcı cevabın hangi
maddeden geldiğini ve ne kadar benzer bir parçaya dayandığını görebiliyor.
Skor eşiğin (`BENZERLIK_ESIGI`) altında kaldığında model hiç çağrılmıyor ve
bu durum arayüzde belirtiliyor.

Arayüz yalnızca sunum katmanıdır; `answer.py` ve `retrieve.py`'yi CLI ile
aynı şekilde kullanır.

---

## Proje yapısı

```
local_llm/
├── baslat.bat          Günlük kullanım: sunucu + model + arayüz
├── demo-hazirla.bat    Sunum/demo öncesi hazırlık
├── khas-docs/          Kaynak PDF'ler — depoda yok, siz koyarsınız
├── docs/               PDF'lerden üretilen Markdown — üretilir, depoda yok
├── data/khas.db        SQLite: chunk'lar + embedding'ler — üretilir, depoda yok
├── src/
│   ├── config.py       Tüm ayarlar tek yerde
│   ├── ingest.py       Chunk'lama → embedding → SQLite
│   ├── retrieve.py     Anlamsal arama
│   ├── answer.py       Prompt kurma + model çağrısı
│   ├── main.py         Komut satırı arayüzü
│   └── app.py          Streamlit web arayüzü
├── tools/
│   ├── pdf_to_md.py    Bir kerelik PDF → Markdown dönüştürücü
│   └── enable_gpu.py   Foundry Local'da GPU'yu (CUDA) devreye alır
└── tests/
    ├── questions.md    Test soruları ve beklenen davranışlar
    └── run_tests.py    Test koşucusu (python tests/run_tests.py)
```

---

## Kapsanan belgeler

| Belge | Kategori |
|---|---|
| İİSBF Staj Uygulama Esasları (EK 1) | staj |
| Mühendislik ve Doğa Bilimleri Fakültesi Staj Esasları (EK 2) | staj |
| Sanat ve Tasarım Fakültesi Staj Esasları (EK 3) | staj |
| Hukuk ve İletişim Fakültesi Gönüllü Staj Esasları (EK 4) | staj |
| İletişim Fakültesi Zorunlu Staj Esasları (EK 5) | staj |
| Lisans Burs Yönergesi | lisans-burs |
| Lisans Eğitim ve Öğretim Yönetmeliği | lisans-egitim |
| Lisansüstü Burs ve Desteğe İlişkin Yönerge | lisansustu-burs |
| Lisansüstü Eğitim ve Öğretim Yönetmeliği | lisansustu-egitim |
| 2025-2026 Öğrenim Ücretleri | ucret |

---

## Tasarım kararları

### Neden ayrı bir vektör veritabanı yok?

Veri kümemiz birkaç yüz parçadan oluşuyor. Bu ölçekte tüm vektörleri belleğe
alıp NumPy ile cosine similarity hesaplamak milisaniyeler sürüyor. FAISS veya
Chroma gibi bir bağımlılık eklemek hız kazandırmaz, yalnızca kurulum ve
öğrenme yükü getirir.

### Neden madde bazlı chunk'lama?

Yönergelerde koşul ile sonuç aynı maddede yer alıyor:

> *"Proje tabanlı bir müfredata bağlı ise ... 60 iş günlük stajın ... tamamlaması gerekmektedir."*

Bu maddeyi ortadan bölersek "60 iş günü" rakamı "proje tabanlı müfredat"
koşulundan kopar ve model yanlış öğrenciye yanlış süreyi söyler. Bu yüzden
chunk'lama madde sınırlarına saygı duyar; ancak çok uzun maddeler cümle
sınırından bölünür.

### Neden her chunk'ın metnine başlık gömülüyor?

Staj süresi fakülteye ve bölüme göre değişiyor — dokuz farklı doğru cevap var.
Metadata yalnızca SQLite sütununda tutulsaydı model bunu göremezdi. Bu yüzden
her parçanın metni şöyle başlıyor:

```
[Mühendislik ... Staj Uygulama Esasları | Mühendislik ve Doğa Bilimleri Fakültesi | Madde 2]
```

### Neden ücret tablosu ayrı işleniyor?

Ücret PDF'i düz metne çevrildiğinde fakülte adları kayboluyor ve geriye
bağlamsız rakamlar kalıyor. `pdfplumber` ile **tablo olarak** çıkarıldığında
program adları, indirim oranları ve giriş yılı sütunları korunuyor.

Ama bu yetmedi. Markdown tablosu olarak yazıldığında chunk'lama başlık satırını
verilerden ayırıyordu; model elindeki tablonun hangi fakülteye ait olduğunu
göremiyordu. Düzeltip her satırı kendi başına anlamlı yaptık — yine yetmedi:
bir satırda beş yılın tutarı birlikte olduğu için model doğru fakülteyi ve
doğru indirim oranını bulmasına rağmen yanlış yıl sütununu seçiyordu
(Psikoloji %50 için 650.000 yerine aynı satırdaki 499.583,70).

Son biçim: **her tutar kendi satırında**, program + indirim oranı + giriş yılı
ile birlikte:

```
**İİSBF (Psikoloji)** bölümünde **%50 İndirimli** öğrenciler için,
**2025-2026 girişli (yeni kayıt)** öğrencinin 2025-2026 eğitim yılı
öğrenim ücreti: **650.000,00 TL** (KDV dahil nakit ödeme tutarı).
```

196 satır üretiyor ve chunk başına tek rakam düştüğü için karıştıracak
alternatif kalmıyor. Ücret grubundaki üç testin üçü de bu değişiklikle geçti.

---

### Neden indeksleme artımlı?

Başlangıçta `ingest.py` her çalıştığında tabloyu silip sıfırdan kuruyordu.
Belge sayısı arttıkça bu tek bir PDF eklemek için bile ~12 dakika demek oldu
(643 parçanın tamamı yeniden vektörleştiriliyordu).

Artık her belgenin içerik özeti (`imza`) veritabanında tutuluyor ve yalnızca
özeti değişen dosyalar yeniden işleniyor:

| Durum | Süre |
|---|---|
| Hiçbir şey değişmedi | ~1 saniye (atlanır) |
| Tek belge değişti | ~10 saniye |
| Tam yeniden indeksleme | ~12 dakika |

Üç koruma var, çünkü artımlı indeksleme dikkatsiz yapılırsa sessizce bozuk
veri üretir:

1. **Aynı belge tekrar işlenirse** eski parçaları önce silinir — yoksa aynı
   bilgi iki kez bağlama girer ve model onu daha güçlü bir sinyal sanır.
2. **Chunk boyutu veya embedding modeli değişirse** artımlı çalışmak
   güvensizdir: farklı model farklı vektör uzayı demektir, eski ve yeni
   vektörler karşılaştırılamaz. Bu yüzden `ayarlar` tablosunda bir kurulum
   imzası (`model|chunk_boyutu`) tutuluyor; değiştiğinde otomatik olarak tam
   indekslemeye düşülüyor.
3. **Şema eskiyse** (imza sütunu olmayan eski veritabanı) yine tam
   indeksleme yapılıyor.

Bu üç durumun ortak özelliği hata vermemeleri — sadece cevap kalitesinin
sessizce düşmesi. O yüzden kontrol kodun içinde, kullanıcının hatırlamasına
bırakılmadı.

---

### Neden cevap son-işlemden geçiyor?

1.5B model "TEK CÜMLE yaz" talimatına her zaman uymuyor ve cevabın ardına
bilgi taşımayan cümleler ekliyor:

> "En az 40 iş günü staj yapar. **Belgedeki açıklamaları göz önünde
> bulundurarak, bu bilginin doğru olduğu kesin olarak belirtilemez ama
> belgenin belirtilmesi gereken koşullarını gösteriyor.**"

Ayrıca token sınırına takılıp cümle ortasında kesilebiliyor:

> "…Madde: 1
> **Sonuç: Gönüllü st**"

`answer.cevabi_sadelestir()` üç şeyi ayıklar: meta-konuşma cümlelerini,
modelin eklediği özet başlıklarını (`Sonuç:`, `Özet:`, `Not:`) ve yarım kalan
son parçayı. Körü körüne ilk cümleyi almıyor, çünkü:

- Koşullu kurallar iki cümle olabiliyor ("Proje tabanlıysa 60 iş günü.
  Değilse 40 iş günü.") — ikisi de gerekli
- Tutarlardaki nokta (`1.230.000,00`) cümle sonu sanılmamalı; bölme kuralı
  "noktalama + büyük harf" ya da "satır sonu + büyük harf"
- **Kaynak satırları yarım sanılmamalı.** `Belge: İİSBF Staj Esasları,
  Madde 1` noktayla bitmez ve kısadır; ilk sürümde bu yüzden atılıyordu.
  Artık `Belge:`/`Kaynak:` ile başlayan veya madde numarasıyla biten
  parçalar sağlam kabul ediliyor.

İlk cümle her zaman korunur, sonrakiler yalnızca meta-konuşma ya da özet
başlığı değilse tutulur (en fazla 3 cümle). Test skoru değişmedi (16/17).

`MAX_TOKEN` da 80'den 160'a çıkarıldı: o sınır CPU döneminden kalmaydı ve
GPU'da gereksiz yere cevapları kesiyordu.

---

## Model seçimi ve GPU

Yedi model ölçüldü. Test seti 17 sorudan oluşuyor: cevabı belgelerde olanlar
(doğru yanıtlanmalı) ve olmayanlar (reddedilmeli). Koşucu:
`python tests/run_tests.py`

### CPU dönemi

| Model | Doğruluk | Süre | Not |
|---|---|---|---|
| qwen2.5-1.5b | 5/17 | 8.3 sn | Bağlamı yok sayıp uydurdu, Çince karakter sızdırdı |
| qwen3-1.7b / 4b | — | 13–37 sn | Yanıt öncesi İngilizce düşünme bloğu üretiyor |
| phi-3.5-mini | — | — | Türkçe'de staj/ücret kavramlarını karıştırdı |
| phi-4-mini | 8/17 | 21.6 sn | **Beş kez yanlış bilgi**: "ücret öder" (tersi), "dört yıl" |
| qwen2.5-7b | 10/17 | 30.3 sn | En doğru, ama en yavaş |

Qwen3 ailesinin düşünme modu kapatılamadı (`/no_think`, `enable_thinking`,
`chat_template_kwargs` — üçü de Foundry Local'ın ONNX çalıştırmasında etkisiz).

CPU'da hiçbir kurulum kapsamın hedeflediği 1-3 saniyeye yaklaşmadı. Ölçümler
darboğazın nerede olduğunu gösterdi: süre **tamamen bağlam uzunluğuyla
doğrusal** (~100 karakter ≈ 1 saniye) ve üretim 4.6 token/saniye. Elenen
hipotezler: swap baskısı (kaldırıldı, kazanç %18), çekirdek kullanımı
(8 çekirdek zaten tam çalışıyor), prompt caching (Foundry Local desteklemiyor),
küçük model (4B ile 7B neredeyse aynı hızda).

### GPU'ya geçiş

Asıl neden başkaydı: **Foundry Local GPU'yu sessizce kullanmıyordu.** Katalog
GPU varyantı göstermiyordu (0 GPU / 46 CPU) ve bu donanım yetersizliği gibi
görünüyordu. Oysa sorun execution provider'ların kayıtlı olmamasıydı; bir kez
kaydedilince katalog **100 GPU / 48 CPU** oldu (bkz.
[tools/enable_gpu.py](tools/enable_gpu.py)).

GPU'da prefill 110 karakter/sn'den **~1750 karakter/sn**'ye çıktı (16×).

| Kurulum | Doğruluk | Süre |
|---|---|---|
| qwen2.5-7b, CPU, TOP_K=2 | 10/17 | 30.3 sn |
| qwen2.5-7b, **GPU**, TOP_K=2 | — | 41–56 sn |
| qwen2.5-1.5b, GPU, TOP_K=2 | 9/17 | 1.9 sn |
| **qwen2.5-1.5b, GPU, TOP_K=4** | **16/17** | **2.3 sn** |

7B modelin GPU sürümü (4.7 GB) 4 GB karta yüklenebiliyor ama taşan kısım sistem
RAM'inde kaldığı için her token PCIe üzerinden gidip geliyor; sonuç CPU'dan da
yavaş. Bu kartta 7B kapalı bir kapı.

Buradaki ince nokta: GPU'da bağlam neredeyse bedava olduğu için `TOP_K`'yı
2'den 4'e çıkarabildik. **Aynı küçük model, daha geniş bağlamla, CPU'daki 7B
modelden daha doğru cevap veriyor** — CPU'da bu imkânsızdı, her ek chunk
15 saniye ekliyordu. TOP_K=5'te 11/17, TOP_K=6'da 10/17'ye düşüyor; fazla
bağlam modeli karıştırıyor, yani 4 tatlı nokta.

### Prompt biçimi

Üç varyant ölçüldü; **belgeler önce, talimatlar sonra** biçimi seçildi. Küçük
modeller en son okudukları talimata daha sadık kalıyor. Talimat kısa tutuldu
(5 satır): uzun talimatlarda küçük modeller kuralları cevabın içine kopyalıyor.

---

> **Yanıtlar yavaşladıysa:** `foundry server restart` çalıştırın. Sunucu uzun
> süre açık kalınca daha önce yüklenmiş modeller bellekte birikiyor ve VRAM
> tıkanıyor; ölçümde yanıt süresi 1.7 saniyeden 7.7 saniyeye çıkmıştı.
> `baslat.bat` bunu her açılışta kendiliğinden yapıyor.

## Bilinen sınırlamalar

- **VRAM 4 GB sınırı model seçimini kısıtlıyor.** Bu makinedeki RTX 3050'ye
  qwen2.5-7b'nin CUDA sürümü (4.7 GB) sığmıyor. Sığan en iyi seçenek 1.5B model;
  geniş bağlamla (TOP_K=4) bunu telafi ediyoruz. Daha fazla VRAM'li bir kartta
  7B modeli GPU'da çalıştırmak hem hızlı hem daha doğru olurdu.
- **Bir soru hâlâ yanlış** (17'de 16 doğru): İşletme staj süresi. Kaynak
  belgede İşletme (20 iş günü) ve Yönetim Bilişim Sistemleri (40 iş günü) aynı
  maddenin içinde geçiyor; model bazen diğerinin rakamını alıyor. Maddeyi
  bölmek kural ile koşulu ayıracağı için tercih edilmedi.
- **Ücret sorusu giriş yılını içermeli.** Ücret, öğrencinin giriş yılına göre
  değişiyor; soru yılı belirtmezse model beş tutardan birini seçiyor.
- **Embedding CPU'da çalışıyor.** Sohbet modeli + embedding birlikte 4 GB VRAM'e
  sığmıyor; ikisi birden GPU'ya alındığında taşma yüzünden yavaşladı.
- **Tek turlu.** Bot önceki soruyu hatırlamaz; "peki doktora için?" gibi takip
  soruları çalışmaz. Her soru bağımsız ve eksiksiz sorulmalıdır.
- **Yalnızca 2025-2026 ücretleri.** Başka bir akademik yıl sorulduğunda bilgi
  olmadığını söyler.
- **Belge hatalarını aynen aktarır.** Örneğin EK 4'ün başlığı "Hukuk ve
  İletişim Fakültesi" iken 6. maddesinde "Hukuk ve İşletme Fakültesi" yazıyor.
  Bu, kaynak belgenin kendi tutarsızlığıdır.

---

## Kaynaklar

- [Foundry Local nedir?](https://learn.microsoft.com/azure/ai-foundry/foundry-local/what-is-foundry-local)
- [Tutorial: Build a RAG application](https://learn.microsoft.com/azure/ai-foundry/foundry-local/tutorials/chat-application-with-open-web-ui)
- [Building Your First Local RAG Application with Foundry Local](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968)
