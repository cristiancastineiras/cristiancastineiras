---
title: "CSS moderno que ya puedes usar: :has(), anidamiento y @layer"
seoTitle: "CSS moderno: :has(), nesting y @layer"
description: "Tres funciones de CSS que reducen JavaScript y guerras de especificidad: el selector :has(), el anidamiento nativo y las capas de cascada con @layer."
date: 2025-10-06
tags: ["CSS", "Tailwind CSS"]
---

Muchas cosas para las que hacía falta un preprocesador o unas líneas de JavaScript ya se pueden resolver con CSS estándar. Estas tres son las que más cambian el día a día, y todas tienen buen soporte en navegadores modernos.

## `:has()`: el selector de padre

Durante décadas, CSS solo podía mirar hacia abajo. `:has()` permite estilizar un elemento según lo que contiene:

```css
/* Tarjeta con imagen: dos columnas */
.tarjeta:has(img) {
  grid-template-columns: 8rem 1fr;
}

/* Marcar el campo cuyo input no es válido */
.campo:has(input:user-invalid) {
  --color-borde: var(--color-error);
}

/* Bloquear el scroll si hay un modal abierto */
body:has(dialog[open]) {
  overflow: hidden;
}
```

Nos ahorra mucho código. Ya no hace falta un `useEffect` que añada una clase al `body`, ni una prop que indique que la tarjeta tiene imagen.

También sirve para reglas según cantidad, combinado con otros selectores:

```css
/* Si hay al menos cuatro elementos, usar dos columnas */
.lista:has(> :nth-child(4)) {
  columns: 2;
}
```

Y `input:user-invalid` es mejor que `:invalid`, ya que solo se aplica después de que el usuario interactúe, por lo que el formulario no aparece lleno de errores nada más abrirse.

## Anidamiento nativo

```css
.tarjeta {
  padding: 1rem;

  & h3 {
    margin-block-start: 0;
  }

  &:hover {
    background: var(--fondo-resaltado);
  }

  @media (width >= 48rem) {
    padding: 2rem;
  }
}
```

Para los casos habituales, ya no necesitas Sass. Hay una diferencia con los preprocesadores: no se puede construir un selector concatenando nombres. `&__titulo` no funciona, porque CSS no opera con cadenas de texto.

Además, la especificidad se calcula como si se tratara de `:is()`. Si anidas dentro de una lista como `#id, .clase`, todos los hijos heredan la especificidad más alta de la lista.

Un consejo: no anides más de dos o tres niveles. Un selector demasiado específico es difícil de sobrescribir, y es el mismo problema que ya había en Sass.

## `@layer`: orden sin guerras de especificidad

Este es el más potente y el menos conocido. Las capas permiten definir el orden de prioridad, independientemente de la especificidad:

```css
@layer reset, base, componentes, utilidades;

@layer reset {
  * {
    margin: 0;
    box-sizing: border-box;
  }
}

@layer componentes {
  .boton#principal {
    background: navy;
  }
}

@layer utilidades {
  .oculto {
    display: none;
  }
}
```

Una clase simple en `utilidades` gana a `.boton#principal` en `componentes`, porque la capa tiene más prioridad. Dentro de cada capa, las reglas de especificidad siguen funcionando como siempre.

Dos reglas importantes:

1. Los estilos fuera de cualquier capa ganan a todos los que están dentro de una capa.
2. Con `!important`, el orden de las capas se invierte.

## Domesticar CSS de terceros

Esto resuelve un problema clásico. Importa la librería en una capa de baja prioridad, y tus estilos siempre ganarán, sin aumentar la especificidad:

```css
@layer terceros, propios;

@import url("libreria.css") layer(terceros);

@layer propios {
  .boton {
    border-radius: 0.25rem;
  }
}
```

Ten en cuenta que `@import` debe ir antes que las demás reglas, salvo por la declaración `@layer` previa.

## Relación con Tailwind

Tailwind 4 organiza sus estilos en capas nativas, y por eso una clase de utilidad gana a los estilos de componentes. Si mezclas CSS propio, colócalo dentro de una capa: si está fuera, ganará a las utilidades de Tailwind y parecerá que no funcionan.

## Comprobar soporte

Para funciones con soporte más reciente, usa `@supports`:

```css
@supports selector(:has(a)) {
  .tarjeta:has(img) {
    grid-template-columns: 8rem 1fr;
  }
}
```

El proyecto Baseline, de MDN, indica de forma clara qué ya es seguro usar en todos los navegadores principales, y desde cuándo.

## Referencias

- [:has() en MDN](https://developer.mozilla.org/docs/Web/CSS/:has)
- [Anidamiento en CSS](https://developer.mozilla.org/docs/Web/CSS/CSS_nesting)
- [@layer en MDN](https://developer.mozilla.org/docs/Web/CSS/@layer)
