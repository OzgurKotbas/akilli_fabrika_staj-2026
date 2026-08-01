import numpy as np
import cv2, os
from tqdm import tqdm

# ── Ayarlar ──────────────────────────────────────────
CONF_THRESHOLD = 1.5
POINT_STRIDE   = 4        # Bellek tasarrufu
WINDOW_FRAMES  = 60       # Kaç önceki kareyi göster
OUTPUT_DIR     = "/content/render_frames"
OUTPUT_VIDEO   = "/content/drive/MyDrive/koridor_992_pointcloud.mp4"
FPS            = 30
# ─────────────────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. NPZ yükle
print("📂 NPZ yükleniyor...")
data       = np.load("/content/koridor_992_merged.npz")
depths     = data['depth'][:,:,:,0]
confs      = data['depth_conf']
extrinsics = data['extrinsic']
intrinsics = data['intrinsic']
images     = data['images']
N, H, W    = depths.shape
print(f"✅ {N} kare, {H}x{W}")

# 2. Tüm karelerin dünya koordinatlarını hesapla
print("\n⏳ Nokta bulutları hesaplanıyor...")
world_pts  = []
world_clrs = []

for i in tqdm(range(N)):
    K  = intrinsics[i]
    E  = extrinsics[i]
    d  = depths[i]
    c  = confs[i]
    im = images[i].transpose(1,2,0)  # (H,W,3)

    mask = (c > CONF_THRESHOLD) & (d > 0) & (d < 100)
    fx, fy, cx, cy = K[0,0], K[1,1], K[0,2], K[1,2]
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    z = d
    pts_cam = np.stack([(uu-cx)*z/fx, (vv-cy)*z/fy, z], -1).reshape(-1,3)

    R, t = E[:,:3], E[:,3]
    pts_w = (pts_cam - t) @ R  # x_world = R^T(x_cam - t)

    mf   = mask.reshape(-1)
    p    = pts_w[mf][::POINT_STRIDE].astype(np.float32)
    clr  = im.reshape(-1,3)[mf][::POINT_STRIDE].astype(np.float32)
    if clr.max() > 1.5:
        clr = clr / 255.0

    world_pts.append(p)
    world_clrs.append(clr)

# 3. Her kare için render
print("\n🎬 Kareler render ediliyor...")
kernel = np.ones((3,3), np.uint8)

for i in tqdm(range(N)):
    K    = intrinsics[i]
    E    = extrinsics[i]
    R, t = E[:,:3], E[:,3]
    fx, fy, cx, cy = K[0,0], K[1,1], K[0,2], K[1,2]

    # Son WINDOW_FRAMES kareyi topla
    s    = max(0, i - WINDOW_FRAMES)
    pts  = np.concatenate(world_pts[s:i+1],  axis=0)
    clrs = np.concatenate(world_clrs[s:i+1], axis=0)

    # Kamera koordinatına projeksiyon: x_cam = R @ x_world + t
    pts_cam = pts @ R.T + t
    z       = pts_cam[:,2]
    valid   = z > 0.1

    pts_cam = pts_cam[valid]
    clrs_v  = clrs[valid]
    z       = pts_cam[:,2]

    u = (pts_cam[:,0]/z*fx + cx).astype(np.int32)
    v = (pts_cam[:,1]/z*fy + cy).astype(np.int32)

    inb = (u>=0)&(u<W)&(v>=0)&(v<H)
    u, v, clrs_v, z = u[inb], v[inb], clrs_v[inb], z[inb]

    # Uzaktan yakına sırala (yakın üste gelsin)
    idx = np.argsort(-z)
    u, v, clrs_v = u[idx], v[idx], clrs_v[idx]

    # Kanvas: siyah arka plan
    canvas = np.zeros((H, W, 3), np.uint8)
    canvas[v, u] = (clrs_v * 255).clip(0,255).astype(np.uint8)
    canvas = cv2.dilate(canvas, kernel)  # Noktaları kalınlaştır

    # Orijinal kare
    orig = images[i].transpose(1,2,0)
    if orig.max() <= 1.0:
        orig = (orig*255).astype(np.uint8)
    orig = orig.astype(np.uint8)

    # Yan yana birleştir
    combined = np.hstack([orig, canvas])
    cv2.putText(combined, f"Frame {i+1}/{N}", (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    cv2.putText(combined, "RGB Input", (10, H-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,180,180), 1)
    cv2.putText(combined, "3D Nokta Bulutu", (W+10, H-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,180,180), 1)

    cv2.imwrite(os.path.join(OUTPUT_DIR, f"frame_{i:04d}.png"),
                cv2.cvtColor(combined, cv2.COLOR_RGB2BGR))

print("✅ Tüm kareler render edildi!")

# 4. FFmpeg ile video
print("\n📹 Video oluşturuluyor...")
ret = os.system(f'ffmpeg -y -framerate {FPS} '
                f'-i "{OUTPUT_DIR}/frame_%04d.png" '
                f'-c:v libx264 -pix_fmt yuv420p "{OUTPUT_VIDEO}"')

if os.path.exists(OUTPUT_VIDEO):
    mb = os.path.getsize(OUTPUT_VIDEO)/1024/1024
    print(f"\n🎉 Video hazır! {mb:.1f} MB")
    print(f"📍 {OUTPUT_VIDEO}")
else:
    print("❌ Video oluşmadı")
