---
title: "Migrar a .NET 10 LTS: qué revisar antes de cambiar el TargetFramework"
seoTitle: "Migrar a .NET 10 LTS: checklist"
description: "Una lista práctica para actualizar a .NET 10 LTS: calendario de soporte de .NET 8 y 9, global.json, paquetes, cambios incompatibles, imágenes Docker y CI."
date: 2026-01-19
tags: [".NET", "C#", "Migración"]
---

.NET 10 es LTS, con soporte hasta noviembre de 2028. Hay otro dato que marca el calendario: .NET 8 y .NET 9 dejan de recibir soporte el mismo día, el 10 de noviembre de 2026. Cualquier proyecto en esas versiones tiene una fecha límite clara.

Cambiar `TargetFramework` es la parte fácil. Lo que requiere atención es todo lo demás.

## Antes de tocar nada

Deja la rama principal en un estado del que puedas fiarte:

1. pruebas pasando en CI;
2. dependencias revisadas con `dotnet list package --outdated`;
3. avisos del compilador bajo control, para distinguir los nuevos;
4. una forma de comparar el comportamiento después: métricas o pruebas de carga.

Si el proyecto viene de varias versiones atrás, las notas de migración de cada una te interesan todas. Los cambios incompatibles se documentan por versión.

## Fijar el SDK

Un `global.json` evita que cada máquina compile con un SDK distinto:

```json
{
  "sdk": {
    "version": "10.0.100",
    "rollForward": "latestFeature"
  }
}
```

## Cambiar el framework y los paquetes

Si varios proyectos comparten configuración, `Directory.Build.props` permite cambiarlo en un solo lugar:

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
  </PropertyGroup>
</Project>
```

Actualiza en el mismo paso los paquetes `Microsoft.AspNetCore.*`, `Microsoft.EntityFrameworkCore.*` y `Microsoft.Extensions.*`, que suelen ir alineados con la versión del runtime. Para los proveedores de EF Core, como Npgsql, comprueba que exista versión compatible.

## Qué revisar a fondo

Algunos cambios no rompen la compilación pero sí el comportamiento:

- **Resolución de sobrecargas de C# 14**: los *first-class spans* pueden hacer que una llamada elija una sobrecarga distinta, sobre todo en `Reverse()` sobre arrays. Compila, pero puede comportarse diferente.
- **Imágenes de contenedor**: las imágenes por defecto de .NET 10 están basadas en Ubuntu en vez de Debian. Si tu `Dockerfile` usa `apt` con paquetes concretos o instala cosas específicas, revísalo.
- **OpenAPI**: el generador integrado produce OpenAPI 3.1 por defecto, lo que afecta a cómo se representan los tipos que admiten nulos. Si generas clientes a partir del documento, compara la salida.
- **EF Core**: si actualizas entre versiones mayores, revisa la lista de cambios incompatibles y vuelve a generar el `snapshot` si procede.

## Imágenes y CI

Busca todas las referencias a la versión antigua, no solo los `csproj`:

```bash
git grep -nE "(net8\.0|net9\.0|dotnet/(aspnet|sdk):(8|9)\.0|dotnet-version: *'?(8|9))"
```

Suele haber restos en `Dockerfile`, pipelines, `compose.yaml`, documentación y scripts de despliegue.

## Desplegar por etapas

No la mezcles con cambios funcionales. Una migración aislada hace que cualquier regresión sea fácil de atribuir y permite revertir sin arrastrar nada.

Al desplegar, compara con la versión anterior latencia, memoria y errores durante un tiempo razonable, idealmente con una parte del tráfico. Un cambio en el recolector de basura o en el JIT no se ve en las pruebas unitarias.

## ¿Merece la pena esperar a .NET 11?

.NET 11 será una versión STS. Salvo que necesites una novedad concreta, para un sistema que debe durar años lo más razonable es asentarse en la LTS y planificar el salto de una LTS a la siguiente.

## Referencias

- [Política de soporte de .NET](https://dotnet.microsoft.com/platform/support/policy/dotnet-core)
- [Novedades de .NET 10](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/overview)
- [Cambios incompatibles en .NET 10](https://learn.microsoft.com/dotnet/core/compatibility/10.0)
