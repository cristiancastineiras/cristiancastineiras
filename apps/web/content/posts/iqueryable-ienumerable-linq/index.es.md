---
title: "IQueryable e IEnumerable: la diferencia que cambia tus consultas LINQ"
seoTitle: "IQueryable vs IEnumerable en LINQ"
description: "Por qué el mismo Where puede ejecutarse en la base de datos o en memoria, cómo afecta al rendimiento en EF Core y qué devolver desde un repositorio."
date: 2025-05-26
tags: ["LINQ", "C#", "Entity Framework Core"]
---

Estas dos consultas se leen casi igual, y el resultado es el mismo. Sin embargo, una puede traer un millón de filas a memoria y la otra diez.

```csharp
// Filtra en la base de datos
IQueryable<Pedido> consulta = db.Pedidos;
var a = await consulta.Where(p => p.Total > 1000).ToListAsync(ct);

// Trae toda la tabla y filtra en memoria
IEnumerable<Pedido> enumerable = db.Pedidos;
var b = enumerable.Where(p => p.Total > 1000).ToList();
```

## Qué recibe cada `Where`

`IEnumerable<T>` usa `Enumerable.Where`, que recibe un delegado (`Func<T, bool>`): código compilado que se ejecuta fila a fila en tu proceso.

`IQueryable<T>` usa `Queryable.Where`, que recibe un árbol de expresiones (`Expression<Func<T, bool>>`): una descripción del código que el proveedor puede traducir a SQL.

La lambda se escribe igual en ambos casos, y el compilador decide en función del tipo estático. Por eso declarar `IEnumerable<Pedido>` es suficiente para cambiar el comportamiento.

## El error típico: el repositorio

```csharp
public IEnumerable<Pedido> ObtenerTodos() => _db.Pedidos;

// En el llamador
var caros = repositorio.ObtenerTodos().Where(p => p.Total > 1000);
```

El tipo de retorno convierte cualquier `Where`, `OrderBy` o `Take` posterior en una operación en memoria. La aplicación funciona igual, solo que trae la tabla entera cada vez. Este error es difícil de ver en una revisión porque el código parece correcto.

## ¿Devolver `IQueryable` desde el repositorio?

Permite componer, pero tiene un coste: cualquier consumidor puede escribir cualquier consulta, y el SQL final deja de estar en un único lugar. Además, el `DbContext` debe seguir vivo cuando se enumera.

Yo prefiero métodos que expresan la intención y devuelven datos ya materializados:

```csharp
public Task<List<PedidoResumen>> ObtenerCarosAsync(
    decimal minimo, int cantidad, CancellationToken ct) =>
    _db.Pedidos
        .Where(p => p.Total >= minimo)
        .OrderByDescending(p => p.Total)
        .Take(cantidad)
        .Select(p => new PedidoResumen(p.Id, p.Total))
        .ToListAsync(ct);
```

Dentro de la capa de datos, `IQueryable` es perfecto para componer filtros.

## Composición condicional

Es donde más brilla:

```csharp
IQueryable<Pedido> consulta = db.Pedidos;

if (filtro.ClienteId is { } clienteId)
    consulta = consulta.Where(p => p.ClienteId == clienteId);

if (filtro.Desde is { } desde)
    consulta = consulta.Where(p => p.Fecha >= desde);

var pagina = await consulta
    .OrderByDescending(p => p.Fecha)
    .Take(50)
    .ToListAsync(ct);
```

Hasta `ToListAsync` no se ejecuta nada, y el SQL final contiene solo los filtros aplicados.

## Lo que no se puede traducir

Un árbol de expresiones puede contener código que el proveedor no sabe convertir:

```csharp
// InvalidOperationException: no se puede traducir
db.Clientes.Where(c => Normalizar(c.Nombre) == "ANA");
```

Desde EF Core 3, esto lanza una excepción en vez de evaluar en cliente de forma silenciosa. Es buena noticia: el error te avisa. La solución no debería ser añadir `.AsEnumerable()` sin pensar, porque volverías a traer todas las filas.

Es mejor reescribirla con funciones traducibles, o guardar el valor normalizado en una columna indexada.

`AsEnumerable()` tiene un uso legítimo: filtrar primero en SQL y aplicar después una transformación que solo existe en .NET.

```csharp
var resultado = db.Clientes
    .Where(c => c.Activo)
    .Select(c => new { c.Id, c.Nombre })
    .AsEnumerable()
    .Select(c => new ClienteVista(c.Id, Normalizar(c.Nombre)));
```

## Evaluación diferida y múltiples enumeraciones

Ambos tipos son diferidos. Si enumeras dos veces una consulta, se ejecuta dos veces:

```csharp
var consulta = db.Pedidos.Where(p => p.Activo);
var total = await consulta.CountAsync(ct);    // una consulta
var datos = await consulta.ToListAsync(ct);   // otra consulta
```

A veces es lo que quieres. Cuando no, materializa una vez con `ToListAsync` y reutiliza la lista.

## Referencias

- [Evaluación de cliente y servidor en EF Core](https://learn.microsoft.com/ef/core/querying/client-eval)
- [Árboles de expresión](https://learn.microsoft.com/dotnet/csharp/advanced-topics/expression-trees/)
