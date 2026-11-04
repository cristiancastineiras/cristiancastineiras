---
title: "dialog y popover nativos: modales accesibles sin una librería"
seoTitle: "dialog y popover nativos en HTML"
description: "Cómo usar dialog y el atributo popover para modales, menús y avisos con accesibilidad, foco y capa superior incluidos, y cuándo sigue siendo necesaria una librería."
date: 2025-05-01
tags: ["HTML", "Accesibilidad", "React"]
---

Hacer bien un modal siempre ha sido más difícil de lo que parece: atrapar el foco, cerrarlo con Escape, devolver el foco al cerrar, bloquear el fondo y evitar los problemas de `z-index`. Por eso casi todos los proyectos incorporan una librería. Hoy, el navegador resuelve gran parte de ello.

## `<dialog>` como modal

```html
<button id="abrir">Eliminar cuenta</button>

<dialog id="confirmar" aria-labelledby="titulo">
  <h2 id="titulo">¿Eliminar la cuenta?</h2>
  <p>Esta acción no se puede deshacer.</p>
  <form method="dialog">
    <button value="cancelar">Cancelar</button>
    <button value="eliminar">Eliminar</button>
  </form>
</dialog>
```

```js
const dialogo = document.querySelector("#confirmar");

document.querySelector("#abrir").addEventListener("click", () => {
  dialogo.showModal();
});

dialogo.addEventListener("close", () => {
  if (dialogo.returnValue === "eliminar") eliminarCuenta();
});
```

`showModal()` aporta, sin más código:

- capa superior: se muestra por encima de todo, sin `z-index`;
- el contenido del fondo queda inerte: no se puede enfocar ni interactuar con él;
- `Escape` lo cierra;
- el foco entra al abrir y regresa al elemento anterior al cerrar;
- rol y semántica de diálogo modal para las tecnologías de asistencia.

Con `<form method="dialog">`, un botón lo cierra y deja su `value` en `returnValue`, sin JavaScript adicional.

## Estilos y fondo

```css
dialog {
  border: 0;
  border-radius: 0.5rem;
  max-inline-size: min(90vw, 32rem);
}

dialog::backdrop {
  background: rgb(0 0 0 / 0.5);
}
```

El pseudoelemento `::backdrop` es el fondo del modal. Cerrar al hacer clic fuera no viene incluido, aunque es fácil añadirlo, ya que al pulsar sobre el fondo el destino del evento es el propio `dialog`:

```js
dialogo.addEventListener("click", (e) => {
  if (e.target === dialogo) dialogo.close();
});
```

Para que funcione, el contenido debe ir en un elemento interno sin que el `dialog` tenga relleno propio. Si no, un clic sobre ese relleno también lo cerraría.

## El atributo `popover`

Para menús, avisos y elementos que no son modales, `popover` funciona incluso sin JavaScript:

```html
<button popovertarget="menu">Opciones</button>

<div id="menu" popover>
  <a href="/perfil">Perfil</a>
  <a href="/salir">Salir</a>
</div>
```

Por defecto (`popover="auto"`) se muestra en la capa superior, se cierra con `Escape` o al pulsar fuera, y solo uno está abierto a la vez. Con `popover="manual"`, los cierras tú, lo que es ideal para notificaciones.

Eso sí, `popover` no aporta semántica por sí mismo: el rol y las etiquetas dependen del contenido. Tampoco convierte un `div` en un menú accesible con navegación con flechas.

## Usarlos en React

```tsx
function Confirmacion({ abierto, onCerrar, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialogo = ref.current;
    if (!dialogo) return;

    if (abierto && !dialogo.open) dialogo.showModal();
    if (!abierto && dialogo.open) dialogo.close();
  }, [abierto]);

  return (
    <dialog ref={ref} onClose={onCerrar}>
      {children}
    </dialog>
  );
}
```

No pongas el atributo `open` directamente para mostrarlo como modal: así se muestra, pero sin fondo, sin capa superior ni foco atrapado. Hay que usar `showModal()`.

## Qué falta todavía

- **Bloquear el scroll del fondo**: se puede con CSS, usando `body:has(dialog[open]) { overflow: hidden; }`.
- **Posicionar respecto a un elemento**: el posicionamiento con anclas en CSS aún no está disponible en todos los navegadores, por lo que hay que recurrir a una alternativa en algunos casos.
- **Animaciones de entrada y salida**: requieren `@starting-style` y `transition-behavior`, con soporte reciente.
- **Componentes complejos**: combobox, menús con flechas o listas con búsqueda requieren mucho más que un popover.

## Cuándo seguir con una librería

Si necesitas un sistema de diseño con combobox, menús anidados y selector de fechas, las librerías *headless*, como Radix UI o React Aria, siguen valiendo la pena. Para un modal de confirmación o un menú sencillo, es probable que el HTML sea suficiente, y con cero kilobytes adicionales.

## Referencias

- [Elemento dialog en MDN](https://developer.mozilla.org/docs/Web/HTML/Element/dialog)
- [API Popover en MDN](https://developer.mozilla.org/docs/Web/API/Popover_API)
