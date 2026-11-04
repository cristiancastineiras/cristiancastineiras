---
title: "Proyecciones y AsNoTracking: consultas de EF Core que no cargan de más"
seoTitle: "Proyecciones y AsNoTracking en EF Core"
description: "Por qué un Select bien escrito suele rendir más que optimizar Includes, qué aporta AsNoTracking de verdad y cómo escribir consultas de solo lectura eficientes en EF Core."
date: 2025-02-17
tags: ["Entity Framework Core", ".NET", "Rendimiento"]
---

La mayoría de las consultas de una aplicación solo leen. Sin embargo, es habitual que traigan la entidad completa, con todas sus columnas, y activen el seguimiento de cambios para algo que nunca se modificará. Es un coste pequeño por petición, que se paga miles de veces.

## Qué hace el seguimiento de cambios

Por defecto, EF Core guarda una instantánea de cada entidad que carga, para detectar cambios al llamar a `SaveChanges`. Eso supone memoria adicional, trabajo de CPU y resolución de identidades.

Si la consulta es de solo lectura, nada de eso aporta.

```csharp
var clientes = await db.Clientes
    .AsNoTracking()
    .Where(c => c.Activo)
    .ToListAsync(ct);
```

Una diferencia a tener en cuenta: sin seguimiento no hay resolución de identidad. Si dos filas apuntan al mismo cliente, se materializan dos instancias distintas. Para mantener esa unicidad sin el seguimiento, existe `AsNoTrackingWithIdentityResolution`.

## Proyectar es aún mejor

`AsNoTracking` evita el seguimiento, pero sigue leyendo todas las columnas. Con una proyección, el SQL pide exactamente lo que necesitas:

```csharp
var clientes = await db.Clientes
    .Where(c => c.Activo)
    .Select(c => new ClienteResumen(
        c.Id,
        c.Nombre,
        c.Pedidos.Count,
        c.Pedidos.Max(p => (DateTime?)p.Fecha)))
    .ToListAsync(ct);
```

Dos ventajas:

- No hace falta un `Include`: EF Core genera el SQL necesario para los datos relacionados.
- Las entidades no se materializan, así que no se aplica seguimiento alguno. El `AsNoTracking` resulta redundante en este caso, salvo que el resultado incluya alguna entidad.

Si tu entidad tiene una columna `Contenido` con un documento de 2 MB, la diferencia entre traerla o no es enorme.

## Reutilizar proyecciones

Para no repetir el mismo `Select`, guárdalo como expresión:

```csharp
public static class ClienteProyecciones
{
    public static readonly Expression<Func<Cliente, ClienteResumen>> Resumen = c =>
        new ClienteResumen(c.Id, c.Nombre, c.Pedidos.Count, c.Pedidos.Max(p => (DateTime?)p.Fecha));
}

var clientes = await db.Clientes.Select(ClienteProyecciones.Resumen).ToListAsync(ct);
```

Es importante que sea una expresión. Si fuese un método normal, como `.Select(c => ToResumen(c))`, EF Core no podría traducirlo a SQL dentro de una consulta compuesta, y acabaría trayendo más datos de los necesarios.

## Hacerlo el modo por defecto

Si un `DbContext` se usa solo para lecturas, se puede desactivar el seguimiento a nivel global:

```csharp
options.UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking);
```

Esto es útil para un contexto de solo lectura, o quizás apuntando a una réplica. No lo haría en un contexto compartido con escrituras, porque el código que espera entidades seguidas dejaría de guardar sus cambios sin avisar.

## Escrituras

Para actualizar una entidad concreta, cárgala con seguimiento: es el camino simple y correcto. Si necesitas modificar muchas filas sin leerlas antes, usa `ExecuteUpdate`:

```csharp
await db.Sesiones
    .Where(s => s.ExpiraEn < ahora)
    .ExecuteDeleteAsync(ct);
```

Se ejecuta directamente en SQL, sin cargar entidades y sin pasar por `SaveChanges`.

## Cómo decidir

| Situación | Enfoque |
|---|---|
| Listado o informe | Proyección a un DTO |
| Detalle completo de solo lectura | `AsNoTracking` |
| Cargar, modificar y guardar | Seguimiento normal |
| Modificación masiva | `ExecuteUpdate` o `ExecuteDelete` |

No hace falta optimizar cada consulta. Empieza por las más frecuentes y las que tocan columnas grandes, que suele ser donde el cambio se nota.

## Referencias

- [Consultas de seguimiento y sin seguimiento](https://learn.microsoft.com/ef/core/querying/tracking)
- [Consultas eficientes](https://learn.microsoft.com/ef/core/performance/efficient-querying)
