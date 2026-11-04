---
title: "TypeScript no valida en ejecución: usa Zod en las fronteras de tu aplicación"
seoTitle: "Validar datos externos con Zod"
description: "Por qué un as Tipo no protege frente a datos externos y cómo validar respuestas de API, variables de entorno y almacenamiento local con Zod en TypeScript."
date: 2025-06-23
tags: ["TypeScript", "Zod", "Arquitectura"]
---

Los tipos de TypeScript desaparecen al compilar. Este código compila sin problemas, y no comprueba absolutamente nada:

```ts
const cliente = (await respuesta.json()) as Cliente;
```

Si la API cambia, `cliente.nombre.toUpperCase()` fallará lejos del origen, en un componente que no tiene nada que ver. El `as` es una promesa que le haces al compilador, y nadie la verifica.

## Dónde validar

No hace falta validar en todas partes. Dentro de tu aplicación, los tipos son fiables si lo son los datos que entran. Hay que hacerlo en las fronteras:

- respuestas de APIs, sobre todo si son de terceros;
- variables de entorno;
- `localStorage` y parámetros de URL;
- mensajes de `postMessage` y WebSockets.

## Validar una respuesta

```ts
import { z } from "zod";

const clienteSchema = z.object({
  id: z.number().int(),
  nombre: z.string(),
  email: z.string().email().nullable(),
  creadoEn: z.coerce.date(),
});

type Cliente = z.infer<typeof clienteSchema>;

export async function obtenerCliente(id: number): Promise<Cliente> {
  const respuesta = await fetch(`/api/clientes/${id}`);

  if (!respuesta.ok) {
    throw new Error(`Error HTTP ${respuesta.status}`);
  }

  return clienteSchema.parse(await respuesta.json());
}
```

Si la forma no coincide, el error aparece aquí, con una descripción exacta del campo y el motivo. No tres pantallas más allá con `Cannot read properties of undefined`.

Observa también `z.coerce.date()`, que transforma el texto en un objeto `Date`. Por defecto, Zod elimina además las propiedades no declaradas.

## Fallar o degradar

`parse` lanza una excepción, y `safeParse` devuelve un resultado:

```ts
const resultado = clienteSchema.safeParse(datos);

if (!resultado.success) {
  registrarError("Contrato de cliente inesperado", resultado.error.issues);
  return null;
}

return resultado.data;
```

En una API de terceros que puede cambiar sin avisar, a menudo es mejor registrar la anomalía y seguir, que romper toda la pantalla por un campo opcional.

## Variables de entorno

Es la validación con mejor relación coste-beneficio. Falla al arrancar, en vez de semanas más tarde en una ruta poco usada:

```ts
const envSchema = z.object({
  VITE_API_URL: z.string().url(),
  VITE_ENTORNO: z.enum(["desarrollo", "preproduccion", "produccion"]),
  VITE_PAGINA: z.coerce.number().int().positive().default(25),
});

export const env = envSchema.parse(import.meta.env);
```

## `localStorage`

Lo que se guardó con una versión anterior puede no tener ya la forma que espera la actual:

```ts
const preferenciasSchema = z.object({
  tema: z.enum(["claro", "oscuro"]),
});

function leerPreferencias() {
  try {
    const crudo = JSON.parse(localStorage.getItem("preferencias") ?? "null");
    return preferenciasSchema.parse(crudo);
  } catch {
    return { tema: "claro" as const };
  }
}
```

## ¿Y si ya genero los tipos con OpenAPI?

Un cliente generado te da tipos correctos respecto a la especificación en el momento de generar, lo que elimina la duplicación. Pero sigue sin haber comprobación en ejecución. Para tus propias APIs, desplegadas junto al frontend, eso puede ser suficiente.

Yo añadiría validación si el servicio lo mantiene otro equipo o un tercero, o si un fallo es especialmente caro. Algunos generadores, como Hey API, pueden producir esquemas Zod desde la especificación, evitando escribirlos a mano.

## El coste

Validar no es gratuito: añade código al bundle y tiempo de CPU, lo que se nota si recorres listas de miles de elementos. Si es tu caso, valida solo un muestreo en producción, o considera librerías más pequeñas, como Valibot.

Eso sí, valida y confía después. No vuelvas a comprobar el mismo dato en cada capa. Una vez pasada la frontera, el tipo ya es verdad.

## Referencias

- [Documentación de Zod](https://zod.dev/)
- [Parse, don't validate, de Alexis King](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/)
