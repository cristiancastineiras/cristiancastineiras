---
title: "Errores HTTP coherentes con ProblemDetails en ASP.NET Core"
seoTitle: "ProblemDetails en ASP.NET Core"
description: "Cómo devolver errores uniformes en una API ASP.NET Core con ProblemDetails e IExceptionHandler, sin filtrar detalles internos ni repetir código."
date: 2025-01-27
tags: [".NET", "ASP.NET Core", "REST"]
---

Una API sin una convención de errores acaba devolviendo de todo: texto plano, objetos con forma distinta en cada controlador y, en el peor caso, una traza de pila. El cliente tiene que escribir un caso para cada formato.

La RFC 9457 define un formato estándar, *Problem Details*, y ASP.NET Core lo trae de serie.

## El formato

```json
{
  "type": "https://api.ejemplo.com/errores/saldo-insuficiente",
  "title": "Saldo insuficiente",
  "status": 422,
  "detail": "La cuenta no tiene saldo para este cargo.",
  "instance": "/cuentas/42/cargos"
}
```

Se sirve con `application/problem+json` y admite campos adicionales, como un identificador de traza o un código de error propio.

## Activarlo

```csharp
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();
```

Con esto, una excepción no controlada y las respuestas de error sin cuerpo, como un 404 de ruta inexistente, pasan a devolver ese formato.

## Convertir excepciones en respuestas

Desde .NET 8, `IExceptionHandler` centraliza esta traducción:

```csharp
public sealed class ReglaDeNegocioHandler(IProblemDetailsService problemas)
    : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext context, Exception exception, CancellationToken ct)
    {
        if (exception is not ReglaDeNegocioException regla)
            return false;

        context.Response.StatusCode = StatusCodes.Status422UnprocessableEntity;

        return await problemas.TryWriteAsync(new ProblemDetailsContext
        {
            HttpContext = context,
            Exception = exception,
            ProblemDetails =
            {
                Title = "La operación no cumple una regla de negocio",
                Detail = regla.Message,
                Type = "https://api.ejemplo.com/errores/regla-de-negocio",
            },
        });
    }
}
```

```csharp
builder.Services.AddExceptionHandler<ReglaDeNegocioHandler>();
```

Al devolver `false`, el siguiente manejador registrado tiene su oportunidad. Si ninguno la trata, la respuesta es un 500 genérico. Es lo que quieres.

## No filtrar información

`Detail` con `exception.Message` solo es seguro para excepciones que has escrito tú y cuyo mensaje está pensado para el cliente. El mensaje de una `SqlException` puede incluir nombres de tablas o fragmentos de consultas.

La regla: detalles completos en los logs, información mínima en la respuesta. Para unir ambos mundos, añade el identificador de traza:

```csharp
builder.Services.AddProblemDetails(options =>
{
    options.CustomizeProblemDetails = context =>
    {
        context.ProblemDetails.Extensions["traceId"] =
            Activity.Current?.Id ?? context.HttpContext.TraceIdentifier;
    };
});
```

Si un usuario reporta un error con ese identificador, puedes encontrar la entrada exacta en los logs sin haberle mostrado nada interno.

## Errores de validación

Los controladores con `[ApiController]` devuelven automáticamente un `ValidationProblemDetails` con los errores por campo. En Minimal APIs, puedes devolver lo mismo con:

```csharp
return Results.ValidationProblem(new Dictionary<string, string[]>
{
    ["email"] = ["El correo no tiene un formato válido."],
});
```

Eso permite al frontend asociar cada mensaje a su campo sin analizar textos.

## Códigos estables para el cliente

Un cliente no debería decidir nada analizando `title` o `detail`, porque esos textos pueden cambiar o traducirse. Usa `type` como identificador estable, o una extensión como `code`. Documéntalos en tu especificación OpenAPI para que formen parte del contrato.

## Referencias

- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457)
- [Control de errores en ASP.NET Core](https://learn.microsoft.com/aspnet/core/fundamentals/error-handling)
