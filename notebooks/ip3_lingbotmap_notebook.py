# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  İP3 Tekrar — LingBot-Map Kaggle Notebook                                  ║
# ║  1034 frame limitini AŞAN tam çözüm                                         ║
# ║                                                                              ║
# ║  Bu dosyayı Kaggle'da "New Notebook" açarak HÜCRELERİ TEK TEK yapıştır.    ║
# ║  Accelerator: GPU T4 x2 seç.                                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ==============================================================================
# HÜCRE 1 — Sistem Kontrolü & GPU Doğrulama
# ==============================================================================
"""
import subprocess, platform

print("=" * 55)
print("SİSTEM BİLGİSİ")
print("=" * 55)
result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
print(result.stdout if result.returncode == 0 else "GPU bulunamadı!")

import torch
print(f"\nPyTorch   : {torch.__version__}")
print(f"CUDA var  : {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU       : {torch.cuda.get_device_name(0)}")
    print(f"VRAM      : {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
"""

# ==============================================================================
# HÜCRE 2 — LingBot-Map Kurulumu
# (İlk çalıştırmada ~5-7 dk sürer, sonra Kaggle cache'ler)
#
# ⚠️ NOT: PyTorch'u yeniden KURMA — Kaggle'da zaten yüklü geliyor.
#    Üstüne kurmak "Process is interrupted" hatasına neden olur.
# ==============================================================================
"""
%%bash
set -e

echo ">>> Mevcut PyTorch sürümü kontrol ediliyor..."
python -c "import torch; print('PyTorch:', torch.__version__, '| CUDA:', torch.cuda.is_available())"

echo ">>> Repo klonlanıyor..."
if [ ! -d "lingbot-map" ]; then
    git clone https://github.com/robbyant/lingbot-map.git
fi
cd lingbot-map

echo ">>> LingBot-Map bağımlılıkları kuruluyor (torch hariç)..."
# setup.cfg veya pyproject.toml'daki torch satırını atlayarak kur
pip install -e . --no-deps -q

# Eksik kalan bağımlılıkları elle kur (torch ve torchvision hariç)
pip install einops timm opencv-python-headless tqdm pyyaml -q
# Görselleştirme/Batch bağımlılıkları
pip install viser trimesh matplotlib onnxruntime requests -q

echo ">>> FlashInfer (opsiyonel)..."
pip install flashinfer-python -q || echo "FlashInfer atlandı, SDPA kullanılacak"

echo ">>> HuggingFace Hub (model indirmek için)..."
pip install huggingface_hub -q

echo ""
echo "✅ Kurulum tamamlandı!"
"""

# ==============================================================================
# HÜCRE 3 — Model İndirme (HuggingFace)
# (~500 MB, ~2-3 dk)
# ==============================================================================
"""
import os
from huggingface_hub import hf_hub_download

os.makedirs("/kaggle/working/models", exist_ok=True)

print("Model indiriliyor: lingbot-map-long.pt  (~500 MB)...")
print("(Bu model uzun koridorlar için optimize edilmiş)")

model_path = hf_hub_download(
    repo_id   = "robbyant/lingbot-map",
    filename  = "lingbot-map-long.pt",   # Uzun sequence için daha iyi
    local_dir = "/kaggle/working/models",
)

print(f"✅ Model hazır: {model_path}")
size_mb = os.path.getsize(model_path) / 1e6
print(f"   Boyut: {size_mb:.1f} MB")
"""

# ==============================================================================
# HÜCRE 4 — Dataset Yükle (Kaggle Dataset olarak eklediğin ZIP)
# ==============================================================================
"""
import os, json, shutil

FRAMES_DIR = "/kaggle/working/frames"

# 1. /kaggle/input içinde .jpg dosyalarının nerede olduğunu otomatik bul
kaynak_klasor = None
for root, dirs, files in os.walk("/kaggle/input"):
    if any(f.endswith(".jpg") for f in files):
        kaynak_klasor = root
        print(f"Kareler şurada bulundu: {kaynak_klasor}")
        break

if kaynak_klasor is None:
    print("❌ HATA: /kaggle/input içinde hiç .jpg dosyası bulunamadı!")
    print("Dataset'in doğru yüklendiğinden emin ol.")
else:
    # 2. Bulunan klasördeki tüm .jpg'leri çalışma dizinine (frames/) kopyala
    print(f"Kareler {FRAMES_DIR} klasörüne kopyalanıyor...")
    os.makedirs(FRAMES_DIR, exist_ok=True)
    
    kare_sayisi = 0
    for dosya in os.listdir(kaynak_klasor):
        if dosya.endswith(".jpg") or dosya.endswith(".json"):
            src = os.path.join(kaynak_klasor, dosya)
            dst = os.path.join(FRAMES_DIR, dosya)
            shutil.copy2(src, dst)
            if dosya.endswith(".jpg"):
                kare_sayisi += 1
                
    print(f"✅ {kare_sayisi} kare hazır → {FRAMES_DIR}")
    
    # Meta bilgiyi oku (varsa)
    meta_path = os.path.join(FRAMES_DIR, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        print(f"   Kaynak video : {meta.get('source_video','?')}")
        print(f"   Süre         : {meta.get('duration_sec','?')} sn")
        print(f"   Etkili FPS   : {meta.get('effective_fps','?')}")

"""

# ==============================================================================
# HÜCRE 5 — LingBot-Map Çalıştır  [1034 FRAME LİMİTİNİ ÇÖZEN HÜCRE]
# ==============================================================================
"""
# ==============================================================================
# HÜCRE 5 — LingBot-Map Çalıştır (batch_demo.py ile)
# ==============================================================================
"""
# 1034 Frame Limiti Neden Oluştu?
# Eski Colab'da "no module named frustum_cull_ext" hatası alıyordun.
# Şimdi batch_demo.py'ye --no_render veriyoruz, böylece video oluşturmayı 
# atlıyor (hata veren modül kullanılmıyor), sadece 3D noktaları NPZ'ye kaydediyor.

import subprocess, os

FRAMES_DIR   = "/kaggle/working/frames"
MODEL_PATH   = "/kaggle/working/models/lingbot-map-long.pt"
OUTPUT_DIR   = "/kaggle/working/output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

frame_count = len([f for f in os.listdir(FRAMES_DIR) if f.endswith(".jpg")])
print(f"Toplam kare: {frame_count}")

keyframe_interval = max(1, frame_count // 150)
print(f"keyframe_interval: {keyframe_interval}  (otomatik hesaplandı)")
print()
print("▶️  LingBot-Map başlatılıyor...")
print("    (Yaklaşık süre: ~3-10 dk)")
print()

cmd = [
    "python", "demo_render/batch_demo.py",
    "--input_folder",      FRAMES_DIR,
    "--output_folder",     OUTPUT_DIR,
    "--model_path",        MODEL_PATH,
    "--use_sdpa",
    # ─── BELLEK YÖNETİMİ (Windowed Mode) ───
    # window_size LingBot-Map'te "kare sayısı" değil "anahtar kare sayısı"dır!
    # 32 anahtar kare 15 GB GPU için son derece güvenlidir (asla VRAM taşmaz).
    "--mode",              "windowed",
    "--window_size",       "32",
    "--keyframe_interval", "10",
    # ────────────────────────────────────────
    "--save_predictions",
    "--no_render"
]

result = subprocess.run(
    cmd,
    cwd="/kaggle/working/lingbot-map",
    capture_output=False,
    text=True,
)

if result.returncode == 0:
    print(f"\\n✅ İnference tamamlandı. NPZ'ler kaydedildi.")
else:
    print("\\n❌ HATA — Lütfen logları kontrol et.")
"""

# ==============================================================================
# HÜCRE 6 — NPZ'den PLY (Nokta Bulutu) Oluştur  [open3d GEREKMİYOR]
# ==============================================================================
"""
import numpy as np
import os, glob, struct

NPZ_DIR    = "/kaggle/working/output/frames"
OUTPUT_PLY = "/kaggle/working/output/altin_tur_v2.ply"

def write_ply(path, pts, clrs):
    """open3d gerektirmeden saf numpy ile ikili PLY yaz."""
    n = len(pts)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {n}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
    )
    clrs_u8 = (np.clip(clrs, 0, 1) * 255).astype(np.uint8)
    with open(path, 'wb') as f:
        f.write(header.encode('ascii'))
        for i in range(n):
            f.write(struct.pack('<fff', pts[i,0], pts[i,1], pts[i,2]))
            f.write(struct.pack('BBB', clrs_u8[i,0], clrs_u8[i,1], clrs_u8[i,2]))
    print(f"PLY yazıldı: {path}  ({os.path.getsize(path)/1e6:.1f} MB)")

npz_files = sorted(glob.glob(os.path.join(NPZ_DIR, "frame_*.npz")))
print(f"NPZ klasörü: {NPZ_DIR}")
if not npz_files:
    print("❌ HATA: Hiç NPZ bulunamadı.")
else:
    print(f"Bulunan kare sayısı: {len(npz_files)}")
    world_pts, world_clrs = [], []
    STRIDE = 4   # Her 4 pikselden 1'ini al (hafıza tasarrufu)
    errors = 0

    for npz_path in npz_files:
        try:
            data  = np.load(npz_path)
            keys  = list(data.keys())

            depth     = data['depth'].squeeze()
            conf      = data['depth_conf'].squeeze()
            extrinsic = data['extrinsic'].squeeze()
            intrinsic = data['intrinsic'].squeeze()
            img       = data['images'].squeeze()

            if img.ndim == 3 and img.shape[0] == 3:
                img = img.transpose(1, 2, 0)     # (H,W,3)

            H, W = depth.shape
            fx, fy = intrinsic[0,0], intrinsic[1,1]
            cx, cy = intrinsic[0,2], intrinsic[1,2]

            mask = (conf > 1.5) & (depth > 0.05) & (depth < 200)

            uu, vv = np.meshgrid(np.arange(W), np.arange(H))
            z = depth
            pts_cam = np.stack([(uu-cx)*z/fx, (vv-cy)*z/fy, z], -1).reshape(-1,3)

            R = extrinsic[:3, :3]
            t = extrinsic[:3, 3]
            pts_w = (pts_cam - t) @ R

            mf = mask.reshape(-1)
            p   = pts_w[mf][::STRIDE].astype(np.float32)
            clr = img.reshape(-1,3)[mf][::STRIDE].astype(np.float32)
            if clr.max() > 1.5:
                clr = clr / 255.0

            world_pts.append(p)
            world_clrs.append(clr)
        except Exception as e:
            errors += 1

    if errors:
        print(f"⚠️  {errors} kare atlandı (NPZ okuma hatası)")

    pts  = np.concatenate(world_pts,  axis=0)
    clrs = np.concatenate(world_clrs, axis=0)
    print(f"Toplam Nokta: {len(pts):,}")

    os.makedirs(os.path.dirname(OUTPUT_PLY), exist_ok=True)
    write_ply(OUTPUT_PLY, pts, clrs)
    print(f"\n✅ 3D Harita Hazır: {OUTPUT_PLY}")
"""

# ==============================================================================
# HÜCRE 7 — Google Drive'a Yükle
# ==============================================================================
"""
# ── Adım 1: Kütüphane kur ────────────────────────────────────────────────────
import subprocess
subprocess.run(['pip', 'install', 'pydrive2', '-q'], check=True)
print("✅ pydrive2 kuruldu")
"""

# ==============================================================================
# HÜCRE 8 — Drive OAuth + Yükle
# (Hücre 7 bittikten sonra çalıştır)
# ==============================================================================
"""
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

PLY_PATH = "/kaggle/working/output/altin_tur_v2.ply"

# 1. OAuth bağlantısı kur — bir URL gösterecek
#    URL'ye git → Google hesabını onayla → kodu kopyala → buraya yapıştır
gauth = GoogleAuth()
gauth.CommandLineAuth()

# 2. Drive'a bağlan
drive = GoogleDrive(gauth)

# 3. Dosyayı yükle
print(f"Yükleniyor: {PLY_PATH}")
size_mb = os.path.getsize(PLY_PATH) / 1e6
print(f"Boyut: {size_mb:.1f} MB  (~{size_mb/10:.0f} dk)")

file_obj = drive.CreateFile({'title': 'altin_tur_v2.ply'})
file_obj.SetContentFile(PLY_PATH)
file_obj.Upload()

print(f"\n✅ Google Drive'a yüklendi!")
print(f"   Görüntüle: https://drive.google.com/file/d/{file_obj['id']}/view")
"""
