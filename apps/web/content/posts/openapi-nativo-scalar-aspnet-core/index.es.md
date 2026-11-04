---
title: "OpenAPI nativo en ASP.NET Core: cómo sustituir Swashbuckle y usar Scalar"
seoTitle: "OpenAPI nativo y Scalar en ASP.NET Core"
description: "Generar el documento OpenAPI con Microsoft.AspNetCore.OpenApi, publicar una interfaz con Scalar y exportar el contrato al compilar para usarlo en CI y en el frontend."
date: 2025-08-04
tags: [".NET", "ASP.NET Core", "OpenAPI"]
---

Desde .NET 9, las plantillas de ASP.NET Core ya no incluyen Swashbuckle. En su lugar, el framework genera por sí mismo el documento OpenAPI con `Microsoft.AspNetCore.OpenApi`. Lo que desaparece es la interfaz: ya no viene Swagger UI de serie.

## Generar el documento

```csharp
builder.Services.AddOpenApi();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi(); // sirve /openapi/v1.json
}
```

Con esto ya tienes el JSON. La generación usa los metadatos de los endpoints, así que su calidad depende de lo bien que declares las respuestas.

## Una interfaz con Scalar

El documento es lo importante; la interfaz, intercambiable. Scalar es una alternativa moderna con un paquete oficial para .NET:

```bash
dotnet add package Scalar.AspNetCore
```

```csharp
using Scalar.AspNetCore;

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.MapScalarApiReference(); // sirve /scalar
}
```

También puedes mantener Swagger UI si el equipo lo prefiere: basta con apuntar a `/openapi/v1.json`.

## Describir bien las respuestas

Si el documento no describe las respuestas de error, el cliente generado tampoco las conocerá:

```csharp
app.MapGet("/clientes/{id:int}", Obtener)
   .WithName("ObtenerCliente")
   .WithSummary("Obtiene un cliente por su identificador")
   .Produces<ClienteDto>()
   .ProducesProblem(StatusCodes.Status404NotFound);
```

Con `TypedResults` y `Results<Ok<T>, NotFound>`, la firma ya aporta esa información sin atributos adicionales. El `operationId` que produce `WithName` importa porque muchos generadores lo usan para nombrar las funciones del cliente.

## Personalizar con transformadores

Los transformadores modifican el documento generado. Por ejemplo, para añadir información general:

```csharp
builder.Services.AddOpenApi(options =>
{
    options.AddDocumentTransformer((document, context, ct) =>
    {
        document.Info.Title = "API de Facturación";
        document.Info.Contact = new() { Email = "equipo@ejemplo.com" };
        return Task.CompletedTask;
    });
});
```

También existen transformadores por operación y por esquema, útiles para declarar seguridad o ajustar tipos concretos.

## Exportar el contrato al compilar

Para usar el contrato en CI o generar clientes sin arrancar la aplicación, añade este paquete:

```bash
dotnet add package Microsoft.Extensions.ApiDescription.Server
```

```xml
<PropertyGroup>
  <OpenApiDocumentsDirectory>$(MSBuildProjectDirectory)/openapi</OpenApiDocumentsDirectory>
</PropertyGroup>
```

Al compilar se escribe el documento en ese directorio, y lo puedes versionar. Los cambios en el contrato aparecen en cada pull request como un diff normal, visibles para quien revisa.

Una advertencia: la generación ejecuta el punto de entrada de la aplicación. Si `Program.cs` conecta con servicios al arrancar, puede fallar en CI. La comprobación `Assembly.GetEntryAssembly()?.GetName().Name == "GetDocument.Insider"` sirve para saltarse ese trabajo.

## Cuándo seguir con Swashbuckle

No hay ninguna urgencia en migrar si Swashbuckle funciona y dependes de sus filtros. Conviene planificarlo si necesitas soporte para las últimas versiones de OpenAPI, si quieres reducir dependencias o si estás arrancando un proyecto nuevo.

## Publicar o no en producción

Publicar el documento en producción no es malo en sí mismo si la API ya es pública. Para una API interna, sí conviene exigir autenticación o generar el contrato solo en CI, para no exponer rutas que un atacante podría aprovechar.

## Referencias

- [Generar documentos OpenAPI](https://learn.microsoft.com/aspnet/core/fundamentals/openapi/aspnetcore-openapi)
- [Scalar para ASP.NET Core](https://github.com/scalar/scalar/tree/main/integrations/aspnetcore)
