# Anormallik Senaryo Listesi — Özgür Kotbaş
**Tarih:** 27 Temmuz 2026 · **İş Paketi:** İP2

## Tespit Edilecek Anormallikler (Öncelik Sıralı)

| # | Senaryo | Açıklama | Öncelik | Tespit Yöntemi |
|---|---------|----------|---------|----------------|
| 1 | Yerde bırakılmış nesne | Koridorda veya makine başında bırakılan alet, çanta vb. | 🔴 Yüksek | Sahne fark analizi |
| 2 | Kapatılmış acil çıkış | Acil çıkış kapısının kapalı/bloke olması | 🔴 Yüksek | Fark + anomali modeli |
| 3 | Sızıntı/döküntü izi | Zemin veya boru üzerinde sıvı lekesi | 🟡 Orta | Anomali modeli |
| 4 | Değiştirilmiş güvenlik işareti | Uyarı levhası kaldırılmış/değiştirilmiş | 🟡 Orta | Sahne fark analizi |
| 5 | Hasar görmüş ekipman | Makine üzerinde kırık, çatlak | 🟢 Düşük | Anomali modeli |

## Veri Toplama Planı

- **Normal durum (altın tur):** Koridorda tripod ile sabit rotalı video — waypoint bazlı
- **Anormal durumlar:** Her senaryo için kontrollü saha testi
- **Waypoint listesi:** Bkz. `PROJE/waypoint_listesi.yaml`

## Kapsam Dışı (V1)
- Kişi tespiti (bu Bedirhan'ın modülü)
- Gösterge okuma (Reşit'in modülü)
- Gerçek zamanlı video akışı (önce offline test)
