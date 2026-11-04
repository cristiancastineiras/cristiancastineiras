---
title: "Tailwind CSS 4: qué cambia y cómo migrar a la configuración en CSS"
seoTitle: "Migrar a Tailwind CSS 4"
description: "Lo importante de Tailwind CSS 4: configuración con @theme, motor más rápido, plugin para Vite, requisitos de navegador y qué vigilar al ejecutar el actualizador."
date: 2025-03-20
tags: ["Tailwind CSS", "CSS", "Vite"]
---

Tailwind CSS 4, publicado en enero de 2025, es una reescritura importante. La novedad más visible es que la configuración pasa de JavaScript a CSS. Las clases siguen siendo casi iguales, de modo que la mayor parte del trabajo está en la configuración.

## Instalación con Vite

Ya no hay que configurar PostCSS ni Autoprefixer:

```bash
pnpm add -D tailwindcss @tailwindcss/vite
```

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

```css
/* src/index.css */
@import "tailwindcss";
```

Esa única línea sustituye a las tres directivas `@tailwind` anteriores. Los archivos que contienen clases se detectan automáticamente, y no hace falta la lista `content`.

## Tu tema en CSS

Lo que antes iba en `tailwind.config.js` se declara con `@theme`:

```css
@import "tailwindcss";

@theme {
  --font-sans: "Inter", system-ui, sans-serif;
  --color-marca-500: oklch(0.62 0.19 255);
  --color-marca-700: oklch(0.45 0.16 255);
  --spacing-18: 4.5rem;
  --breakpoint-3xl: 112rem;
}
```

Cada variable genera sus utilidades: `bg-marca-500`, `text-marca-700`, `p-18`, `3xl:flex`. También quedan disponibles como variables CSS normales, lo cual facilita usarlas en estilos propios:

```css
.grafica-linea {
  stroke: var(--color-marca-500);
}
```

Si tienes una configuración compleja en JavaScript, puedes cargarla explícitamente mientras migras:

```css
@config "../tailwind.config.js";
```

## El actualizador

La herramienta oficial se encarga de casi todo el trabajo mecánico:

```bash
npx @tailwindcss/upgrade
```

Actualiza dependencias, migra la configuración y renombra clases en tus plantillas. Ejecútala en una rama limpia y revisa el diff con calma. Necesita Node 20 o superior.

## Cambios que afectan a lo visual

Son los que un compilador no te va a señalar, y por eso hay que buscarlos:

- **Clases renombradas**: `shadow-sm` pasa a `shadow-xs`, `shadow` a `shadow-sm`, `rounded` a `rounded-sm`, `blur` a `blur-sm` y `outline-none` a `outline-hidden`.
- **Color de borde**: el valor por defecto pasa a ser `currentColor`, en lugar de gris. Un `border` sin color puede cambiar de aspecto.
- **`ring` por defecto**: pasa de 3 a 1 píxel y usa `currentColor`.
- **Botones**: `cursor` vuelve a ser el predeterminado del navegador, en lugar de `pointer`.
- **Importante**: el modificador `!` pasa al final, como `flex!`, aunque la sintaxis antigua se mantiene por ahora.

Es recomendable una comparación visual de las pantallas principales, ya sea a mano o con capturas automatizadas.

## Requisitos de navegador

Es lo primero que hay que comprobar. La versión 4 requiere Safari 16.4, Chrome 111 y Firefox 128 o superiores, porque usa funciones como `@layer`, `color-mix()` y propiedades registradas con `@property`.

Si necesitas compatibilidad con navegadores más antiguos, por ejemplo por un cliente corporativo, quédate en la versión 3.4. Se sigue manteniendo, y es una decisión perfectamente válida.

## Funciones nuevas que merece la pena conocer

- **Container queries incluidas**: `@container` y `@md:flex`, sin plugin.
- **Valores dinámicos**: `grid-cols-15` o `mt-17` funcionan sin configurarlos.
- **Paleta en oklch**: colores más vivos en pantallas modernas.
- **Variantes como `not-*` e `in-*`**: menos necesidad de CSS a medida.
- **Directiva `@utility`**: reemplaza a `@layer utilities` para las utilidades propias.

```css
@utility contenido-truncado {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

## Monorepos

Si tus componentes viven en otro paquete, la detección automática puede no incluirlos. Es porque por defecto no recorre lo que hay en `node_modules` ni lo ignorado por Git. Puedes indicarle el origen de forma explícita:

```css
@import "tailwindcss";
@source "../../packages/ui/src";
```

Mantén el tema en un paquete compartido que importen todas las aplicaciones.

## Referencias

- [Guía de actualización de Tailwind](https://tailwindcss.com/docs/upgrade-guide)
- [Tema con @theme](https://tailwindcss.com/docs/theme)
