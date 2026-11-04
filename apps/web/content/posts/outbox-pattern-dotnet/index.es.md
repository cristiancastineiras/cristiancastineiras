---
title: "Patrón Outbox en .NET: publicar eventos sin perder ninguno"
seoTitle: "Patrón Outbox en .NET y EF Core"
description: "Cómo evitar la doble escritura entre base de datos y broker con el patrón Outbox en EF Core, un procesador con SKIP LOCKED y consumidores idempotentes."
date: 2026-10-12
tags: [".NET", "Arquitectura", "PostgreSQL"]
---

Guardar un pedido y publicar `PedidoConfirmado` parecen dos líneas seguidas. En realidad son dos sistemas sin una transacción común:

```csharp
await db.SaveChangesAsync(ct);
await bus.PublishAsync(new PedidoConfirmado(pedido.Id), ct);
```

Si el proceso falla entre ambas, el pedido queda guardado y nadie se entera. Si inviertes el orden, puedes publicar un evento de algo que nunca se guardó. Es el problema de la doble escritura, y ocurrirá tarde o temprano.

## La idea

En lugar de publicar directamente, guarda el evento en una tabla de la misma base de datos, dentro de la misma transacción. Un proceso aparte lo enviará después.

```text
Transacción
 ├─ INSERT pedidos
 └─ INSERT outbox
         │
         ▼
Procesador ──► Broker ──► Consumidores
```

O se guardan ambos, o ninguno. La publicación se reintenta hasta que salga bien.

## La tabla

```csharp
public sealed class MensajeOutbox
{
    public Guid Id { get; init; } = Guid.CreateVersion7();
    public required string Tipo { get; init; }
    public required string Contenido { get; init; }
    public DateTimeOffset CreadoEn { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ProcesadoEn { get; set; }
    public int Intentos { get; set; }
}
```

## Escribir en la misma transacción

```csharp
db.Pedidos.Add(pedido);

db.Outbox.Add(new MensajeOutbox
{
    Tipo = nameof(PedidoConfirmado),
    Contenido = JsonSerializer.Serialize(new PedidoConfirmado(pedido.Id, pedido.Total)),
});

await db.SaveChangesAsync(ct);
```

`SaveChanges` envuelve todo en una transacción. Para no acordarse de hacerlo en cada caso, puedes convertir eventos de dominio en filas con un interceptor.

## El procesador

```csharp
public sealed class ProcesadorOutbox(
    IServiceScopeFactory scopes,
    ILogger<ProcesadorOutbox> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var temporizador = new PeriodicTimer(TimeSpan.FromSeconds(2));

        while (await temporizador.WaitForNextTickAsync(stoppingToken))
        {
            try
            {
                await ProcesarLoteAsync(stoppingToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                logger.LogError(ex, "Error al procesar el outbox");
            }
        }
    }

    private async Task ProcesarLoteAsync(CancellationToken ct)
    {
        await using var scope = scopes.CreateAsyncScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var bus = scope.ServiceProvider.GetRequiredService<IBus>();

        await using var tx = await db.Database.BeginTransactionAsync(ct);

        var lote = await db.Outbox
            .FromSql($"""
                SELECT * FROM outbox
                WHERE procesado_en IS NULL
                ORDER BY id
                LIMIT 50
                FOR UPDATE SKIP LOCKED
                """)
            .ToListAsync(ct);

        foreach (var mensaje in lote)
        {
            await bus.PublicarAsync(mensaje.Tipo, mensaje.Contenido, mensaje.Id, ct);
            mensaje.ProcesadoEn = DateTimeOffset.UtcNow;
        }

        await db.SaveChangesAsync(ct);
        await tx.CommitAsync(ct);
    }
}
```

`FOR UPDATE SKIP LOCKED` permite que varias réplicas procesen a la vez sin coger los mismos mensajes: cada una se salta las filas bloqueadas por otra. No hace falta nada más para coordinarlas.

Hay un índice parcial que mantiene la consulta rápida, aunque la tabla crezca:

```sql
CREATE INDEX ix_outbox_pendientes ON outbox (id) WHERE procesado_en IS NULL;
```

## Entrega al menos una vez

Puede fallar tras publicar y antes de confirmar. Al reintentar, el mensaje se volverá a enviar. Por tanto, el patrón garantiza que se entrega **al menos una vez**, y los consumidores tienen que tolerar duplicados.

La forma más directa es que recuerden lo que ya han procesado, en la misma transacción que su trabajo:

```csharp
var insertadas = await db.Database.ExecuteSqlAsync($"""
    INSERT INTO mensajes_procesados (id) VALUES ({mensajeId})
    ON CONFLICT DO NOTHING
    """, ct);

if (insertadas == 0) return; // ya procesado

await AplicarCambios(evento, ct);
await db.SaveChangesAsync(ct);
```

## Lo que hay que vigilar

- **El orden.** Con varias réplicas y reintentos, el orden no está garantizado. Si importa, particiona por una clave y procesa en orden dentro de cada una, o haz que los consumidores toleren el desorden.
- **Mensajes venenosos.** Un mensaje que siempre falla no debería bloquear a los demás: cuenta los intentos y apártalo tras un máximo.
- **Limpieza.** Borra por lotes los mensajes procesados, o la tabla crecerá sin parar.
- **Observabilidad.** Mide cuántos hay pendientes y la antigüedad del más viejo. Es la mejor alerta para saber si el procesador se ha detenido. Propaga además el `traceparent` en el mensaje, para conectar las trazas.
- **Latencia.** El sondeo añade unos segundos. Si no es aceptable, reacciona con `LISTEN/NOTIFY` o usa captura de cambios con Debezium, que lee directamente el WAL.

## ¿Escribirlo o usar una librería?

Wolverine, MassTransit y otras librerías ya incluyen un *outbox* maduro. Si ya usas alguna, no lo escribas tú. Implementarlo a mano tiene sentido si solo necesitas un caso sencillo y quieres evitar la dependencia, pero los detalles de reintentos y limpieza llevan más trabajo del que parece.

## Referencias

- [Patrón Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- [SKIP LOCKED en PostgreSQL](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
