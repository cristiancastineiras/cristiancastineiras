---
title: "HttpClient en .NET: IHttpClientFactory y resiliencia sin reinventar nada"
seoTitle: "IHttpClientFactory y resiliencia"
description: "Por qué no debes crear HttpClient a mano y cómo añadir reintentos, tiempos límite y circuit breaker en .NET con Microsoft.Extensions.Http.Resilience."
date: 2025-05-19
tags: [".NET", "ASP.NET Core", "Resiliencia"]
---

`HttpClient` tiene dos formas clásicas de usarse mal. Crear una instancia por petición agota los sockets bajo carga. Mantener una sola instancia estática para siempre evita eso, pero puede dejar de ver cambios de DNS.

`IHttpClientFactory` existe para resolver ambos problemas gestionando el ciclo de vida de los manejadores que hay por debajo.

## Clientes tipados

La forma que suele quedar más limpia es un cliente tipado, una clase que encapsula las llamadas a una API concreta:

```csharp
public sealed class CatastroClient(HttpClient http)
{
    public Task<Parcela?> ObtenerAsync(string referencia, CancellationToken ct) =>
        http.GetFromJsonAsync<Parcela>($"parcelas/{referencia}", ct);
}
```

```csharp
builder.Services.AddHttpClient<CatastroClient>(client =>
{
    client.BaseAddress = new Uri("https://api.ejemplo.com/");
    client.Timeout = Timeout.InfiniteTimeSpan; // lo controla la capa de resiliencia
});
```

El resto de la aplicación depende de `CatastroClient` y no sabe nada de URLs ni de cabeceras.

Una advertencia: no guardes un cliente tipado dentro de un singleton. Quedaría capturado el `HttpClient` y, con él, el manejador, perdiendo la rotación que hace la factoría.

## Resiliencia estándar en una línea

El paquete `Microsoft.Extensions.Http.Resilience`, construido sobre Polly, añade una configuración razonable sin tener que diseñarla:

```csharp
builder.Services.AddHttpClient<CatastroClient>(/* ... */)
    .AddStandardResilienceHandler();
```

Ese manejador encadena limitación de concurrencia, tiempo total, reintentos con espera exponencial, circuit breaker y tiempo por intento.

Es un buen punto de partida, y se pueden ajustar los valores:

```csharp
.AddStandardResilienceHandler(options =>
{
    options.Retry.MaxRetryAttempts = 2;
    options.AttemptTimeout.Timeout = TimeSpan.FromSeconds(3);
    options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(10);
});
```

## Qué es seguro reintentar

Los reintentos son la parte más peligrosa. Un `POST` que ha fallado por tiempo de espera puede haberse procesado igualmente en el servidor. Reintentarlo puede duplicar un pago o un registro.

Reintenta sin más las operaciones idempotentes (`GET`, `PUT`, `DELETE` bien implementados). Para el resto, desactiva el reintento o exige una clave de idempotencia. El handler permite excluir los métodos inseguros:

```csharp
options.Retry.DisableForUnsafeHttpMethods();
```

## Reintentos que no empeoran una caída

Si un servicio está saturado, reintentar desde todos los clientes a la vez multiplica su carga. Por eso importan dos detalles que la configuración estándar ya aplica:

- espera exponencial con *jitter*, para que los clientes no se sincronicen;
- circuit breaker, para dejar de insistir cuando casi todo falla.

Revisa también cómo se multiplican los reintentos en una cadena. Tres reintentos en cada uno de tres servicios encadenados pueden convertir una petición en decenas de llamadas contra el último.

## Probarlo

No hace falta un servidor para probar el comportamiento del cliente. Se puede sustituir el manejador:

```csharp
sealed class Falla503(int veces) : HttpMessageHandler
{
    private int _llamadas;

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken ct) =>
        Task.FromResult(new HttpResponseMessage(
            ++_llamadas <= veces ? HttpStatusCode.ServiceUnavailable : HttpStatusCode.OK));
}
```

## Referencias

- [Crear solicitudes HTTP con IHttpClientFactory](https://learn.microsoft.com/aspnet/core/fundamentals/http-requests)
- [Aplicaciones HTTP resilientes](https://learn.microsoft.com/dotnet/core/resilience/http-resilience)
