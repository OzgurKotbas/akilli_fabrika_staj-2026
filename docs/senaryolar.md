# Anomali Senaryoları — Görsel Devriye Sistemi
**Proje:** Görsel Anomali Tespiti + Otomatik Devriye Raporu (İP2)
**Tarih:** 10.08.2026 | **Yazar:** Özgür Kotbaş

> Bu doküman, robotun devriye sırasında tespit etmesi beklenen anormallik türlerini
> **öncelik sırasıyla** listeler. Öncelik; güvenlik riski, tespit zorlugu ve
> proje kapsamıyla iş birlikte belirlendi.

---

## Öncelik 1 — Yüksek Risk / Acil Müdahale Gerektirir

### S1 · Yerde Bırakılmış / Duran Cisim
**Neden öncelikli?** Çalışan güvenliğini doğrudan tehdit eder — düşme, takılma, çarpmaca riski.

| Alan | Detay |
|------|-------|
| **Örnekler** | Su şişesi, alet çantası, palet, koli, kablo sarımı |
| **Tespit yöntemi** | Altın tur ile referans kıyası (ORB + fark maskesi) |
| **Bitti kriteri** | Bounding box ile konumlandırılmış, raporda "Zemin engeli" uyarısı |
| **Zorluğu** | Düşük — nesne zemine oturur, gölge hariç belirgin |
| **Test senaryosu** | ✅ `ip8_test`: engel.mp4 — WP1 su şişesi testi yapıldı |

---

### S2 · Acil Çıkış Kapısı Durumu (Açık / Kapalı Anomali)
**Neden öncelikli?** Normalde kapalı tutulması gereken yangın/acil çıkış kapısının açık kalması güvenlik ihlalidir; ya da tersi — normalde açık geçiş kapısının kapatılması koridoru tıkar.

| Alan | Detay |
|------|-------|
| **Örnekler** | Yangın kapısı açık kalmış, çelik kapı engel koyularak kilitlenmiş |
| **Tespit yöntemi** | Waypoint kare kıyası — kapı bölgesindeki piksel farkı + bounding box |
| **Bitti kriteri** | Raporda "Kapı durumu değişikliği" uyarısı + referans karesiyle yan yana |
| **Zorluğu** | Orta — aydınlatma farkı kapıyı "açık gibi" gösterebilir |
| **Test senaryosu** | ✅ `ip8_test`: engel.mp4 — WP3 kapalı kapı testi yapıldı |

---

## Öncelik 2 — Orta Risk / Günlük Kontrol

### S3 · Yola / Koridora Bırakılan Büyük Engel
**Neden?** Forklift veya robot hareket yolunu bloke edebilir, iş akışını durdurur.

| Alan | Detay |
|------|-------|
| **Örnekler** | Çöp kovası, taşıma arabası, bariyer/koni, boş palet |
| **Tespit yöntemi** | Referans kıyası (S1 ile aynı pipeline, farklı min_area eşiği) |
| **Bitti kriteri** | Raporda "Yol engeli" uyarısı, waypoint + konum bilgisiyle |
| **Zorluğu** | Düşük-orta — büyük nesne, yüksek piksel farkı |
| **Test senaryosu** | ✅ `ip8_test`: engel.mp4 — WP2 çöp kovası testi yapıldı |

---

### S4 · Zemin Sızıntısı / Su Birikintisi
**Neden?** Kayma riski (iş kazası) ve makine arızasının erken belirtisi.

| Alan | Detay |
|------|-------|
| **Örnekler** | Yağ sızıntısı, su birikintisi, kimyasal döküntü |
| **Tespit yöntemi** | HSV renk kanalı farkı — zemin rengi değişimi (parlak/koyu leke) |
| **Bitti kriteri** | Heatmap'te zemin bölgesinde yüksek skor → rapor uyarısı |
| **Zorluğu** | Yüksek — yansıma ve aydınlatma farkıyla karışabilir |
| **Test senaryosu** | ⬜ Henüz test edilmedi |

---

### S5 · Yangın Tüpü Eksik veya Yerinden Oynatılmış
**Neden?** Acil durumda erişilemeyen tüp ciddi güvenlik ihlali; periyodik kontrol zorunluluğu var.

| Alan | Detay |
|------|-------|
| **Örnekler** | Tüp duvardaki askısından alınmış, yere devrilmiş, farklı konuma taşınmış |
| **Tespit yöntemi** | Waypoint kıyası — sabit noktadaki renk/şekil kaybı |
| **Bitti kriteri** | Raporda "Yangın güvenlik ekipmanı eksik" uyarısı |
| **Zorluğu** | Orta — kırmızı renk belirgin ama küçük nesne |
| **Test senaryosu** | ⬜ Henüz test edilmedi |

---

## Öncelik 3 — Düşük Risk / Haftalık / Periyodik Kontrol

### S6 · Uyarı / Bilgi Levhası Eksik veya Değişmiş
**Neden?** Yanlış yönlendirme (tahliye, tehlikeli madde ikaz) iş güvenliği açısından önemli.

| Alan | Detay |
|------|-------|
| **Örnekler** | İkaz levhası söküldü, tahliye yönü değişti, makine uyarısı kapandı |
| **Tespit yöntemi** | Belirli bölgede metin/logo değişimi — yüzey fark maskesi |
| **Bitti kriteri** | "Levha değişikliği" uyarısı, referans+güncel yan yana |
| **Zorluğu** | Yüksek — küçük değişiklik, mesafeye bağlı çözünürlük |
| **Test senaryosu** | ⬜ Henüz test edilmedi |

---

### S7 · Kablo veya Hortum Karmaşası / Zemin Kablaj
**Neden?** Takılma riski ve elektrik güvenliği.

| Alan | Detay |
|------|-------|
| **Örnekler** | Uzatma kablosu koridorda açık bırakılmış, hortum zemine sarkmış |
| **Tespit yöntemi** | İnce-uzun nesne tespiti — kontur şekli analizi |
| **Bitti kriteri** | Raporda "Zemin kablaj" uyarısı |
| **Zorluğu** | Çok yüksek — ince nesne, zeminle renk benzerliği |
| **Test senaryosu** | ⬜ Henüz test edilmedi |

---

## Özet Tablo

| # | Senaryo | Risk | Tespit Zorluğu | Test Edildi mi? |
|---|---------|------|----------------|-----------------|
| S1 | Yerde duran cisim | 🔴 Yüksek | ⭐ Kolay | ✅ |
| S2 | Kapı durumu anomalisi | 🔴 Yüksek | ⭐⭐ Orta | ✅ |
| S3 | Yol/koridor engeli | 🟠 Orta | ⭐ Kolay | ✅ |
| S4 | Zemin sızıntısı | 🟠 Orta | ⭐⭐⭐ Zor | ⬜ |
| S5 | Yangın tüpü eksik | 🟠 Orta | ⭐⭐ Orta | ⬜ |
| S6 | Levha değişikliği | 🟡 Düşük | ⭐⭐⭐ Zor | ⬜ |
| S7 | Zemin kablaj | 🟡 Düşük | ⭐⭐⭐ Çok Zor | ⬜ |

---

## Kapsam Dışı (Şimdilik)

Aşağıdaki senaryolar bu staj kapsamında **hedeflenmemiştir**; gelecek çalışma olarak not edilir:

- Duman / buhar tespiti (video seviyesinde optik akış gerektirir)
- Yüz tanıma / yetkisiz kişi tespiti (KVKK kapsamı, ayrı sistem)
- Makine üzerinde arıza izi (yüzey anomali modeli — MVTec-AD tipi veri gerektirir)
- Termal kamera entegrasyonu (donanım bağımlı)

---

> **Not:** S1–S3 senaryoları `ip8_test/` klasöründeki pipeline ile test edilmiş ve
> 3/3 başarıyla tespit edilmiştir. S4–S7 gelecek iş paketlerinde (İP12 eşik ayarı)
> ele alınabilir.
