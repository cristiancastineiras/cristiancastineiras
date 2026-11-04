---
title: "Uniones discriminadas en TypeScript: haz imposibles los estados inválidos"
seoTitle: "Uniones discriminadas en TypeScript"
description: "Cómo modelar estados con uniones discriminadas en TypeScript para eliminar combinaciones imposibles, y comprobar en compilación que has cubierto todos los casos."
date: 2025-03-03
tags: ["TypeScript", "React", "Arquitectura"]
---

Muchos errores de frontend se deben a estados que no deberían existir: `cargando` a `true` junto a `error` con un valor, o `datos` vacíos sin que nada indique el motivo. El tipo los permite, así que tarde o temprano ocurren.

## El problema de las banderas

```ts
type Estado = {
  cargando: boolean;
  error?: string;
  datos?: Cliente;
};
```

Con tres propiedades hay varias combinaciones posibles, y solo unas pocas tienen sentido. Cada componente que lo usa tiene que adivinar cuáles pueden darse:

```tsx
if (estado.cargando) return <Cargando />;
if (estado.error) return <Error mensaje={estado.error} />;
return <Ficha cliente={estado.datos!} />; // ¿y si no hay datos?
```

## Una propiedad que discrimina

```ts
type Estado =
  | { tipo: "inactivo" }
  | { tipo: "cargando" }
  | { tipo: "error"; mensaje: string }
  | { tipo: "listo"; datos: Cliente };
```

Solo existen las combinaciones declaradas, y TypeScript estrecha el tipo al comprobar `tipo`:

```tsx
switch (estado.tipo) {
  case "inactivo":
    return null;
  case "cargando":
    return <Cargando />;
  case "error":
    return <Error mensaje={estado.mensaje} />;
  case "listo":
    return <Ficha cliente={estado.datos} />;
}
```

No hace falta `!`, porque `datos` solo existe dentro de la rama `listo`.

## Exhaustividad en compilación

Si mañana añades un caso, quieres que el compilador te indique cada lugar afectado. `never` sirve para eso:

```ts
function noEsperado(valor: never): never {
  throw new Error(`Caso no contemplado: ${JSON.stringify(valor)}`);
}

function etiqueta(estado: Estado): string {
  switch (estado.tipo) {
    case "inactivo":
      return "Sin empezar";
    case "cargando":
      return "Cargando";
    case "error":
      return estado.mensaje;
    case "listo":
      return estado.datos.nombre;
    default:
      return noEsperado(estado);
  }
}
```

Al añadir `{ tipo: "cancelado" }`, `estado` ya no es `never` en el `default`, y la compilación falla justo en ese punto. Además, se protege en tiempo de ejecución si llega un valor inesperado.

## Reductores

Encaja muy bien con `useReducer`, tanto para las acciones como para el estado:

```ts
type Accion =
  | { tipo: "iniciar" }
  | { tipo: "exito"; datos: Cliente }
  | { tipo: "fallo"; mensaje: string };

function reducer(_estado: Estado, accion: Accion): Estado {
  switch (accion.tipo) {
    case "iniciar":
      return { tipo: "cargando" };
    case "exito":
      return { tipo: "listo", datos: accion.datos };
    case "fallo":
      return { tipo: "error", mensaje: accion.mensaje };
  }
}
```

Con `tipo: "exito"`, TypeScript exige `datos`. No puedes olvidarlo.

## Props que dependen unas de otras

También funciona con componentes cuando una prop solo tiene sentido según otra:

```tsx
type Props =
  | { variante: "enlace"; href: string }
  | { variante: "boton"; onClick: () => void };

function Accion(props: Props) {
  return props.variante === "enlace"
    ? <a href={props.href}>Abrir</a>
    : <button onClick={props.onClick}>Abrir</button>;
}
```

`<Accion variante="enlace" />` no compila sin `href`, y `<Accion variante="boton" href="/" />` tampoco.

Si desestructuras las props en la firma de la función, TypeScript todavía puede estrechar cuando extraes todas juntas y son `const`. Si lo mezclas con otras variables, puede perder la relación, y ahí es más sencillo seguir usando `props.variante`.

## Resultados sin excepciones

El mismo patrón sirve para errores de negocio esperados:

```ts
type Resultado<T, E> =
  | { ok: true; valor: T }
  | { ok: false; error: E };

function dividir(a: number, b: number): Resultado<number, "division-por-cero"> {
  return b === 0
    ? { ok: false, error: "division-por-cero" }
    : { ok: true, valor: a / b };
}
```

El tipo de retorno declara el fallo, de forma que quien llama tiene que contemplarlo para acceder al valor.

## Cuándo no merece la pena

Con dos o tres estados que no llevan datos propios, un simple `"a" | "b" | "c"` es suficiente. Y si el dato viene de fuera, recuerda que los tipos solo existen en compilación: tendrás que validar el contenido antes de confiar en que tiene esta forma.

## Referencias

- [Uniones discriminadas](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#discriminated-unions)
- [El tipo never](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#the-never-type)
