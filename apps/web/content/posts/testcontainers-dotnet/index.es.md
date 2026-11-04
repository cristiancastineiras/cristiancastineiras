---
title: "Testcontainers en .NET: pruebas de integración con una base de datos de verdad"
seoTitle: "Testcontainers en .NET con PostgreSQL"
description: "Cómo usar Testcontainers con xUnit y PostgreSQL para probar contra el motor real, compartir el contenedor, reiniciar datos con Respawn y ejecutar en CI sin servicios externos."
date: 2025-08-14
tags: [".NET", "Testing", "PostgreSQL", "Docker"]
---

Probar con el proveedor en memoria de EF Core da una falsa sensación de seguridad. No traduce a SQL, por lo que no detecta una consulta incorrecta, una restricción, un índice único ni una transacción mal gestionada. Con Testcontainers puedes usar la base de datos real, en un contenedor desechable, sin tener que instalar nada en la máquina de cada desarrollador.

## Instalar

```bash
dotnet add package Testcontainers.PostgreSql
dotnet add package Respawn
```

Solo necesitas Docker disponible en la máquina.

## Un fixture compartido

Arrancar un contenedor tarda unos segundos, así que conviene compartirlo entre pruebas:

```csharp
public sealed class BaseDeDatosFixture : IAsyncLifetime
{
    private readonly PostgreSqlContainer _contenedor = new PostgreSqlBuilder()
        .WithImage("postgres:17-alpine")
        .Build();

    public string CadenaDeConexion => _contenedor.GetConnectionString();

    public async Task InitializeAsync()
    {
        await _contenedor.StartAsync();

        await using var db = CrearContexto();
        await db.Database.MigrateAsync();
    }

    public Task DisposeAsync() => _contenedor.DisposeAsync().AsTask();

    public AppDbContext CrearContexto() =>
        new(new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(CadenaDeConexion)
            .Options);
}

[CollectionDefinition(nameof(BaseDeDatosCollection))]
public sealed class BaseDeDatosCollection : ICollectionFixture<BaseDeDatosFixture>;
```

Usa la misma versión que tienes en producción: esa es la razón de todo esto. Al aplicar las migraciones reales, además, verificas que funcionan.

## Una prueba

```csharp
[Collection(nameof(BaseDeDatosCollection))]
public sealed class PedidosTests(BaseDeDatosFixture fixture)
{
    [Fact]
    public async Task No_permite_dos_facturas_para_el_mismo_pedido()
    {
        await using var db = fixture.CrearContexto();

        db.Facturas.Add(new Factura { PedidoId = 1, Numero = "F-1" });
        await db.SaveChangesAsync();

        db.Facturas.Add(new Factura { PedidoId = 1, Numero = "F-2" });

        await Assert.ThrowsAsync<DbUpdateException>(() => db.SaveChangesAsync());
    }
}
```

Esta prueba verifica una restricción única real. En el proveedor en memoria, pasaría sin comprobar nada.

## Aislar las pruebas

Compartir la base de datos significa que los datos de una prueba pueden afectar a otra. Tienes varias opciones:

**Transacción con rollback.** Es rápido y sencillo, pero no sirve si el código bajo prueba usa sus propias transacciones o varias conexiones.

**Limpiar con Respawn.** Borra los datos de todas las tablas respetando las claves foráneas, y es rápido:

```csharp
private Respawner _limpiador = null!;

public async Task InitializeAsync()
{
    await _contenedor.StartAsync();
    // ... migraciones

    await using var conexion = new NpgsqlConnection(CadenaDeConexion);
    await conexion.OpenAsync();

    _limpiador = await Respawner.CreateAsync(conexion, new RespawnerOptions
    {
        DbAdapter = DbAdapter.Postgres,
        SchemasToInclude = ["public"],
        TablesToIgnore = ["__EFMigrationsHistory"],
    });
}

public async Task ReiniciarAsync()
{
    await using var conexion = new NpgsqlConnection(CadenaDeConexion);
    await conexion.OpenAsync();
    await _limpiador.ResetAsync(conexion);
}
```

Llámalo al inicio de cada prueba. Las pruebas de una misma colección de xUnit se ejecutan en serie, lo que evita pisarse.

**Datos únicos por prueba.** Cada una crea su propio inquilino o cliente. Esto permite ejecutar en paralelo, y es el enfoque más escalable si tu dominio lo permite.

## Con la API completa

Se combina muy bien con `WebApplicationFactory`, para probar desde la petición HTTP hasta la base de datos:

```csharp
public sealed class ApiFactory(string cadena) : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder) =>
        builder.UseSetting("ConnectionStrings:Principal", cadena);
}
```

## Otros servicios

También hay módulos para Redis, RabbitMQ, Elasticsearch o SQL Server, por lo que puedes probar la integración con el mismo enfoque:

```csharp
var redis = new RedisBuilder().WithImage("redis:7-alpine").Build();
```

## En CI

Los ejecutores de GitHub Actions con Linux ya tienen Docker, así que funciona sin más:

```yaml
- run: dotnet test -c Release
```

En Jenkins o en otros entornos con contenedores anidados, debes permitir el acceso a Docker. Hazlo con cuidado: dar acceso al socket de Docker equivale prácticamente a dar acceso de administrador a la máquina.

## Mantener el tiempo bajo control

- Comparte el contenedor entre pruebas, y no lo crees para cada una.
- Mantén una pirámide razonable: las reglas de dominio con pruebas unitarias, rápidas, y estas para lo que dependa de SQL.
- Si usas el proveedor en memoria, retíralo poco a poco: da más trabajo mantener dos comportamientos.
- Reutiliza imágenes en CI, para no tener que descargarlas cada vez.

## Referencias

- [Testcontainers para .NET](https://dotnet.testcontainers.org/)
- [Respawn](https://github.com/jbogard/Respawn)
- [Estrategias de prueba en EF Core](https://learn.microsoft.com/ef/core/testing/choosing-a-testing-strategy)
