---
title: "Cómo generar clientes TypeScript desde OpenAPI con Hey API"
seoTitle: "Generar clientes TypeScript con Hey API"
description: "Cómo eliminar DTOs duplicados y generar clientes TypeScript tipados para varias APIs ASP.NET Core usando OpenAPI, Hey API y pnpm."
date: 2026-11-04
tags: ["TypeScript", "OpenAPI", "ASP.NET Core", "Hey API"]
---

Cuando una aplicación frontend consume una API ASP.NET Core, es habitual terminar manteniendo dos representaciones del mismo contrato: los DTOs originales en C# y una copia manual en TypeScript.

Al principio parece una solución rápida. El problema aparece cuando cambia una propiedad, se añade un valor a un enum o un endpoint empieza a devolver otro tipo. El backend compila, pero el frontend conserva un contrato desactualizado y el error no aparece hasta ejecutar la aplicación.

OpenAPI permite eliminar esa duplicación. Si la API publica una especificación correcta, podemos generar automáticamente los tipos y el cliente HTTP que necesita el frontend.

## El problema: contratos duplicados

Imaginemos una solución con esta estructura:

```text
HTN.SistemaRepresentaciones.Contracts
HTN.SistemaRepresentaciones.WebApi
HTN.SistemaRepresentaciones.WebApiOper
HTN.SistemaRepresentaciones.Webs
```

El proyecto `Contracts` contiene los DTOs compartidos por las APIs:

```csharp
public sealed record RepresentacionDto(
    int Id,
    string Nombre,
    DateTime Fecha);
```

Si el frontend vuelve a declarar ese contrato manualmente, aparece una segunda fuente de verdad:

```ts
export interface RepresentacionDto {
  id: number;
  nombre: string;
  fecha: string;
}
```

TypeScript solo puede comprobar que el frontend utiliza correctamente su propia definición. No puede saber si esa interfaz sigue coincidiendo con el contrato publicado por la API.

La solución no consiste en sincronizar mejor ambos archivos. Consiste en dejar de escribir la copia.

## Qué aporta Hey API

`@hey-api/openapi-ts` genera código TypeScript a partir de una especificación OpenAPI. Según la configuración elegida, puede producir:

- tipos para los esquemas de entrada y salida;
- funciones para consumir los endpoints;
- clientes basados en `fetch` u otras implementaciones;
- validadores y transformaciones mediante plugins;
- una salida reproducible que puede regenerarse cuando cambie la API.

El contrato OpenAPI pasa a ser el punto de unión entre backend y frontend:

```text
DTOs de C#
    ↓
ASP.NET Core genera OpenAPI
    ↓
Hey API genera TypeScript
    ↓
El frontend importa tipos y funciones
```

Esto no convierte OpenAPI en la fuente original del dominio. Los DTOs de C# siguen definiendo el contrato en el backend, pero la especificación publicada se convierte en la fuente que consume el frontend.

## Instalar el generador

En el paquete del frontend:

```powershell
pnpm add -D @hey-api/openapi-ts
```

Conviene instalarlo como dependencia de desarrollo. La generación ocurre durante el desarrollo o en integración continua; el generador no necesita formar parte del código enviado al navegador.

## Una configuración mínima

En lugar de mantener un comando largo en `package.json`, podemos guardar la configuración en un archivo dedicado:

```ts
// openapi-ts.config.ts
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "https://localhost:7137/swagger/v1/swagger.json",
  output: "src/api/webApi",
});
```

Después añadimos un script:

```json
{
  "scripts": {
    "gen:api": "openapi-ts"
  }
}
```

La generación se ejecuta con:

```powershell
pnpm gen:api
```

El contenido exacto de la salida depende de la versión y de los plugins configurados, pero el resultado permite importar los contratos generados en lugar de mantener interfaces manuales.

```ts
import type { RepresentacionDto } from "@/api/webApi";
```

## Generar clientes para dos APIs

Si la solución expone una API general y otra operativa, no mezclaría ambos contratos en el mismo directorio. Generaría un cliente independiente para cada especificación:

```text
src/
└── api/
    ├── webApi/
    └── webApiOper/
```

Una configuración puede declarar las dos generaciones:

```ts
// openapi-ts.config.ts
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig([
  {
    input: "https://localhost:7137/swagger/v1/swagger.json",
    output: "src/api/webApi",
  },
  {
    input: "https://localhost:7227/swagger/v1/swagger.json",
    output: "src/api/webApiOper",
  },
]);
```

El script del paquete sigue siendo sencillo:

```json
{
  "scripts": {
    "gen:api": "openapi-ts"
  }
}
```

Separar las salidas tiene varias ventajas:

- deja claro qué API posee cada operación;
- evita colisiones entre tipos con el mismo nombre;
- permite regenerar y revisar cada contrato de forma independiente;
- impide que el frontend dependa accidentalmente de endpoints de la API equivocada.

## Configurar la URL de ejecución

La URL usada para descargar la especificación no tiene por qué ser la misma que empleará el cliente en ejecución.

La primera pertenece al proceso de generación:

```text
https://localhost:7137/swagger/v1/swagger.json
```

La segunda depende del entorno donde se despliegue la aplicación:

```text
Desarrollo: https://localhost:7137
Producción:  https://api.ejemplo.com
```

No conviene incrustar la URL de producción en los archivos generados. Debe configurarse desde el código de arranque de la aplicación o mediante las variables de entorno que ya utilice el frontend.

```ts
import { client } from "@/api/webApi/client.gen";

client.setConfig({
  baseUrl: import.meta.env.VITE_WEB_API_URL,
});
```

Así, el cliente generado conserva el contrato mientras cada despliegue decide dónde está la API.

## Qué hacer con los DTOs manuales

Antes de introducir el generador, buscaría definiciones TypeScript que dupliquen los contratos de C#:

```text
interface *Dto
type *Dto
RepresentacionDto
SolicitudRepresentacionDto
PersonaDto
```

La migración debe hacerse de forma gradual:

1. generar el cliente en un directorio nuevo;
2. sustituir los imports de un flujo concreto;
3. ejecutar comprobaciones de tipos y pruebas;
4. eliminar únicamente los DTOs manuales que ya no tengan consumidores;
5. repetir el proceso por funcionalidad.

No eliminaría todas las interfaces que terminen en `Dto` de una vez. Algunas pueden representar estado exclusivo de la interfaz, formularios o modelos adaptados que no deberían depender directamente del contrato HTTP.

## No todo tipo generado debe llegar a la interfaz

Consumir tipos generados no significa que toda la aplicación deba trabajar con ellos.

Para operaciones sencillas, usar el DTO directamente puede ser suficiente:

```ts
import type { RepresentacionDto } from "@/api/webApi";

export function RepresentacionResumen({
  representacion,
}: {
  representacion: RepresentacionDto;
}) {
  return <strong>{representacion.nombre}</strong>;
}
```

En dominios más complejos puede ser preferible adaptar el resultado en la frontera:

```ts
import type { RepresentacionDto } from "@/api/webApi";

export interface Representacion {
  id: number;
  nombre: string;
  fecha: Date;
}

export function toRepresentacion(dto: RepresentacionDto): Representacion {
  return {
    id: dto.id,
    nombre: dto.nombre,
    fecha: new Date(dto.fecha),
  };
}
```

El tipo generado representa el contrato de transporte. El modelo interno representa las necesidades de la aplicación. Separarlos merece la pena cuando existen conversiones, invariantes o comportamiento de dominio; no cuando el adaptador solo copia cada propiedad sin aportar nada.

## Integrarlo en el flujo de trabajo

La generación manual funciona al principio, pero es fácil olvidar ejecutarla. Como mínimo, dejaría scripts explícitos:

```json
{
  "scripts": {
    "gen:api": "openapi-ts",
    "typecheck": "tsc --noEmit",
    "check:api": "pnpm gen:api && pnpm typecheck"
  }
}
```

En integración continua se puede regenerar el cliente y comprobar que el repositorio no queda con cambios:

```powershell
pnpm gen:api
git diff --exit-code
```

Esta comprobación solo es adecuada si los archivos generados se versionan. Si se generan durante la instalación o la compilación, la estrategia debe ser distinta: basta con generar y ejecutar el `typecheck` y las pruebas.

## ¿Versionar el código generado?

Ambas opciones son válidas, pero conviene elegir una de forma consciente.

Versionaría el cliente cuando:

- las APIs no están disponibles en todos los entornos de desarrollo;
- quiero revisar los cambios del contrato en cada pull request;
- el frontend debe poder instalarse y compilarse sin arrancar el backend;
- necesito compilaciones reproducibles sin depender de red.

No lo versionaría cuando:

- la especificación está publicada como un artefacto estable;
- la generación forma parte obligatoria del pipeline;
- el equipo quiere evitar diffs grandes producidos por el generador.

En una solución empresarial con varias APIs locales, normalmente empezaría versionando la salida. Reduce la fricción para desarrollar el frontend y hace visibles los cambios de contrato.

## Certificados locales y Swagger

Con HTTPS local, el generador debe confiar en el certificado de desarrollo de ASP.NET Core. Desactivar globalmente la validación TLS para resolverlo es una mala práctica: oculta errores reales y puede afectar a otros comandos.

La solución correcta es confiar en el certificado de desarrollo:

```powershell
dotnet dev-certs https --trust
```

También conviene comprobar que ambas APIs están arrancadas y que las URLs de Swagger responden antes de ejecutar la generación.

## Errores que la generación no corrige

Un generador no puede compensar una especificación OpenAPI deficiente. Si el backend publica esquemas ambiguos, respuestas sin tipo o campos marcados incorrectamente como opcionales, el cliente reproducirá esos problemas.

Antes de culpar al código generado, revisaría:

- tipos de respuesta declarados por cada endpoint;
- códigos HTTP documentados;
- nulabilidad de las propiedades;
- nombres y valores de los enums;
- formatos de fechas y números;
- autenticación y cabeceras requeridas;
- diferencias entre el documento de desarrollo y el de producción.

El beneficio real aparece cuando el contrato del backend es preciso.

## Resultado

Con este enfoque, los proyectos quedan separados por responsabilidad:

```text
HTN.SistemaRepresentaciones.Contracts
└── define los DTOs en C#

HTN.SistemaRepresentaciones.WebApi
└── publica su especificación OpenAPI

HTN.SistemaRepresentaciones.WebApiOper
└── publica su propia especificación OpenAPI

HTN.SistemaRepresentaciones.Webs
└── genera y consume dos clientes TypeScript
```

El cambio importante no es usar una herramienta concreta. Es dejar de mantener manualmente el mismo contrato en dos lenguajes.

Cuando cambia un DTO, se regenera el cliente, TypeScript señala los consumidores incompatibles y el error aparece durante el desarrollo, no después de desplegar.

## Referencias

- [Hey API](https://heyapi.dev/)
- [Repositorio de Hey API](https://github.com/hey-api/hey-api)
- [OpenAPI en ASP.NET Core](https://learn.microsoft.com/aspnet/core/fundamentals/openapi/overview)