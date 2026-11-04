// Mejoras opcionales: la web funciona igual sin JavaScript.

// Índice del post: abierto en pantallas anchas y con la sección en la que estás marcada (aria-current).
const toc = document.querySelector("[data-toc]");
if (toc) {
  const wide = matchMedia("(min-width: 1100px)");
  const sync = () => (toc.open = wide.matches);
  sync();
  wide.addEventListener("change", sync);

  const links = [...toc.querySelectorAll('a[href^="#"]')];
  const heads = links.map((a) => document.getElementById(decodeURIComponent(a.hash.slice(1))));
  let current = null;
  let queued = false;
  const update = () => {
    queued = false;
    // La sección activa es la última cuyo título ya ha pasado del primer tercio de la pantalla; al final de la
    // página, la última, aunque sea tan corta que su título no llegue a esa altura.
    const line = innerHeight / 3;
    let i = -1;
    heads.forEach((h, n) => {
      if (h && h.getBoundingClientRect().top <= line) i = n;
    });
    if (innerHeight + scrollY >= document.documentElement.scrollHeight - 2) i = heads.length - 1;
    const next = links[i] ?? null;
    if (next === current) return;
    current?.removeAttribute("aria-current");
    next?.setAttribute("aria-current", "location");
    current = next;
  };
  addEventListener("scroll", () => {
    if (!queued) (queued = true), requestAnimationFrame(update);
  }, { passive: true });
  addEventListener("resize", update);
  update();
  // En móvil el índice va encima del texto: al elegir una sección, se cierra.
  toc.addEventListener("click", (e) => {
    if (e.target.closest("a") && !wide.matches) toc.open = false;
  });
}

// Botón de copiar en los bloques de código (render-codeblock.html).
if (navigator.clipboard) {
  for (const button of document.querySelectorAll(".code-copy")) {
    const label = button.textContent;
    button.hidden = false;
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.closest(".code").querySelector("pre code").textContent);
      } catch {
        return; // Sin permiso para el portapapeles: el código sigue ahí para copiarlo a mano.
      }
      button.textContent = button.dataset.copied;
      setTimeout(() => (button.textContent = label), 1600);
    });
  }
}
