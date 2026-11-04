// Dibuja los diagramas de render-codeblock-mermaid.html. Solo se carga en las páginas que tienen alguno.
// static/vendor/pele-*/ es dist/esm de `npm pack pele@<versión>`, sin modificar. Pele descarga únicamente el tipo de
// diagrama que necesita. Para actualizarlo: copia la versión nueva con su LICENSE y cambia aquí la ruta.
for (const el of document.querySelectorAll("[data-diagram]")) {
  import("../vendor/pele-1.13.0/lazy.js")
    .then(({ mountAsync }) => mountAsync(el, el.textContent))
    // Se quita aunque falle: el CSS oculta el código fuente mientras este atributo siga puesto.
    .finally(() => el.removeAttribute("data-diagram"));
}
