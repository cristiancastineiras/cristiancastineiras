---
title: "TypeScript 7: el compilador nativo y qué comprobar antes de actualizar"
seoTitle: "TypeScript 7: compilador nativo"
description: "Qué cambia con TypeScript 7 y su compilador en Go, qué se elimina respecto a versiones anteriores y cómo preparar un proyecto con herramientas que aún dependen de la API."
date: 2026-08-10
tags: ["TypeScript", "Herramientas", "Rendimiento"]
---

TypeScript 7 ya es estable desde julio de 2026, y no añade tanto lenguaje como cambia el motor: el compilador se ha reescrito en Go. Para un proyecto grande, esto puede convertir una comprobación de tipos de varios minutos en algo que ya no te hace cambiar de tarea.

## Qué mejora

Sigues usando el paquete `typescript` y el comando `tsc`. Las notas de la versión hablan de compilaciones completas varias veces más rápidas que con TypeScript 6, gracias a la ejecución nativa y al paralelismo. También hay opciones nuevas para controlar este último:

```bash
tsc --noEmit --checkers 4
tsc --build --builders 2
```

Se nota sobre todo en dos lugares:

- **CI**: el `typecheck` deja de ser el paso que más tarda.
- **Editor**: el servidor de lenguaje responde antes en proyectos grandes.

Mide con tu proyecto: la ganancia varía según el tamaño y la complejidad de los tipos.

```bash
time pnpm tsc --noEmit
```

## El camino: pasar antes por TypeScript 6

TypeScript 6 fue la última versión basada en JavaScript, y existe en parte para preparar el salto: marca como obsoleto lo que la versión 7 elimina. Si tu proyecto compila en la 6 sin avisos de obsolescencia, ya tienes hecho casi todo.

Lo que más puede afectarte:

- **`strict` por defecto**: si no lo declaras en tu `tsconfig`, puede que aparezcan errores nuevos.
- **Se retira el destino ES5.**
- **Desaparecen los módulos AMD, UMD y SystemJS.**
- **Se retira la resolución de módulos clásica de Node**, y hay que elegir una moderna.

Una configuración típica de una aplicación con Vite ya estaba cerca de esto:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true
  }
}
```

Si llevas tiempo dejando estos ajustes de lado, [activar strict de forma gradual]({{< relref "/posts/typescript-strict-proyecto-existente" >}}) sigue siendo la parte más larga del trabajo. Y conviene hacerlo antes de cambiar de compilador, no al mismo tiempo.

## La limitación importante: la API

TypeScript 7.0 no ofrece una API programática estable. Esto no afecta a `tsc`, sino a las herramientas que usan el compilador como librería:

- plantillas y extensiones de editor de frameworks como Vue, Svelte o Angular;
- generadores de código o de documentación basados en la API;
- reglas de lint que requieren información de tipos;
- transformadores personalizados.

Si usas alguna, comprueba su estado antes de actualizar. Mientras tanto, existe una alternativa: mantener instalada la versión basada en JavaScript junto a la nativa, usando un paquete de compatibilidad. Así, cada herramienta usa la que necesita.

La versión 7.1, en fase beta en el momento de escribir esto, debería resolver parte de este problema con nuevos puntos de entrada de la API.

Un proyecto con React, Vite y Biome no suele depender de esa API, y por eso es buen candidato para adoptarla pronto.

## Cómo migrar

1. Actualiza primero a TypeScript 6 y elimina los avisos de obsolescencia.
2. Comprueba que el proyecto compila sin errores.
3. Prueba TypeScript 7 en una rama y compara errores. Puede señalar diferencias, sobre todo en casos límite.
4. Actualiza la extensión o la configuración del editor.
5. Comprueba tu linter, tus generadores y tus plugins.
6. Actualízalo primero en un paquete del monorepo y extiéndelo después.

Fija la versión con un catálogo de pnpm, para que todos los paquetes usen la misma. Dos compiladores distintos en el mismo repositorio dan resultados distintos, y eso es difícil de entender.

## Lo que no cambia

Los tipos no se comprueban en ejecución, y `tsc` más rápido no valida datos externos. Lo que sí cambia es lo razonable: si el `typecheck` tarda segundos, puedes ejecutarlo en cada guardado o en un gancho de Git, algo que antes resultaba demasiado lento. Esa es, en mi opinión, la mejora real: más comprobaciones, antes.

## Referencias

- [Blog de TypeScript](https://devblogs.microsoft.com/typescript/)
- [Repositorio del compilador nativo](https://github.com/microsoft/typescript-go)
