---
title: "HybridCache en ASP.NET Core: caché en dos niveles sin estampidas"
seoTitle: "HybridCache en ASP.NET Core"
description: "Cómo usar HybridCache en .NET para combinar memoria local y Redis, evitar estampidas de caché e invalidar por etiquetas con muy poco código."
date: 2025-07-07
tags: [".NET", "ASP.NET Core", "Rendimiento"]
---

El patrón típico de caché en .NET siempre ha sido el mismo: comprobar si la clave existe, consultar el origen si no, guardar el resultado. Es poco código, pero tiene un problema: si una clave muy usada expira, cientos de peticiones simultáneas ven el hueco y todas van a la base de datos. Es la llamada estampida de caché.

`HybridCache`, disponible desde .NET 9 con el paquete `Microsoft.Extensions.Caching.Hybrid`, resuelve esto y unifica los dos niveles de caché.

## Instalación

```csharp
builder.Services.AddHybridCache(options =>
{
    options.DefaultEntryOptions = new HybridCacheEntryOptions
    {
        Expiration = TimeSpan.FromMinutes(10),
        LocalCacheExpiration = TimeSpan.FromMinutes(1),
    };
});

// Opcional: segundo nivel
builder.Services.AddStackExchangeRedisCache(options =>
    options.Configuration = builder.Configuration.GetConnectionString("Redis"));
```

Si hay un `IDistributedCache` registrado, `HybridCache` lo usa como segundo nivel. Si no lo hay, funciona solo en memoria y puedes añadir Redis después sin tocar el código que la consume.

## Usarla

Todo se reduce a un método:

```csharp
public sealed class TarifasService(HybridCache cache, AppDbContext db)
{
    public async Task<Tarifa?> ObtenerAsync(int id, CancellationToken ct) =>
        await cache.GetOrCreateAsync(
            $"tarifa:{id}",
            async token => await db.Tarifas
                .AsNoTracking()
                .FirstOrDefaultAsync(t => t.Id == id, token),
            tags: ["tarifas"],
            cancellationToken: ct);
}
```

Mientras una petición calcula el valor de una clave, las demás que piden la misma clave esperan a ese resultado. Para cada instancia, la función de carga se ejecuta una vez. Esto hace casi innecesario escribir bloqueos propios.

## Los dos niveles

- **L1, memoria local**: muy rápida, propia de cada instancia.
- **L2, distribuida**: compartida entre instancias y conservada en un reinicio.

`LocalCacheExpiration` suele ser más corta que `Expiration`, porque la memoria local de otras réplicas no se entera de los cambios. Ese valor es, en la práctica, el tiempo máximo que una réplica podría servir un dato obsoleto después de invalidarlo en otra.

## Invalidar

Se puede borrar por clave o por etiqueta:

```csharp
await cache.RemoveAsync($"tarifa:{id}", ct);
await cache.RemoveByTagAsync("tarifas", ct);
```

La invalidación por etiqueta evita tener que recordar todas las claves derivadas de una entidad, algo muy difícil de mantener.

## Qué vigilar

**Claves con datos de usuario.** Si el resultado depende del usuario o del inquilino, la clave debe incluirlo. Olvidarlo significa servir los datos de una persona a otra.

**Objetos mutables.** En el nivel local, lo habitual es que cada lectura deserialice una copia, salvo que el tipo sea `sealed` y esté marcado con `[ImmutableObject(true)]`. En ese caso se reutiliza la misma instancia, así que no la modifiques después de obtenerla.

**Datos de gran tamaño.** Existen límites configurables de tamaño máximo por entrada. Las entradas que los superan no se almacenan y la aplicación no recibe ningún error, así que mide antes de asumir que algo está en caché.

**Serialización.** Por defecto usa `System.Text.Json`. Si necesitas algo más compacto en el segundo nivel, puedes registrar otro serializador.

## Cuándo no merece la pena

Los datos que cambian en cada petición o que ya se leen en poco tiempo no ganan nada. Antes de añadir caché, comprueba que no estás escondiendo una consulta sin índice: arreglar la causa es más barato que mantener una capa más.

## Referencias

- [Biblioteca HybridCache en ASP.NET Core](https://learn.microsoft.com/aspnet/core/performance/caching/hybrid)
