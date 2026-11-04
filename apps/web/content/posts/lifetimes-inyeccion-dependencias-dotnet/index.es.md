---
title: "Singleton, scoped y transient: los errores de lifetime que rompen una API .NET"
seoTitle: "Lifetimes de dependencias en .NET"
description: "Qué es una dependencia cautiva, por qué un DbContext dentro de un singleton acaba mal y cómo detectar errores de lifetime en .NET antes de desplegar."
date: 2025-07-14
tags: [".NET", "ASP.NET Core", "Arquitectura"]
---

La inyección de dependencias de .NET es sencilla de usar y fácil de usar mal. Los errores de lifetime no fallan siempre: aparecen como datos de otro usuario, excepciones intermitentes o memoria que no deja de crecer.

## Los tres lifetimes

- **Transient**: una instancia nueva cada vez que se resuelve.
- **Scoped**: una instancia por ámbito; en ASP.NET Core, por petición HTTP.
- **Singleton**: una instancia para toda la aplicación.

## La dependencia cautiva

Una regla resume casi todos los problemas: un servicio no debe depender de otro con una vida más corta.

```csharp
builder.Services.AddSingleton<CacheDeTarifas>();
builder.Services.AddScoped<AppDbContext>();

public sealed class CacheDeTarifas(AppDbContext db) { /* ... */ }
```

`CacheDeTarifas` vive para siempre y retiene el `DbContext` de la primera petición. Ese contexto no es seguro entre hilos, acumula entidades rastreadas y su conexión no se comporta como se espera. Se ha convertido en un cautivo.

Lo mismo ocurre con el estado de usuario: un singleton que captura un servicio scoped con datos del usuario actual puede devolver datos de otra persona.

## Cómo consumir algo scoped desde un singleton

Crea un ámbito explícito cuando lo necesites:

```csharp
public sealed class CacheDeTarifas(IServiceScopeFactory scopes)
{
    public async Task RefrescarAsync(CancellationToken ct)
    {
        await using var scope = scopes.CreateAsyncScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        _tarifas = await db.Tarifas.AsNoTracking().ToListAsync(ct);
    }

    private IReadOnlyList<Tarifa> _tarifas = [];
}
```

Para `DbContext`, `AddDbContextFactory` es otra opción directa: inyectas la factoría y creas un contexto por operación.

## Que el contenedor te avise

El proveedor de servicios sabe validar estos errores:

```csharp
builder.Host.UseDefaultServiceProvider(options =>
{
    options.ValidateScopes = true;
    options.ValidateOnBuild = true;
});
```

- `ValidateScopes` lanza una excepción si se resuelve un servicio scoped desde el ámbito raíz.
- `ValidateOnBuild` comprueba al arrancar que todos los servicios registrados se pueden construir.

En el entorno `Development` ya vienen activadas. Merece la pena activarlas también en los tests de integración o en otros entornos, porque un fallo al arrancar se diagnostica mejor que uno intermitente en producción.

Hay un límite: `ValidateOnBuild` no puede analizar lo que se resuelve de forma dinámica con `GetService`.

## Transient y `IDisposable`

Si un servicio transient implementa `IDisposable` y se resuelve desde el contenedor raíz, el contenedor guarda una referencia para eliminarlo al final. Si eso ocurre repetidamente en un singleton, la memoria crece sin que nada lo libere. Resuélvelo dentro de un ámbito que termine.

## Elegir lifetime

Una forma práctica de decidir:

| Tipo de servicio | Lifetime habitual |
|---|---|
| Sin estado y seguro entre hilos | Singleton |
| `DbContext`, unidad de trabajo, datos del usuario | Scoped |
| Ligero, con estado propio y no compartible | Transient |

Ante la duda, un servicio sin estado puede ser singleton siempre que todas sus dependencias también lo sean.

## Referencias

- [Inyección de dependencias en .NET](https://learn.microsoft.com/dotnet/core/extensions/dependency-injection)
- [Directrices de inyección de dependencias](https://learn.microsoft.com/dotnet/core/extensions/dependency-injection-guidelines)
