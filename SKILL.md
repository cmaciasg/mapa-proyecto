---
name: mapa-proyecto
description: Genera o actualiza un mapa mental interactivo (mapa.html) de los .md de un proyecto, con dudas, decisiones, requisitos, huecos y contradicciones enlazados a su fichero de origen; úsala cuando pidan "mapa del proyecto", "actualiza el mapa" o no sepan dónde está algo en la documentación.
argument-hint: "[ruta-del-proyecto]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
context: |
  Pensada para proyectos con mucha documentación Markdown repartida en varias
  carpetas: notas de aprendizaje, idas y venidas entre compañeros y specs SDD
  (OpenSpec u otros). La parte determinista (escaneo, detección de cambios por
  sha1 y generación del HTML con d3 y marked) la hace scripts/mapa.py; Claude
  solo clasifica por tema y estado. Las pasadas son incrementales.
---

# Mapa del proyecto

Objetivo: que el usuario sepa **dónde buscar** sin abrir .md a mano. El resultado es siempre `mapa.html` en la raíz del proyecto, que se abre con doble clic en el navegador. Nunca entregues el mapa como Markdown.

## 1. Script

El script está en `scripts/mapa.py`, dentro de la carpeta de esta skill (`<skill_dir>`). Necesita Python 3.8 o superior y no tiene dependencias. No lo modifiques.

## 2. Escanear

```bash
python3 <skill_dir>/scripts/mapa.py scan <raiz>
```

- Recorre todo el árbol de forma recursiva e ignora `.git`, `node_modules`, `vendor`, `dist`, `build`, `var`, `cache` y carpetas ocultas.
- Respeta un `.mapignore` en la raíz (patrones glob, uno por línea).
- Devuelve cada .md con el estado `new`, `changed` o `same` respecto a la última pasada, y la lista de borrados.
- Si hay más de unos 80 ficheros o el árbol es dudoso, enseña al usuario el recuento por carpeta y pregúntale qué excluir antes de seguir.

## 3. Construir los datos

**Primera vez** (no existe `<raiz>/.mapa/datos.json`): lee todos los .md.

**Siguientes veces**: parte de `.mapa/datos.json`. Lee solo los ficheros `new` o `changed`, y quita las fuentes de los ficheros borrados. Si un nodo se queda sin fuentes, elimínalo salvo que sea un tema. Vuelve a comprobar las contradicciones que afecten a lo que ha cambiado.

Escribe un JSON con esta forma en un fichero temporal:

```json
{"project": "Nombre",
 "root": {"name": "Nombre", "children": [
   {"name": "Tema (p. ej. Autenticación)", "children": [
     {"name": "Etiqueta corta del punto", "status": "decidido",
      "summary": "1-2 frases: qué se pregunta o se decidió",
      "who": "opcional: quién lo dijo (yo, compañero, IA, cliente)",
      "sources": [{"file": "ruta/relativa.md", "section": "Texto del encabezado"}]}
   ]}
 ]}}
```

Reglas:
- **Agrupa por tema funcional, no por carpeta.** La carpeta ya aparece en la ruta de cada fuente.
- El nivel 1 son los temas; puede haber subtemas. Las hojas son puntos concretos y siempre llevan `status` y al menos una fuente.
- Valores de `status`:
  - `pendiente`: duda o pregunta abierta.
  - `decidido`: decisión tomada.
  - `requisito`.
  - `hueco`: algo que nadie ha cubierto y debería.
  - `aprendido`: concepto ya entendido; para proyectos de aprendizaje.
  - `contradiccion`: dos fuentes dicen cosas distintas.
- Una duda que se resuelve en otro .md pasa a `decidido` o `aprendido` y lleva **ambas** fuentes (la pregunta y la respuesta).
- `section` es el texto literal del encabezado más cercano; el visor lo resalta. Omítelo si el punto no está bajo ningún encabezado.
- Si existe `openspec/`, úsalo como fuente más: requisitos y escenarios de `specs/`, propuestas y tareas de `changes/`. `archive/` cuenta como decidido.
- Etiquetas de nodo de 3 a 7 palabras. No inventes datos que no estén en los ficheros.
- No pongas `isNew`: lo calcula el script.

## 4. Generar

```bash
python3 <skill_dir>/scripts/mapa.py build <raiz> <datos.json>
```

El comando escribe `<raiz>/mapa.html` y actualiza `.mapa/state.json` y `.mapa/datos.json`. Si avisa de fuentes inexistentes, corrige las rutas y repite.

Si el proyecto es un repositorio git, sugiere una sola vez añadir `mapa.html` y `.mapa/` al `.gitignore`, salvo que quieran compartir el mapa con el compañero.

## 5. Entregar

En 2 o 3 líneas: dónde está `mapa.html`, cuántos puntos hay por estado y lo más relevante (contradicciones, huecos y novedades). No describas el mapa entero.
