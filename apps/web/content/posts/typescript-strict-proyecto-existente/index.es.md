---
title: "Activar strict en TypeScript en un proyecto que ya existe"
seoTitle: "Activar strict en TypeScript"
description: "Cómo pasar a strict en un proyecto TypeScript grande, flag por flag, con una estrategia para no bloquear al equipo y sin llenar el código de any y aserciones."
date: 2025-02-20
tags: ["TypeScript", "Refactorización"]
---

Con `strict: false`, TypeScript deja pasar justo los errores que más cuestan en producción: `undefined` que nadie contempla, o parámetros que son `any` sin que nadie lo decidiera. Activarlo de golpe en un proyecto grande puede generar miles de errores. Por suerte, no hace falta hacerlo todo a la vez.

## `strict` es un grupo de opciones

Se pueden activar por separado y en orden:

```json
{
  "compilerOptions": {
    "noImplicitAny": true,
    "strictNullChecks": false,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": false,
    "useUnknownInCatchVariables": true,
    "alwaysStrict": true
  }
}
```

Cuando todas estén en `true`, las sustituyes por `"strict": true`. Así, los proyectos futuros y las nuevas comprobaciones que se añadan al grupo quedan incluidas.

## Un orden razonable

1. **`alwaysStrict`, `strictBindCallApply`, `useUnknownInCatchVariables`**: suelen dar pocos errores, fáciles de arreglar.
2. **`noImplicitAny`**: obliga a anotar parámetros sin tipo, y descubre los huecos.
3. **`strictFunctionTypes`**: encuentra incompatibilidades reales.
4. **`strictNullChecks`**: el más trabajoso y el más valioso.
5. **`strictPropertyInitialization`**: requiere el anterior, y solo importa si usas clases.

## Evitar el bloqueo: comprobar solo lo que está limpio

Con un `tsconfig` separado, puedes aplicar las opciones estrictas a una parte creciente del código:

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "strict": true,
    "noEmit": true
  },
  "include": [
    "src/utilidades/**/*",
    "src/api/**/*"
  ]
}
```

```json
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "typecheck:strict": "tsc -p tsconfig.strict.json"
  }
}
```

Añade ambos a CI. Lo que entra en la lista queda protegido y no vuelve a empeorar. Hay un matiz: los archivos importados se comprueban también, aunque no estén en `include`. Por eso conviene empezar por las hojas del grafo de dependencias.

## Arreglar sin hacer trampas

La forma rápida de quitar errores es añadir `any` o `!`. Eso solo cambia el error de sitio y hace que el compilador deje de avisar.

```ts
// Falsa solución
const nombre = usuario!.nombre;

// Solución real: tratar el caso
if (!usuario) return null;
const nombre = usuario.nombre;
```

Cuando de verdad no puedas arreglarlo en ese momento, usa `@ts-expect-error` con un motivo, no `@ts-ignore`:

```ts
// @ts-expect-error: pendiente de tipar la respuesta de la API antigua
const importe = respuesta.importe;
```

`@ts-expect-error` falla cuando el error desaparece, lo que evita comentarios huérfanos. Es fácil de buscar, y puedes contar cuántos quedan.

## `unknown` en lugar de `any`

Para los datos externos, `unknown` obliga a comprobar antes de usarlos:

```ts
function esCliente(valor: unknown): valor is Cliente {
  return (
    typeof valor === "object" &&
    valor !== null &&
    "id" in valor &&
    typeof (valor as { id: unknown }).id === "number"
  );
}
```

Para respuestas de una API, es mejor generar los tipos o validar con un esquema que escribir esto a mano.

## Más allá de strict

Una vez dentro, hay dos opciones que merecen la pena:

```json
{
  "compilerOptions": {
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

`noUncheckedIndexedAccess` añade `undefined` al acceder a un array o a un diccionario por índice. Refleja lo que puede pasar de verdad, y detecta muchos errores. Es algo incómodo al principio, pero en un proyecto nuevo yo lo activaría desde el primer día.

## Mantener el avance visible

Cuenta los errores restantes y los `@ts-expect-error`, y hazlo visible. Una regla sencilla ayuda: el número solo puede bajar. Con eso, el proyecto mejora cada semana aunque nadie le dedique un trabajo específico.

## Referencias

- [Opción strict en TSConfig](https://www.typescriptlang.org/tsconfig/#strict)
- [noUncheckedIndexedAccess](https://www.typescriptlang.org/tsconfig/#noUncheckedIndexedAccess)
