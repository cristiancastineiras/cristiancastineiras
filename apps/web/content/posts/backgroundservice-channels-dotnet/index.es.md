---
title: "BackgroundService y Channels en .NET: trabajo en segundo plano sin perder tareas"
seoTitle: "BackgroundService y Channels en .NET"
description: "Cómo montar una cola en memoria con Channels y BackgroundService en .NET, qué pasa al apagar la aplicación y cuándo necesitas una cola de verdad."
date: 2025-08-25
tags: [".NET", "ASP.NET Core", "Arquitectura"]
---

Enviar un correo, generar un PDF o llamar a un sistema lento no debería mantener abierta una petición HTTP. Para eso no siempre hace falta RabbitMQ: `BackgroundService` y `System.Threading.Channels` cubren muchos casos, siempre que se conozcan sus límites.

## La cola

Un `Channel` acotado es una cola en memoria segura entre hilos:

```csharp
public sealed class ColaDeCorreos
{
    private readonly Channel<Correo> _canal = Channel.CreateBounded<Correo>(
        new BoundedChannelOptions(1_000)
        {
            FullMode = BoundedChannelFullMode.Wait,
            SingleReader = true,
        });

    public ValueTask EncolarAsync(Correo correo, CancellationToken ct) =>
        _canal.Writer.WriteAsync(correo, ct);

    public IAsyncEnumerable<Correo> LeerAsync(CancellationToken ct) =>
        _canal.Reader.ReadAllAsync(ct);
}
```

Usa siempre uno acotado. Un canal sin límite solo traslada el problema: si los productores van más rápido que el consumidor, la memoria crece hasta que el proceso muere. Con `FullMode.Wait` el productor espera, lo que aplica contrapresión.

## El consumidor

```csharp
public sealed class EnvioDeCorreos(
    ColaDeCorreos cola,
    IServiceScopeFactory scopes,
    ILogger<EnvioDeCorreos> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var correo in cola.LeerAsync(stoppingToken))
        {
            try
            {
                await using var scope = scopes.CreateAsyncScope();
                var smtp = scope.ServiceProvider.GetRequiredService<IEnviador>();
                await smtp.EnviarAsync(correo, stoppingToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                logger.LogError(ex, "No se pudo enviar el correo a {Destino}", correo.Destino);
            }
        }
    }
}
```

Tres detalles importan:

- **El ámbito por mensaje.** `BackgroundService` es singleton, así que los servicios scoped deben resolverse dentro de un ámbito propio.
- **El `try/catch`.** Sin él, una excepción termina `ExecuteAsync`. Por defecto, desde .NET 6 eso detiene toda la aplicación (`BackgroundServiceExceptionBehavior.StopHost`).
- **El registro.** Una tarea fallida tiene que dejar rastro o se perderá en silencio.

```csharp
builder.Services.AddSingleton<ColaDeCorreos>();
builder.Services.AddHostedService<EnvioDeCorreos>();
```

## Qué pasa al apagar

Al detener la aplicación se cancela `stoppingToken` y el host espera un tiempo limitado, 30 segundos por defecto en ASP.NET Core en versiones recientes. Se puede ajustar:

```csharp
builder.Services.Configure<HostOptions>(o =>
    o.ShutdownTimeout = TimeSpan.FromSeconds(60));
```

En Kubernetes, ese tiempo debe caber dentro de `terminationGracePeriodSeconds`, o el contenedor recibirá `SIGKILL` antes de terminar.

## El límite real

Esta cola vive en memoria. Si el proceso se reinicia o falla, todo lo pendiente se pierde. Por eso sirve cuando perder una tarea es aceptable o se puede recomponer: refrescar una caché, recalcular un agregado o enviar una notificación no crítica.

No sirve cuando la tarea representa un compromiso con el usuario, como un cobro o un documento legal. En ese caso, escribe primero en una tabla dentro de la misma transacción de negocio y procesa desde ahí, o usa un broker.

También hay que recordar que una cola en memoria no se reparte entre réplicas. Si la API corre en tres instancias, cada una tiene su propia cola.

## Referencias

- [Tareas en segundo plano con servicios hospedados](https://learn.microsoft.com/aspnet/core/fundamentals/host/hosted-services)
- [System.Threading.Channels](https://learn.microsoft.com/dotnet/core/extensions/channels)
