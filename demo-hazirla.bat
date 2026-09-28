@echo off
REM ===================================================================
REM  DEMO HAZIRLIGI - videoyu cekmeden ONCE calistirin
REM
REM  Yaptiklari:
REM    1. Sanat ve Tasarim staj belgesini projeden gecici olarak cikarir
REM       (demo-yedek klasorune tasir, silmez)
REM    2. Foundry sunucusunu YENIDEN baslatir ve modelleri yukler
REM    3. Veritabanindan o belgenin kayitlarini temizler
REM    4. Modeli isitir (videodaki ilk soru yavas olmasin diye)
REM
REM  Video sirasinda belgeyi arayuzden geri yukleyeceksiniz:
REM       demo-yedek\ek3-sanat-ve-tasarim-fakultesi-staj-uygulama-esaslari1.pdf
REM ===================================================================

cd /d "%~dp0"
set BELGE=ek3-sanat-ve-tasarim-fakultesi-staj-uygulama-esaslari1.pdf

echo.
echo ============================================================
echo   DEMO HAZIRLIGI
echo ============================================================
echo.

REM --- 1. Belgeyi cikar -------------------------------------------
if not exist demo-yedek mkdir demo-yedek
if exist "khas-docs\%BELGE%" (
    move /y "khas-docs\%BELGE%" "demo-yedek\%BELGE%" >nul
    echo [1/4] Belge cikarildi -^> demo-yedek\%BELGE%
) else (
    echo [1/4] Belge zaten cikarilmis.
)
if exist "docs\staj-sanat-tasarim.md" del /q "docs\staj-sanat-tasarim.md"

REM --- 2. Sunucu ve modeller --------------------------------------
REM restart kullaniyoruz, start degil: sunucu uzun sure acik kalinca
REM onceki modeller bellekte birikiyor ve VRAM tikaniyor.
REM Olculdu: tikali durumda yanit 7.7 sn, temiz baslangicta 1.7 sn.
echo [2/4] Foundry sunucusu yeniden baslatiliyor ve modeller yukleniyor...
foundry server restart >nul 2>&1
foundry model load qwen2.5-1.5b-instruct-cuda-gpu >nul 2>&1
foundry model load qwen3-embedding-0.6b-generic-cpu >nul 2>&1

REM --- 3. Veritabanini temizle ------------------------------------
echo [3/4] Veritabanindan belge kayitlari siliniyor...
python src\ingest.py

REM --- 4. Modeli isit ---------------------------------------------
echo [4/4] Model isitiliyor...
echo Sanat ve Tasarim Fakultesi staj suresi kac is gunu?> "%TEMP%\khas_isinma.txt"
echo q>> "%TEMP%\khas_isinma.txt"
python src\main.py < "%TEMP%\khas_isinma.txt" >nul 2>&1
del /q "%TEMP%\khas_isinma.txt"

echo.
echo ============================================================
echo   HAZIR. Simdi baslat.bat ile arayuzu acin ve kayda baslayin.
echo.
echo   Video sirasinda yukleyeceginiz dosya:
echo   demo-yedek\%BELGE%
echo ============================================================
echo.
pause
