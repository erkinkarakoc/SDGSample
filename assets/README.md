# Kaynak varlıklar

| Dosya | Model / yazar | Kaynak | Kaynakta belirtilen lisans |
|---|---|---|---|
| `car.blend` | Aston martin vantage — abd3d | https://www.blenderkit.com/asset-gallery-detail/13b87d90-9d7f-4b26-bcff-d782821588f4/ | CC0 |
| `road_truck.blend` | Pinzgauer — Ermia J | https://www.blenderkit.com/asset-gallery-detail/f71a3c39-7279-4206-ae19-d5b861318f48/ | Royalty Free |

BlenderKit/Blendkit API yanıtları `sources/car.json` ve `sources/road_truck.json` içinde saklanmıştır. Her örnekte kullanılan `.blend` dosyalarının SHA256 hash'leri kaydedilir. Kamyonun 1K doku sürümü kullanılır.

Materyaller uyarlanır: otomobil boyası PBR materyalle değiştirilir, camlar opak yansıtıcıdır, kamyon gövde/kumaş dokuları renklendirilir. Otomobilin ayrı logo mesh'leri çıkarılır. Kaynak model tasarımının veya başka işaretlerin bütün hukuki haklarının bize geçtiği iddia edilmez.

[Lisans açıklaması](https://www.blendkit.com/docs/licenses/) ve [Lisans FAQ](https://www.blendkit.com/docs/licenses/licensing-faq/) render kullanımına izin verir. Royalty Free kaynak varlığın bağımsız model olarak yeniden satış/dağıtımına izin veren bir CC0 lisansı değildir. Yerel dosyalar üretim girdisidir; görüntü ve anotasyonlar kaynak dosyalardan ayrı tutulur.

Orijinal varlıklar Blender 3.2 ve 3.5 sürümlerindendir. Blender 3.4.1 ile yükleme ve render denenmiştir; rig animasyonu kullanılmaz, evaluated mesh'ler statik olarak alınır. Dış blend dosyalarının Python script'leri çalıştırılmaz (`--disable-autoexec`).

Dosyalar kaybolursa `fetch_assets.py`, kayıtlı resmi download endpoint'lerinden aynı dosyaları indirir ve `manifest.json` SHA256 değerleriyle doğrular. Yerelde doğru dosya zaten varsa ağa bağlanmadan atlar. Gelecekte kaynak hizmetin erişim koşulları değişirse indirme kullanılamayabilir.
