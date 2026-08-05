New-Item -ItemType Directory -Force docs/proje_tanimi/makaleler
New-Item -ItemType Directory -Force docs/raporlar
New-Item -ItemType Directory -Force data/raw_videos
New-Item -ItemType Directory -Force data/waypoints
New-Item -ItemType Directory -Force scripts
New-Item -ItemType Directory -Force outputs/model_results

git mv PROJE/senaryo_listesi.md docs/proje_tanimi/
git mv PROJE/literatur_ozeti.md docs/proje_tanimi/
git mv PROJE/h1/30.07/Makaleler.md docs/proje_tanimi/makaleler/
git mv PROJE/h1/30.07/Notlar.md docs/proje_tanimi/makaleler/
git mv PROJE/referans_kareler data/waypoints/
git mv PROJE/waypoint_listesi.yaml data/waypoints/
git mv PROJE/referans_kareler_cikart.py scripts/

git mv 31.07/koridor_992.mp4 data/raw_videos/
git mv 31.07/koridor_992_pointcloud.mp4 data/raw_videos/
git mv 31.07/Renderer_kodu.md scripts/renderer_notlari.md
git mv 31.07/Frames_linki.txt data/raw_videos/
git mv 31.07/batch_results.json data/raw_videos/

git mv 01-02.08 outputs/model_results/01-02.08_eski
git mv h2-3 outputs/model_results/h2-3_eski
git mv results outputs/model_results/results_eski

git mv RAPORLAR/rapor.md docs/raporlar/
git mv anomali_test.py scripts/

Remove-Item -Recurse -Force PROJE
Remove-Item -Recurse -Force 31.07
Remove-Item -Recurse -Force RAPORLAR

git add .
git commit -m "refactor: lokal klasor yapisi moduler olarak duzenlendi"
