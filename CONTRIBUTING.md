# Contribuir

1. Haz un fork y crea una rama: `git checkout -b mejora/lo-que-sea`.
2. Si tocas `scripts/mapa.py`, comprueba que el ejemplo sigue funcionando:
   ```bash
   python3 scripts/mapa.py build examples/demo examples/demo-datos.json
   ```
   Abre `examples/demo/mapa.html` y revisa la consola del navegador.
3. Si cambias el formato de `datos.json`, actualiza `SKILL.md` y sube la versión del docstring de `mapa.py`.
4. Abre un pull request explicando qué problema resuelve.

Ideas abiertas:
- Traducción al inglés de `SKILL.md` y de la interfaz.
- Versión offline del HTML, con d3 y marked embebidos.
- Soporte para otros formatos (`.txt`, `.adoc`).
- Vista de grafo además del árbol.

Para bugs o propuestas, abre un issue.
