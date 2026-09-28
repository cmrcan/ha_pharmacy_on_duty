# Home Assistant Nöbetçi Eczane

İstanbul Eczacı Odası'nın güncel web servisini kullanarak İstanbul ve Yalova'daki nöbetçi eczaneleri Home Assistant'a ekler.

## Ne oluşturur?

- Her aktif eczane için bir `geo_location` entity'si. Entity durumu, Home Assistant ev konumuna kuş uçuşu mesafedir.
- Entity niteliklerinde telefon, adres, yol tarifi notu, koordinatlar, nöbet bitişi, il ve ilçe bilgileri.
- **Son başarılı kontrol** tanı sensörü.
- İsteğe bağlı **Nöbetçi Eczane Card**: bulunan eczaneleri mesafeye göre sıralar; arama ve Google Maps düğmeleri sunar.

Nöbet sona erdiğinde ilgili konum entity'si kaldırılır, yeni eczaneler otomatik eklenir. Veriler 30 dakikada bir yenilenir. İstek doğrulama anahtarı her sorguda yeniden alınır; anahtar kod içine sabitlenmez.

## Kurulum

1. `custom_components/nobetci_eczane` klasörünü Home Assistant içindeki `/config/custom_components/` klasörüne kopyalayın.
2. Home Assistant'ı yeniden başlatın.
3. **Ayarlar → Cihazlar ve Hizmetler → Entegrasyon Ekle → Nöbetçi Eczane** yolunu açın.
4. İl ve ilçeyi seçin.

## Haritada gösterme

Standart Home Assistant harita kartı, `nobetci_eczane` kaynağındaki tüm aktif konumları doğrudan gösterebilir:

```yaml
type: map
auto_fit: true
entities:
  - zone.home
geo_location_sources:
  - nobetci_eczane
```

Birden fazla ilçe eklediyseniz aynı kaynak altındaki eczaneler aynı haritada görünür.

## Özel kart

Entegrasyon kart dosyasını şu adreste sunar:

```text
/nobetci_eczane/nobetci-eczane-card.js?v=0.3.0
```

**Ayarlar → Panolar → Kaynaklar** bölümüne bu adresi `JavaScript Module` olarak bir kez ekleyin. Ardından kartı ekleyin:

```yaml
type: custom:nobetci-eczane-card
source: nobetci_eczane
district: Çekmeköy
title: Çekmeköy Nöbetçi Eczaneler
show_address: true
show_distance: true
show_directions: true
show_source: true
```

`district` isteğe bağlıdır. Kaldırıldığında `nobetci_eczane` kaynağındaki tüm ilçeler tek kartta listelenir. Kart entity adına bağımlı değildir; nöbet listesi değiştiğinde yeni `geo_location` entity'lerini otomatik bulur.

## Neden Tile yerine geo_location ve özel kart?

Tile kart sabit bir entity kimliği bekler. Nöbetçi eczaneler ise nöbet değişiminde oluşup kaybolduğu için Harita kartındaki `geo_location_sources` filtresi bu veri modeline daha uygundur. Liste, telefon ve yol tarifi işlemleri için özel kart kullanılabilir.

## 0.1.x sürümünden yükseltme

Yükseltme sırasında eski **Nöbetçi eczaneler** ve **En yakın nöbetçi eczane** özet sensörleri entity registry'den kaldırılır. Panolardaki eski sensör tabanlı kart yapılandırmasını yukarıdaki `source` tabanlı yapılandırmayla değiştirin ve kart kaynağındaki önbellek parametresini `v=0.3.0` yapın.

## Geliştirme ve npm build

Kartın düzenlenebilir kaynağı `src/nobetci-eczane-card.js` dosyasındadır. `custom_components/nobetci_eczane/static/` altındaki dosya build çıktısıdır; doğrudan düzenlemeyin.

```bash
npm ci
npm run build
```

Geliştirme sırasında değişiklikleri otomatik derlemek için:

```bash
npm run dev
```

Kart testleriyle birlikte temiz bir production build almak için:

```bash
npm test
```

Build işlemi esbuild kullanır, sürümü `package.json` içinden karta enjekte eder ve Home Assistant'ın sunduğu static dosyayı minify eder.

## Kaynak ve sınırlamalar

- Kaynak: [İstanbul Eczacı Odası Nöbetçi Eczane Uygulaması](https://www.istanbuleczaciodasi.org.tr/nobetci-eczane/)
- Desteklenen iller: İstanbul ve Yalova.
- Servis belgelenmiş genel amaçlı bir API değildir; resmî web arayüzünün kullandığı JSON yanıtı okunur.
- Mesafe, Home Assistant ev koordinatından eczaneye kuş uçuşu hesaplanır; yol mesafesi değildir.
- Koordinatı bulunmayan bir kayıt harita/konum entity'si olarak oluşturulamaz.
- Kaynağa yük bindirmemek için varsayılan yenileme aralığı 30 dakikadır.
