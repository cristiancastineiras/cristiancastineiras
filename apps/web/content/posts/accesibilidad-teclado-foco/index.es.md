---
title: "Navegación con teclado: el foco como parte del diseño de tu aplicación"
seoTitle: "Accesibilidad: teclado y gestión del foco"
description: "Cómo hacer que una aplicación React funcione con teclado: foco visible, orden lógico, elementos nativos, cambios de ruta y patrones como modales y menús."
date: 2025-04-24
tags: ["Accesibilidad", "React", "CSS"]
---

Muchas personas navegan sin ratón: por una discapacidad motora, usando un lector de pantalla o por simple preferencia. Comprobar si tu aplicación funciona con teclado es una de las pruebas de accesibilidad más rápidas: desconecta el ratón e intenta completar una tarea.

## Usa elementos nativos

La mayor parte de los problemas surgen por reinventar controles:

```tsx
// Mal: sin foco, sin teclado y sin rol
<div className="boton" onClick={guardar}>Guardar</div>

// Bien
<button type="button" onClick={guardar}>Guardar</button>
```

Un `<button>` recibe el foco, responde a Enter y Espacio y se anuncia correctamente, sin ningún código adicional. Un `<a href>` hace lo propio para navegar. La regla: si lleva a otro lugar, es un enlace; si realiza una acción, es un botón.

Replicarlo con un `div` exige `role`, `tabIndex` y manejar teclas, y es fácil olvidar alguna parte.

## Que el foco se vea

Eliminar el contorno de foco sin una alternativa impide saber dónde estás:

```css
/* Nunca así, sin alternativa */
*:focus {
  outline: none;
}

/* Bien: visible al navegar con teclado */
:focus-visible {
  outline: 2px solid var(--color-foco);
  outline-offset: 2px;
}
```

`:focus-visible` soluciona la queja habitual de los diseñadores: no aparece al hacer clic en un botón con el ratón, pero sí al llegar a él con el teclado. Asegúrate de que tenga contraste suficiente sobre todos los fondos.

También hay que evitar que una cabecera fija tape el elemento enfocado:

```css
html {
  scroll-padding-top: 5rem;
}
```

## Orden lógico

El orden del foco sigue el orden del DOM. Si reordenas con CSS, usando `order` en flex o colocando elementos en grid, lo visual y el foco pueden dejar de coincidir, y el foco saltará de forma confusa.

Y no uses valores positivos en `tabindex`: rompen el orden natural en toda la página.

- `tabindex="0"`: añade un elemento al orden natural.
- `tabindex="-1"`: lo hace enfocable por código, pero no con Tab.

## Saltar al contenido

Sin esto, un usuario de teclado atraviesa toda la navegación en cada página:

```html
<body>
  <a href="#principal" class="saltar">Saltar al contenido</a>
  <nav>...</nav>
  <main id="principal" tabindex="-1">...</main>
</body>
```

```css
.saltar:not(:focus) {
  position: absolute;
  clip-path: inset(50%);
  overflow: hidden;
  width: 1px;
  height: 1px;
}
```

## Cambios de ruta en una SPA

Al cambiar de página en una aplicación de una sola página, el foco se queda donde estaba, a menudo en un elemento que ya no existe, y un lector de pantalla no anuncia nada. La solución habitual es mover el foco al título o al contenido principal:

```tsx
function Pagina({ titulo, children }: Props) {
  const ref = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = titulo;
    ref.current?.focus();
  }, [titulo]);

  return (
    <main>
      <h1 ref={ref} tabIndex={-1}>{titulo}</h1>
      {children}
    </main>
  );
}
```

Algunos enrutadores lo facilitan. Compruébalo en el tuyo.

## Controles que aparecen y desaparecen

Cuando se abre o se cierra algo, decide a dónde va el foco.

- **Modal**: el foco entra al abrir, se queda dentro y vuelve al botón que lo abrió. `<dialog>` con `showModal()` ya lo hace.
- **Eliminar una fila**: si el botón desaparece, mueve el foco a la siguiente fila o al título de la lista. Si no, el foco se pierde en el inicio del documento.
- **Contenido nuevo**: no muevas el foco, si no es necesario. Anúncialo con `role="status"`.

## Widgets complejos

Pestañas, menús y listas siguen el patrón de *roving tabindex*: Tab entra una vez en el componente, y las flechas se mueven dentro. Construirlos bien requiere mucho detalle, por lo que recomiendo apoyarse en librerías como React Aria o Radix UI. Si los haces a mano, sigue la guía de patrones de WAI-ARIA, y prueba con usuarios reales de lector de pantalla si es posible.

## Atajos de teclado

Si los añades, evita conflictos con el navegador o el lector, y permite desactivarlos si son de un solo carácter, porque quienes dictan por voz pueden activarlos sin querer.

## Una prueba de cinco minutos

1. Pulsa Tab desde el principio: ¿ves siempre dónde estás?
2. ¿Llegas a todo lo interactivo, en un orden lógico?
3. ¿Puedes activar todo con Enter o Espacio?
4. ¿Sales de los modales y menús con Escape?
5. Tras cerrar algo, ¿el foco queda en un lugar lógico?

## Referencias

- [Guía de patrones ARIA de la WAI](https://www.w3.org/WAI/ARIA/apg/)
- [Enfoque visible en WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)
