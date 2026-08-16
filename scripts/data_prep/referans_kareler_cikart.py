import cv2, os, yaml

# Proje dizininde çalıştırıldığını varsayıyoruz
os.makedirs("PROJE/referans_kareler", exist_ok=True)

with open("PROJE/waypoint_listesi.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

video_path = "31.07/koridor_992.mp4"
if not os.path.exists(video_path):
    print(f"[Hata] Video bulunamadi: {video_path}")
    exit(1)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)

for wp in config["waypoints"]:
    kare_no = int(wp["saniye"] * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, kare_no)
    ret, frame = cap.read()
    if ret:
        out_path = wp["referans_kare"]
        cv2.imwrite(out_path, frame)
        print(f"[OK] {wp['id']} -> {out_path}")
    else:
        print(f"[Hata] {wp['id']} okunamadi")

cap.release()
print("Tamamlandi!")
