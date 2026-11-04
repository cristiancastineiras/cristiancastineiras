---
title: "Health checks en ASP.NET Core: liveness y readiness bien separados"
seoTitle: "Health checks en ASP.NET Core"
description: "Cómo diseñar health checks en ASP.NET Core: separar liveness y readiness, qué dependencias comprobar y qué errores provocan reinicios en cadena en producción."
date: 2025-06-02
tags: [".NET", "ASP.NET Core", "Observabilidad"]
---

Un endpoint `/health` que siempre responde 200 no comprueba nada. Uno que consulta todas las dependencias puede ser peor: si la base de datos tiene un mal momento, el orquestador reinicia todas las réplicas y una degradación se convierte en una caída completa.

La clave es que hay dos preguntas distintas.

## Dos preguntas, dos endpoints

- **Liveness**: ¿el proceso está vivo o bloqueado sin remedio? Si falla, reiniciar puede ayudar.
- **Readiness**: ¿puede atender peticiones ahora? Si falla, se le deja de enviar tráfico, pero no se reinicia.

Una base de datos caída nunca debe hacer fallar el *liveness*. Reiniciar la API no arregla la base de datos.

## Implementación

```csharp
builder.Services.AddHealthChecks()
    .AddCheck<BaseDeDatosHealthCheck>("base-de-datos", tags: ["ready"]);

var app = builder.Build();

app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false, // ninguna dependencia: solo que el proceso responde
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready"),
});
```

Un check propio es una clase pequeña:

```csharp
public sealed class BaseDeDatosHealthCheck(AppDbContext db) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context, CancellationToken ct = default)
    {
        return await db.Database.CanConnectAsync(ct)
            ? HealthCheckResult.Healthy()
            : HealthCheckResult.Unhealthy("Sin conexión con la base de datos");
    }
}
```

Para EF Core existe `AddDbContextCheck<AppDbContext>()` en el paquete `Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore`, que evita escribir esta clase.

## Qué comprobar en readiness

Solo aquello sin lo cual esta instancia no puede servir su función principal. Si una dependencia opcional, como un servicio de recomendaciones, se cae, la API debería degradarse, no salir del balanceador.

Pregúntate también qué pasa si la dependencia falla para todas las réplicas al mismo tiempo. Si todas dejan de estar listas, el balanceador no tiene a quién enviar tráfico y los clientes reciben 503 aunque parte de la API podría haber funcionado. A veces lo mejor es que el check no incluya esa dependencia.

## Mantenerlos ligeros

Estos endpoints se llaman cada pocos segundos desde varios sitios. Un check que ejecuta una consulta costosa añade carga precisamente al sistema que está vigilando. Por eso conviene usar `SELECT 1` o algo equivalente, añadir un tiempo límite y, si la comprobación es cara, guardar el último resultado en memoria durante unos segundos.

Si alguna comprobación se vuelve lenta, también lo será el endpoint, y el orquestador la contará como un fallo.

## Exposición

Una respuesta detallada puede revelar versiones, nombres de hosts o topología. Para el orquestador basta con el código de estado y un texto corto. Si quieres más detalle para el equipo, publícalo en un puerto interno o con autorización, no en la API pública:

```csharp
app.MapHealthChecks("/health/ready")
   .RequireHost("*:8081");
```

## Relación con Kubernetes

Estos endpoints encajan directamente con `livenessProbe` y `readinessProbe`. Mantén esta correspondencia y revisa los umbrales de fallos, para que un pico puntual no reinicie un pod sano.

## Referencias

- [Comprobaciones de estado en ASP.NET Core](https://learn.microsoft.com/aspnet/core/host-and-deploy/health-checks)
