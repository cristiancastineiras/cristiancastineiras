---
title: "Concurrencia optimista en EF Core: evitar que dos usuarios se pisen"
seoTitle: "Concurrencia optimista en EF Core"
description: "Cómo evitar actualizaciones perdidas con tokens de concurrencia en EF Core, en SQL Server y PostgreSQL, y qué hacer cuando se produce un conflicto en la API."
date: 2025-06-30
tags: ["Entity Framework Core", ".NET", "SQL"]
---

Dos personas abren el mismo expediente. Una cambia el titular y guarda. La otra cambia la dirección y guarda poco después. Sin ninguna protección, la segunda escritura sobrescribe la primera y nadie recibe un aviso. Es una actualización perdida.

## Bloquear o detectar

El bloqueo pesimista impide que otros modifiquen una fila mientras la tienes en uso. Es útil en operaciones cortas, pero no puede mantenerse mientras un usuario piensa frente a un formulario.

La concurrencia optimista no bloquea nada: cada fila lleva una versión y una actualización solo se aplica si esa versión no ha cambiado.

```sql
UPDATE expedientes
SET direccion = 'Calle Mayor 1', version = version + 1
WHERE id = 42 AND version = 7;
```

Si afecta a 0 filas, alguien cambió el registro antes.

## En SQL Server

`rowversion` se actualiza automáticamente en cada cambio:

```csharp
public class Expediente
{
    public int Id { get; set; }
    public string Direccion { get; set; } = "";

    [Timestamp]
    public byte[] Version { get; set; } = [];
}
```

## En PostgreSQL

Con Npgsql, se puede usar la columna de sistema `xmin`, que cambia con cada actualización de la fila:

```csharp
public class Expediente
{
    public int Id { get; set; }
    public string Direccion { get; set; } = "";
    public uint Version { get; set; }
}

modelBuilder.Entity<Expediente>()
    .Property(e => e.Version)
    .IsRowVersion();
```

## Tratar el conflicto

Al guardar, EF Core incluye el valor original del token en el `WHERE`. Si no se ve afectada ninguna fila, lanza `DbUpdateConcurrencyException`:

```csharp
try
{
    await db.SaveChangesAsync(ct);
}
catch (DbUpdateConcurrencyException)
{
    return Results.Problem(
        statusCode: StatusCodes.Status409Conflict,
        title: "El expediente ha cambiado",
        detail: "Otra persona lo ha modificado. Recárgalo y revisa los cambios.");
}
```

No reintentes automáticamente: repetir la misma escritura sobrescribiría al otro usuario, que es justo lo que querías evitar.

## El detalle que suele fallar: la API

La protección solo sirve si la versión que comparas es la que el usuario *vio*, no la que acabas de leer. Si en cada petición cargas la entidad, le aplicas los cambios y guardas, el token siempre coincide y solo proteges una ventana de milisegundos.

La versión debe ir y volver con el cliente:

```csharp
public sealed record ActualizarExpediente(string Direccion, uint Version);

var expediente = await db.Expedientes.FindAsync([id], ct);
if (expediente is null) return Results.NotFound();

// Le decimos a EF Core cuál es el valor original a comparar
db.Entry(expediente).Property(e => e.Version).OriginalValue = peticion.Version;
expediente.Direccion = peticion.Direccion;

await db.SaveChangesAsync(ct);
```

## ETag: la forma HTTP de hacerlo

HTTP tiene un mecanismo estándar para esto, con `ETag` e `If-Match`:

```http
GET /expedientes/42
ETag: "7"

PUT /expedientes/42
If-Match: "7"
```

Si la versión no coincide, el servidor responde `412 Precondition Failed`. Es más estándar que mandar la versión dentro del cuerpo. Requiere algo más de código, y muchos clientes tendrán que aprenderlo, así que elige según quién consuma la API.

## Qué mostrar al usuario

Un mensaje de «ha ocurrido un error» es frustrante después de rellenar un formulario largo. Como mínimo, no pierdas lo que ha escrito. Lo ideal es enseñarle qué cambió y permitirle decidir qué conservar.

## Cuándo no hace falta

Para datos que solo modifica un proceso, o en los que gana sin problema la última escritura, esto no aporta nada. Reserva esta técnica para registros que varias personas o procesos pueden editar a la vez.

## Referencias

- [Tratar conflictos de concurrencia en EF Core](https://learn.microsoft.com/ef/core/saving/concurrency)
- [Tokens de concurrencia en Npgsql](https://www.npgsql.org/efcore/modeling/concurrency.html)
