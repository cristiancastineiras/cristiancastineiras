---
title: "El problema N+1 en Entity Framework Core: cómo detectarlo y eliminarlo"
seoTitle: "N+1 en Entity Framework Core"
description: "Cómo aparece el problema N+1 en EF Core, cómo verlo en los logs y cuándo usar Include, proyecciones o AsSplitQuery para resolverlo sin crear otro problema."
date: 2025-01-20
tags: ["Entity Framework Core", ".NET", "SQL"]
---

Una página tarda dos segundos y ninguna consulta parece lenta. Cada una tarda 3 ms, pero se ejecutan 400. Es el problema N+1: una consulta trae una lista y luego se lanza otra por cada elemento.

## Cómo aparece

Con carga diferida, ni siquiera hay que hacer nada para provocarlo:

```csharp
var pedidos = await db.Pedidos.ToListAsync(ct);

foreach (var pedido in pedidos)
{
    // Con lazy loading, cada acceso lanza una consulta
    Console.WriteLine(pedido.Cliente.Nombre);
}
```

Sin carga diferida también ocurre, con código más explícito, cuando se llama a un repositorio dentro de un bucle:

```csharp
foreach (var pedido in pedidos)
{
    var cliente = await db.Clientes.FindAsync([pedido.ClienteId], ct);
    // ...
}
```

Con 10 pedidos en desarrollo nadie lo nota. Con 5 000 en producción, sí.

## Hacerlo visible

Lo primero es ver el SQL en desarrollo:

```csharp
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(cadena)
           .LogTo(Console.WriteLine, LogLevel.Information)
           .EnableSensitiveDataLogging(builder.Environment.IsDevelopment()));
```

Un patrón repetido de la misma consulta con distinto parámetro es la señal. En producción, las trazas distribuidas lo muestran con claridad: una petición con cientos de tramos de base de datos idénticos.

También se puede fijar en un test de integración:

```csharp
sealed class ContadorDeConsultas : DbCommandInterceptor
{
    public int Total;

    public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
        DbCommand command, CommandEventData eventData,
        InterceptionResult<DbDataReader> result, CancellationToken ct = default)
    {
        Interlocked.Increment(ref Total);
        return ValueTask.FromResult(result);
    }
}
```

Afirmar que un listado no supera cierto número de consultas evita que el problema regrese sin que nadie lo vea.

## Solución 1: proyectar

Si solo necesitas ciertos campos, esta suele ser la mejor opción. EF Core genera un único `JOIN` y trae lo justo:

```csharp
var pedidos = await db.Pedidos
    .Select(p => new PedidoResumen(p.Id, p.Fecha, p.Cliente.Nombre))
    .ToListAsync(ct);
```

## Solución 2: `Include`

Si necesitas las entidades completas, por ejemplo para modificarlas:

```csharp
var pedidos = await db.Pedidos
    .Include(p => p.Cliente)
    .ToListAsync(ct);
```

## Cuidado con la explosión cartesiana

Cargar con `Include` dos colecciones en la misma consulta multiplica las filas: 50 líneas por 20 pagos generan 1 000 filas por pedido. EF Core avisa de ello en los logs.

`AsSplitQuery` lo divide en varias consultas:

```csharp
var pedidos = await db.Pedidos
    .Include(p => p.Lineas)
    .Include(p => p.Pagos)
    .AsSplitQuery()
    .ToListAsync(ct);
```

Tiene una contrapartida: al ser varias consultas, sin una transacción adecuada pueden ver datos en momentos distintos. Es una buena herramienta, no un valor por defecto universal.

## Solución 3: cargar por lotes

Si los datos vienen de otro lugar y el bucle es inevitable, reúne los identificadores primero:

```csharp
var ids = pedidos.Select(p => p.ClienteId).Distinct().ToList();

var clientes = await db.Clientes
    .Where(c => ids.Contains(c.Id))
    .ToDictionaryAsync(c => c.Id, ct);
```

Dos consultas en total, sea cual sea el número de pedidos.

## Y la carga diferida

La carga diferida hace invisible el coste de un acceso a una propiedad. En una aplicación web, yo la dejaría desactivada: con ella, un cambio en una vista puede añadir decenas de consultas sin tocar el código de datos.

## Referencias

- [Carga de datos relacionados](https://learn.microsoft.com/ef/core/querying/related-data/)
- [Consultas divididas](https://learn.microsoft.com/ef/core/querying/single-split-queries)
