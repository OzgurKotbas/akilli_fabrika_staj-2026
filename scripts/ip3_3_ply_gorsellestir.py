"""
İP3 Tekrar — 3. Adım: PLY → Nokta Bulutu Görselleştirme
=========================================================
Kaggle'dan indirdiğin .ply dosyasını açar ve görselleştirir.
Yerel makinende çalıştır:

    pip install open3d
    python ip3_tekrar/scripts/3_ply_gorsellestir.py ip3_tekrar/outputs/altin_tur_v2.ply

Çıktı:
    ip3_tekrar/outputs/pointcloud_screenshot.png
"""

import sys
import os
import numpy as np

try:
    import open3d as o3d
except ImportError:
    print("[HATA] open3d kurulu değil. Kur: pip install open3d")
    sys.exit(1)


def ply_gorsellestir(ply_path):
    if not os.path.exists(ply_path):
        print(f"[HATA] PLY dosyası bulunamadı: {ply_path}")
        sys.exit(1)

    print(f"📂 Yükleniyor: {ply_path}")
    pcd = o3d.io.read_point_cloud(ply_path)

    pts = np.asarray(pcd.points)
    print(f"✅ {len(pts):,} nokta yüklendi")
    print(f"   X aralığı: [{pts[:,0].min():.2f}, {pts[:,0].max():.2f}]")
    print(f"   Y aralığı: [{pts[:,1].min():.2f}, {pts[:,1].max():.2f}]")
    print(f"   Z aralığı: [{pts[:,2].min():.2f}, {pts[:,2].max():.2f}]")

    # Gürültü temizle (isteğe bağlı)
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    print(f"   Gürültü sonrası: {len(np.asarray(pcd.points)):,} nokta")

    # Ekran görüntüsü kaydet
    out_dir = os.path.join(os.path.dirname(ply_path))
    screenshot_path = os.path.join(out_dir, "pointcloud_screenshot.png")

    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="İP3 — Altın Tur 3D Harita", width=1280, height=720, visible=False)
    vis.add_geometry(pcd)

    # Renklendirme — yüksekliğe göre (Z ekseni)
    if not pcd.has_colors():
        z_vals = np.asarray(pcd.points)[:, 2]
        z_norm = (z_vals - z_vals.min()) / (z_vals.max() - z_vals.min() + 1e-8)
        colors = np.zeros((len(z_vals), 3))
        colors[:, 0] = z_norm          # Kırmızı = yüksek
        colors[:, 2] = 1 - z_norm      # Mavi = alçak
        pcd.colors = o3d.utility.Vector3dVector(colors)

    opt = vis.get_render_option()
    opt.background_color = np.array([0.05, 0.05, 0.05])
    opt.point_size = 1.5

    vis.update_geometry(pcd)
    vis.poll_events()
    vis.update_renderer()
    vis.capture_screen_image(screenshot_path)
    vis.destroy_window()

    print(f"\n📸 Screenshot  →  {screenshot_path}")
    print()
    print("─" * 50)
    print("İnteraktif görüntüleme için:")
    print("    o3d.visualization.draw_geometries([pcd])")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Varsayılan yol
        default = os.path.join(os.path.dirname(__file__), "..", "outputs", "altin_tur_v2.ply")
        if os.path.exists(default):
            ply_gorsellestir(default)
        else:
            print("Kullanım: python 3_ply_gorsellestir.py <ply_dosyasi>")
            sys.exit(1)
    else:
        ply_gorsellestir(sys.argv[1])
