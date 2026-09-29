const CARD_VERSION = __CARD_VERSION__;

const COPY = {
  tr: {
    title: "Nöbetçi Eczaneler",
    unavailable: "Eczane verisi kullanılamıyor",
    empty: "Şu anda listelenen nöbetçi eczane yok",
    call: "Ara",
    route: "Yol tarifi",
    refresh: "Yenile",
    km: "km",
    source: "Kaynak",
    lastUpdate: "Son güncelleme",
    radius: "Yarıçap",
    pharmacies: "eczane",
    showAll: "Tümünü göster",
    showLess: "Daralt",
  },
  en: {
    title: "Duty Pharmacies",
    unavailable: "Pharmacy data is unavailable",
    empty: "No duty pharmacy is currently listed",
    call: "Call",
    route: "Directions",
    refresh: "Refresh",
    km: "km",
    source: "Source",
    lastUpdate: "Last update",
    radius: "Radius",
    pharmacies: "pharmacies",
    showAll: "Show all",
    showLess: "Show less",
  },
  de: {
    title: "Notdienstapotheken",
    unavailable: "Apothekendaten sind nicht verfügbar",
    empty: "Derzeit ist keine Notdienstapotheke aufgeführt",
    call: "Anrufen",
    route: "Route",
    refresh: "Aktualisieren",
    km: "km",
    source: "Quelle",
    lastUpdate: "Letzte Aktualisierung",
    radius: "Radius",
    pharmacies: "Apotheken",
    showAll: "Alle anzeigen",
    showLess: "Einklappen",
  },
};

class NobetciEczaneCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._renderedKey = "";
    this._expanded = false;
  }

  setConfig(config) {
    if (!config) {
      throw new Error("Card configuration is required");
    }
    this._config = {
      source: "nobetci_eczane",
      show_address: true,
      show_distance: true,
      show_directions: true,
      show_source: true,
      max_items: 3,
      ...config,
    };
    this._expanded = false;
    this._renderedKey = "";
    this._render();
  }

  static getConfigForm() {
    return {
      schema: [
        {
          name: "source",
          required: true,
          selector: { text: {} },
        },
        { name: "district", selector: { text: {} } },
        { name: "title", selector: { text: {} } },
        {
          name: "max_items",
          selector: { number: { min: 1, max: 10, step: 1, mode: "box" } },
        },
        {
          type: "grid",
          name: "",
          flatten: true,
          schema: [
            { name: "show_address", selector: { boolean: {} } },
            { name: "show_distance", selector: { boolean: {} } },
            { name: "show_directions", selector: { boolean: {} } },
            { name: "show_source", selector: { boolean: {} } },
          ],
        },
      ],
      computeLabel: (schema) => {
        const labels = {
          source: "Geo-location source",
          district: "District (optional)",
          title: "Title",
          max_items: "Initially visible pharmacies",
          show_address: "Show address",
          show_distance: "Show distance",
          show_directions: "Show directions note",
          show_source: "Show source",
        };
        return labels[schema.name];
      },
    };
  }

  static getStubConfig() {
    return { source: "nobetci_eczane" };
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._config?.entity];
    const locations = this._geoStates(hass)
      .map((item) => `${item.entity_id}:${item.last_updated}:${item.state}`)
      .join(",");
    const key = [
      state?.last_updated,
      state?.state,
      locations,
      hass.language,
      JSON.stringify(this._config),
    ].join("|");
    if (key !== this._renderedKey) {
      this._renderedKey = key;
      this._render();
    }
  }

  getCardSize() {
    const count = this._visiblePharmacies().length;
    return Math.max(2, count * 2 + 1);
  }

  getGridOptions() {
    return {
      columns: 12,
      min_columns: 6,
      max_columns: 12,
      rows: Math.min(12, this.getCardSize()),
      min_rows: 2,
      max_rows: 12,
    };
  }

  _language() {
    const language = (this._hass?.language || "en").toLowerCase().split("-")[0];
    return COPY[language] || COPY.en;
  }

  _state() {
    return this._hass?.states?.[this._config?.entity];
  }

  _districtMatches(value) {
    const configured = this._config?.district?.trim();
    if (!configured) return true;
    return (
      typeof value === "string" &&
      value.trim().localeCompare(configured, "tr", { sensitivity: "base" }) === 0
    );
  }

  _geoStates(hass = this._hass) {
    if (!hass?.states || this._config?.entity) return [];
    const source = this._config?.source || "nobetci_eczane";
    return Object.values(hass.states)
      .filter((state) => {
        if (!state.entity_id.startsWith("geo_location.")) return false;
        if (state.attributes?.source !== source) return false;
        if (["unknown", "unavailable"].includes(state.state)) return false;
        return this._districtMatches(
          state.attributes?.configured_district || state.attributes?.district,
        );
      })
      .sort((a, b) => a.entity_id.localeCompare(b.entity_id));
  }

  _refreshEntityIds() {
    if (this._config?.entity) return [this._config.entity];

    const representatives = new Map();
    for (const state of this._geoStates()) {
      const key = `${state.attributes?.province || ""}:${state.attributes?.configured_district || state.attributes?.district || ""}`;
      if (!representatives.has(key)) representatives.set(key, state.entity_id);
    }
    if (representatives.size) return [...representatives.values()];

    const source = this._config?.source || "nobetci_eczane";
    return Object.values(this._hass?.states || {})
      .filter(
        (state) =>
          state.entity_id.startsWith("sensor.") &&
          state.attributes?.integration === source &&
          this._districtMatches(state.attributes?.district),
      )
      .map((state) => state.entity_id);
  }

  _pharmacies() {
    const items = this._state()?.attributes?.pharmacies;
    if (Array.isArray(items)) return items;

    return this._geoStates()
      .map((state) => {
        const distance = Number(state.state);
        return {
          entity_id: state.entity_id,
          name: state.attributes?.friendly_name,
          phone: state.attributes?.phone,
          phone_e164: state.attributes?.phone_e164,
          address: state.attributes?.address,
          directions: state.attributes?.directions,
          latitude: Number(state.attributes?.latitude),
          longitude: Number(state.attributes?.longitude),
          distance_km: Number.isFinite(distance) ? distance : null,
          duty_ends: state.attributes?.duty_ends,
          district: state.attributes?.district,
          configured_district: state.attributes?.configured_district,
          province: state.attributes?.province,
          data_source: state.attributes?.data_source,
          source_url: state.attributes?.source_url,
          fetched_at: state.attributes?.fetched_at,
          radius_km: state.attributes?.radius_km,
          update_interval_minutes: state.attributes?.update_interval_minutes,
          last_updated: state.last_updated,
        };
      })
      .sort((a, b) => {
        const distanceA = Number.isFinite(a.distance_km) ? a.distance_km : Infinity;
        const distanceB = Number.isFinite(b.distance_km) ? b.distance_km : Infinity;
        return distanceA - distanceB || (a.name || "").localeCompare(b.name || "");
      });
  }

  _visiblePharmacies(pharmacies = this._pharmacies()) {
    const maxItems = Math.max(1, Number(this._config?.max_items) || 3);
    return this._expanded ? pharmacies : pharmacies.slice(0, maxItems);
  }

  _relativeTime(value) {
    if (!value) return "";
    const timestamp = new Date(value).getTime();
    if (!Number.isFinite(timestamp)) return "";
    const seconds = Math.round((timestamp - Date.now()) / 1000);
    const units = [
      ["day", 86400],
      ["hour", 3600],
      ["minute", 60],
    ];
    const [unit, divisor] = units.find(([, size]) => Math.abs(seconds) >= size) || ["second", 1];
    const locale = this._hass?.locale?.language || this._hass?.language || "en";
    return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
      Math.round(seconds / divisor),
      unit,
    );
  }

  _staticMarkup() {
    return `
      <style>
        :host { display: block; }
        ha-card { overflow: hidden; }
        .header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 18px 18px 12px;
          cursor: pointer;
        }
        .header-icon {
          display: grid;
          place-items: center;
          width: 42px;
          height: 42px;
          border-radius: 14px;
          color: var(--state-icon-color, var(--primary-color));
          background: color-mix(in srgb, var(--state-icon-color, var(--primary-color)) 14%, transparent);
        }
        .header-icon ha-icon { --mdc-icon-size: 26px; }
        .heading { min-width: 0; flex: 1; }
        .title { font-size: 18px; font-weight: 600; line-height: 1.25; }
        .subtitle {
          color: var(--secondary-text-color);
          font-size: 13px;
          margin-top: 2px;
        }
        .refresh {
          border: 0;
          border-radius: 50%;
          background: transparent;
          color: var(--secondary-text-color);
          cursor: pointer;
          display: grid;
          place-items: center;
          height: 40px;
          width: 40px;
        }
        .refresh:hover { background: var(--secondary-background-color); }
        .list { display: grid; gap: 10px; padding: 0 12px 12px; }
        .pharmacy {
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          padding: 14px;
          background: color-mix(in srgb, var(--card-background-color) 92%, var(--primary-color) 8%);
        }
        .pharmacy-top { display: flex; gap: 10px; align-items: flex-start; }
        .name { font-weight: 600; line-height: 1.35; flex: 1; }
        .distance {
          white-space: nowrap;
          color: var(--primary-color);
          font-size: 13px;
          font-weight: 600;
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
          border-radius: 999px;
          padding: 4px 8px;
        }
        .address, .location, .directions {
          color: var(--secondary-text-color);
          font-size: 13px;
          line-height: 1.45;
          margin-top: 6px;
          white-space: pre-line;
        }
        .location { font-size: 12px; margin-top: 4px; }
        .directions { font-size: 12px; }
        .actions { display: flex; gap: 8px; margin-top: 12px; }
        .action {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          min-height: 36px;
          padding: 0 12px;
          border-radius: 10px;
          text-decoration: none;
          font-size: 13px;
          font-weight: 600;
          color: var(--primary-text-color);
          background: var(--secondary-background-color);
        }
        .action.primary { color: var(--text-primary-color); background: var(--primary-color); }
        .action ha-icon { --mdc-icon-size: 18px; }
        .message { padding: 10px 18px 22px; color: var(--secondary-text-color); }
        .expand {
          margin: 0 12px 14px;
          width: calc(100% - 24px);
          min-height: 40px;
          border: 0;
          border-radius: 10px;
          color: var(--primary-color);
          background: var(--secondary-background-color);
          cursor: pointer;
          font: inherit;
          font-weight: 600;
        }
        .source {
          padding: 0 18px 15px;
          color: var(--secondary-text-color);
          font-size: 11px;
        }
        .source a { color: inherit; }
      </style>
      <ha-card>
        <div class="header">
          <div class="header-icon"><ha-icon icon="mdi:pharmacy"></ha-icon></div>
          <div class="heading">
            <div class="title"></div>
            <div class="subtitle"></div>
          </div>
          <button class="refresh" type="button"><ha-icon icon="mdi:refresh"></ha-icon></button>
        </div>
        <div class="list"></div>
        <div class="message" hidden></div>
        <button class="expand" type="button" hidden></button>
        <div class="source" hidden></div>
      </ha-card>`;
  }

  _render() {
    if (!this._config) return;
    if (!this.shadowRoot.querySelector("ha-card")) {
      this.shadowRoot.innerHTML = this._staticMarkup();
      this.shadowRoot.querySelector(".refresh").addEventListener("click", (event) => {
        event.stopPropagation();
        if (this._hass) {
          const entityIds = this._refreshEntityIds();
          if (!entityIds.length) return;
          this._hass.callService("homeassistant", "update_entity", {
            entity_id: entityIds,
          });
        }
      });
      this.shadowRoot.querySelector(".header").addEventListener("click", () => {
        this._toggleExpanded();
      });
      this.shadowRoot.querySelector(".expand").addEventListener("click", () => {
        this._toggleExpanded();
      });
    }

    const copy = this._language();
    const state = this._state();
    const attributes = state?.attributes || {};
    const list = this.shadowRoot.querySelector(".list");
    const message = this.shadowRoot.querySelector(".message");
    const source = this.shadowRoot.querySelector(".source");
    const expand = this.shadowRoot.querySelector(".expand");
    const pharmacies = this._pharmacies();
    const visiblePharmacies = this._visiblePharmacies(pharmacies);
    const first = pharmacies[0] || {};
    const district = this._config.district || attributes.district || first.district;
    const fetchedAt = attributes.fetched_at || first.fetched_at || first.last_updated;
    const radius = attributes.radius_km ?? first.radius_km;
    const metadata = [];
    if (district) metadata.push(district);
    const relativeTime = this._relativeTime(fetchedAt);
    if (relativeTime) metadata.push(`${copy.lastUpdate}: ${relativeTime}`);
    if (Number.isFinite(Number(radius))) {
      metadata.push(
        `${copy.radius}: ${Number(radius).toLocaleString(this._hass?.locale?.language || this._hass?.language)} ${copy.km}`,
      );
    }
    metadata.push(`${pharmacies.length} ${copy.pharmacies}`);

    this.shadowRoot.querySelector(".title").textContent = this._config.title || copy.title;
    this.shadowRoot.querySelector(".subtitle").textContent = metadata.join(" · ");
    this.shadowRoot.querySelector(".refresh").title = copy.refresh;
    list.replaceChildren();

    if (this._config.entity && (!state || ["unavailable", "unknown"].includes(state.state))) {
      message.textContent = copy.unavailable;
      message.hidden = false;
    } else if (!pharmacies.length) {
      message.textContent = copy.empty;
      message.hidden = false;
    } else {
      message.hidden = true;
      visiblePharmacies.forEach((pharmacy) => list.append(this._pharmacyRow(pharmacy, copy)));
    }

    const maxItems = Math.max(1, Number(this._config.max_items) || 3);
    expand.hidden = pharmacies.length <= maxItems;
    expand.textContent = this._expanded
      ? copy.showLess
      : `${copy.showAll} (${pharmacies.length})`;
    expand.setAttribute("aria-expanded", String(this._expanded));

    const sourceName = first.data_source || attributes.source;
    const sourceUrl = first.source_url || attributes.source_url;
    if (this._config.show_source && sourceName) {
      source.replaceChildren();
      source.append(`${copy.source}: `);
      const link = document.createElement("a");
      link.textContent = sourceName;
      link.href = sourceUrl || "#";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      source.append(link);
      source.hidden = false;
    } else {
      source.hidden = true;
    }
  }

  _toggleExpanded() {
    const maxItems = Math.max(1, Number(this._config?.max_items) || 3);
    if (this._pharmacies().length <= maxItems) return;
    this._expanded = !this._expanded;
    this._renderedKey = "";
    this._render();
  }

  _pharmacyRow(pharmacy, copy) {
    const article = document.createElement("article");
    article.className = "pharmacy";

    const top = document.createElement("div");
    top.className = "pharmacy-top";
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = pharmacy.name || "—";
    top.append(name);

    if (this._config.show_distance && Number.isFinite(pharmacy.distance_km)) {
      const distance = document.createElement("div");
      distance.className = "distance";
      distance.textContent = `${Number(pharmacy.distance_km).toLocaleString(this._hass?.locale?.language || this._hass?.language)} ${copy.km}`;
      top.append(distance);
    }
    article.append(top);

    if (this._config.show_address && pharmacy.address) {
      const address = document.createElement("div");
      address.className = "address";
      address.textContent = pharmacy.address;
      article.append(address);
    }
    if (pharmacy.district || pharmacy.province) {
      const location = document.createElement("div");
      location.className = "location";
      location.textContent = [pharmacy.district, pharmacy.province]
        .filter(Boolean)
        .join(" · ");
      article.append(location);
    }
    if (this._config.show_directions !== false && pharmacy.directions) {
      const directions = document.createElement("div");
      directions.className = "directions";
      directions.textContent = pharmacy.directions;
      article.append(directions);
    }

    const actions = document.createElement("div");
    actions.className = "actions";
    if (pharmacy.phone) {
      const digits = String(pharmacy.phone).replace(/\D/g, "").replace(/^0/, "");
      const phoneHref = pharmacy.phone_e164 || `+90${digits}`;
      actions.append(this._actionLink(`tel:${phoneHref}`, "mdi:phone", copy.call, true));
    }
    if (Number.isFinite(pharmacy.latitude) && Number.isFinite(pharmacy.longitude)) {
      actions.append(this._navigationControl(pharmacy, copy.route));
    }
    if (actions.childElementCount) article.append(actions);
    return article;
  }

  _actionLink(href, iconName, label, primary) {
    const link = document.createElement("a");
    link.className = `action${primary ? " primary" : ""}`;
    link.href = href;
    if (!href.startsWith("tel:")) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", iconName);
    const text = document.createElement("span");
    text.textContent = label;
    link.append(icon, text);
    return link;
  }

  _navigationUrl(pharmacy, userAgent = globalThis.navigator?.userAgent || "") {
    const destination = `${pharmacy.latitude},${pharmacy.longitude}`;
    const label = pharmacy.name || "Pharmacy";
    const navigatorObject = globalThis.navigator;
    const isiPad =
      /Macintosh/i.test(userAgent) && Number(navigatorObject?.maxTouchPoints) > 1;

    if (/Android/i.test(userAgent)) {
      return `geo:${destination}?q=${encodeURIComponent(`${destination}(${label})`)}`;
    }
    if (/iPhone|iPad|iPod/i.test(userAgent) || isiPad) {
      return `https://maps.apple.com/?daddr=${encodeURIComponent(destination)}&dirflg=d`;
    }
    return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`;
  }

  _navigationControl(pharmacy, label) {
    const button = document.createElement("ha-control-button");
    button.className = "action navigation";
    button.setAttribute("label", label);
    button.setAttribute("role", "link");
    button.tabIndex = 0;

    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", "mdi:directions");
    const text = document.createElement("span");
    text.textContent = label;
    button.append(icon, text);

    const openNavigation = () => {
      const url = this._navigationUrl(pharmacy);
      if (url.startsWith("geo:")) {
        window.location.href = url;
      } else {
        window.open(url, "_blank", "noopener,noreferrer");
      }
    };
    button.addEventListener("click", openNavigation);
    button.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openNavigation();
      }
    });
    return button;
  }
}

if (!customElements.get("nobetci-eczane-card")) {
  customElements.define("nobetci-eczane-card", NobetciEczaneCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "nobetci-eczane-card",
  name: "Nöbetçi Eczane Card",
  description: "Shows duty pharmacies with call and navigation actions.",
  documentationURL: "https://www.istanbuleczaciodasi.org.tr/nobetci-eczane/",
  preview: true,
  getEntitySuggestion: (hass, entityId) => {
    const state = hass.states[entityId];
    if (
      !entityId.startsWith("geo_location.") ||
      state?.attributes?.source !== "nobetci_eczane"
    ) {
      return null;
    }
    return {
      config: {
        type: "custom:nobetci-eczane-card",
        source: state.attributes.source,
        district:
          state.attributes.configured_district || state.attributes.district,
      },
    };
  },
});

console.info(`%c NÖBETÇİ ECZANE CARD %c v${CARD_VERSION} `, "color:white;background:#d32f2f;font-weight:700", "color:#d32f2f;background:white");
