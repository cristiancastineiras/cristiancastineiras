---
title: "Cómo activar nullable reference types en un proyecto .NET que ya existe"
seoTitle: "Nullable reference types en .NET"
description: "Una estrategia gradual para activar nullable reference types en una solución .NET grande sin bloquear al equipo con miles de avisos de golpe."
date: 2025-02-03
tags: [".NET", "C#", "Refactorización"]
---

Activar `<Nullable>enable</Nullable>` en una solución antigua suele producir miles de avisos en la primera compilación. Si el proyecto compila con `TreatWarningsAsErrors`, directamente deja de compilar. Por eso mucha gente lo prueba, se asusta y lo revierte.

Se puede hacer de forma gradual, y merece la pena: `NullReferenceException` sigue siendo uno de los errores más comunes en producción, y el compilador puede encontrar buena parte de ellos.

## Qué cambia realmente

Los tipos de referencia anotados no cambian nada en tiempo de ejecución. `string` y `string?` son el mismo tipo para el CLR. Lo que cambia es el análisis estático: el compilador sigue el flujo del código y avisa cuando un valor posiblemente nulo se desreferencia o se asigna a algo que no admite nulos.

Dos consecuencias importantes:

- las anotaciones no validan nada en la entrada de tu API;
- una anotación incorrecta da una seguridad falsa, porque el compilador se fía de ella.

## Empezar por contextos, no por la solución entera

La directiva `#nullable` permite activar el análisis por archivo. El orden que seguiría:

1. dejar el proyecto en `<Nullable>disable</Nullable>` si todavía no se ha decidido nada;
2. añadir `#nullable enable` en cada archivo que se toca o que se crea;
3. cuando la mayoría esté anotada, cambiar el proyecto a `enable` y marcar los pendientes con `#nullable disable`;
4. eliminar esas excepciones poco a poco.

```csharp
#nullable enable

public sealed class ClienteService
{
    public string Normalizar(string? nombre) =>
        nombre?.Trim().ToUpperInvariant() ?? string.Empty;
}
```

También existe el modo `warnings`, que activa los avisos sin exigir anotaciones. Sirve para hacerse una idea del volumen antes de anotar nada:

```xml
<PropertyGroup>
  <Nullable>warnings</Nullable>
</PropertyGroup>
```

## Por dónde anotar primero

Conviene empezar por las hojas del grafo de dependencias: proyectos de dominio y utilidades que no dependen de nada. Cuando una librería está bien anotada, sus consumidores reciben información útil. Si se empieza por arriba, cada llamada devuelve tipos «desconocidos» y se acaba anotando a ciegas.

## El operador `!` es una deuda, no una solución

`valor!` silencia el aviso sin comprobar nada. Tiene usos legítimos, pero cada uso es una afirmación que nadie verifica. Antes de escribirlo, considera estas alternativas:

- comprobar y lanzar con `ArgumentNullException.ThrowIfNull(valor)`;
- usar atributos como `[NotNullWhen(true)]` para explicarle el flujo al compilador;
- marcar con `required` las propiedades obligatorias en lugar de inicializarlas con `null!`.

```csharp
using System.Diagnostics.CodeAnalysis;

public static bool TryGetCliente(int id, [NotNullWhen(true)] out Cliente? cliente)
{
    cliente = Buscar(id);
    return cliente is not null;
}
```

## Entidades de EF Core

EF Core respeta las anotaciones: una propiedad `string` no nula se mapea como columna obligatoria y `string?` como opcional. Activar el análisis en las entidades puede generar una migración que cambie la nulabilidad de varias columnas.

Revisa la migración generada antes de aplicarla. Si la base de datos contiene nulos donde tu anotación dice que no puede haberlos, el problema estaba ya antes, pero ahora se convierte en un error al desplegar.

## Cuándo convertirlo en error

Cuando un proyecto esté limpio, protege lo conseguido:

```xml
<PropertyGroup>
  <Nullable>enable</Nullable>
  <WarningsAsErrors>nullable</WarningsAsErrors>
</PropertyGroup>
```

Así los avisos de nulabilidad pasan a ser errores sin tener que hacer lo mismo con todos los demás avisos.

## Referencias

- [Tipos de referencia que aceptan valores nulos](https://learn.microsoft.com/dotnet/csharp/nullable-references)
- [Migrar código existente](https://learn.microsoft.com/dotnet/csharp/nullable-migration-strategies)
