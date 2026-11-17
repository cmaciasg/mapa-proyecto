# Changelog

Cada entrada lleva la fecha que figura en el docstring de `scripts/mapa.py`.

## 2026-11-17

- **Novedades por punto, no por fichero.** Un punto sale como NUEVO solo si no
  estaba en la pasada anterior, si cambia su `status` o su `summary`, o si cambia
  el texto de alguna sección que cita (o del fichero entero, si la fuente no
  tiene `section`). Antes, cualquier cambio en un fichero marcaba como NUEVO
  todos los puntos que lo citaban.
- `datos.json` guarda una huella por punto (`_huella`), que calcula el script.
  Al actualizar no salen novedades falsas: los puntos sin huella previa solo se
  comparan por `status` y `summary`.
- `build` imprime la lista de novedades y de puntos eliminados.
- Si hay fuentes inexistentes, `build` no escribe nada y sale con código 2.
  Antes guardaba el estado igualmente y, al repetir tras corregir las rutas,
  se perdían las novedades.
- La primera pasada no marca nada como NUEVO.
- `SKILL.md`: conservar la etiqueta de los puntos que siguen existiendo (el
  script los reconoce por ella).

## Primera publicación

- Escaneo incremental, clasificación por tema y estado, y `mapa.html` con d3 y marked.
