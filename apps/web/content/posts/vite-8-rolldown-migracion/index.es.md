---
title: "Migrar a Vite 8: Rolldown, Oxc y qué revisar en tu proyecto"
seoTitle: "Migrar a Vite 8 con Rolldown"
description: "Qué cambia con Vite 8 al sustituir esbuild y Rollup por Rolldown y Oxc, qué plugins y opciones hay que revisar, y cómo migrar una aplicación React de forma segura."
date: 2026-04-13
tags: ["Vite", "React", "Rendimiento"]
---

Vite 8, publicado en marzo de 2026, cambia lo que hay por debajo: Rolldown, un empaquetador escrito en Rust, sustituye a la pareja formada por esbuild y Rollup. Se termina así una situación algo incómoda: dos herramientas distintas para desarrollo y producción, con sutiles diferencias de comportamiento entre ambas.

## Qué cambia

| Tarea | Antes | Vite 8 |
|---|---|---|
| Transformar TS y JSX | esbuild | Oxc |
| Preempaquetar dependencias | esbuild | Rolldown |
| Empaquetar para producción | Rollup | Rolldown |
| Minificar | esbuild | Oxc |

Rolldown mantiene la API de plugins de Rollup, por lo que muchos plugins siguen funcionando sin cambios. El proyecto presume de compilaciones mucho más rápidas. Mi consejo es medir en tu aplicación, porque la ganancia real depende del número de módulos, de los plugins y de cuánto pese el resto del pipeline.

## Antes de actualizar

Revisa los requisitos de la versión de Node y la guía de migración. Si vienes de una versión anterior a la 7, conviene ir paso a paso.

```bash
pnpm add -D vite@latest @vitejs/plugin-react@latest
```

También hay que actualizar todos los plugins. En React, `@vitejs/plugin-react` v6 utiliza Oxc en lugar de Babel para la transformación y el Fast Refresh. Es un cambio importante si tienes plugins de Babel.

## El detalle de Babel y React Compiler

Si usas `babel-plugin-react-compiler` u otros plugins de Babel, consulta la guía actualizada de `@vitejs/plugin-react` antes de copiar la configuración antigua:

```ts
// Puede dejar de ser válido en v6
react({ babel: { plugins: ["babel-plugin-react-compiler"] } });
```

La integración de Babel pasa a ser una elección explícita. Mientras la mantengas, parte de la mejora de velocidad se pierde en esos archivos, ya que Babel seguirá procesándolos.

## Opciones de configuración

Las opciones `rollupOptions` y `esbuild` tienen ahora sus equivalentes en Rolldown y Oxc. Hay una capa de compatibilidad que traduce las antiguas, y por eso muchos proyectos siguen funcionando sin cambios, pero conviene pasar a los nombres nuevos para no depender de ella:

```ts
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    // Antes: rollupOptions
    rolldownOptions: {
      external: ["jquery"],
    },
  },
});
```

Presta especial atención a `manualChunks`. Rolldown ofrece otra forma de dividir el código, y si tenías una estrategia manual muy elaborada, es el punto donde más cambios puede haber. Compara el resultado, no solo que compile.

## Cómo validar la migración

Compilar sin errores no garantiza que todo esté bien. Yo comprobaría esto:

1. **Tamaño y división del bundle**: compara el número y el peso de los chunks con la versión anterior. Un visualizador ayuda a detectar cambios inesperados.
2. **Módulos CommonJS**: las diferencias de interoperabilidad pueden afectar a importaciones de librerías antiguas.
3. **Pruebas**: Vitest debe ser compatible con tu versión de Vite. Actualízalo a la vez.
4. **CSS**: comprueba el minificado y las `url()`, y verifica también los navegadores objetivo.
5. **`build.target`**: el valor predeterminado puede cambiar, lo que afecta a los navegadores que soportas. Si tienes requisitos concretos, decláralos.
6. **Flujos end-to-end**: ejecuta Playwright contra el resultado de la compilación con `vite preview`, no contra el servidor de desarrollo.

## Estrategia

Para una aplicación importante:

1. crea una rama aparte, y haz la actualización sin ningún otro cambio;
2. compara el tiempo de compilación antes y después para justificar el esfuerzo con datos;
3. despliégala en un entorno de preproducción y revisa los errores de consola;
4. despliega en producción, vigilando errores y métricas web.

Si un plugin esencial todavía no es compatible, no hay ninguna prisa: Vite 7 sigue siendo una opción sólida mientras el ecosistema se pone al día.

## En un monorepo

Alinea la versión de Vite con un catálogo de pnpm, para evitar que cada paquete use una distinta. Sin esto, puedes acabar con dos copias, y sus tipos serán incompatibles.

## Qué viene después

Rolldown abre la puerta a un modo de desarrollo con empaquetado completo, a chunks más flexibles y a cachés persistentes. Son mejoras de las que te beneficias si ya estás en esta base, y es una buena razón para no quedarte atrás mucho tiempo.

## Referencias

- [Anuncio de la beta de Vite 8](https://vite.dev/blog/announcing-vite8-beta)
- [Guía de migración de Vite](https://vite.dev/guide/migration)
- [Rolldown](https://rolldown.rs/)
