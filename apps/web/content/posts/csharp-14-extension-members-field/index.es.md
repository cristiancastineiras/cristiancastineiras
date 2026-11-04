---
title: "C# 14 en la práctica: extension members y la palabra clave field"
seoTitle: "C# 14: extension members y field"
description: "Las novedades de C# 14 que más cambian el día a día: propiedades de extensión, bloques extension, la palabra clave field y asignación condicional con null."
date: 2026-02-16
tags: ["C#", ".NET"]
---

C# 14 llegó con .NET 10. No cambia cómo se escribe C#, pero sí elimina varias molestias acumuladas durante años. Estas son las novedades que probablemente uses a menudo.

## Bloques extension

Hasta ahora, solo los métodos podían ser de extensión. Los nuevos bloques `extension` permiten añadir también propiedades y miembros estáticos:

```csharp
public static class ColeccionExtensions
{
    extension<T>(IReadOnlyCollection<T> origen)
    {
        public bool EstaVacia => origen.Count == 0;

        public IEnumerable<T> SinNulos() => origen.Where(x => x is not null);
    }

    extension<T>(List<T>)
    {
        public static List<T> ConCapacidad(int capacidad) => new(capacidad);
    }
}
```

Se usan como si pertenecieran al tipo:

```csharp
if (pedidos.EstaVacia) return;

var lista = List<int>.ConCapacidad(100);
```

Los métodos de extensión clásicos con `this` siguen funcionando y son compatibles. No hay que reescribir nada: el nuevo formato se puede adoptar solo donde aporte, como en las propiedades.

## La palabra clave `field`

Antes, añadir validación a una propiedad automática obligaba a declarar un campo de respaldo. Ahora `field` hace referencia al campo que genera el compilador:

```csharp
public string Nombre
{
    get;
    set => field = value?.Trim()
        ?? throw new ArgumentNullException(nameof(value));
}
```

Una posible trampa: si tu tipo ya tiene un miembro llamado `field`, la palabra pasa a tener otro significado dentro de los descriptores de acceso. Se resuelve con `@field` o `this.field`, y el compilador avisa de la ambigüedad.

## Asignación condicional con null

El operador `?.` ya se puede usar a la izquierda de una asignación:

```csharp
// Antes
if (cliente is not null)
{
    cliente.UltimoAcceso = ahora;
}

// Ahora
cliente?.UltimoAcceso = ahora;
```

La parte derecha solo se evalúa si `cliente` no es nulo. Es decir, en `cliente?.Total = Calcular();`, `Calcular` no se llama cuando `cliente` es nulo. Conviene recordarlo si esa llamada tiene efectos secundarios.

## First-class spans

Las conversiones implícitas entre arrays, `Span<T>` y `ReadOnlySpan<T>` son ahora parte del lenguaje. Esto hace más natural escribir APIs de alto rendimiento, y también significa que ciertas llamadas a métodos de extensión pueden resolverse de otra manera que en versiones anteriores.

Si actualizas y un `array.Reverse()` deja de comportarse como esperabas, probablemente esa es la causa: ahora puede elegir `MemoryExtensions.Reverse`, que invierte en el sitio, en lugar de `Enumerable.Reverse`.

## Cambios menores útiles

- **`nameof` con genéricos abiertos**: `nameof(List<>)` ya es válido.
- **Modificadores en lambdas sin tipos**: `(ref x, out y) => ...` sin escribir los tipos.
- **Constructores y eventos parciales**: especialmente útiles para generadores de código.

## Cómo adoptarlo

No hace falta una refactorización global. Yo aplicaría estas reglas:

1. usar `field` en cuanto una propiedad necesite validación, en lugar de crear un campo nuevo;
2. reservar los bloques `extension` para casos en que una propiedad o un miembro estático aporten legibilidad;
3. dejar los métodos de extensión existentes como están.

## Referencias

- [Novedades de C# 14](https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-14)
- [Miembros de extensión](https://learn.microsoft.com/dotnet/csharp/programming-guide/classes-and-structs/extension-methods)
