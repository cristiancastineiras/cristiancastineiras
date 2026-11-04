---
title: "EF Core 10: LeftJoin, filtros con nombre y otras mejoras que sí vas a usar"
seoTitle: "Novedades útiles de EF Core 10"
description: "Lo más práctico de EF Core 10: operadores LeftJoin y RightJoin, filtros de consulta con nombre, ExecuteUpdate más sencillo y mejoras en parámetros de colección."
date: 2026-01-12
tags: ["Entity Framework Core", ".NET", "LINQ"]
---

EF Core 10 llegó con .NET 10 y es una versión LTS. No exige reescribir nada, y algunas de sus mejoras eliminan código incómodo que llevaba años entre nosotros.

## LeftJoin y RightJoin

Durante años, un *left join* en LINQ ha requerido este patrón, nada intuitivo:

```csharp
var consulta =
    from c in db.Clientes
    join p in db.Pedidos on c.Id equals p.ClienteId into grupo
    from p in grupo.DefaultIfEmpty()
    select new { c.Nombre, Total = p == null ? 0 : p.Total };
```

Ahora existe un operador específico:

```csharp
var consulta = db.Clientes.LeftJoin(
    db.Pedidos,
    cliente => cliente.Id,
    pedido => pedido.ClienteId,
    (cliente, pedido) => new
    {
        cliente.Nombre,
        Total = pedido == null ? 0 : pedido.Total,
    });
```

`RightJoin` funciona igual en sentido contrario. Estos operadores forman parte de LINQ en .NET 10, por lo que también funcionan con colecciones en memoria.

## Filtros de consulta con nombre

Los filtros globales son muy útiles para el borrado lógico o la multiinquilinidad. Hasta ahora había dos limitaciones: solo se admitía un filtro por entidad y `IgnoreQueryFilters()` los desactivaba todos a la vez.

Ahora tienen nombre:

```csharp
modelBuilder.Entity<Factura>()
    .HasQueryFilter("BorradoLogico", f => !f.Eliminada)
    .HasQueryFilter("Inquilino", f => f.InquilinoId == inquilinoId);
```

Y se pueden desactivar de forma selectiva:

```csharp
var papelera = await db.Facturas
    .IgnoreQueryFilters(["BorradoLogico"])
    .Where(f => f.Eliminada)
    .ToListAsync(ct);
```

Es una mejora de seguridad real. Antes, para ver elementos eliminados había que desactivar también el filtro de inquilino y volver a aplicarlo a mano. Olvidarlo exponía datos de otros clientes.

## ExecuteUpdate más natural

`ExecuteUpdate` usaba árboles de expresión, lo que complicaba actualizar columnas de forma condicional. Ahora acepta una lambda normal:

```csharp
await db.Clientes
    .Where(c => c.Id == id)
    .ExecuteUpdateAsync(setters =>
    {
        setters.SetProperty(c => c.ModificadoEn, ahora);

        if (peticion.Nombre is not null)
            setters.SetProperty(c => c.Nombre, peticion.Nombre);
    }, ct);
```

## Parámetros de colección

Traducir `ids.Contains(x)` siempre ha tenido sus problemas. Con valores en línea, el plan de consulta no se reutiliza; con un único parámetro JSON, el planificador no conoce el número de elementos.

EF Core 10 traduce por defecto a parámetros escalares independientes, y ajusta su número para que se reutilicen los planes. Si una consulta concreta lo necesita, hay métodos para elegir otro modo de traducción.

Si notas cambios en los planes de consultas críticas tras actualizar, este es uno de los primeros puntos que deberías revisar.

## Tipos complejos

Se amplían los *complex types*: ahora se pueden mapear a JSON, ser opcionales y usarse como `struct`. Para valores sin identidad propia, como una dirección o un importe con moneda, ya son la opción recomendada frente a los *owned types*.

## Cómo actualizar

1. Sube también el proveedor, como `Npgsql.EntityFrameworkCore.PostgreSQL`.
2. Actualiza la herramienta `dotnet-ef`.
3. Revisa los cambios incompatibles, porque pueden afectar al SQL generado.
4. Compara los planes de las consultas más críticas con datos realistas.

Las novedades no obligan a tocar el código existente, de modo que `LeftJoin` y los filtros con nombre se pueden adoptar poco a poco.

## Referencias

- [Novedades de EF Core 10](https://learn.microsoft.com/ef/core/what-is-new/ef-core-10.0/whatsnew)
- [Cambios incompatibles en EF Core 10](https://learn.microsoft.com/ef/core/what-is-new/ef-core-10.0/breaking-changes)
