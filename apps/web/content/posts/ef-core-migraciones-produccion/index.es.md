---
title: "Migraciones de EF Core en producción sin sustos"
seoTitle: "Migraciones de EF Core en producción"
description: "Por qué no conviene ejecutar Migrate al arrancar, cómo usar scripts idempotentes y bundles, y cómo aplicar cambios de esquema compatibles sin tiempo de inactividad."
date: 2025-03-24
tags: ["Entity Framework Core", ".NET", "CI/CD"]
---

`dotnet ef database update` es perfecto en desarrollo. En producción, muchos equipos terminan copiando la idea con `db.Database.Migrate()` al arrancar la aplicación. Funciona hasta que hay varias instancias, una migración larga o un fallo a mitad de camino.

## Por qué no migrar al arrancar

- Varias réplicas arrancando a la vez pueden competir por aplicar la misma migración. Desde EF Core 9 hay un bloqueo que lo mitiga, pero sigue sin ser buena idea.
- El usuario de la aplicación necesita permisos para alterar el esquema, algo que no deberías concederle.
- Una migración lenta bloquea el arranque y puede hacer que el orquestador reinicie el contenedor a mitad de proceso.
- Un fallo se convierte en una aplicación que no arranca, con el esquema a medias.

Es mejor que migrar sea un paso propio del despliegue.

## Opción 1: script SQL idempotente

```bash
dotnet ef migrations script --idempotent -o migracion.sql
```

El script comprueba qué migraciones ya están aplicadas y puede ejecutarse en cualquier estado. Su gran ventaja es que se puede revisar: alguien puede leer exactamente qué SQL se va a ejecutar en producción.

## Opción 2: migration bundles

Un bundle es un ejecutable autónomo, sin depender de SDK ni de código fuente en el servidor:

```bash
dotnet ef migrations bundle --self-contained -r linux-x64 -o efbundle
./efbundle --connection "$CONEXION"
```

Encaja bien en un pipeline: lo construyes en CI y lo ejecutas como un paso previo al despliegue, por ejemplo como un Job de Kubernetes con credenciales propias.

## Revisar lo que se genera

El generador no conoce tus datos ni el tráfico. Revisa cada migración, sobre todo si contiene:

- `DropColumn` o `DropTable`: pérdida de datos irreversible;
- `RenameColumn`, que EF Core puede interpretar como borrar y crear;
- `AlterColumn` que reduce el tamaño o cambia el tipo: puede fallar o reescribir la tabla;
- la creación de un índice en una tabla grande.

Para crear un índice sin bloquear en PostgreSQL, puedes usar SQL explícito fuera de la transacción:

```csharp
migrationBuilder.Sql(
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_pedidos_fecha ON pedidos (fecha);",
    suppressTransaction: true);
```

Las migraciones se ejecutan por defecto en una transacción, y `CREATE INDEX CONCURRENTLY` no puede hacerlo; de ahí `suppressTransaction`.

## Despliegues sin parada: expandir y contraer

Durante un despliegue conviven la versión vieja y la nueva de la aplicación. Por eso, un esquema debe funcionar con ambas. Para renombrar una columna:

1. **Expandir**: añadir la columna nueva y permitir nulos. La versión antigua sigue funcionando.
2. **Desplegar** una versión que escribe en ambas y lee de la nueva, con la anterior como alternativa.
3. **Rellenar** las filas antiguas con un proceso por lotes.
4. **Contraer**: en un despliegue posterior, eliminar la columna vieja.

Son varias migraciones repartidas en varias versiones. Es más trabajo que un `RenameColumn`, pero es lo que evita una ventana de caída.

## Comprobar en CI

Dos controles sencillos:

```bash
# Falla si el modelo tiene cambios sin migración (EF Core 8 o superior)
dotnet ef migrations has-pending-model-changes

# Verifica que el script se genera
dotnet ef migrations script --idempotent -o migracion.sql
```

Aplica también las migraciones sobre una base de datos real en los tests de integración, partiendo de una copia con el mismo esquema que producción. Un fallo ahí cuesta mucho menos.

## Antes de ejecutar

Una migración destructiva no se arregla con un rollback del código. Comprueba que hay copia de seguridad reciente y sabes restaurarla. Cuando sea posible, despliega de forma que volver a la versión anterior de la aplicación no requiera deshacer el esquema.

## Referencias

- [Aplicar migraciones](https://learn.microsoft.com/ef/core/managing-schemas/migrations/applying)
- [Administrar migraciones](https://learn.microsoft.com/ef/core/managing-schemas/migrations/managing)
