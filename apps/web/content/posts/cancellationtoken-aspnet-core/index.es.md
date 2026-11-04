---
title: "CancellationToken en ASP.NET Core: deja de trabajar para quien ya no espera"
seoTitle: "CancellationToken en ASP.NET Core"
description: "Cómo propagar CancellationToken desde el controlador hasta la base de datos en ASP.NET Core para cancelar trabajo inútil y añadir tiempos límite correctos."
date: 2025-04-14
tags: [".NET", "ASP.NET Core", "Rendimiento"]
---

Cuando un usuario cierra la pestaña o el cliente HTTP agota su tiempo de espera, tu servidor no se entera por sí solo. Sigue consultando la base de datos y serializando una respuesta que nadie va a leer.

Con tráfico bajo no se nota. En un momento de saturación, ese trabajo inútil empeora justo el problema que hizo que los clientes abandonaran.

## El token que ya tienes

ASP.NET Core enlaza automáticamente un `CancellationToken` a `HttpContext.RequestAborted` si lo declaras como parámetro:

```csharp
app.MapGet("/informes/{id:int}", async (
    int id,
    InformesService servicio,
    CancellationToken ct) =>
{
    var informe = await servicio.GenerarAsync(id, ct);
    return informe is null ? Results.NotFound() : Results.Ok(informe);
});
```

Funciona igual en un controlador:

```csharp
[HttpGet("{id:int}")]
public async Task<IActionResult> Obtener(int id, CancellationToken ct) { /* ... */ }
```

## Propagarlo hasta el final

El token solo sirve si llega a quien hace el trabajo. EF Core, `HttpClient` y la mayoría de las librerías aceptan uno:

```csharp
public async Task<Informe?> GenerarAsync(int id, CancellationToken ct)
{
    var datos = await _db.Movimientos
        .Where(m => m.InformeId == id)
        .ToListAsync(ct);

    var cambio = await _http.GetFromJsonAsync<Cambio>("/cambio", ct);

    return Calcular(datos, cambio);
}
```

Con EF Core, si la cancelación llega durante la consulta, el proveedor intenta cancelarla en el servidor de base de datos. Es decir, también libera recursos allí.

En bucles largos de CPU, comprueba el token de forma explícita:

```csharp
foreach (var fila in filas)
{
    ct.ThrowIfCancellationRequested();
    Procesar(fila);
}
```

## Qué pasa con la excepción

La cancelación se manifiesta como `OperationCanceledException`. No es un error de la aplicación. Si tu middleware global la registra como error y devuelve un 500, llenarás los logs de ruido.

```csharp
catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested)
{
    // El cliente se ha ido: no hay nadie a quien responder.
}
```

El filtro `when` es importante. Si la excepción procede de un tiempo límite interno, no de la desconexión del cliente, sí quieres tratarla como un fallo.

## Combinarlo con tiempos límite

A veces el problema no es que el cliente se vaya, sino que una dependencia tarda demasiado. `CreateLinkedTokenSource` combina ambas condiciones:

```csharp
using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
cts.CancelAfter(TimeSpan.FromSeconds(5));

var respuesta = await _http.GetAsync(url, cts.Token);
```

Desde .NET 8 también hay middleware de timeouts para aplicar un límite por endpoint sin escribir este código a mano:

```csharp
builder.Services.AddRequestTimeouts();
app.UseRequestTimeouts();

app.MapGet("/lento", Handler).WithRequestTimeout(TimeSpan.FromSeconds(5));
```

## Cuándo no cancelar

No todo debe abortarse con la petición. Si una operación escribe en varios sistemas sin transacción común, cortarla a mitad puede dejar un estado inconsistente. En esos casos, recibir el token al principio y no pasarlo a la parte crítica es una decisión válida, siempre que quede explícita en el código.

Una regla razonable: cancela sin miedo las lecturas y las operaciones idempotentes; piensa antes de cancelar las escrituras compuestas.

## Referencias

- [Middleware de tiempos de espera de solicitud](https://learn.microsoft.com/aspnet/core/performance/timeouts)
- [Cancelación en subprocesos administrados](https://learn.microsoft.com/dotnet/standard/threading/cancellation-in-managed-threads)
