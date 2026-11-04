---
title: "Logs estructurados en .NET con Serilog: que sirvan para investigar un incidente"
seoTitle: "Logs estructurados con Serilog en .NET"
description: "Cómo configurar Serilog en ASP.NET Core para generar logs consultables: plantillas de mensaje, contexto de petición, niveles por categoría y datos que nunca deben registrarse."
date: 2025-07-10
tags: [".NET", "Observabilidad", "Elasticsearch"]
---

Un log en texto libre es fácil de escribir y difícil de usar. Cuando hay un incidente, nadie quiere escribir expresiones regulares para extraer el número de pedido de millones de líneas. Un log estructurado guarda los datos como campos, y permite preguntar directamente: «todos los errores del pedido 8123».

## Plantillas, no interpolación

Esta es la distinción más importante:

```csharp
// Mal: el valor se pierde dentro del texto
logger.LogInformation($"Pedido {pedidoId} confirmado en {ms} ms");

// Bien: PedidoId y Duracion quedan como campos
logger.LogInformation("Pedido {PedidoId} confirmado en {Duracion} ms", pedidoId, ms);
```

Con la plantilla, además, todas las líneas comparten el mismo mensaje base, y es fácil agrupar y contar. El analizador CA2254 avisa si usas interpolación.

## Configurar Serilog

```bash
dotnet add package Serilog.AspNetCore
```

```csharp
using Serilog;
using Serilog.Formatting.Compact;

builder.Host.UseSerilog((context, services, configuration) => configuration
    .ReadFrom.Configuration(context.Configuration)
    .ReadFrom.Services(services)
    .Enrich.FromLogContext()
    .Enrich.WithProperty("Servicio", "api-pedidos")
    .WriteTo.Console(new RenderedCompactJsonFormatter()));
```

En un contenedor, escribe JSON a la salida estándar. De recogerlo y enviarlo se encarga otro componente, como Filebeat o un colector de OpenTelemetry. Evita que tu aplicación dependa de que Elasticsearch esté disponible.

## Niveles por categoría

El ruido del framework suele ser el mayor problema:

```json
{
  "Serilog": {
    "MinimumLevel": {
      "Default": "Information",
      "Override": {
        "Microsoft.AspNetCore": "Warning",
        "Microsoft.EntityFrameworkCore.Database.Command": "Warning",
        "System.Net.Http.HttpClient": "Warning"
      }
    }
  }
}
```

Y una sola línea por petición, en vez de varias:

```csharp
app.UseSerilogRequestLogging(options =>
{
    options.EnrichDiagnosticContext = (contexto, http) =>
    {
        contexto.Set("Usuario", http.User.FindFirst("sub")?.Value);
    };
});
```

## Contexto en cada línea

Con `BeginScope` o `LogContext`, todo lo registrado dentro de un bloque lleva esos campos, sin tener que pasarlos a mano:

```csharp
using (LogContext.PushProperty("PedidoId", pedido.Id))
{
    await ProcesarAsync(pedido, ct);
}
```

Lo más valioso es incluir el identificador de traza. Serilog añade `TraceId` y `SpanId` cuando hay una actividad en curso. Permite saltar de un log a la traza completa, y a todo lo ocurrido en esa petición.

## Niveles con criterio

- **Error**: algo ha fallado, y alguien debería mirarlo. Si un error no requiere ninguna acción, no debería tener este nivel.
- **Warning**: situación inesperada, pero controlada: un reintento, una degradación.
- **Information**: hechos de negocio y del ciclo de vida. Pedido confirmado, servicio iniciado.
- **Debug**: detalles para diagnóstico, desactivados en producción por defecto.

Un patrón muy común: registrar la excepción en cada capa antes de relanzarla. El mismo error aparecerá cinco veces. Regístralo una sola vez, donde se gestiona.

```csharp
try
{
    await EnviarAsync(mensaje, ct);
}
catch (HttpRequestException ex)
{
    logger.LogError(ex, "No se pudo enviar el mensaje {MensajeId}", mensaje.Id);
    throw; // quien lo gestione no volverá a registrarlo
}
```

Pasa siempre la excepción como primer argumento, para conservar la pila completa.

## Lo que nunca debe aparecer

Los logs suelen tener menos controles de acceso que la base de datos, y se conservan mucho tiempo:

- contraseñas, tokens y cadenas de conexión;
- datos personales, salvo que los necesites de verdad;
- cuerpos completos de peticiones y respuestas;
- números de tarjeta o de cuentas.

Ten cuidado con el operador `@`, que serializa objetos enteros:

```csharp
// Puede filtrar más de lo que parece
logger.LogInformation("Usuario creado {@Usuario}", usuario);

// Solo lo necesario
logger.LogInformation("Usuario creado {UsuarioId}", usuario.Id);
```

Si un campo con datos personales entra en los logs, es difícil de eliminar después, y puede convertirse en un problema de cumplimiento normativo.

## Rendimiento

Registrar tiene un coste. En rutas muy frecuentes, el generador de código `LoggerMessage` evita asignaciones y comprueba las plantillas en compilación:

```csharp
public static partial class Registros
{
    [LoggerMessage(Level = LogLevel.Information,
        Message = "Pedido {PedidoId} confirmado en {Duracion} ms")]
    public static partial void PedidoConfirmado(
        this ILogger logger, int pedidoId, double duracion);
}
```

El volumen también es un coste: almacenar logs cuesta dinero. Pregúntate si alguien utilizará realmente cada línea.

## ¿Serilog o el logger integrado?

`Microsoft.Extensions.Logging` ya soporta plantillas estructuradas y JSON a la consola con `AddJsonConsole()`. Si no necesitas sus *sinks* y su enriquecimiento, es probable que el registro integrado junto a OpenTelemetry sea suficiente, con una dependencia menos.

Tu código solo debería depender de `ILogger<T>`, sea cual sea la implementación, y así podrás cambiarla sin tocar nada.

## Referencias

- [Serilog](https://serilog.net/)
- [Serilog.AspNetCore](https://github.com/serilog/serilog-aspnetcore)
- [Logging de alto rendimiento](https://learn.microsoft.com/dotnet/core/extensions/high-performance-logging)
