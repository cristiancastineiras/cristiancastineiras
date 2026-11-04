---
title: "Idempotencia en APIs REST: reintentos seguros sin cobros dobles"
seoTitle: "Idempotencia en APIs REST"
description: "Cómo implementar claves de idempotencia en una API con ASP.NET Core y PostgreSQL para que los reintentos de red no dupliquen pagos, pedidos ni otras operaciones."
date: 2025-10-27
tags: ["REST", "ASP.NET Core", "PostgreSQL"]
---

Un cliente envía un `POST /pagos`, el servidor lo procesa y la respuesta se pierde por un corte de red. El cliente no sabe si el pago se ha hecho. Si reintenta, puede cobrar dos veces. Si no reintenta, puede que el pago nunca se haya registrado.

La idempotencia resuelve este dilema: repetir la misma operación tiene el mismo efecto que hacerla una vez.

## Qué métodos ya son idempotentes

Según la semántica HTTP, `GET`, `PUT` y `DELETE` deberían serlo. `POST` no lo es, y es donde suelen estar las operaciones delicadas. Ahí entra la clave de idempotencia.

## La clave de idempotencia

El cliente genera un identificador único por intención de operación y lo envía con cada intento:

```http
POST /pagos HTTP/1.1
Idempotency-Key: 8f14e45f-ceea-4e7b-9a55-7f5d3c1b2a90
Content-Type: application/json

{ "importe": 25.00, "cuenta": "ES12..." }
```

El servidor guarda la clave con su resultado. Si llega de nuevo, devuelve la misma respuesta sin repetir nada.

La clave se genera antes del primer intento y se conserva en todos los reintentos. Si se crea una nueva por cada intento, no sirve de nada.

## La tabla

La restricción de unicidad hace el trabajo importante:

```sql
CREATE TABLE idempotencia (
    clave        text        NOT NULL,
    cliente_id   text        NOT NULL,
    hash_peticion text       NOT NULL,
    estado_http  int,
    respuesta    jsonb,
    creado_en    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (cliente_id, clave)
);
```

Incluir el cliente en la clave primaria impide que un usuario colisione con la clave de otro, o que pueda leer su respuesta.

## El flujo

```csharp
public async Task<IResult> CrearPago(
    string clave, CrearPago peticion, string clienteId, CancellationToken ct)
{
    var hash = CalcularHash(peticion);

    await using var tx = await _db.Database.BeginTransactionAsync(ct);

    var insertadas = await _db.Database.ExecuteSqlAsync($"""
        INSERT INTO idempotencia (clave, cliente_id, hash_peticion)
        VALUES ({clave}, {clienteId}, {hash})
        ON CONFLICT DO NOTHING
        """, ct);

    if (insertadas == 0)
    {
        await tx.RollbackAsync(ct);
        return await RepetirRespuesta(clave, clienteId, hash, ct);
    }

    var pago = await RegistrarPago(peticion, ct);
    await GuardarRespuesta(clave, clienteId, 201, pago, ct);

    await tx.CommitAsync(ct);
    return Results.Created($"/pagos/{pago.Id}", pago);
}
```

La inserción y la operación de negocio van en la misma transacción. Si algo falla, desaparecen ambas y el reintento puede volver a empezar.

Con dos peticiones simultáneas, la segunda se queda esperando en el `INSERT` hasta que la primera confirme. Cuando termina, no inserta nada y devuelve la respuesta guardada.

## Casos que hay que decidir

**La misma clave con otro contenido.** Compara el hash de la petición y devuelve un error, por ejemplo un 422. Es casi siempre un fallo del cliente, y ejecutarlo o devolver la respuesta anterior ocultaría un problema.

**Errores.** Guardar los errores de validación (4xx) es razonable. Los 5xx generalmente no se guardan, para que un reintento pueda funcionar. Con el rollback del ejemplo, ya no quedan almacenados.

**Llamadas a terceros.** La transacción no cubre lo que ocurre fuera de tu base de datos. Si el pago llama a una pasarela, reenvíale también una clave de idempotencia derivada de la tuya. Sin eso, un fallo tras la llamada duplicaría la operación en el proveedor.

**Retención.** Las claves no se guardan para siempre. Elimina las antiguas con una tarea periódica, sabiendo que el periodo debe cubrir los reintentos razonables, normalmente horas o unos pocos días.

## Alternativas más sencillas

No todo necesita una tabla específica. A veces hay una clave natural: una restricción `UNIQUE (pedido_id)` en la tabla de facturas ya impide facturar dos veces el mismo pedido. Si tu dominio ofrece esa garantía, aprovéchala y añade la clave genérica solo donde haga falta.

## Referencias

- [RFC 9110: métodos idempotentes](https://www.rfc-editor.org/rfc/rfc9110#name-idempotent-methods)
- [Borrador de la cabecera Idempotency-Key en el IETF](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)
