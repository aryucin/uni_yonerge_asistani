"""Foundry Local'da GPU'yu (CUDA) devreye alir.

NEDEN GEREKLI
-------------
Foundry Local varsayilan kurulumda modelleri sessizce CPU'da calistirir.
Katalog GPU varyantlarini HIC GOSTERMEZ; "foundry model list --variants"
ciktisinda her sey CPU gorunur. Bu, donanimin yetersiz oldugu anlamina
gelmez -- execution provider'lar (EP) kayitli olmadigi icin katalog onlari
listelemez. Hicbir hata veya uyari da vermez.

Bu betik EP'leri bir kez indirip kaydeder. Sonrasinda katalogda GPU
varyantlari gorunur (bu makinede 0 -> 100 varyant).

ANACONDA UYARISI
----------------
SDK Anaconda ortaminda baslamiyor:
    OSError [WinError 1114] DLL initialization routine failed
Sebep: SDK kendi onnxruntime.dll'ini on-yuklemeye calisiyor ama
C:\Windows\System32\onnxruntime.dll ile surum catismasi oluyor.
Cozum: ayri bir temiz sanal ortam kullanmak (asagida anlatiliyor).

KULLANIM
--------
    py -3.12 -m venv .gpu-venv
    .gpu-venv\Scripts\python -m pip install foundry-local-sdk
    .gpu-venv\Scripts\python tools\enable_gpu.py

Sonra GPU varyantlarini indirip yukleyin:
    foundry model download qwen2.5-1.5b-instruct-cuda-gpu
    foundry model load     qwen2.5-1.5b-instruct-cuda-gpu

Bu betik yalnizca kurulum icindir; uygulama (src/) SDK'ya hic dokunmaz,
Foundry Local'in OpenAI-uyumlu HTTP ucuna baglanir.
"""

import sys
import time


def main() -> int:
    try:
        from foundry_local_sdk import Configuration, FoundryLocalManager
    except ImportError:
        print("HATA: foundry-local-sdk kurulu degil.\n"
              "  pip install foundry-local-sdk")
        return 1

    print("SDK baslatiliyor...")
    try:
        FoundryLocalManager.initialize(Configuration(app_name="khas-gpu-setup"))
    except OSError as hata:
        print(f"HATA: SDK baslatilamadi -> {hata}")
        print("\nWinError 1114 aldiysaniz Anaconda ortamindasiniz demektir.")
        print("Temiz bir sanal ortam kullanin (dosyanin basindaki nota bakin).")
        return 1

    mgr = FoundryLocalManager.instance

    print("\nMevcut execution provider'lar:")
    for ep in mgr.discover_eps():
        print(f"  {ep.name:<34} kayitli={ep.is_registered}")

    print("\nEP'ler indiriliyor ve kaydediliyor (birkac dakika surebilir)...")
    gorulen: dict[str, int] = {}

    def ilerleme(ad: str, oran: float) -> None:
        yuzde = int(oran * 100) if oran <= 1 else int(oran)
        if gorulen.get(ad) != yuzde // 20:       # her %20'de bir yaz
            gorulen[ad] = yuzde // 20
            print(f"  {ad}: %{yuzde}", flush=True)

    t0 = time.time()
    sonuc = mgr.download_and_register_eps(progress_callback=ilerleme)
    print(f"\nBitti ({time.time() - t0:.0f} saniye)")
    print(f"  basarili : {sonuc.success}")
    print(f"  kaydedilen: {', '.join(sonuc.registered_eps) or '-'}")
    if sonuc.failed_eps:
        print(f"  basarisiz : {', '.join(sonuc.failed_eps)}")

    print("\nSon durum:")
    for ep in mgr.discover_eps():
        print(f"  {ep.name:<34} kayitli={ep.is_registered}")

    print("\nDogrulama:  foundry model list --variants    (GPU satirlari gorunmeli)")
    return 0 if sonuc.success else 1


if __name__ == "__main__":
    sys.exit(main())
