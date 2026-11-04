---
title: "Ejecutar TypeScript directamente en Node.js: qué funciona y qué no"
seoTitle: "TypeScript nativo en Node.js"
description: "Node.js ya puede ejecutar archivos TypeScript sin compilarlos. Qué significa quitar tipos, qué sintaxis no se admite y cómo aprovecharlo en scripts y herramientas."
date: 2026-02-23
tags: ["Node.js", "TypeScript"]
---

Para muchos proyectos, ejecutar un script TypeScript ha significado instalar `ts-node` o `tsx`, y mantener su configuración. Desde Node.js 22.18 y 23.6, ya no hace falta en muchos casos:

```bash
node scripts/generar-informe.ts
```

Sin dependencias adicionales ni opciones experimentales.

## Cómo funciona

Node no comprueba los tipos ni transforma el código: simplemente los quita. Sustituye las anotaciones por espacios en blanco, lo que también preserva los números de línea de las trazas de error, sin necesidad de *source maps*.

```ts
// Antes de ejecutar
function saludar(nombre: string): string {
  return `Hola, ${nombre}`;
}

// Lo que ejecuta Node (mismo número de líneas y columnas)
function saludar(nombre        )         {
  return `Hola, ${nombre}`;
}
```

Esto tiene una consecuencia importante: **un error de tipos no impide la ejecución**. Sigue haciendo falta `tsc --noEmit` en CI.

## Qué no funciona

Solo se admite la sintaxis que se puede eliminar. Lo que genera código en tiempo de ejecución falla:

- `enum`
- `namespace` con código en su interior
- propiedades de parámetro en constructores
- decoradores, que aún no se ejecutan de forma nativa

```ts
// No funciona con la eliminación de tipos
enum Estado { Activo, Inactivo }

class Cliente {
  constructor(private nombre: string) {}
}

// Alternativa válida
const Estado = { Activo: "activo", Inactivo: "inactivo" } as const;
type Estado = (typeof Estado)[keyof typeof Estado];

class Cliente {
  #nombre: string;

  constructor(nombre: string) {
    this.#nombre = nombre;
  }
}
```

La opción de TypeScript `erasableSyntaxOnly`, disponible desde la versión 5.8, hace que el compilador te avise de estos casos desde el editor.

## Importaciones

Hay dos reglas que suelen dar problemas al principio.

La extensión es obligatoria y debe ser real, porque Node no va a adivinarla:

```ts
import { cargar } from "./configuracion.ts";
```

Los tipos se importan de forma explícita. Como Node no analiza nada, necesita saber qué puede eliminar:

```ts
import type { Configuracion } from "./tipos.ts";
```

## Un tsconfig adecuado

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "module": "NodeNext",
    "noEmit": true,
    "strict": true,
    "allowImportingTsExtensions": true,
    "rewriteRelativeImportExtensions": true,
    "erasableSyntaxOnly": true,
    "verbatimModuleSyntax": true
  }
}
```

- `verbatimModuleSyntax` obliga a marcar con `type` las importaciones de tipos.
- `allowImportingTsExtensions` permite escribir `.ts` en las rutas.
- `rewriteRelativeImportExtensions` convierte esas rutas en `.js` si más adelante compilas para publicar.

## Dónde encaja

Es perfecto para:

- scripts del repositorio: generadores, migraciones, tareas de CI;
- herramientas internas de línea de comandos;
- pruebas con el ejecutor nativo: `node --test`;
- configuraciones que se puedan escribir en TypeScript.

Es menos adecuado para:

- **paquetes publicados**: Node se niega a quitar tipos dentro de `node_modules`, a propósito. Debes publicar JavaScript;
- **aplicaciones con mucha transformación**, como JSX o alias de rutas de `tsconfig`, que no se resuelven;
- **código con decoradores**, habitual en algunos frameworks de backend.

## Si necesitas más

`tsx` sigue siendo válido cuando necesitas ejecutar `enum`, alias u otras transformaciones sin cambiar el código. Y en una aplicación con Vite, esto no aporta nada, porque el empaquetador ya se ocupa de ello.

## Comprobar en CI

Como la ejecución no valida nada, separa ambas cosas:

```json
{
  "scripts": {
    "generar": "node scripts/generar.ts",
    "typecheck": "tsc --noEmit"
  },
  "engines": {
    "node": ">=22.18.0"
  }
}
```

Declarar `engines` evita que alguien con otra versión reciba un error confuso. Fija también la versión de Node en CI.

## Referencias

- [Soporte de TypeScript en Node.js](https://nodejs.org/api/typescript.html)
- [erasableSyntaxOnly](https://www.typescriptlang.org/tsconfig/#erasableSyntaxOnly)
