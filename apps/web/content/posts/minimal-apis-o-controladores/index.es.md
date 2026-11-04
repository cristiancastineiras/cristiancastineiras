---
title: "Minimal APIs o controladores en ASP.NET Core: cómo decidir sin dogmas"
seoTitle: "Minimal APIs o controladores"
description: "Comparativa práctica entre Minimal APIs y controladores en ASP.NET Core: organización, filtros, validación y rendimiento, con criterios para elegir en proyectos reales."
date: 2025-02-24
tags: [".NET", "ASP.NET Core", "Arquitectura"]
---

La elección entre Minimal APIs y controladores se presenta a menudo como una batalla entre lo moderno y lo antiguo. No lo es. Ambos modelos usan el mismo enrutado, los mismos middlewares y la misma inyección de dependencias. Lo que cambia es cómo organizas el código y qué te da hecho el framework.

## Mismo endpoint, dos estilos

```csharp
// Minimal API
app.MapGet("/clientes/{id:int}", async (int id, AppDbContext db, CancellationToken ct) =>
    await db.Clientes.FindAsync([id], ct) is { } cliente
        ? Results.Ok(cliente)
        : Results.NotFound());
```

```csharp
// Controlador
[ApiController]
[Route("clientes")]
public sealed class ClientesController(AppDbContext db) : ControllerBase
{
    [HttpGet("{id:int}")]
    public async Task<ActionResult<Cliente>> Obtener(int id, CancellationToken ct)
    {
        var cliente = await db.Clientes.FindAsync([id], ct);
        return cliente is null ? NotFound() : Ok(cliente);
    }
}
```

## Dónde se diferencian de verdad

**Dependencias por endpoint.** En Minimal APIs, cada manejador declara solo lo que necesita. En un controlador, el constructor acumula las dependencias de todas sus acciones.

**Filtros y convenciones.** MVC ofrece filtros de acción, de autorización y de resultado, además de convenciones globales. Minimal APIs tiene filtros de endpoint y grupos de rutas, algo más sencillos.

**Validación.** `[ApiController]` valida automáticamente el modelo. Minimal APIs no incluye esa validación automática, así que hay que hacerla con una librería o a mano.

**Funciones exclusivas.** *Model binding* muy personalizado, `OData` y ciertas integraciones siguen esperando controladores.

**Rendimiento.** Minimal APIs es algo más rápido porque hace menos trabajo. En una API que pasa la mayoría del tiempo esperando a la base de datos, esa diferencia rara vez es lo que decide.

## Organizar Minimal APIs para que escalen

El argumento de que no escalan viene de ponerlo todo en `Program.cs`. Con grupos y métodos de extensión, cada funcionalidad tiene su sitio:

```csharp
public static class ClientesEndpoints
{
    public static IEndpointRouteBuilder MapClientes(this IEndpointRouteBuilder app)
    {
        var grupo = app.MapGroup("/clientes")
            .WithTags("Clientes")
            .RequireAuthorization();

        grupo.MapGet("/{id:int}", Obtener);
        grupo.MapPost("/", Crear);

        return app;
    }

    private static async Task<Results<Ok<ClienteDto>, NotFound>> Obtener(
        int id, ClientesService servicio, CancellationToken ct) =>
        await servicio.ObtenerAsync(id, ct) is { } dto
            ? TypedResults.Ok(dto)
            : TypedResults.NotFound();
}
```

Dos ventajas de este estilo: los métodos estáticos se prueban sin levantar un servidor, y `TypedResults` documenta las respuestas en OpenAPI sin atributos adicionales.

## Cómo decidir

Yo elegiría Minimal APIs en un servicio nuevo o una API pequeña o mediana, sobre todo si se organiza por funcionalidades.

Mantendría controladores si:

- el proyecto ya los usa y funcionan, porque migrar por estética no aporta nada;
- dependes de filtros de MVC o de funciones como OData;
- el equipo tiene convenciones consolidadas alrededor de ellos.

También pueden convivir en la misma aplicación, así que el código nuevo puede usar otro estilo sin reescribir lo existente. Lo que sí evitaría es que cada desarrollador decida por su cuenta en un mismo módulo.

## Referencias

- [Elegir entre API basadas en controladores y API mínimas](https://learn.microsoft.com/aspnet/core/fundamentals/apis)
- [Referencia de API mínimas](https://learn.microsoft.com/aspnet/core/fundamentals/minimal-apis)
