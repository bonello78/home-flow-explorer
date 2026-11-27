// home-flow-explorer v1.0.0 — https://github.com/bonello78/home-flow-explorer — MIT
// Interactive map of how messages travel through a smart home (Lovelace card).
// No data inside: nodes, edges and scenarios come from the card configuration.
const HFE_CSS = `
:host{--bg:var(--primary-background-color,#f2f4f9);--panel:var(--card-background-color,#fff);--box:var(--secondary-background-color,#e7ebf4);
--ink:var(--primary-text-color,#121829);--mute:var(--secondary-text-color,#596278);--line:var(--divider-color,#c3cad9);
--loc:#08867e;--cld:#d2470e;--wifi:#2d6be0;--zig:#c0237a;display:block;color:var(--ink);font-size:16px;line-height:1.5}
:host([dark]){--loc:#3ee0cf;--cld:#ff8a5c;--wifi:#6ea2ff;--zig:#ff70b6}
*{box-sizing:border-box;min-width:0}
.wrap{padding:clamp(8px,2vw,24px)}
h1{font-size:clamp(24px,3vw,34px);line-height:1.1;margin:0 0 6px;font-weight:600}
.lead{margin:0;color:var(--mute)}.note{font-size:13px;color:var(--mute);margin:4px 0 0}
.tabs{display:inline-flex;gap:4px;margin:16px 0 10px;padding:4px;background:var(--panel);border:1px solid var(--line);border-radius:14px}
.tab{font:inherit;font-size:15px;font-weight:500;border:0;background:none;color:var(--mute);padding:8px 16px;min-height:42px;border-radius:10px;cursor:pointer}
.tab[aria-selected=true]{background:var(--ink);color:var(--panel)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px}
.chip{font:inherit;font-size:15px;line-height:1.3;font-weight:500;text-align:left;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:12px;padding:11px 14px;min-height:64px;cursor:pointer}
.chip small{display:block;font-size:13px;font-weight:400;color:var(--mute);margin-top:4px}
.chip small::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:var(--loc)}
.chip.c small::before{background:var(--cld)}
.chip[aria-pressed=true]{border-color:var(--ink);box-shadow:inset 0 0 0 1px var(--ink)}
.hint{font-size:14px;color:var(--mute);margin:10px 0 0}
button:focus-visible,.n:focus-visible{outline:2px solid var(--wifi);outline-offset:2px}
.main{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(0,1fr);grid-template-areas:"fig ctl" "fig side";grid-template-rows:auto 1fr;gap:14px 20px;margin-top:14px}
.figw{grid-area:fig;align-self:start;position:relative;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:10px}
svg.map{display:block;width:100%}
.ctl{grid-area:ctl;display:flex;align-items:center;gap:8px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:8px 10px}
.cnt{flex:1;font-size:14px;color:var(--mute)}.cnt b{display:none;color:var(--ink);font-weight:500}
.btn{width:44px;height:44px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);display:grid;place-items:center;cursor:pointer}
.btn:disabled{opacity:.4;cursor:default}
.btn.pl{background:var(--ink);color:var(--panel);border-color:var(--ink)}
.btn svg{width:20px;height:20px;fill:currentColor}
aside{grid-area:side;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px 20px}
aside h2{font-size:21px;line-height:1.15;margin:0 0 6px;font-weight:600}aside p{margin:0 0 10px}
.off{font-size:14px;color:var(--mute);border-left:3px solid var(--cld);padding-left:10px}.off.l{border-color:var(--loc)}
.step{border-top:1px solid var(--line);margin-top:14px;padding-top:14px}
.tag{font-size:13px;font-weight:500;padding:2px 9px;border-radius:20px;color:var(--panel);background:var(--loc)}.tag.c{background:var(--cld)}
.step h3{font-size:18px;line-height:1.2;margin:8px 0 6px;font-weight:600}
dl{margin:12px 0 0;background:var(--bg);border-radius:12px;padding:10px 12px;font:14px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}
dl div{display:grid;grid-template-columns:8.5em minmax(0,1fr);gap:8px;padding:3px 0}dt{color:var(--mute)}dd{margin:0;overflow-wrap:anywhere}
ol{list-style:none;margin:16px 0 0;padding:0;counter-reset:s}
ol button{all:unset;box-sizing:border-box;display:flex;gap:10px;width:100%;padding:7px 4px;min-height:40px;align-items:center;font-size:15px;cursor:pointer;color:var(--mute);border-radius:8px}
ol button::before{counter-increment:s;content:counter(s);flex:none;width:24px;height:24px;border-radius:50%;display:grid;place-items:center;font-size:13px;border:1px solid var(--line)}
ol .c button::before{border-color:var(--cld)}
ol button.on{color:var(--ink);font-weight:500}ol button.on::before{background:var(--loc);border-color:var(--loc);color:var(--panel)}
ol .c button.on::before{background:var(--cld);border-color:var(--cld)}
.leg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--mute);padding:6px 6px 2px}
.leg span{display:inline-flex;align-items:center;gap:6px}.leg i{display:inline-block;width:24px;height:0;border-top:3px solid}
.leg .dt{width:10px;height:10px;border:0;border-radius:50%}
.ni{position:absolute;left:18px;top:18px;max-width:min(340px,calc(100% - 36px));background:var(--panel);border:1px solid var(--ink);border-radius:14px;padding:14px 16px;box-shadow:0 10px 30px rgb(0 0 0/.25);display:none;z-index:5}
.ni.open{display:block}.ni h4{margin:0 40px 2px 0;font-size:18px}.ni .s{font:13px ui-monospace,monospace;color:var(--mute);margin:0 0 8px}.ni p{margin:0;font-size:15px}
.ni h5{margin:12px 0 4px;font-size:13px;font-weight:500;color:var(--mute)}
.nil{display:flex;flex-direction:column;gap:2px;max-height:190px;overflow-y:auto}
.nil button{all:unset;cursor:pointer;font-size:15px;padding:6px 0;min-height:32px;color:var(--wifi)}
.nix{position:absolute;right:6px;top:6px;width:40px;height:40px;border:0;background:none;color:var(--mute);font-size:22px;cursor:pointer}
.bd{stroke:var(--line);stroke-width:2;stroke-dasharray:10 8}.bt{fill:var(--mute);font-size:var(--f2)}
.bx{fill:var(--box);stroke:var(--line);stroke-width:1.5}.bxt{fill:var(--mute);font-size:var(--f2);font-weight:500}
.e{fill:none;stroke-width:2.5;transition:opacity .3s}
.e.c{stroke:var(--mute)}.e.w{stroke:var(--wifi);stroke-dasharray:7 6}
.e.z{stroke:var(--zig);stroke-dasharray:1 6;stroke-linecap:round;stroke-width:3.5}
.e.i{stroke:var(--cld);stroke-dasharray:1 7;stroke-linecap:round;stroke-width:3}
.e.p{stroke:var(--loc);opacity:.7}
svg.run .e{opacity:.16}svg.run .e.on{opacity:1;stroke-width:5}
.n{cursor:pointer;transition:opacity .3s}svg.run .n:not(.on){opacity:.4}
.hit{fill:transparent}.nd{fill:var(--panel);stroke-width:3}
.zc .nd{stroke:var(--cld)}.zr .nd{stroke:var(--ink)}.zs .nd{stroke:var(--loc)}.zd .nd{stroke:var(--wifi)}
.core{fill:var(--mute)}.n.on .core{fill:var(--ink)}.n.on .nd{stroke-width:5}
.pill{fill:var(--panel);opacity:.92}
.t1{fill:var(--ink);font-size:var(--f1);font-weight:500}.t2{fill:var(--mute);font-size:var(--f2);font-family:ui-monospace,monospace}
.pk .halo{fill:var(--pk);opacity:.28;animation:pulse 1.2s ease-in-out infinite}.pk .dot{fill:var(--pk);stroke:var(--panel);stroke-width:2}
@keyframes pulse{50%{opacity:.08}}
@media (prefers-reduced-motion:reduce){.pk .halo{animation:none}.e,.n{transition:none}}
.narrow .main{grid-template-columns:minmax(0,1fr);grid-template-areas:"fig" "ctl" "side";grid-template-rows:auto}
.narrow .ctl{position:sticky;bottom:10px;z-index:3;box-shadow:0 8px 24px rgb(0 0 0/.22)}
.narrow .cnt b{display:block;font-size:15px;line-height:1.25}
.narrow .figw{padding:4px}
.narrow .ni{position:fixed;left:12px;right:12px;top:auto;bottom:96px;max-width:none}
.phone .cards{grid-template-columns:repeat(2,minmax(0,1fr))}.phone .chip{font-size:14px;padding:9px 11px}
.phone dl div{grid-template-columns:minmax(0,1fr);gap:0}`;

const HFE_I18N = {
 it: {lead:'Scegli cosa succede e segui il messaggio un salto alla volta, dal dispositivo al cloud e ritorno.',
  hint:'Oppure tocca un dispositivo sulla mappa per vedere dove passa.',
  groups:{gesti:'Gesti quotidiani',automazioni:'Automazioni',everyday:'Gesti quotidiani',automations:'Automazioni'},
  out:'esce di casa',in:'resta in casa',steps:'passi',step:'Passo',of:'di',outside:'fuori casa ↑',inside:'in casa ↓',
  via:n=>n?`Ci passa in ${n} scenari`:'Nessuno scenario passa di qui',
  leg:['Cavo','Wi-Fi','Zigbee','Internet','Dentro il server','Resta in casa','Esce di casa'],
  prev:'Indietro',next:'Avanti',play:'Riproduci',pause:'Pausa',close:'Chiudi',scen:'Scenari',map:'Mappa'},
 en: {lead:'Pick what happens and follow the message one hop at a time, from the device to the cloud and back.',
  hint:'Or tap a device on the map to see which flows pass through it.',
  groups:{gesti:'Everyday actions',automazioni:'Automations',everyday:'Everyday actions',automations:'Automations'},
  out:'leaves the house',in:'stays local',steps:'steps',step:'Step',of:'of',outside:'internet ↑',inside:'home ↓',
  via:n=>n?`Used by ${n} flows`:'No flow passes here',
  leg:['Cable','Wi-Fi','Zigbee','Internet','Inside the server','Stays local','Leaves the house'],
  prev:'Previous',next:'Next',play:'Play',pause:'Pause',close:'Close',scen:'Flows',map:'Map'}};
const HFE_ICO = {prev:'<svg viewBox="0 0 24 24"><path d="M15.4 5.4 14 4l-8 8 8 8 1.4-1.4L8.8 12z"/></svg>',
 next:'<svg viewBox="0 0 24 24"><path d="M8.6 18.6 10 20l8-8-8-8-1.4 1.4 6.6 6.6z"/></svg>',
 play:'<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',pause:'<svg viewBox="0 0 24 24"><path d="M7 5h4v14H7zm6 0h4v14h-4z"/></svg>'};
const ZC = {cloud:'c',net:'r',server:'s',device:'d'}, MC = {cable:'c',wifi:'w',zigbee:'z',internet:'i',internal:'p'};
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const key = (a,b) => [a,b].sort().join('|');

class HomeFlowExplorer extends HTMLElement {
  setConfig(c) {
    if (!c || !Array.isArray(c.nodes) || !Array.isArray(c.scenarios)) throw new Error('home-flow-explorer: nodes and scenarios are required');
    this.c = c; this.sc = 0; this.si = 0; this.playing = false; this.prog = 1; this.mob = null;
    this.nodes = {}; c.nodes.forEach(n => this.nodes[n.id] = n);
    this.S = c.scenarios;
    this.groups = [...new Set(this.S.map(s => s.group || 'gesti'))];
    this.grp = this.groups[0];
    if (this.isConnected) this.build();
  }
  set hass(h) { this._h = h; const d = !!(h && h.themes && h.themes.darkMode); if (d !== this._dark) { this._dark = d; this.toggleAttribute('dark', d); } }
  getCardSize() { return 14; }
  connectedCallback() {
    if (this._hass === undefined && !this.hasAttribute('dark') && matchMedia('(prefers-color-scheme: dark)').matches && this.c && this.c.standalone) this.setAttribute('dark', '');
    if (this.c && !this.built) this.build();
  }
  disconnectedCallback() { cancelAnimationFrame(this.anim); clearTimeout(this.timer); this.ro && this.ro.disconnect(); this.built = false; }
  $(s) { return this.root.querySelector(s); }
  build() {
    this.built = true; this.ro && this.ro.disconnect();
    if (!this.root) this.root = this.attachShadow({mode:'open'});
    const c = this.c, lang = String(c.language || (this._h && this._h.language) || document.documentElement.lang || 'en').slice(0, 2);
    const t = this.t = HFE_I18N[lang] || HFE_I18N.en;
    if (c.standalone) this.toggleAttribute('dark', matchMedia('(prefers-color-scheme: dark)').matches);
    const gl = g => (c.group_labels && c.group_labels[g]) || t.groups[g] || g;
    this.root.innerHTML = `<style>${HFE_CSS}</style><div class="wrap">
${c.title ? `<h1>${esc(c.title)}</h1>` : ''}<p class="lead">${esc(c.intro || t.lead)}</p>${c.note ? `<p class="note">${esc(c.note)}</p>` : ''}
${this.groups.length > 1 ? `<div class="tabs" role="tablist">${this.groups.map(g => `<button class="tab" role="tab" type="button" data-g="${esc(g)}">${esc(gl(g))}</button>`).join('')}</div>` : '<div style="height:14px"></div>'}
<nav class="cards" aria-label="${t.scen}"></nav><p class="hint">${esc(t.hint)}</p>
<div class="main"><div class="figw"><div class="mapw"></div>
<div class="leg"><span><i style="border-color:var(--mute)"></i>${t.leg[0]}</span><span><i style="border-top-style:dashed;border-color:var(--wifi)"></i>${t.leg[1]}</span><span><i style="border-top-style:dotted;border-color:var(--zig)"></i>${t.leg[2]}</span><span><i style="border-top-style:dotted;border-color:var(--cld)"></i>${t.leg[3]}</span><span><i style="border-color:var(--loc)"></i>${t.leg[4]}</span><span><i class="dt" style="background:var(--loc)"></i>${t.leg[5]}</span><span><i class="dt" style="background:var(--cld)"></i>${t.leg[6]}</span></div>
<div class="ni" role="dialog"><button class="nix" type="button" aria-label="${t.close}">×</button><h4></h4><p class="s"></p><p class="d"></p><h5></h5><div class="nil"></div></div></div>
<div class="ctl"><div class="cnt"><span class="cn"></span><b></b></div><button class="btn prev" type="button" aria-label="${t.prev}">${HFE_ICO.prev}</button><button class="btn pl" type="button"></button><button class="btn next" type="button" aria-label="${t.next}">${HFE_ICO.next}</button></div>
<aside><h2 class="scT"></h2><p class="scS"></p><p class="off"></p><div class="step"><span class="tag"></span><h3></h3><p class="stD"></p><dl></dl></div><ol></ol></aside></div></div>`;
    this.mapw = this.$('.mapw'); this.fig = this.$('.figw'); this.wrap = this.$('.wrap');
    this.root.querySelectorAll('.tab').forEach(b => b.onclick = () => this.cards(b.dataset.g));
    this.$('.cards').onclick = e => { const b = e.target.closest('.chip'); if (b) this.sel(+b.dataset.i, true); };
    this.$('ol').onclick = e => { const b = e.target.closest('button'); if (b) { this.playing = false; this.go(+b.dataset.i); } };
    this.$('.prev').onclick = () => { if (this.si > 0) { this.playing = false; this.go(this.si - 1); } };
    this.$('.next').onclick = () => { if (this.si < this.cur().steps.length - 1) { this.playing = false; this.go(this.si + 1); } };
    this.$('.pl').onclick = () => { this.playing = !this.playing; if (this.playing) this.go(this.si == this.cur().steps.length - 1 ? 0 : this.si + 1); else { clearTimeout(this.timer); this.ui(); } };
    this.mapw.onclick = e => { const g = e.target.closest('g.n'); if (g) this.info(g.dataset.id); };
    this.mapw.onkeydown = e => { const g = e.target.closest('g.n'); if (g && (e.key == 'Enter' || e.key == ' ')) { e.preventDefault(); this.info(g.dataset.id); } };
    this.$('.nix').onclick = () => this.$('.ni').classList.remove('open');
    this.$('.nil').onclick = e => { const b = e.target.closest('button'); if (b) { this.$('.ni').classList.remove('open'); this.sel(+b.dataset.i, true); } };
    this.ro = new ResizeObserver(() => { try { this.resize(); } catch (e) { this.log('home-flow-explorer errore resize: ' + e); } }); this.ro.observe(this.wrap);
    try { this.resize(true); } catch (e) { this.log('home-flow-explorer errore draw: ' + (e && e.stack || e)); }
    const i0 = Math.max(0, this.S.findIndex(s => s.id === c.start));
    this.cards(this.S[i0].group || 'gesti'); this.sel(i0, c.autoplay !== false);
  }
  resize(force) {
    const w = this.wrap.clientWidth || 800;
    this.wrap.classList.toggle('narrow', w < 900); this.wrap.classList.toggle('phone', w < 600);
    const m = (this.fig.clientWidth || w) < 640;
    if (force || m !== this.mob) { this.mob = m;
      try { this._place(); } catch (e) { this.log('home-flow-explorer layout: ' + e.name + ': ' + e.message + ' @' + e.line + ':' + e.column); throw e; }
      try { this.draw(); } catch (e) { this.log('home-flow-explorer draw: ' + e.name + ': ' + e.message + ' @' + e.line + ':' + e.column); throw e; } }
    this.fitH();
  }
  // Safari ignores the viewBox aspect ratio with height:auto: set an explicit height
  fitH() { if (!this.svg) return; const w = this.svg.getBoundingClientRect().width; if (w && this.W) this.svg.style.height = Math.round(w * this.H / this.W) + 'px'; }
  cur() { return this.S[this.sc]; }
  // Method names start with _: HA sets properties such as layout and preview on cards, which would overwrite them
  _place() {
    const m = this.mob, W = m ? 400 : 1200, P = {}, ns = this.c.nodes, zone = n => ZC[n.zone] || 'd';
    const cl = ns.filter(n => zone(n) == 'c'), net = ns.filter(n => zone(n) == 'r'), srv = ns.filter(n => zone(n) == 's'), dev = ns.filter(n => zone(n) == 'd');
    const per = m ? 4 : 8; let y = m ? 62 : 80, rows = Math.ceil(cl.length / per) || 0;
    for (let r = 0; r < rows; r++) { const row = cl.slice(r * per, r * per + per); row.forEach((n, i) => P[n.id] = [(i + .5) * W / row.length, y, r == 0 ? 'u' : 'd']); if (r < rows - 1) y += m ? 88 : 95; }
    const by = rows ? y + (rows > 1 ? 70 : 55) : 20; this.by = by;
    if (net.length) { P[net[0].id] = [W / 2, by + 50, m ? 'l' : 'r']; const o = net.slice(1); o.forEach((n, i) => P[n.id] = [o.length == 1 ? W * .28 : (i + .5) * W / o.length, by + 130, 'd']); }
    let top = by + (net.length > 1 ? 205 : net.length ? 125 : 30);
    // devices: network-attached ones (Wi-Fi) above the servers, server-attached ones (Zigbee, USB) below
    const sid = new Set(srv.map(n => n.id)), E = this.c.edges || [];
    const onSrv = n => E.some(([a, b]) => (a == n.id && sid.has(b)) || (b == n.id && sid.has(a)));
    const devA = dev.filter(n => !onSrv(n)), devB = dev.filter(onSrv);
    const dp = m ? 4 : 9, rowsOf = (list, y0) => { let y = y0; for (let r = 0; r * dp < list.length; r++) { const row = list.slice(r * dp, r * dp + dp); const sp = W / Math.max(row.length, m ? 3 : 6); row.forEach((n, i) => P[n.id] = [W / 2 + (i - (row.length - 1) / 2) * sp, y, 'd']); y += 100; } return y; };
    if (devA.length) top = rowsOf(devA, top + 15) - 10;
    const bm = {}; srv.forEach(n => { const b = n.box || '_s'; (bm[b] = bm[b] || []).push(n); });
    const bl = (this.c.boxes || []).reduce((a, b) => (a[b.id] = b.label, a), {});
    const cw = m ? 120 : 135, chh = 90, boxes = Object.keys(bm).map(id => { const list = bm[id], cols = Math.min(m ? 2 : 3, list.length), rws = Math.ceil(list.length / cols); return {id, list, cols, w: cols * cw + 20, h: 45 + rws * chh}; });
    const lines = []; let line = [], lw = 0;
    boxes.forEach(b => { if (line.length && lw + b.w + 20 > W - 20) { lines.push(line); line = []; lw = 0; } line.push(b); lw += b.w + (line.length > 1 ? 20 : 0); });
    if (line.length) lines.push(line);
    this.B = [];
    lines.forEach(L => { const tw = L.reduce((a, b) => a + b.w, 0) + 20 * (L.length - 1); let x = (W - tw) / 2, lh = 0;
      L.forEach(b => { this.B.push([x, top, b.w, b.h, bl[b.id] || (b.id == '_s' ? 'Server' : b.id)]);
        // snake order: odd rows run right to left, so chained nodes stay next to each other
        b.list.forEach((n, i) => { const r = Math.floor(i / b.cols), k = i % b.cols, col = r % 2 ? b.cols - 1 - k : k; P[n.id] = [x + 10 + (col + .5) * cw, top + 55 + r * chh, 'd']; }); x += b.w + 20; lh = Math.max(lh, b.h); });
      top += lh + 20; });
    let H = top + 10;
    if (devB.length) H = rowsOf(devB, top + 45) - 30;
    // manual coordinates, when given, win
    const man = this.c.layout && this.c.layout[m ? 'mobile' : 'desktop'];
    if (man) { ns.forEach(n => { if (man.nodes && man.nodes[n.id]) P[n.id] = man.nodes[n.id]; }); if (man.boxes) this.B = man.boxes; if (man.height) H = man.height; if (man.boundary) this.by = man.boundary; }
    this.P = P; this.W = W; this.H = H;
  }
  lab(x, y, pos, R, f1, f2) {
    if (pos == 'u') return [x, y - R - 6 - f2 - 3, x, y - R - 6, 'middle'];
    if (pos == 'd') return [x, y + R + f1, x, y + R + f1 + f2 + 3, 'middle'];
    const dx = pos == 'r' ? R + 9 : -R - 9; return [x + dx, y - 3, x + dx, y + f2 + 3, pos == 'r' ? 'start' : 'end'];
  }
  draw() {
    const m = this.mob, W = this.W, H = this.H, f1 = m ? 14 : 21, f2 = m ? 12 : 17, R = m ? 14 : 17, P = this.P, t = this.t; this.R = R;
    const fw = this.mapw.getBoundingClientRect().width || (m ? 380 : 800);
    const by = this.by;
    let h = this.c.nodes.some(n => n.zone == 'cloud') ? `<line class="bd" x1="10" y1="${by}" x2="${W - 10}" y2="${by}"/><text class="bt" x="${W - 10}" y="${by - 8}" text-anchor="end">${t.outside}</text><text class="bt" x="${W - 10}" y="${by + f2 + 6}" text-anchor="end">${t.inside}</text>` : '';
    h += this.B.map(b => `<rect class="bx" x="${b[0]}" y="${b[1]}" width="${b[2]}" height="${b[3]}" rx="14"/><text class="bxt" x="${b[0] + 12}" y="${b[1] + f2 + 4}">${esc(b[4])}</text>`).join('');
    h += (this.c.edges || []).map(([a, b, k]) => { const p = P[a], q = P[b]; if (!p || !q) return ''; return `<line class="e ${MC[k] || k}" data-k="${esc(key(a, b))}" x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}"/>`; }).join('');
    h += this.c.nodes.map(n => { const p = P[n.id]; if (!p) return ''; const [x, y, pos] = p, l = this.lab(x, y, pos || 'd', R, f1, f2);
      return `<g class="n z${ZC[n.zone] || 'd'}" data-id="${esc(n.id)}" tabindex="0" role="button" aria-label="${esc(n.name)}"><circle class="hit" cx="${x}" cy="${y}" r="${R + 12}"/><circle class="nd" cx="${x}" cy="${y}" r="${R}"/><circle class="core" cx="${x}" cy="${y}" r="${R * .36}"/><rect class="pill" rx="6"/><text class="t1" x="${l[0]}" y="${l[1]}" text-anchor="${l[4]}">${esc(n.name)}</text><text class="t2" x="${l[2]}" y="${l[3]}" text-anchor="${l[4]}">${esc(n.sub)}</text></g>`; }).join('');
    h += `<g class="pk" style="display:none"><circle class="halo" r="${R * 1.15}"/><circle class="dot" r="${R * .55}"/></g>`;
    // whole SVG built by the HTML parser: the most Safari-friendly way
    this.mapw.innerHTML = `<svg class="map" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${t.map}" style="height:${Math.round(fw * H / W)}px;--f1:${f1}px;--f2:${f2}px">${h}</svg>`;
    const svg = this.svg = this.mapw.querySelector('svg');
    svg.querySelectorAll('g.n').forEach(g => { try { const a = g.querySelector('.t1').getBBox(), b = g.querySelector('.t2').getBBox(), r = g.querySelector('.pill');
      const x0 = Math.min(a.x, b.x) - 5, y0 = Math.min(a.y, b.y) - 1, x1 = Math.max(a.x + a.width, b.x + b.width) + 5, y1 = Math.max(a.y + a.height, b.y + b.height) + 1;
      r.setAttribute('x', x0); r.setAttribute('y', y0); r.setAttribute('width', x1 - x0); r.setAttribute('height', y1 - y0); } catch (e) {} });
    if (this.S.length) { this.mark(); this.place(); }
    if (this.c.debug && !this._dbg) { this._dbg = 1; setTimeout(() => this.report(), 2500); }
  }
  report() {
    const r = this.svg.getBoundingClientRect(), f = this.fig.getBoundingClientRect();
    const msg = 'home-flow-explorer debug ' + JSON.stringify({v: '1.0.0', mob: this.mob, W: this.W, H: this.H, vb: this.svg.getAttribute('viewBox'), svg: [Math.round(r.width), Math.round(r.height)], fig: [Math.round(f.width), Math.round(f.height)], kids: this.svg.childElementCount, lines: this.svg.querySelectorAll('line').length, ns: this.svg.namespaceURI, ua: navigator.userAgent.slice(0, 140)});
    this.log(msg);
  }
  log(msg) {
    try { this._h && this._h.callService('system_log', 'write', {message: msg, level: 'warning', logger: 'home_flow_explorer'}); } catch (e) {}
  }
  isOut(s) { return !!s.out; }
  mark() {
    const s = this.cur().steps[this.si], p = s.path, ks = new Set();
    for (let i = 0; i < p.length - 1; i++) ks.add(key(p[i], p[i + 1]));
    this.svg.classList.add('run');
    this.svg.querySelectorAll('.e').forEach(e => e.classList.toggle('on', ks.has(e.dataset.k)));
    this.svg.querySelectorAll('g.n').forEach(g => g.classList.toggle('on', p.includes(g.dataset.id)));
    this.svg.style.setProperty('--pk', s.out ? 'var(--cld)' : 'var(--loc)');
  }
  at(t) {
    const Q = this.cur().steps[this.si].path.map(id => this.P[id]).filter(Boolean); if (!Q.length) return [0, 0]; if (Q.length < 2) return Q[0];
    const seg = []; let tot = 0; for (let i = 0; i < Q.length - 1; i++) { const d = Math.hypot(Q[i + 1][0] - Q[i][0], Q[i + 1][1] - Q[i][1]); seg.push(d); tot += d; }
    let d = t * tot; for (let i = 0; i < seg.length; i++) { if (d <= seg[i] || i == seg.length - 1) { const f = seg[i] ? Math.min(1, d / seg[i]) : 1; return [Q[i][0] + (Q[i + 1][0] - Q[i][0]) * f, Q[i][1] + (Q[i + 1][1] - Q[i][1]) * f]; } d -= seg[i]; }
  }
  place() { const g = this.svg.querySelector('.pk'); if (!g) return; const q = this.at(this.prog); g.style.display = ''; g.setAttribute('transform', `translate(${q[0]},${q[1]})`); }
  run() {
    cancelAnimationFrame(this.anim); clearTimeout(this.timer);
    const s = this.cur().steps[this.si], hops = Math.max(1, s.path.length - 1), red = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dur = red ? 0 : Math.min(4200, 650 + hops * 520), t0 = performance.now(); this.prog = 0;
    const f = now => { this.prog = dur ? Math.min(1, (now - t0) / dur) : 1; this.place();
      if (this.prog < 1) this.anim = requestAnimationFrame(f);
      else if (this.playing) { if (this.si < this.cur().steps.length - 1) this.timer = setTimeout(() => this.go(this.si + 1), 2600); else { this.playing = false; this.ui(); } } };
    this.anim = requestAnimationFrame(f);
  }
  ui() { const b = this.$('.pl'); b.innerHTML = this.playing ? HFE_ICO.pause : HFE_ICO.play; b.setAttribute('aria-label', this.playing ? this.t.pause : this.t.play);
    this.$('.prev').disabled = this.si == 0; this.$('.next').disabled = this.si == this.cur().steps.length - 1; }
  _panel() {
    const c = this.cur(), s = c.steps[this.si], t = this.t;
    this.$('.cn').textContent = `${t.step} ${this.si + 1} ${t.of} ${c.steps.length}`; this.$('.cnt b').textContent = s.title;
    const k = this.$('.tag'); k.textContent = s.out ? t.out : t.in; k.className = 'tag' + (s.out ? ' c' : '');
    this.$('.step h3').textContent = s.title; this.$('.stD').textContent = s.text || '';
    this.$('dl').innerHTML = (s.data || []).map(r => `<div><dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd></div>`).join('');
    this.$('dl').style.display = (s.data || []).length ? '' : 'none';
    this.root.querySelectorAll('ol button').forEach((b, i) => b.classList.toggle('on', i == this.si));
    this.ui();
  }
  go(i) { this.si = i; this.mark(); this._panel(); this.run(); }
  cards(g) {
    this.grp = g; const t = this.t;
    this.root.querySelectorAll('.tab').forEach(b => b.setAttribute('aria-selected', b.dataset.g == g));
    this.$('.cards').innerHTML = this.S.map((c, i) => { if ((c.group || 'gesti') != g) return ''; const o = c.steps.some(s => s.out);
      return `<button class="chip ${o ? 'c' : 'l'}" type="button" data-i="${i}" aria-pressed="${i == this.sc}">${esc(c.title)}<small>${o ? t.out : t.in} · ${c.steps.length} ${t.steps}</small></button>`; }).join('');
  }
  sel(i, auto) {
    this.sc = i; this.si = 0; this.playing = auto; const c = this.cur(), o = c.steps.some(s => s.out);
    if ((c.group || 'gesti') != this.grp) this.cards(c.group || 'gesti'); else this.root.querySelectorAll('.chip').forEach(b => b.setAttribute('aria-pressed', +b.dataset.i == i));
    this.$('.scT').textContent = c.title; this.$('.scS').textContent = c.summary || '';
    const off = this.$('.off'); off.textContent = c.offline || ''; off.className = 'off' + (o ? '' : ' l'); off.style.display = c.offline ? '' : 'none';
    this.$('ol').innerHTML = c.steps.map((s, j) => `<li class="${s.out ? 'c' : 'l'}"><button type="button" data-i="${j}">${esc(s.title)}</button></li>`).join('');
    this.go(0);
  }
  info(id) {
    const n = this.nodes[id], L = this.S.map((c, i) => [c, i]).filter(([c]) => c.steps.some(s => s.path.includes(id)));
    this.$('.ni h4').textContent = n.name; this.$('.ni .s').textContent = n.sub || ''; this.$('.ni .d').textContent = n.info || '';
    this.$('.ni h5').textContent = this.t.via(L.length);
    this.$('.nil').innerHTML = L.map(([c, i]) => `<button type="button" data-i="${i}">${esc(c.title)}</button>`).join('');
    this.$('.ni').classList.add('open');
  }
}
if (!customElements.get('home-flow-explorer')) customElements.define('home-flow-explorer', HomeFlowExplorer);
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'home-flow-explorer')) window.customCards.push({type:'home-flow-explorer', name:'Home Flow Explorer', description:'Interactive map of how messages travel through your smart home'});
