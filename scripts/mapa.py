#!/usr/bin/env python3
"""mapa.py v3 — escanea los .md de un proyecto y construye mapa.html.

Uso:
  python3 mapa.py scan  <raiz>                 -> inventario JSON (new/changed/same)
  python3 mapa.py build <raiz> <datos.json>    -> escribe <raiz>/mapa.html y actualiza .mapa/state.json
"""
import fnmatch, hashlib, json, os, re, sys, datetime, html

IGNORAR_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".idea", ".vscode", ".mapa", "var", "cache"}


def patrones_ignore(raiz):
    p = os.path.join(raiz, ".mapignore")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def listar_md(raiz):
    pats = patrones_ignore(raiz)
    out = []
    for d, dirs, files in os.walk(raiz):
        rel_d = os.path.relpath(d, raiz)
        dirs[:] = [x for x in dirs if x not in IGNORAR_DIRS and not x.startswith(".")
                   and not any(fnmatch.fnmatch(os.path.normpath(os.path.join(rel_d, x)), p.rstrip("/")) for p in pats)]
        for fn in files:
            if not fn.lower().endswith(".md"):
                continue
            rel = os.path.normpath(os.path.join(rel_d, fn))
            if fn == "MAP.md" or any(fnmatch.fnmatch(rel, p) for p in pats):
                continue
            out.append(rel)
    return sorted(out)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def estado_previo(raiz):
    p = os.path.join(raiz, ".mapa", "state.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def scan(raiz):
    prev = estado_previo(raiz)
    inv = []
    for rel in listar_md(raiz):
        h = sha(os.path.join(raiz, rel))
        st = "new" if rel not in prev else ("changed" if prev[rel] != h else "same")
        inv.append({"path": rel, "status": st, "bytes": os.path.getsize(os.path.join(raiz, rel))})
    borrados = [p for p in prev if p not in {i["path"] for i in inv}]
    return {"root": os.path.abspath(raiz), "files": inv, "deleted": borrados}


def seccion(texto, section):
    """Texto bajo el encabezado que contiene `section` (hasta el siguiente de igual o mayor nivel).
    Sin `section`, o si no se encuentra, devuelve el fichero entero."""
    if not section:
        return texto
    buscado = section.lower().lstrip("#").strip()
    lineas = texto.splitlines()
    encabezados, en_codigo = [], False
    for i, l in enumerate(lineas):
        if l.lstrip().startswith("```"):
            en_codigo = not en_codigo
            continue
        m = None if en_codigo else re.match(r"^(#{1,6})\s+(.*)", l)
        if m:
            encabezados.append((i, len(m.group(1)), m.group(2).lower()))
    for k, (i, nivel, txt) in enumerate(encabezados):
        if buscado in txt:
            fin = next((j for j, n, _ in encabezados[k + 1:] if n <= nivel), len(lineas))
            return "\n".join(lineas[i:fin])
    return texto


def hojas_previas(raiz, datos_path):
    """Puntos de la pasada anterior por etiqueta, o None si no hay con qué comparar."""
    p = os.path.join(raiz, ".mapa", "datos.json")
    if not os.path.exists(p):
        return None
    if os.path.abspath(p) == os.path.abspath(datos_path):
        print("AVISO: datos.json es el de .mapa/; escríbelo en un fichero temporal para detectar novedades.", file=sys.stderr)
        return None
    with open(p, encoding="utf-8") as f:
        previo = json.load(f)
    out = {}

    def indexar(n):
        for c in n.get("children", []):
            indexar(c)
        if n.get("sources"):
            out[n["name"].strip().lower()] = n

    indexar(previo["root"])
    return out


def build(raiz, datos_path):
    previas = hojas_previas(raiz, datos_path)
    with open(datos_path, encoding="utf-8") as f:
        datos = json.load(f)
    inv = {i["path"]: i["status"] for i in scan(raiz)["files"]}
    contenidos, faltan, novedades, vistos = {}, [], [], set()

    def recorrer(n):
        nuevo = False
        for c in n.get("children", []):
            nuevo = recorrer(c) or nuevo
        n.pop("isNew", None)
        if n.get("sources"):
            partes = []
            for s in n["sources"]:
                fp = s["file"]
                if fp not in inv:
                    faltan.append(fp)
                    continue
                if fp not in contenidos:
                    with open(os.path.join(raiz, fp), encoding="utf-8", errors="replace") as f:
                        contenidos[fp] = f.read()
                partes.append(fp + "\n" + seccion(contenidos[fp], s.get("section")))
            huella = hashlib.sha1("\n\0".join(partes).encode("utf-8")).hexdigest()
            clave = n["name"].strip().lower()
            vistos.add(clave)
            if previas is not None:
                p = previas.get(clave)
                cambia = (p is None or p.get("status") != n.get("status") or p.get("summary") != n.get("summary")
                          or (p.get("_huella") is not None and p["_huella"] != huella))
                if cambia:
                    novedades.append(n["name"])
                nuevo = cambia or nuevo
            n["_huella"] = huella
            n["isNew"] = nuevo
        return nuevo

    recorrer(datos["root"])
    if faltan:
        print("ERROR: fuentes inexistentes; no se ha escrito nada:", sorted(set(faltan)), file=sys.stderr)
        sys.exit(2)
    os.makedirs(os.path.join(raiz, ".mapa"), exist_ok=True)
    with open(os.path.join(raiz, ".mapa", "datos.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    if previas is None:
        print("NOVEDADES: primera pasada, nada con qué comparar")
    else:
        print("NOVEDADES:", len(novedades), "|", "; ".join(novedades))
        quitados = sorted(p["name"] for k, p in previas.items() if k not in vistos)
        print("ELIMINADOS:", len(quitados), "|", "; ".join(quitados))
    datos["files"] = contenidos
    datos["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    datos.setdefault("project", os.path.basename(os.path.abspath(raiz)))
    payload = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    out = PLANTILLA.replace("__TITULO__", html.escape(datos["project"])).replace("__DATOS__", payload)
    with open(os.path.join(raiz, "mapa.html"), "w", encoding="utf-8") as f:
        f.write(out)
    os.makedirs(os.path.join(raiz, ".mapa"), exist_ok=True)
    with open(os.path.join(raiz, ".mapa", "state.json"), "w", encoding="utf-8") as f:
        json.dump({p: sha(os.path.join(raiz, p)) for p in inv}, f, indent=1)
    print(os.path.join(raiz, "mapa.html"))


PLANTILLA = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Mapa · __TITULO__</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.2/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@18.2.1/lib/marked.umd.js"></script>
<style>
:root{--bg:#14161a;--panel:#1c1f25;--txt:#e6e6e6;--muted:#8a919c;--line:#3a3f48;
--pendiente:#f0a43a;--decidido:#4cc38a;--requisito:#5aa9f0;--hueco:#e5534b;--aprendido:#b48ef0;--contradiccion:#ff4d8d;--tema:#9aa4b2}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--txt);display:flex;height:100vh;overflow:hidden}
#main{flex:1;display:flex;flex-direction:column;min-width:0}
header{display:flex;gap:12px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--line);flex-wrap:wrap}
header h1{font-size:16px;margin:0 8px 0 0}header .gen{color:var(--muted);font-size:12px}
input,button{background:var(--panel);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:5px 9px;font:inherit}
button{cursor:pointer}button.on{border-color:var(--txt)}
.leg{display:flex;gap:6px;flex-wrap:wrap}.leg button{font-size:12px;padding:3px 8px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}
svg{flex:1;cursor:grab}
.link{fill:none;stroke:var(--line);stroke-width:1.4px}
.node text{fill:var(--txt);font-size:13px;paint-order:stroke;stroke:var(--bg);stroke-width:4px}
.node.dim{opacity:.18}.node.hit text{fill:#fff;font-weight:600}
.node.sel circle{stroke:#fff;stroke-width:3px}
.new-badge{fill:#ff4d8d;font-size:10px;font-weight:700}
#side{width:44%;max-width:720px;min-width:340px;background:var(--panel);border-left:1px solid var(--line);overflow:auto;padding:18px 22px;display:none}
#side.open{display:block}#side .close{float:right}
#side h2{margin:0 0 6px;font-size:18px}.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;color:#111;font-weight:600}
.src{margin-top:18px;border-top:1px solid var(--line);padding-top:10px}.src .path{color:var(--muted);font-family:ui-monospace,monospace;font-size:12px}
.md{background:var(--bg);border-radius:8px;padding:6px 16px;margin-top:8px;max-height:60vh;overflow:auto}
.md pre{background:#0d0f12;padding:8px;border-radius:6px;overflow:auto}.md code{font-family:ui-monospace,monospace;font-size:12.5px}
.md table{border-collapse:collapse}.md td,.md th{border:1px solid var(--line);padding:3px 7px}
.md .mark{background:#3b3420;outline:2px solid var(--pendiente);border-radius:4px}
a{color:var(--requisito)}
</style></head><body>
<div id="main"><header><h1>__TITULO__</h1><span class="gen" id="gen"></span>
<input id="q" placeholder="Buscar… (Enter)" size="24"><button id="exp">Expandir todo</button><button id="col">Plegar</button><button id="nuevos">Solo novedades</button>
<div class="leg" id="leg"></div></header><svg id="svg"></svg></div>
<aside id="side"></aside>
<script>
const DATA=__DATOS__;
const COL={pendiente:'--pendiente',decidido:'--decidido',requisito:'--requisito',hueco:'--hueco',aprendido:'--aprendido',contradiccion:'--contradiccion'};
const LBL={pendiente:'Pendiente',decidido:'Decidido',requisito:'Requisito',hueco:'Hueco',aprendido:'Aprendido',contradiccion:'Contradicción'};
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const color=d=>css(COL[d.data.status]||'--tema');
document.getElementById('gen').textContent='Generado '+DATA.generated;
const filtros=new Set();let soloNuevos=false;
const leg=document.getElementById('leg');
Object.keys(LBL).forEach(k=>{const b=document.createElement('button');b.innerHTML=`<span class="dot" style="background:${css(COL[k])}"></span>${LBL[k]}`;
 b.onclick=()=>{filtros.has(k)?filtros.delete(k):filtros.add(k);b.classList.toggle('on');aplicarFiltro()};leg.appendChild(b)});
const svg=d3.select('#svg'),g=svg.append('g');
const zoom=d3.zoom().scaleExtent([.2,3]).on('zoom',e=>g.attr('transform',e.transform));svg.call(zoom);
const root=d3.hierarchy(DATA.root);root.x0=0;root.y0=0;
root.descendants().forEach((d,i)=>{d.id=i;d._children=d.children;if(d.depth>1)d.children=null});
const tree=d3.tree().nodeSize([26,250]);let sel=null;
function update(src){
 tree(root);const nodes=root.descendants(),links=root.links();
 const node=g.selectAll('g.node').data(nodes,d=>d.id);
 const ent=node.enter().append('g').attr('class','node').attr('transform',`translate(${src.y0},${src.x0})`).style('cursor','pointer')
  .on('click',(e,d)=>{if(d._children){d.children=d.children?null:d._children;update(d)}mostrar(d)});
 ent.append('circle').attr('r',6);
 ent.append('text').attr('dy','0.32em');
 ent.append('text').attr('class','new-badge').attr('dy','-0.7em');
 const all=ent.merge(node);
 all.transition().duration(250).attr('transform',d=>`translate(${d.y},${d.x})`);
 all.select('circle').attr('fill',d=>d._children&&!d.children?color(d):css('--bg')).attr('stroke',color).attr('stroke-width',2.5);
 all.select('text:not(.new-badge)').attr('x',d=>d._children?-10:10).attr('text-anchor',d=>d._children?'end':'start').text(d=>d.data.name);
 all.select('.new-badge').attr('x',10).text(d=>d.data.isNew?'NUEVO':'');
 all.classed('sel',d=>d===sel);
 node.exit().transition().duration(200).attr('transform',`translate(${src.y},${src.x})`).remove();
 const link=g.selectAll('path.link').data(links,d=>d.target.id);
 const diag=d3.linkHorizontal().x(d=>d.y).y(d=>d.x);
 link.enter().insert('path','g').attr('class','link').attr('d',()=>{const o={x:src.x0,y:src.y0};return diag({source:o,target:o})})
  .merge(link).transition().duration(250).attr('d',diag);
 link.exit().remove();
 nodes.forEach(d=>{d.x0=d.x;d.y0=d.y});aplicarFiltro();
}
function setAll(open){root.descendants().forEach(d=>{if(d._children)d.children=open||d.depth===0?d._children:null});update(root)}
function abrirAncestros(d){let p=d.parent;while(p){p.children=p._children;p=p.parent}}
function hojasDe(d){return d._children?d._children.flatMap(hojasDe):[d]}
function hojas(){return root.descendants().filter(d=>!d.data.children)}
function aplicarFiltro(){
 const activo=filtros.size||soloNuevos;
 g.selectAll('g.node').classed('dim',d=>{if(!activo)return false;
  const ok=n=>(!filtros.size||filtros.has(n.data.status))&&(!soloNuevos||n.data.isNew);
  if(!d.data.children)return !ok(d);
  return !hojasDe(d).some(ok);})
}
document.getElementById('exp').onclick=()=>setAll(true);
document.getElementById('col').onclick=()=>setAll(false);
document.getElementById('nuevos').onclick=e=>{soloNuevos=!soloNuevos;e.target.classList.toggle('on');
 if(soloNuevos){hojas().filter(d=>d.data.isNew).forEach(abrirAncestros);update(root)}else aplicarFiltro()};
document.getElementById('q').addEventListener('keydown',e=>{if(e.key!=='Enter')return;const q=e.target.value.trim().toLowerCase();
 g.selectAll('g.node').classed('hit',false);if(!q)return;
 const hits=root.descendants().filter(d=>(d.data.name+' '+(d.data.summary||'')).toLowerCase().includes(q));
 hits.forEach(abrirAncestros);update(root);g.selectAll('g.node').classed('hit',d=>hits.includes(d));if(hits[0])mostrar(hits[0])});
const side=document.getElementById('side');
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function mostrar(d){sel=d;g.selectAll('g.node').classed('sel',x=>x===d);
 const n=d.data;let h=`<button class="close" onclick="side.classList.remove('open')">✕</button><h2>${esc(n.name)}</h2>`;
 if(n.status)h+=`<span class="tag" style="background:${color(d)}">${LBL[n.status]||n.status}</span> `;
 if(n.isNew)h+=`<span class="tag" style="background:var(--contradiccion)">NUEVO</span>`;
 if(n.summary)h+=`<p>${esc(n.summary)}</p>`;
 if(n.who)h+=`<p style="color:var(--muted)">Origen: ${esc(n.who)}</p>`;
 const kids=(d._children||[]);
 if(kids.length&&!n.sources){h+='<ul>'+kids.map(k=>`<li>${esc(k.data.name)}${k.data.status?' · '+(LBL[k.data.status]||''):''}</li>`).join('')+'</ul>'}
 (n.sources||[]).forEach((s,i)=>{const txt=DATA.files[s.file];
  h+=`<div class="src"><div class="path">${esc(s.file)}${s.section?' › '+esc(s.section):''}</div>`+
   (txt!=null?`<div class="md" id="md${i}">${marked.parse(txt)}</div>`:'<p>(fichero no encontrado)</p>')+'</div>'});
 side.innerHTML=h;side.classList.add('open');
 (n.sources||[]).forEach((s,i)=>{if(!s.section)return;const box=document.getElementById('md'+i);if(!box)return;
  const t=s.section.toLowerCase().replace(/^#+\s*/,'');
  const hd=[...box.querySelectorAll('h1,h2,h3,h4,h5,h6')].find(x=>x.textContent.toLowerCase().includes(t));
  if(hd){hd.classList.add('mark');box.scrollTop=hd.offsetTop-box.offsetTop-8}});
}
update(root);
const bb=document.getElementById('svg').getBoundingClientRect();
svg.call(zoom.transform,d3.zoomIdentity.translate(120,bb.height/2));
</script></body></html>"""

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "scan":
        print(json.dumps(scan(sys.argv[2]), ensure_ascii=False, indent=1))
    elif len(sys.argv) >= 4 and sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
