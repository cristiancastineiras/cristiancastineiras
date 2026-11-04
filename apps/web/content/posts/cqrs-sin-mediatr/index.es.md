---
title: "CQRS sin MediatR: separar lecturas y escrituras con muy poco código"
seoTitle: "CQRS sin MediatR en .NET"
description: "Qué aporta realmente CQRS, cómo aplicarlo en ASP.NET Core sin librerías, con manejadores simples, y cuándo un mediador o dos bases de datos solo añaden complejidad."
date: 2026-05-25
tags: [".NET", "Arquitectura", "ASP.NET Core"]
---

CQRS se ha asociado tanto a ciertas librerías que parece que hagan falta para aplicarlo. Sobre todo desde que MediatR pasó a ser comercial en 2025, muchos equipos se preguntan qué hacer. Conviene volver a la idea original: es mucho más sencilla de lo que suele parecer.

## La idea

Las lecturas y las escrituras tienen necesidades distintas:

- **Escribir** implica reglas, invariantes, transacciones y entidades con comportamiento.
- **Leer** significa traer datos en la forma exacta que necesita una pantalla, cuanto más rápido, mejor.

Forzar un único modelo a cubrir ambas cosas acaba en entidades cargadas de columnas solo para listados, o en consultas llenas de `Include` para mostrar tres campos. CQRS propone separar ambos caminos.

No implica dos bases de datos, ni eventos, ni un bus. Eso son opciones adicionales, para casos concretos.

## Una consulta

Va directa a los datos, sin pasar por el modelo de dominio:

```csharp
public sealed class ListarPedidos(AppDbContext db)
{
    public sealed record Fila(int Id, string Cliente, decimal Total);

    public Task<List<Fila>> EjecutarAsync(int clienteId, CancellationToken ct) =>
        db.Pedidos
            .Where(p => p.ClienteId == clienteId)
            .OrderByDescending(p => p.Fecha)
            .Select(p => new Fila(p.Id, p.Cliente.Nombre, p.Total))
            .ToListAsync(ct);
}
```

Sin seguimiento de cambios, sin entidades cargadas y sin repositorio. Si una lectura lo necesita, puede usar SQL con Dapper, una vista o una tabla preparada para ello, y nadie más se ve afectado.

## Un comando

Pasa por el dominio, porque ahí es donde están las reglas:

```csharp
public sealed class ConfirmarPedido(AppDbContext db)
{
    public async Task<Resultado> EjecutarAsync(int id, CancellationToken ct)
    {
        var pedido = await db.Pedidos
            .Include(p => p.Lineas)
            .FirstOrDefaultAsync(p => p.Id == id, ct);

        if (pedido is null)
            return Resultado.NoEncontrado;

        if (!pedido.PuedeConfirmarse())
            return Resultado.EstadoInvalido;

        pedido.Confirmar();
        await db.SaveChangesAsync(ct);

        return Resultado.Correcto;
    }
}
```

## Registrar y usar

Cada manejador es una clase normal, inyectada donde se necesita:

```csharp
builder.Services.AddScoped<ListarPedidos>();
builder.Services.AddScoped<ConfirmarPedido>();

app.MapGet("/clientes/{id:int}/pedidos",
    (int id, ListarPedidos consulta, CancellationToken ct) =>
        consulta.EjecutarAsync(id, ct));

app.MapPost("/pedidos/{id:int}/confirmar",
    async (int id, ConfirmarPedido comando, CancellationToken ct) =>
        await comando.EjecutarAsync(id, ct) switch
        {
            Resultado.Correcto => Results.NoContent(),
            Resultado.NoEncontrado => Results.NotFound(),
            _ => Results.Conflict(),
        });
```

Si quieres ir a la definición, el IDE te lleva a la clase real. Es una ventaja que se pierde con un mediador, en el que `Send(new ConfirmarPedido())` obliga a buscar quién lo atiende.

## ¿Y el comportamiento transversal?

La razón legítima para usar un mediador son las *pipelines*: logs, validación y transacciones aplicados a todos los manejadores. Sin él, tienes otras opciones:

- **Filtros de endpoint** para validar:

```csharp
var pedidos = app.MapGroup("/pedidos").AddEndpointFilter<ValidacionFilter>();
```

- **Middleware** para logs y métricas, y OpenTelemetry para trazas.
- **Decoradores** con la librería Scrutor, cuando sea necesario envolver un servicio.
- **Interfaz común** si necesitas tratar todos los manejadores de forma uniforme:

```csharp
public interface IComando<TEntrada, TSalida>
{
    Task<TSalida> EjecutarAsync(TEntrada entrada, CancellationToken ct);
}
```

Si tienes muchos comportamientos transversales de verdad, y varias pipelines por tipo de mensaje, entonces una librería puede compensar. Pero suele ser más sencillo de lo que parece, y no merece la pena añadirla por adelantado.

## Organizar por funcionalidad

Encaja muy bien con la organización vertical, con todo lo que pertenece a una operación junto:

```text
Pedidos/
├── Confirmar/
│   ├── ConfirmarPedido.cs
│   └── ConfirmarPedidoEndpoint.cs
└── Listar/
    ├── ListarPedidos.cs
    └── ListarPedidosEndpoint.cs
```

Al modificar una operación no tienes que recorrer cinco carpetas por tipo de archivo, y el impacto del cambio queda bastante claro.

## Cuándo no merece la pena

En un CRUD sin reglas, un manejador por operación es solo ceremonia. Y ya no digamos separar bases de datos: añade consistencia eventual, procesos de sincronización y mucha más complejidad. Solo se justifica si tienes lecturas con cargas muy diferentes, y lo has medido.

Empieza por lo pequeño: consultas directas para leer, y dominio para escribir. Si algún día una lectura necesita su propia base de datos, el código ya estará preparado para ello.

## Referencias

- [CQRS, de Martin Fowler](https://martinfowler.com/bliki/CQRS.html)
- [Patrón CQRS en Azure Architecture Center](https://learn.microsoft.com/azure/architecture/patterns/cqrs)
