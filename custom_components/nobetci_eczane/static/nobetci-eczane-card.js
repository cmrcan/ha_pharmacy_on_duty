/* Nöbetçi Eczane Card v0.4.2 — generated; edit src/ instead. */
(()=>{var g="0.4.2",p={tr:{title:"Nöbetçi Eczaneler",unavailable:"Eczane verisi kullanılamıyor",empty:"Şu anda listelenen nöbetçi eczane yok",call:"Ara",route:"Yol tarifi",refresh:"Yenile",km:"km",source:"Kaynak"},en:{title:"Duty Pharmacies",unavailable:"Pharmacy data is unavailable",empty:"No duty pharmacy is currently listed",call:"Call",route:"Directions",refresh:"Refresh",km:"km",source:"Source"},de:{title:"Notdienstapotheken",unavailable:"Apothekendaten sind nicht verfügbar",empty:"Derzeit ist keine Notdienstapotheke aufgeführt",call:"Anrufen",route:"Route",refresh:"Aktualisieren",km:"km",source:"Quelle"}},d=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"}),this._renderedKey=""}setConfig(e){if(!e)throw new Error("Card configuration is required");this._config={source:"nobetci_eczane",show_address:!0,show_distance:!0,show_directions:!0,show_source:!0,...e},this._renderedKey="",this._render()}static getConfigForm(){return{schema:[{name:"source",required:!0,selector:{text:{}}},{name:"district",selector:{text:{}}},{name:"title",selector:{text:{}}},{type:"grid",name:"",flatten:!0,schema:[{name:"show_address",selector:{boolean:{}}},{name:"show_distance",selector:{boolean:{}}},{name:"show_directions",selector:{boolean:{}}},{name:"show_source",selector:{boolean:{}}}]}],computeLabel:e=>({source:"Geo-location source",district:"District (optional)",title:"Title",show_address:"Show address",show_distance:"Show distance",show_directions:"Show directions note",show_source:"Show source"})[e.name]}}static getStubConfig(){return{source:"nobetci_eczane"}}set hass(e){this._hass=e;let t=e.states[this._config?.entity],i=this._geoStates(e).map(s=>`${s.entity_id}:${s.last_updated}:${s.state}`).join(","),n=[t?.last_updated,t?.state,i,e.language,JSON.stringify(this._config)].join("|");n!==this._renderedKey&&(this._renderedKey=n,this._render())}getCardSize(){let e=this._pharmacies().length;return Math.max(2,e*2+1)}getGridOptions(){return{columns:12,min_columns:6,max_columns:12,rows:Math.min(12,this.getCardSize()),min_rows:2,max_rows:12}}_language(){let e=(this._hass?.language||"en").toLowerCase().split("-")[0];return p[e]||p.en}_state(){return this._hass?.states?.[this._config?.entity]}_districtMatches(e){let t=this._config?.district?.trim();return t?typeof e=="string"&&e.trim().localeCompare(t,"tr",{sensitivity:"base"})===0:!0}_geoStates(e=this._hass){if(!e?.states||this._config?.entity)return[];let t=this._config?.source||"nobetci_eczane";return Object.values(e.states).filter(i=>!i.entity_id.startsWith("geo_location.")||i.attributes?.source!==t||["unknown","unavailable"].includes(i.state)?!1:this._districtMatches(i.attributes?.configured_district||i.attributes?.district)).sort((i,n)=>i.entity_id.localeCompare(n.entity_id))}_refreshEntityIds(){if(this._config?.entity)return[this._config.entity];let e=new Map;for(let i of this._geoStates()){let n=`${i.attributes?.province||""}:${i.attributes?.configured_district||i.attributes?.district||""}`;e.has(n)||e.set(n,i.entity_id)}if(e.size)return[...e.values()];let t=this._config?.source||"nobetci_eczane";return Object.values(this._hass?.states||{}).filter(i=>i.entity_id.startsWith("sensor.")&&i.attributes?.integration===t&&this._districtMatches(i.attributes?.district)).map(i=>i.entity_id)}_pharmacies(){let e=this._state()?.attributes?.pharmacies;return Array.isArray(e)?e:this._geoStates().map(t=>{let i=Number(t.state);return{entity_id:t.entity_id,name:t.attributes?.friendly_name,phone:t.attributes?.phone,phone_e164:t.attributes?.phone_e164,address:t.attributes?.address,directions:t.attributes?.directions,latitude:Number(t.attributes?.latitude),longitude:Number(t.attributes?.longitude),distance_km:Number.isFinite(i)?i:null,duty_ends:t.attributes?.duty_ends,district:t.attributes?.district,configured_district:t.attributes?.configured_district,province:t.attributes?.province,data_source:t.attributes?.data_source,source_url:t.attributes?.source_url}}).sort((t,i)=>{let n=Number.isFinite(t.distance_km)?t.distance_km:1/0,s=Number.isFinite(i.distance_km)?i.distance_km:1/0;return n-s||(t.name||"").localeCompare(i.name||"")})}_staticMarkup(){return`
      <style>
        :host { display: block; }
        ha-card { overflow: hidden; }
        .header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 18px 18px 12px;
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
        <div class="source" hidden></div>
      </ha-card>`}_render(){if(!this._config)return;this.shadowRoot.querySelector("ha-card")||(this.shadowRoot.innerHTML=this._staticMarkup(),this.shadowRoot.querySelector(".refresh").addEventListener("click",()=>{if(this._hass){let a=this._refreshEntityIds();if(!a.length)return;this._hass.callService("homeassistant","update_entity",{entity_id:a})}}));let e=this._language(),t=this._state(),i=t?.attributes||{},n=this.shadowRoot.querySelector(".list"),s=this.shadowRoot.querySelector(".message"),o=this.shadowRoot.querySelector(".source"),r=this._pharmacies(),c=r[0]||{},u=this._config.district||i.district||c.district;this.shadowRoot.querySelector(".title").textContent=this._config.title||e.title,this.shadowRoot.querySelector(".subtitle").textContent=u?`${u} · ${r.length}`:String(r.length),this.shadowRoot.querySelector(".refresh").title=e.refresh,n.replaceChildren(),this._config.entity&&(!t||["unavailable","unknown"].includes(t.state))?(s.textContent=e.unavailable,s.hidden=!1):r.length?(s.hidden=!0,r.forEach(a=>n.append(this._pharmacyRow(a,e)))):(s.textContent=e.empty,s.hidden=!1);let h=c.data_source||i.source,m=c.source_url||i.source_url;if(this._config.show_source&&h){o.replaceChildren(),o.append(`${e.source}: `);let a=document.createElement("a");a.textContent=h,a.href=m||"#",a.target="_blank",a.rel="noopener noreferrer",o.append(a),o.hidden=!1}else o.hidden=!0}_pharmacyRow(e,t){let i=document.createElement("article");i.className="pharmacy";let n=document.createElement("div");n.className="pharmacy-top";let s=document.createElement("div");if(s.className="name",s.textContent=e.name||"—",n.append(s),this._config.show_distance&&Number.isFinite(e.distance_km)){let r=document.createElement("div");r.className="distance",r.textContent=`${Number(e.distance_km).toLocaleString(this._hass?.locale?.language||this._hass?.language)} ${t.km}`,n.append(r)}if(i.append(n),this._config.show_address&&e.address){let r=document.createElement("div");r.className="address",r.textContent=e.address,i.append(r)}if(e.district||e.province){let r=document.createElement("div");r.className="location",r.textContent=[e.district,e.province].filter(Boolean).join(" · "),i.append(r)}if(this._config.show_directions!==!1&&e.directions){let r=document.createElement("div");r.className="directions",r.textContent=e.directions,i.append(r)}let o=document.createElement("div");if(o.className="actions",e.phone){let r=String(e.phone).replace(/\D/g,"").replace(/^0/,""),c=e.phone_e164||`+90${r}`;o.append(this._actionLink(`tel:${c}`,"mdi:phone",t.call,!0))}if(Number.isFinite(e.latitude)&&Number.isFinite(e.longitude)){let r=`${e.latitude},${e.longitude}`,c=`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(r)}`;o.append(this._actionLink(c,"mdi:map-marker-path",t.route,!1))}return o.childElementCount&&i.append(o),i}_actionLink(e,t,i,n){let s=document.createElement("a");s.className=`action${n?" primary":""}`,s.href=e,e.startsWith("tel:")||(s.target="_blank",s.rel="noopener noreferrer");let o=document.createElement("ha-icon");o.setAttribute("icon",t);let r=document.createElement("span");return r.textContent=i,s.append(o,r),s}};customElements.get("nobetci-eczane-card")||customElements.define("nobetci-eczane-card",d);window.customCards=window.customCards||[];window.customCards.push({type:"nobetci-eczane-card",name:"Nöbetçi Eczane Card",description:"Shows duty pharmacies with call and navigation actions.",documentationURL:"https://www.istanbuleczaciodasi.org.tr/nobetci-eczane/",preview:!0,getEntitySuggestion:(l,e)=>{let t=l.states[e];return!e.startsWith("geo_location.")||t?.attributes?.source!=="nobetci_eczane"?null:{config:{type:"custom:nobetci-eczane-card",source:t.attributes.source,district:t.attributes.configured_district||t.attributes.district}}}});console.info(`%c NÖBETÇİ ECZANE CARD %c v${g} `,"color:white;background:#d32f2f;font-weight:700","color:#d32f2f;background:white");})();
