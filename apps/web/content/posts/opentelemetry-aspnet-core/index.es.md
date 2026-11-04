---
title: "OpenTelemetry en ASP.NET Core: trazas, métricas y logs desde el primer día"
seoTitle: "OpenTelemetry en ASP.NET Core"
description: "Cómo instrumentar una API ASP.NET Core con OpenTelemetry: trazas automáticas, spans propios, métricas, propagación entre servicios y envío a un colector con OTLP."
date: 2025-11-27
tags: [".NET", "Observabilidad", "OpenTelemetry"]
---

Cuando un usuario dice que algo va lento y la petición cruza cuatro servicios, los logs de cada uno no bastan para saber dónde se ha ido el tiempo. Una traza distribuida responde a esa pregunta. OpenTelemetry es el estándar neutral para generarlas, y evita casarte con un proveedor.

## Las tres señales

- **Trazas**: el recorrido de una petición, con el tiempo de cada paso.
- **Métricas**: números agregados: peticiones por segundo, latencia, errores.
- **Logs**: eventos concretos, ahora vinculados a la traza que los generó.

Se complementan. Las métricas avisan de que algo va mal, las trazas muestran dónde, y los logs explican el porqué.

## Instalación

```bash
dotnet add package OpenTelemetry.Extensions.Hosting
dotnet add package OpenTelemetry.Exporter.OpenTelemetryProtocol
dotnet add package OpenTelemetry.Instrumentation.AspNetCore
dotnet add package OpenTelemetry.Instrumentation.Http
dotnet add package OpenTelemetry.Instrumentation.Runtime
dotnet add package Npgsql.OpenTelemetry
```

```csharp
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("api-pedidos"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddNpgsql()
        .AddSource("Pedidos"))
    .WithMetrics(m => m
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddRuntimeInstrumentation()
        .AddMeter("Pedidos"))
    .WithLogging()
    .UseOtlpExporter();
```

Con esto ya tienes spans automáticos para cada petición entrante, cada llamada HTTP de salida y cada consulta SQL, sin tocar tu código.

La dirección del destino suele venir del entorno:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

## Propagación entre servicios

Las llamadas con `HttpClient` añaden automáticamente la cabecera `traceparent`, y el servicio receptor continúa la misma traza. No hay que hacer nada más, siempre que todos los servicios estén instrumentados.

Con las colas de mensajes, esto no ocurre solo, salvo que tu librería lo incluya: debes guardar el contexto en el mensaje al publicar y restaurarlo al consumirlo. De lo contrario, la traza se corta justo donde más la necesitas.

## Spans propios

Las operaciones automáticas no conocen tu dominio. .NET usa `ActivitySource` para esto:

```csharp
public sealed class ConfirmarPedido(AppDbContext db)
{
    private static readonly ActivitySource Fuente = new("Pedidos");

    public async Task EjecutarAsync(int id, CancellationToken ct)
    {
        using var actividad = Fuente.StartActivity("ConfirmarPedido");
        actividad?.SetTag("pedido.id", id);

        try
        {
            await ValidarYGuardarAsync(id, ct);
        }
        catch (Exception ex)
        {
            actividad?.SetStatus(ActivityStatusCode.Error, ex.Message);
            actividad?.AddException(ex);
            throw;
        }
    }
}
```

Fíjate en el `?.`: `StartActivity` devuelve `null` si nadie está escuchando, de modo que el coste es casi cero. El nombre de la fuente debe coincidir con `AddSource`, o sus spans no se exportarán. Es el error más habitual.

## Métricas propias

```csharp
public sealed class MetricasPedidos
{
    private readonly Counter<long> _confirmados;
    private readonly Histogram<double> _importe;

    public MetricasPedidos(IMeterFactory factoria)
    {
        var medidor = factoria.Create("Pedidos");
        _confirmados = medidor.CreateCounter<long>("pedidos.confirmados");
        _importe = medidor.CreateHistogram<double>("pedidos.importe", unit: "EUR");
    }

    public void PedidoConfirmado(decimal importe, string canal)
    {
        _confirmados.Add(1, new KeyValuePair<string, object?>("canal", canal));
        _importe.Record((double)importe);
    }
}
```

Cuidado con la cardinalidad. Una etiqueta como `canal` tiene pocos valores, pero si usas `usuario.id` o `pedido.id` en una métrica, se creará una serie por valor, lo que dispara el consumo de memoria y los costes. Esos datos van en las trazas, no en las métricas.

## El colector

Puedes enviar directamente a tu sistema, aunque es mejor pasar por un colector de OpenTelemetry:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch: {}
  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  otlp/elastic:
    endpoint: https://apm.ejemplo.com:8200
    headers:
      Authorization: "Bearer ${env:ELASTIC_APM_TOKEN}"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/elastic]
```

Tu aplicación no sabe adónde van los datos, y cambiar de proveedor no requiere desplegarla de nuevo. Además, el colector puede filtrar datos, añadir información y aplicar muestreo.

## Muestreo

Guardar el 100 % de las trazas en un sistema con mucho tráfico es muy caro:

```bash
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
```

Esto conserva el 10 %, respetando la decisión del servicio anterior, para que no queden trazas incompletas. El problema es que puedes descartar justo lo interesante. El *tail sampling* en el colector decide al final, cuando ya se sabe si hubo errores o latencia alta, a cambio de más memoria y complejidad.

## Datos sensibles

La instrumentación automática puede registrar consultas SQL y URLs. Revisa lo que se envía, y evita incluir datos personales en atributos. Un endpoint como `/usuarios/ana@ejemplo.com` acabaría en tus trazas.

## Empezar

No hace falta instrumentar todo el sistema a la vez. Conecta dos servicios, y haz que el equipo use la traza para resolver un problema real. Cuando se vea lo útil que es, el resto llega por sí solo.

En desarrollo, puedes usar el panel de .NET Aspire de forma independiente, o Jaeger en un contenedor, para ver las trazas sin ningún proveedor.

## Referencias

- [OpenTelemetry para .NET](https://opentelemetry.io/docs/languages/dotnet/)
- [Observabilidad en .NET](https://learn.microsoft.com/dotnet/core/diagnostics/observability-with-otel)
- [Convenciones semánticas](https://opentelemetry.io/docs/concepts/semantic-conventions/)
