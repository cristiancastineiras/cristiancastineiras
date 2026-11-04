---
title: "Cómo versionar una API REST sin romper a tus clientes"
seoTitle: "Versionar una API REST"
description: "Qué cambios rompen un contrato, cómo evolucionar una API sin subir de versión, y cuándo usar URL, cabecera o Asp.Versioning en ASP.NET Core."
date: 2025-09-22
tags: ["REST", "ASP.NET Core", "Arquitectura"]
---

La pregunta habitual es si la versión debe ir en la URL o en una cabecera. Hay otra más importante: ¿hace falta una versión nueva? Mantener dos versiones activas tiene un coste real, y muchos cambios se pueden desplegar sin que ningún cliente lo note.

## Qué rompe y qué no

Cambios compatibles, normalmente seguros:

- añadir un endpoint nuevo;
- añadir una propiedad opcional a una petición;
- añadir una propiedad a una respuesta, si los clientes toleran campos desconocidos.

Cambios incompatibles:

- eliminar o renombrar un campo o una ruta;
- cambiar un tipo o el formato de una fecha;
- hacer obligatorio un campo que no lo era;
- cambiar el significado de un valor existente;
- añadir un valor a un enum, si los clientes hacen comprobaciones exhaustivas.

Este último caso se olvida con frecuencia. Si un cliente generado trata el enum como una unión cerrada, un valor nuevo puede romperlo.

## Evolucionar antes de versionar

Muchas veces basta con la técnica de expandir y contraer:

1. añadir el campo nuevo junto al antiguo;
2. esperar a que los clientes migren;
3. medir el uso del campo o del endpoint antiguo;
4. eliminarlo cuando nadie lo use.

Esto evita dos versiones completas para un único cambio.

Para anunciar la retirada de una ruta, existen las cabeceras estándar `Deprecation` y `Sunset`:

```http
Deprecation: @1767225600
Sunset: Wed, 30 Sep 2026 23:59:59 GMT
Link: <https://api.ejemplo.com/docs/migracion-v2>; rel="deprecation"
```

## URL, cabecera o parámetro

| Enfoque | Ventajas | Inconvenientes |
|---|---|---|
| URL: `/v2/pedidos` | Evidente, fácil de probar y enrutar | La versión forma parte de la identidad del recurso |
| Cabecera: `Api-Version: 2` | URLs estables | Menos visible, más fácil de olvidar |
| Query: `?api-version=2` | Sencillo de añadir | Afecta a la caché y a las URLs |

Para una API pública o consumida por varios equipos, yo usaría la URL. Es la opción menos sorprendente y facilita que un gateway enrute cada versión por separado.

## Versionar en ASP.NET Core

El paquete `Asp.Versioning.Http` añade versionado a Minimal APIs, y `Asp.Versioning.Mvc` hace lo propio con controladores:

```csharp
builder.Services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1);
    options.ReportApiVersions = true;
    options.ApiVersionReader = new UrlSegmentApiVersionReader();
});

var versiones = app.NewApiVersionSet()
    .HasApiVersion(new ApiVersion(1))
    .HasApiVersion(new ApiVersion(2))
    .Build();

var pedidos = app.MapGroup("/v{version:apiVersion}/pedidos")
    .WithApiVersionSet(versiones);

pedidos.MapGet("/", ListarV1).MapToApiVersion(1);
pedidos.MapGet("/", ListarV2).MapToApiVersion(2);
```

`ReportApiVersions` añade cabeceras con las versiones soportadas y las obsoletas.

## Organizar el código

Evita duplicar toda la aplicación por versión. Lo que suele funcionar es esto: los endpoints y DTOs están versionados, mientras que la lógica de negocio es una sola y cada versión adapta su entrada y su salida. Si la lógica se bifurca, es señal de que lo versionado es el negocio, no la API.

## Política de soporte

Publica cuántas versiones mantienes y durante cuánto tiempo. Una regla simple, como «la anterior se mantiene doce meses tras publicar la nueva», permite a los consumidores planificar. Y antes de apagar nada, consulta las métricas: la fecha del calendario no garantiza que el último cliente haya migrado.

## Referencias

- [Asp.Versioning](https://github.com/dotnet/aspnet-api-versioning)
- [RFC 8594: cabecera Sunset](https://www.rfc-editor.org/rfc/rfc8594)
- [RFC 9745: cabecera Deprecation](https://www.rfc-editor.org/rfc/rfc9745)
