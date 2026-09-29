import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const registry = new Map();
const context = vm.createContext({
  console: { info() {} },
  HTMLElement: class {},
  customElements: {
    define: (name, constructor) => registry.set(name, constructor),
    get: (name) => registry.get(name),
  },
  window: {},
});

const bundle = await readFile(
  new URL(
    "../custom_components/nobetci_eczane/static/nobetci-eczane-card.js",
    import.meta.url,
  ),
  "utf8",
);
vm.runInContext(bundle, context);

const Card = registry.get("nobetci-eczane-card");

function createCard(config, states) {
  const card = Object.create(Card.prototype);
  card._config = config;
  card._hass = { states };
  return card;
}

test("kart doğru source ve ilçeyi mesafeye göre listeler", () => {
  const card = createCard(
    { source: "nobetci_eczane", district: "SARIYER" },
    {
      "geo_location.uzak": {
        entity_id: "geo_location.uzak",
        state: "5.2",
        attributes: {
          source: "nobetci_eczane",
          district: "Sarıyer",
          friendly_name: "Uzak",
          latitude: 41.1,
          longitude: 29.1,
        },
      },
      "geo_location.yakin": {
        entity_id: "geo_location.yakin",
        state: "1.4",
        attributes: {
          source: "nobetci_eczane",
          district: "Sarıyer",
          friendly_name: "Yakın",
          latitude: 41.2,
          longitude: 29.2,
        },
      },
      "geo_location.komsu_ilce": {
        entity_id: "geo_location.komsu_ilce",
        state: "0.8",
        attributes: {
          source: "nobetci_eczane",
          configured_district: "Sarıyer",
          district: "Beşiktaş",
          province: "İstanbul",
          friendly_name: "Komşu İlçede Daha Yakın",
          phone: "02165551234",
          phone_e164: "+902165551234",
          latitude: 41.15,
          longitude: 29.05,
        },
      },
      "geo_location.diger": {
        entity_id: "geo_location.diger",
        state: "0.2",
        attributes: { source: "other", district: "Sarıyer" },
      },
    },
  );

  assert.deepEqual(
    Array.from(card._pharmacies(), (pharmacy) => pharmacy.name),
    ["Komşu İlçede Daha Yakın", "Yakın", "Uzak"],
  );
  assert.equal(card._pharmacies()[0].phone_e164, "+902165551234");
});

test("yenileme için her ilçe koordinatöründen tek entity seçer", () => {
  const card = createCard(
    { source: "nobetci_eczane" },
    {
      "geo_location.a": {
        entity_id: "geo_location.a",
        state: "1",
        attributes: {
          source: "nobetci_eczane",
          province: "İstanbul",
          district: "Çekmeköy",
        },
      },
      "geo_location.b": {
        entity_id: "geo_location.b",
        state: "2",
        attributes: {
          source: "nobetci_eczane",
          province: "İstanbul",
          district: "Çekmeköy",
        },
      },
      "geo_location.c": {
        entity_id: "geo_location.c",
        state: "3",
        attributes: {
          source: "nobetci_eczane",
          province: "İstanbul",
          district: "Kadıköy",
        },
      },
    },
  );

  assert.deepEqual(Array.from(card._refreshEntityIds()), [
    "geo_location.a",
    "geo_location.c",
  ]);
});

test("konum yoksa tanı sensörü üzerinden yenileme yapabilir", () => {
  const card = createCard(
    { source: "nobetci_eczane", district: "Kadıköy" },
    {
      "sensor.last_check": {
        entity_id: "sensor.last_check",
        state: "2026-09-28T00:00:00+00:00",
        attributes: {
          integration: "nobetci_eczane",
          district: "Kadıköy",
        },
      },
    },
  );

  assert.deepEqual(Array.from(card._refreshEntityIds()), ["sensor.last_check"]);
});

test("kart ilk açılışta üç eczane gösterir ve genişletilince tümünü döndürür", () => {
  const card = createCard({ source: "nobetci_eczane", max_items: 3 }, {});
  const pharmacies = [1, 2, 3, 4, 5].map((id) => ({ name: `Eczane ${id}` }));

  card._expanded = false;
  assert.deepEqual(
    Array.from(card._visiblePharmacies(pharmacies), (item) => item.name),
    ["Eczane 1", "Eczane 2", "Eczane 3"],
  );
  card._expanded = true;
  assert.equal(card._visiblePharmacies(pharmacies).length, 5);
});

test("navigasyon bağlantısı cihaz platformuna uygun oluşturulur", () => {
  const card = createCard({ source: "nobetci_eczane" }, {});
  const pharmacy = {
    name: "Ebru Eczanesi",
    latitude: 41.025,
    longitude: 29.075,
  };

  assert.match(card._navigationUrl(pharmacy, "Android"), /^geo:/);
  assert.match(card._navigationUrl(pharmacy, "iPhone"), /^https:\/\/maps\.apple\.com/);
  assert.match(
    card._navigationUrl(pharmacy, "Windows NT"),
    /^https:\/\/www\.google\.com\/maps\/dir/,
  );
});
