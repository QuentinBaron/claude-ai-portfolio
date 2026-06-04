#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nudis_editor_gen.py -- Generateur du module d'edition manuelle des especes
Usage : python nudis_editor_gen.py
Sortie: nudis_editor.html (ouvrir dans le navigateur)
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

# Mapping famille -> coloration par defaut (miroir de COLORATION_FAMILY du template)
COLORATION_FAMILY = {
    'Chromodorididae':'vif','Hexabranchidae':'vif','Facelinidae':'vif',
    'Flabellinidae':'vif','Polyceridae':'vif','Goniodorididae':'vif',
    'Vayssiereidae':'vif','Costasiellidae':'vif','Elysiidae':'vif',
    'Phyllidiidae':'motifs','Dorididae':'motifs','Discodorididae':'motifs',
    'Aegiridae':'motifs','Tritoniidae':'motifs','Arminidae':'motifs',
    'Aeolidiidae':'camouflage','Pleurobranchidae':'camouflage','Aplysiidae':'camouflage',
    'Dolabriferidae':'camouflage','Dendrodorididae':'camouflage','Bornellidae':'camouflage',
    'Dotidae':'camouflage','Trinchesiidae':'camouflage','Eubranchidae':'camouflage',
    'Scyllaeidae':'camouflage','Tethydidae':'camouflage','Actinocyclidae':'camouflage',
    'Aglajidae':'sobre','Runcinidae':'sobre','Limapontiidae':'sobre',
    'Haminoeidae':'sobre','Velutinidae':'camouflage','Bullidae':'camouflage',
}

print("Chargement des donnees...")
enriched  = json.loads((HERE / "nudis_enriched.json").read_text(encoding="utf-8"))
colors    = json.loads((HERE / "nudis_colors.json").read_text(encoding="utf-8")) if (HERE / "nudis_colors.json").exists() else {}
overrides = json.loads((HERE / "nudis_species_overrides.json").read_text(encoding="utf-8")) if (HERE / "nudis_species_overrides.json").exists() else {}

species_data = []
for sp in enriched:
    slug = sp.get("s", "")
    if not slug:
        continue
    photo = sp.get("p", "") or ""
    if not photo:
        ps = sp.get("ps") or []
        photo = ps[0] if ps else ""
    fam  = sp.get("f", "") or ""
    auto = colors.get(slug, {})
    species_data.append({
        "s":    slug,
        "n":    sp.get("n", "") or slug,
        "f":    fam,
        "o":    sp.get("o", "") or "",
        "p":    photo,
        "ac":   auto.get("couleurs", []),
        "acol": COLORATION_FAMILY.get(fam, ""),
        "asrc": auto.get("source", ""),
        "hac":  bool(auto.get("couleurs", [])),
        "acaj": auto.get("couleurs_adj", []),
    })

species_data.sort(key=lambda x: (x["f"] or "zzz", x["n"] or ""))
print(f"  {len(species_data)} especes chargees")

species_json   = json.dumps(species_data,   ensure_ascii=False, separators=(',', ':'))
overrides_json = json.dumps(overrides,      ensure_ascii=False, separators=(',', ':'))

# ── Template HTML ──────────────────────────────────────────────────────────────
HTML_TMPL = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Nudidex Editor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;display:flex;height:100vh;overflow:hidden;background:#f8fafc;font-size:14px}
#sidebar{width:270px;border-right:1px solid #e2e8f0;display:flex;flex-direction:column;background:#fff;flex-shrink:0}
#main{flex:1;overflow-y:auto;padding:24px 32px}
#search{width:100%;padding:8px 12px;border:none;border-bottom:1px solid #e2e8f0;font-size:13px;outline:none}
#topbar{display:flex;align-items:center;gap:8px;padding:6px 10px;border-bottom:1px solid #e2e8f0;background:#f8fafc}
#progress{font-size:11px;color:#64748b;flex:1}
#export-btn{font-size:11px;padding:4px 10px;border-radius:6px;border:1px solid #cbd5e1;background:#fff;cursor:pointer;color:#475569}
#export-btn:hover{background:#f1f5f9}
#sp-list{flex:1;overflow-y:auto}
.fam-hdr{font-size:10px;font-weight:700;color:#94a3b8;padding:10px 12px 3px;text-transform:uppercase;letter-spacing:.5px;position:sticky;top:0;background:#fff;border-top:1px solid #f1f5f9}
.sp-item{padding:5px 12px 5px 20px;font-size:12px;cursor:pointer;color:#334155;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-style:italic}
.sp-item:hover{background:#f1f5f9}
.sp-item.active{background:#eff6ff;color:#2563eb}
.sp-item.done{color:#16a34a}
.sp-item.done::before{content:"\\2713 ";font-style:normal;font-size:10px}
.sp-item.auto-only{color:#2563eb;opacity:.7}
.sp-item.auto-only::before{content:"\\25CF ";font-style:normal;font-size:8px;opacity:.5}
#sp-name{font-size:22px;font-style:italic;color:#1e293b;margin-bottom:3px}
#sp-meta{font-size:12px;color:#94a3b8;margin-bottom:16px}
#sp-photo{display:block;max-height:260px;max-width:100%;object-fit:contain;border-radius:10px;background:#f1f5f9;margin-bottom:20px}
.sec{font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;margin-top:18px}
.swatches{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.swatch{width:30px;height:30px;border-radius:50%;cursor:pointer;border:3px solid transparent;transition:all .12s;flex-shrink:0}
.swatch.sel{border-color:#1e293b;transform:scale(1.15)}
.col-btns{display:flex;gap:8px;flex-wrap:wrap}
.col-btn{padding:5px 16px;border-radius:99px;border:2px solid #cbd5e1;background:#f8fafc;cursor:pointer;font-size:13px;color:#475569;transition:all .12s}
.col-btn.sel{background:#1e293b;color:#fff;border-color:#1e293b}
.l1-row{display:flex;align-items:center;gap:10px;margin-top:18px}
.l1-row label{font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;white-space:nowrap}
.l1-row select{padding:5px 8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;color:#475569;background:#fff}
.auto-box{background:#f8fafc;border-radius:8px;padding:9px 13px;font-size:11px;color:#94a3b8;margin-top:16px;line-height:1.7}
.auto-box b{color:#64748b}
.nav-bar{display:flex;gap:10px;align-items:center;margin-top:20px;padding-top:16px;border-top:1px solid #f1f5f9}
.nav-btn{padding:7px 18px;border-radius:8px;border:1px solid #cbd5e1;background:#fff;cursor:pointer;font-size:13px;color:#475569}
.nav-btn:hover{background:#f1f5f9}
.save-btn{padding:7px 24px;border-radius:8px;border:none;background:#2563eb;color:#fff;cursor:pointer;font-size:13px;font-weight:700}
.save-btn:hover{background:#1d4ed8}
#mod{font-size:11px;color:#f59e0b;font-weight:700;display:none;margin-left:4px}
.clear-btn{padding:5px 12px;border-radius:6px;border:1px solid #fca5a5;background:#fff;cursor:pointer;font-size:12px;color:#dc2626;margin-left:auto}
.clear-btn:hover{background:#fee2e2}
</style>
</head>
<body>
<div id="sidebar">
  <input id="search" type="search" placeholder="Rechercher une espece...">
  <div id="topbar">
    <span id="progress">0 / 0 renseignees</span>
    <button id="export-btn" onclick="exportJSON()">Exporter JSON</button>
  </div>
  <div id="sp-list"></div>
</div>
<div id="main">
  <div id="sp-name">Chargement...</div>
  <div id="sp-meta"></div>
  <img id="sp-photo" src="" alt="">
  <div class="sec">Couleurs certaines <span id="src-badge" style="font-style:normal;font-weight:400;font-size:9px;color:#94a3b8;text-transform:none;letter-spacing:0;margin-left:6px;"></span></div>
  <div id="swatches" class="swatches"></div>
  <div class="sec" style="margin-top:10px">Confusions acceptables <span style="font-style:normal;font-weight:400;font-size:9px;color:#94a3b8;text-transform:none;letter-spacing:0;margin-left:6px;">+6 pts, pas de penalite</span></div>
  <div id="swatches-adj" class="swatches" style="margin-bottom:4px"></div>
  <div class="sec">Coloration generale</div>
  <div id="col-btns" class="col-btns"></div>
  <div class="l1-row">
    <label>Override L1</label>
    <select id="l1-sel">
      <option value="">-- (defaut famille)</option>
      <option value="cerates">cerates</option>
      <option value="couronne">couronne</option>
      <option value="coquille">coquille</option>
      <option value="crete">crete</option>
      <option value="rien">rien</option>
    </select>
  </div>
  <div class="auto-box" id="auto-box"></div>
  <div class="nav-bar">
    <button class="nav-btn" onclick="navigate(-1)">&larr; Prec</button>
    <button class="save-btn" onclick="save()">Enregistrer</button>
    <button class="nav-btn" onclick="navigate(1)">Suivant &rarr;</button>
    <span id="mod">&#9679; modifie</span>
    <button class="clear-btn" onclick="clearCurrent()">Effacer</button>
  </div>
</div>
<script>
var SP=__SPECIES__;
var OV=__OVERRIDES__;
var LS='nudis_ov2';
try{var _s=JSON.parse(localStorage.getItem(LS));if(_s)OV=_s;}catch(e){}
var CI=0;

var COLS=[
  {k:'blanc',l:'Blanc',h:'#f5f5eb',b:'#bbb'},
  {k:'noir',l:'Noir',h:'#1a1a2e',b:'#333'},
  {k:'rouge',l:'Rouge',h:'#e53e3e',b:'#c53030'},
  {k:'orange',l:'Orange',h:'#ed8936',b:'#c05621'},
  {k:'jaune',l:'Jaune',h:'#ecc94b',b:'#b7791f'},
  {k:'vert',l:'Vert',h:'#48bb78',b:'#276749'},
  {k:'bleu',l:'Bleu',h:'#4299e1',b:'#2b6cb0'},
  {k:'violet',l:'Violet',h:'#805ad5',b:'#553c9a'},
  {k:'rose',l:'Rose',h:'#ed64a6',b:'#b83280'},
  {k:'brun',l:'Brun',h:'#a0522d',b:'#744210'},
  {k:'gris',l:'Gris',h:'#718096',b:'#4a5568'},
  {k:'translucide',l:'Transl.',h:'#e8f4fd',b:'#bee3f8'},
  {k:'irise',l:'Irise',h:'#d6bcfa',b:'#9f7aea'},
];
var COLORATION=[
  {k:'vives',      l:'Couleurs vives'},
  {k:'motifs',     l:'Sobre + motifs'},
  {k:'camouflage', l:'Camouflage'},
];

function makeSwatch(container, c, adjMode) {
  var d=document.createElement('div');
  d.className='swatch';d.dataset.k=c.k;d.title=c.l+(adjMode?' (confusion)':'');
  d.style.background=c.h;
  if(adjMode) d.style.boxShadow='0 0 0 1px '+c.b+', 0 0 0 3px #fff, 0 0 0 4px '+c.b;
  else d.style.boxShadow='0 0 0 1px '+c.b;
  d.onclick=function(){this.classList.toggle('sel');mark();};
  container.appendChild(d);
}
var sw=document.getElementById('swatches');
var swAdj=document.getElementById('swatches-adj');
COLS.forEach(function(c){
  makeSwatch(sw, c, false);
  makeSwatch(swAdj, c, true);
});

var cb=document.getElementById('col-btns');
COLORATION.forEach(function(c){
  var b=document.createElement('button');
  b.className='col-btn';b.dataset.k=c.k;b.textContent=c.l;
  b.onclick=function(){
    document.querySelectorAll('.col-btn').forEach(function(x){x.classList.remove('sel');});
    this.classList.add('sel');mark();
  };
  cb.appendChild(b);
});

document.getElementById('l1-sel').onchange=mark;

function mark(){document.getElementById('mod').style.display='inline';}

function buildSidebar(){
  var list=document.getElementById('sp-list');
  var q=document.getElementById('search').value.toLowerCase();
  list.innerHTML='';
  var lastF=null;
  SP.forEach(function(sp,i){
    if(q&&!(sp.n.toLowerCase().includes(q)||(sp.f||'').toLowerCase().includes(q)))return;
    if(sp.f!==lastF){
      var h=document.createElement('div');h.className='fam-hdr';
      h.textContent=sp.f||'--';list.appendChild(h);lastF=sp.f;
    }
    var el=document.createElement('div');
    var cls='sp-item'+(i===CI?' active':'');
    if(OV[sp.s])cls+=' done';
    else if(sp.hac)cls+=' auto-only';
    el.className=cls;
    el.title=sp.n+(OV[sp.s]?' [manuel]':sp.hac?' [auto]':'');el.textContent=sp.n;
    el.onclick=(function(idx){return function(){load(idx);};})(i);
    list.appendChild(el);
  });
}

function load(idx){
  CI=idx;
  document.getElementById('mod').style.display='none';
  var sp=SP[idx];
  var ov=OV[sp.s]||{};
  document.getElementById('sp-name').textContent=sp.n||sp.s;
  document.getElementById('sp-meta').textContent=(sp.o||'')+(sp.f?' \xb7 '+sp.f:'');
  var img=document.getElementById('sp-photo');
  if(sp.p){img.src=sp.p;img.style.display='block';}
  else{img.src='';img.style.display='none';}

  var isManual=!!ov.couleurs;
  var selC   =ov.couleurs    ||sp.ac  ||[];
  var selCAdj=ov.couleurs_adj||sp.acaj||[];
  document.querySelectorAll('#swatches .swatch').forEach(function(s){
    s.classList.toggle('sel',selC.indexOf(s.dataset.k)>=0);
  });
  document.querySelectorAll('#swatches-adj .swatch').forEach(function(s){
    s.classList.toggle('sel',selCAdj.indexOf(s.dataset.k)>=0);
  });
  var badge=document.getElementById('src-badge');
  if(isManual) badge.textContent='[manuel]';
  else if(sp.ac&&sp.ac.length) badge.textContent='[auto - '+sp.asrc+']';
  else badge.textContent='[aucune donnee]';
  var selCol=ov.coloration||sp.acol||'';
  document.querySelectorAll('.col-btn').forEach(function(b){
    b.classList.toggle('sel',b.dataset.k===selCol);
  });
  document.getElementById('l1-sel').value=ov.l1_override||'';

  var info='<b>Auto :</b> couleurs: '+(sp.ac.length?sp.ac.join(', '):'--');
  info+=' &nbsp;|&nbsp; coloration: '+(sp.acol||'--');
  info+=' &nbsp;|&nbsp; source: '+(sp.asrc||'--');
  document.getElementById('auto-box').innerHTML=info;

  buildSidebar();updateProg();
}

function save(){
  var sp=SP[CI];
  var couleurs=[], coulAdj=[];
  document.querySelectorAll('#swatches .swatch.sel').forEach(function(s){couleurs.push(s.dataset.k);});
  document.querySelectorAll('#swatches-adj .swatch.sel').forEach(function(s){coulAdj.push(s.dataset.k);});
  var coloration='';
  document.querySelectorAll('.col-btn.sel').forEach(function(b){coloration=b.dataset.k;});
  var l1=document.getElementById('l1-sel').value;
  if(couleurs.length||coulAdj.length||coloration||l1){
    OV[sp.s]={};
    if(couleurs.length)OV[sp.s].couleurs=couleurs;
    if(coulAdj.length)OV[sp.s].couleurs_adj=coulAdj;
    if(coloration)OV[sp.s].coloration=coloration;
    if(l1)OV[sp.s].l1_override=l1;
  } else {
    delete OV[sp.s];
  }
  localStorage.setItem(LS,JSON.stringify(OV));
  document.getElementById('mod').style.display='none';
  buildSidebar();updateProg();
}

function clearCurrent(){
  var sp=SP[CI];delete OV[sp.s];
  localStorage.setItem(LS,JSON.stringify(OV));load(CI);
}

function navigate(dir){
  save();
  CI=(CI+dir+SP.length)%SP.length;
  load(CI);
  setTimeout(function(){
    var a=document.querySelector('.sp-item.active');
    if(a)a.scrollIntoView({block:'nearest'});
  },50);
}

function updateProg(){
  var manual=Object.keys(OV).length;
  var withAuto=SP.filter(function(s){return s.hac;}).length;
  document.getElementById('progress').textContent=
    manual+' manuelles · '+withAuto+' auto / '+SP.length;
}

function exportJSON(){
  var blob=new Blob([JSON.stringify(OV,null,2)],{type:'application/json'});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='nudis_species_overrides.json';a.click();
}

document.getElementById('search').oninput=buildSidebar;
buildSidebar();load(0);
</script>
</body>
</html>"""

out = HTML_TMPL.replace('__SPECIES__', species_json).replace('__OVERRIDES__', overrides_json)
out_path = HERE / "nudis_editor.html"
out_path.write_text(out, encoding="utf-8")
print(f"OK nudis_editor.html genere ({len(species_data)} especes, {out_path.stat().st_size // 1024} KB)")
