"""KHAS Yönerge Asistanı — Streamlit arayüzü.

Kapsamın Week 5 "Option B" adımı. CLI (main.py) ile aynı çekirdeği kullanır;
arayüz yalnızca sunum katmanıdır, iş mantığı answer.py / retrieve.py'de.

Çalıştırma:
    streamlit run src/app.py
"""

import subprocess
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from answer import BILGI_YOK, answer_query  # noqa: E402
from retrieve import onbellegi_temizle  # noqa: E402

st.set_page_config(page_title="KHAS Yönerge Asistanı", page_icon="K", layout="wide")

STIL = """
<style>
  .ust-baslik {font-size: 1.5rem; font-weight: 700; margin-bottom: .1rem;}
  .ust-alt {color: #6b7280; font-size: .86rem;}
  .rozet {
    display:inline-block; background:#f3f4f6; color:#374151;
    border:1px solid #e5e7eb; border-radius:999px;
    padding:.18rem .7rem; font-size:.78rem; margin-left:.35rem;
  }
  .rozet-yesil {background:#ecfdf5; color:#065f46; border-color:#a7f3d0;}
  .rozet-sari  {background:#fffbeb; color:#92400e; border-color:#fde68a;}
  .kart {
    background:#fff; border:1px solid #e5e7eb; border-radius:10px;
    padding:.8rem 1rem; margin-bottom:.65rem;
  }
  .kaynak-ust {font-size:.82rem; margin-bottom:.3rem;}
  .kaynak-ad {font-weight:600; color:#111827;}
  .kaynak-etiket {color:#6b7280;}
  .kaynak-metin {font-size:.85rem; color:#374151; line-height:1.45;}
  .cevap-kart {
    background:#f8fafc; border:1px solid #dbeafe; border-left:4px solid #3b82f6;
    border-radius:10px; padding:1rem 1.15rem; margin-bottom:1rem;
  }
  .cevap-metin {font-size:1.02rem; color:#0f172a; line-height:1.55;}
  .chunk-sayi {color:#9ca3af; font-size:.75rem;}
  .bos-durum {color:#9ca3af; font-size:.9rem; padding:2.2rem 0; text-align:center;}
</style>
"""
st.markdown(STIL, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Veri yardimcilari
# --------------------------------------------------------------------------
def db_durumu() -> tuple[int, list[tuple[str, str, int]]]:
    """(toplam chunk, [(kaynak, md_dosyasi, adet), ...]); yoksa (0, [])."""
    import sqlite3

    if not config.DB_YOLU.exists():
        return 0, []
    try:
        with sqlite3.connect(config.DB_YOLU) as b:
            toplam = b.execute("SELECT COUNT(*) FROM chunklar").fetchone()[0]
            dagilim = b.execute(
                "SELECT kaynak, MAX(dosya), COUNT(*) FROM chunklar"
                " GROUP BY kaynak ORDER BY 3 DESC"
            ).fetchall()
        return toplam, dagilim
    except sqlite3.Error:
        return 0, []


def pdf_listesi() -> list[Path]:
    if not config.PDF_DIZIN.exists():
        return []
    return sorted(config.PDF_DIZIN.glob("*.pdf"))


def betik_calistir(betik: Path, *ekler: str) -> tuple[bool, str]:
    """Hazirlik betiklerini ayri surecte calistirir (pdf_to_md / ingest)."""
    sonuc = subprocess.run(
        [sys.executable, "-u", str(betik), *ekler],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(config.PROJE_KOK),
    )
    return sonuc.returncode == 0, ((sonuc.stdout or "") + (sonuc.stderr or ""))[-3000:]


def belge_sil(md_dosyasi: str) -> str:
    """Bir belgeyi sistemden tamamen kaldirir.

    Uc yerden birden silmek gerekiyor, yoksa belge kismen yasamaya devam eder:
      1. docs/*.md      - yoksa bir sonraki indekslemede geri gelir
      2. khas-docs/*.pdf - yoksa "Yukle ve indeksle" onu tekrar isler
      3. veritabani      - yoksa bot silinmis belgeden cevap vermeye devam eder
    Ayrica bellekteki vektor onbellegi temizlenir; o da guncellenmezse arama
    hala eski veriyle calisir.
    """
    import sqlite3

    silinenler = []
    md_yolu = config.MD_DIZIN / md_dosyasi
    if md_yolu.exists():
        # Frontmatter'daki "dosya:" alani kaynak PDF'in adini tutuyor
        try:
            ilk = md_yolu.read_text(encoding="utf-8").split("---", 2)
            for satir in (ilk[1] if len(ilk) > 2 else "").splitlines():
                if satir.strip().startswith("dosya:"):
                    pdf_adi = satir.split(":", 1)[1].strip()
                    pdf_yolu = config.PDF_DIZIN / pdf_adi
                    if pdf_yolu.exists():
                        pdf_yolu.unlink()
                        silinenler.append(pdf_adi)
        except (OSError, IndexError):
            pass
        md_yolu.unlink()
        silinenler.append(md_dosyasi)

    with sqlite3.connect(config.DB_YOLU) as b:
        b.execute("DELETE FROM chunklar WHERE dosya = ?", (md_dosyasi,))
        b.commit()

    onbellegi_temizle()
    return ", ".join(silinenler) or md_dosyasi


def cihaz_adi(model_id: str) -> str:
    return "GPU (CUDA)" if "cuda" in model_id.lower() else "CPU"


# --------------------------------------------------------------------------
# Ust bar
# --------------------------------------------------------------------------
toplam_chunk, dagilim = db_durumu()
pdfler = pdf_listesi()

ust_sol, ust_sag = st.columns([3, 2])
with ust_sol:
    st.markdown(
        '<div class="ust-baslik">KHAS Yonerge Asistani</div>'
        '<div class="ust-alt">Staj, burs, ucret ve lisansustu sorularini resmi '
        'KHAS belgelerine dayanarak yanitlar. Tamamen cevrimdisi calisir.</div>',
        unsafe_allow_html=True,
    )
with ust_sag:
    db_rozet = ('<span class="rozet rozet-yesil">DB hazir</span>' if toplam_chunk
                else '<span class="rozet rozet-sari">DB bos</span>')
    st.markdown(
        '<div style="text-align:right; padding-top:.4rem;">'
        f'<span class="rozet">{len(pdfler)} PDF</span>'
        f'<span class="rozet">{toplam_chunk} chunk</span>'
        f'{db_rozet}'
        f'<span class="rozet">{cihaz_adi(config.SOHBET_MODELI)}</span>'
        '</div>',
        unsafe_allow_html=True,
    )

st.divider()
sol, sag = st.columns([1, 2.2], gap="medium")

# --------------------------------------------------------------------------
# Sol panel - belgeler
# --------------------------------------------------------------------------
with sol:
    st.markdown("#### Belge Yukle")
    yuklenen = st.file_uploader(
        "PDF dosyalari", type=["pdf"], accept_multiple_files=True,
        label_visibility="collapsed",
    )

    b1, b2 = st.columns(2)
    yukle_bas = b1.button("Yukle ve indeksle", type="primary", use_container_width=True)
    indeksle_bas = b2.button("Degisenleri indeksle", use_container_width=True)
    tam_indeks = st.checkbox(
        "Her seyi bastan indeksle",
        help="Normalde yalnizca yeni veya degismis belgeler islenir (hizli). "
             "Bu secenek tum belgeleri yeniden vektorlestirir; chunk ayarlari "
             "degistiyse gereklidir.",
    )

    if yukle_bas or indeksle_bas:
        if yuklenen:
            config.PDF_DIZIN.mkdir(parents=True, exist_ok=True)
            for dosya in yuklenen:
                (config.PDF_DIZIN / dosya.name).write_bytes(dosya.getbuffer())
            st.success(f"{len(yuklenen)} PDF kaydedildi.")

        with st.status("Belgeler hazirlaniyor...", expanded=True) as durum:
            st.write("PDF -> Markdown donusturuluyor")
            ok1, log1 = betik_calistir(config.PROJE_KOK / "tools" / "pdf_to_md.py")
            if not ok1:
                durum.update(label="Donusturme basarisiz", state="error")
                st.code(log1)
                st.stop()

            if tam_indeks:
                st.write("Tum belgeler yeniden vektorlestiriliyor (birkac dakika)")
                ek = ("--tam",)
            else:
                st.write("Yeni ve degismis belgeler vektorlestiriliyor")
                ek = ()
            ok2, log2 = betik_calistir(config.PROJE_KOK / "src" / "ingest.py", *ek)
            if not ok2:
                durum.update(label="Indeksleme basarisiz", state="error")
                st.code(log2)
                st.stop()

            st.code("\n".join([s for s in log2.splitlines() if s.strip()][-7:]))
            durum.update(label="Tamamlandi", state="complete")
        
        # Indeksleme ayri surecte calisti; bu surecteki vektor onbellegi
        # hala eski. Temizlenmezse yeni belge aramaya hic girmez.
        onbellegi_temizle()
        st.session_state.pop("son_sonuc", None)
        st.rerun()

    st.markdown("#### Dokumanlar")
    if not dagilim:
        st.info("Henuz indekslenmis belge yok. Yukaridan indeksleyin.")
        st.session_state["secili_kaynaklar"] = []
    else:
        s1, s2 = st.columns(2)
        if s1.button("Tumunu sec", use_container_width=True):
            for kaynak, _, _ in dagilim:
                st.session_state[f"blg_{kaynak}"] = True
            st.rerun()
        if s2.button("Secimi kaldir", use_container_width=True):
            for kaynak, _, _ in dagilim:
                st.session_state[f"blg_{kaynak}"] = False
            st.rerun()

        secili: list[str] = []
        secili_dosyalar: list[str] = []
        for kaynak, md_dosyasi, adet in dagilim:
            if st.checkbox(kaynak, key=f"blg_{kaynak}"):
                secili.append(kaynak)
                secili_dosyalar.append(md_dosyasi)
            st.markdown(
                f'<div class="chunk-sayi" style="margin:-.55rem 0 .45rem 1.7rem;">'
                f'{adet} chunk</div>',
                unsafe_allow_html=True,
            )

        st.caption(
            f"{len(secili)} belge secili - arama bunlarla sinirli"
            if secili else "Belge secilmedi - tum belgelerde aranir"
        )
        st.session_state["secili_kaynaklar"] = secili

        # --- Secilenleri sistemden kaldir (iki asamali onay) ---
        if secili_dosyalar:
            if st.session_state.get("silme_onayi"):
                st.warning(
                    f"{len(secili_dosyalar)} belge kalici olarak silinecek: "
                    "PDF, Markdown ve veritabani kayitlari."
                )
                o1, o2 = st.columns(2)
                if o1.button("Evet, sil", type="primary", use_container_width=True):
                    for md_dosyasi in secili_dosyalar:
                        belge_sil(md_dosyasi)
                    for kaynak in secili:
                        st.session_state.pop(f"blg_{kaynak}", None)
                    st.session_state["silme_onayi"] = False
                    st.session_state.pop("son_sonuc", None)
                    st.rerun()
                if o2.button("Vazgec", use_container_width=True):
                    st.session_state["silme_onayi"] = False
                    st.rerun()
            elif st.button("Secilenleri sistemden sil", use_container_width=True):
                st.session_state["silme_onayi"] = True
                st.rerun()

# --------------------------------------------------------------------------
# Sag panel - soru ve cevap
# --------------------------------------------------------------------------
with sag:
    sonuc = st.session_state.get("son_sonuc")

    if sonuc:
        st.markdown(f"**{sonuc['soru']}**")
        st.markdown(
            f'<div class="cevap-kart"><div class="cevap-metin">{sonuc["cevap"]}</div></div>',
            unsafe_allow_html=True,
        )
        if sonuc["cevap"] != BILGI_YOK and sonuc["chunklar"]:
            st.caption(f"Kullanilan belgeler - {sonuc['sure']:.1f} sn")
            for i, c in enumerate(sonuc["chunklar"], 1):
                # Chunk metninin ilk satiri gomulu baslik; onizlemede govdeyi gosteriyoruz.
                govde = c["icerik"].split("\n", 1)[-1].replace("\n", " ")[:260]
                madde = f" - {c['madde']}" if c["madde"] else ""
                st.markdown(
                    '<div class="kart">'
                    f'<div class="kaynak-ust">{i}. '
                    f'<span class="kaynak-ad">{c["kaynak"]}</span>'
                    f'<span class="kaynak-etiket">{madde} - Skor {c["skor"]:.4f}</span></div>'
                    f'<div class="kaynak-metin">{govde}...</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption(
                f"En yuksek benzerlik esigin ({config.BENZERLIK_ESIGI}) altinda kaldi "
                f"- {sonuc['sure']:.1f} sn"
            )
    else:
        st.markdown(
            '<div class="bos-durum">Soru sorun - cevap ve dayandigi belgeler '
            'burada gorunecek.<br><br>'
            'Ornek: "Muhendislik ogrencisi kac is gunu staj yapar?"</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    soru = st.text_area(
        "Soru", height=88, label_visibility="collapsed",
        placeholder="Sorunuzu yazin... (ucret sorularinda giris yilini belirtin)",
    )
    sor = st.button("Sor", type="primary")

    k1, k2, k3 = st.columns([1, 1, 2])
    top_k = k1.number_input("Top K", min_value=1, max_value=10, value=config.TOP_K)
    k2.text_input("Cihaz", value=cihaz_adi(config.SOHBET_MODELI), disabled=True)
    k3.text_input("Model", value=config.SOHBET_MODELI, disabled=True)

    if sor and soru.strip():
        if not toplam_chunk:
            st.error("Veritabani bos. Once soldaki panelden belgeleri indeksleyin.")
        else:
            t0 = time.time()
            try:
                cevap, chunklar = answer_query(
                    soru.strip(), k=int(top_k),
                    kaynaklar=st.session_state.get("secili_kaynaklar") or None,
                )
                st.session_state["son_sonuc"] = {
                    "soru": soru.strip(),
                    "cevap": cevap,
                    "chunklar": chunklar,
                    "sure": time.time() - t0,
                }
                st.rerun()
            except Exception as hata:  # noqa: BLE001 - kullaniciya anlasilir mesaj
                st.error(
                    f"Hata: {hata}\n\n"
                    "Foundry Local calisiyor mu? Kontrol: foundry server status"
                )
