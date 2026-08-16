@echo off
chcp 65001 >nul
title Anomali Tespiti Demo — Özgür Kotbaş

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   ANOMALİ TESPİT DEMO — Özgür Kotbaş · BTÜ · 2026      ║
echo  ║   İP8 (SSIM+ORB) + İP9 (MOG2 Ensemble) Gerçek Zamanlı  ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Proje kök dizinine geç
cd /d "%~dp0"

:: Python kontrolü
where python >nul 2>&1
if errorlevel 1 (
    echo  [HATA] Python bulunamadi! Lutfen Python 3.9+ kurunuz.
    echo  https://www.python.org/downloads/
    pause
    exit /b 1
)

:: OpenCV kontrolü
python -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo  [BİLGİ] OpenCV bulunamadi, kuruluyor...
    echo.
    pip install opencv-python numpy
    echo.
)

:: scikit-image kontrolü (İP8 SSIM için)
python -c "from skimage.metrics import structural_similarity" >nul 2>&1
if errorlevel 1 (
    echo  [BİLGİ] scikit-image bulunamadi, kuruluyor...
    pip install scikit-image
    echo.
)

echo  Çalıştırılıyor...
echo.
echo  [Klavye Kısayolları]
echo    Q / ESC  - Çık
echo    SPACE    - Duraklat / Devam
echo    N        - Sonraki waypoint (Mod A)
echo    +/-      - Anomali eşiğini artır/azalt
echo    S        - Ekran görüntüsü kaydet (outputs/demo_ciktilari/)
echo.

python scripts\demo_anomali.py %*

echo.
echo  Demo tamamlandi.
pause
