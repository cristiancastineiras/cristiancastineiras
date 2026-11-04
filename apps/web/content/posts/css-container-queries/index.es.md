---
title: "Container queries: componentes que se adaptan a su espacio, no a la pantalla"
seoTitle: "Container queries en CSS"
description: "Cómo usar container queries para que un componente se adapte al espacio disponible, con unidades cqi, ejemplos reales y diferencias respecto a las media queries."
date: 2025-07-03
tags: ["CSS", "Responsive"]
---

Las media queries preguntan por el tamaño de la ventana. Pero un componente no suele vivir a pantalla completa: la misma tarjeta puede ir en una columna lateral estrecha y en un área principal ancha, dentro de la misma pantalla. Una media query no sabe nada de esto.

Las container queries sí, y funcionan en todos los navegadores modernos desde 2023.

## El ejemplo básico

Primero, se declara el contenedor:

```css
.tarjeta-contenedor {
  container-type: inline-size;
}
```

Después, el componente responde a su anchura:

```css
.tarjeta {
  display: grid;
  gap: 1rem;
}

@container (min-width: 28rem) {
  .tarjeta {
    grid-template-columns: 10rem 1fr;
  }
}
```

`@container` consulta al contenedor más cercano. Si la tarjeta está en una columna estrecha, se apila; si está en un área ancha, se pone en horizontal. Es el mismo CSS, sin clases modificadoras como `tarjeta--horizontal`.

## Por qué hace falta un contenedor

Sin esta declaración, habría una dependencia circular: el tamaño del contenedor depende de sus hijos, y los estilos de los hijos dependerían del tamaño del contenedor.

`container-type: inline-size` rompe el ciclo, aplicando una contención: el tamaño en línea del contenedor deja de depender de su contenido. Tiene un efecto secundario: un contenedor con ancho automático en un contexto que se ajusta a su contenido, como un `flex` sin más, puede colapsar. Si tu elemento desaparece después de añadirlo, suele ser por esto.

Otra limitación: un elemento no puede consultarse a sí mismo. La regla se aplica a sus descendientes, de modo que necesitas un elemento envoltorio.

## Contenedores con nombre

Con varios niveles anidados, puedes elegir a cuál preguntar:

```css
.lateral {
  container: lateral / inline-size;
}

@container lateral (max-width: 20rem) {
  .enlace-texto {
    display: none;
  }
}
```

## Unidades de contenedor

Las unidades `cqi` son el 1 % del tamaño en línea del contenedor. Se combinan muy bien con `clamp` para tipografía fluida:

```css
.tarjeta h3 {
  font-size: clamp(1rem, 4cqi, 1.5rem);
}
```

El título crece con el espacio de la tarjeta, no con la ventana, y `clamp` evita tamaños extremos. Usar `rem` en los límites respeta la preferencia de tamaño de letra del usuario.

## Container queries con Tailwind

En Tailwind 4 se incluyen de serie:

```html
<div class="@container">
  <article class="grid gap-4 @md:grid-cols-[10rem_1fr]">
    <img src="/foto.jpg" alt="" />
    <div>Contenido</div>
  </article>
</div>
```

## Cuándo usar cada una

No sustituyen a las media queries. Se complementan:

| Decisión | Herramienta |
|---|---|
| Estructura general de la página | Media query |
| Mostrar u ocultar la navegación principal | Media query |
| Cómo se organiza un componente reutilizable | Container query |
| Preferencias del usuario: tema, movimiento | Media query |

Una regla práctica: si un componente se usará en varios sitios con anchuras diferentes, lo más seguro es que deba responder a su contenedor.

## Fallback

Para navegadores sin soporte, el componente muestra los estilos que están fuera de `@container`. Por eso conviene escribir como base la versión apilada, que funciona en cualquier anchura. Las reglas que no se entienden se ignoran sin más.

```css
.tarjeta {
  display: grid; /* base: una columna */
}

@container (min-width: 28rem) {
  .tarjeta {
    grid-template-columns: 10rem 1fr;
  }
}
```

## Consultas de estilo

Existen también consultas sobre valores de propiedades personalizadas, con `@container style(--tema: oscuro)`. Su soporte aún no es completo, por lo que yo no las usaría sin comprobar antes el público de la aplicación.

## Referencias

- [Container queries en MDN](https://developer.mozilla.org/docs/Web/CSS/CSS_containment/Container_queries)
- [Soporte en Can I Use](https://caniuse.com/css-container-queries)
