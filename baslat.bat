@echo off
REM ===================================================================
REM  KHAS Yonerge Asistani - tek tikla baslatma
REM
REM  Bu dosyaya cift tiklayin. Yaptiklari:
REM    1. Foundry Local sunucusunu baslatir (kapaliysa)
REM    2. Gerekli modelleri bellege yukler
REM    3. Web arayuzunu acar
REM
REM  Kapatmak icin: bu pencerede Ctrl+C, sonra pencereyi kapatin.
REM ===================================================================

cd /d "%~dp0"
echo.
echo ============================================================
echo   KHAS Yonerge Asistani baslatiliyor
echo ============================================================
echo.

REM --- 1. Foundry Local sunucusu ---------------------------------
REM restart kullaniyoruz, start degil: sunucu uzun sure acik kalinca
REM onceki testlerden yuklenmis modeller bellekte birikiyor ve VRAM tikaniyor.
REM Olculdu: tikali durumda yanit 7.7 sn, temiz baslangicta 1.7 sn.
echo [1/3] Foundry Local sunucusu yeniden baslatiliyor (temiz baslangic)...
foundry server restart >nul 2>&1
echo       sunucu hazir.

REM --- 2. Modeller ------------------------------------------------
REM Sohbet modeli GPU'da, embedding CPU'da calisir. Sebebi VRAM:
REM kart 4 GB ve ikisi birlikte sigmiyor (bkz. README).
echo [2/3] Modeller yukleniyor...
foundry model load qwen2.5-1.5b-instruct-cuda-gpu >nul 2>&1
foundry model load qwen3-embedding-0.6b-generic-cpu >nul 2>&1
echo       modeller hazir.

REM --- 3. Arayuz --------------------------------------------------
echo [3/3] Web arayuzu aciliyor...
echo. 
echo       http://localhost:8501
echo.
echo ============================================================
echo.

python -m streamlit run src\app.py

REM Streamlit kapaninca pencere hemen kapanmasin ki hata mesaji okunabilsin
echo.
echo Uygulama kapandi. Kapatmak icin bir tusa basin.
pause >nul
