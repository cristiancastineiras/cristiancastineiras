---
title: "Patrón Strangler Fig con YARP: sustituir un sistema legacy sin reescribirlo de golpe"
seoTitle: "Strangler Fig con YARP en .NET"
description: "Cómo migrar un sistema legacy por partes, poniendo YARP delante, enrutando funcionalidad a la nueva aplicación y compartiendo la sesión sin una gran reescritura."
date: 2025-02-13
tags: [".NET", "Arquitectura", "Refactorización"]
---

Las grandes reescrituras tienen mala fama por buenos motivos: durante meses o años se mantienen dos sistemas, se persigue un objetivo que no deja de moverse y nada llega a los usuarios hasta el final. El patrón *Strangler Fig* propone otro camino: la aplicación nueva crece alrededor de la antigua, y la va sustituyendo poco a poco.

## La idea

Se coloca un proxy delante de ambos sistemas. Cada ruta se dirige a uno u otro:

```text
              ┌──────────────┐
Usuarios ───► │  Proxy YARP  │
              └──┬────────┬──┘
    /pedidos/*   │        │   todo lo demás
                 ▼        ▼
          App nueva    App legacy
```

Para los usuarios, solo hay un sistema. Internamente, cada migración se reduce a mover una ruta.

## YARP

YARP es un proxy inverso para .NET, de Microsoft, y se aloja dentro de una aplicación ASP.NET Core:

```bash
dotnet add package Yarp.ReverseProxy
```

```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddReverseProxy()
    .LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"));

var app = builder.Build();
app.MapReverseProxy();
app.Run();
```

```json
{
  "ReverseProxy": {
    "Routes": {
      "pedidos": {
        "ClusterId": "nueva",
        "Match": { "Path": "/pedidos/{**resto}" },
        "Order": 1
      },
      "legacy": {
        "ClusterId": "antigua",
        "Match": { "Path": "/{**resto}" },
        "Order": 100
      }
    },
    "Clusters": {
      "nueva": {
        "Destinations": { "d1": { "Address": "http://app-nueva:8080/" } }
      },
      "antigua": {
        "Destinations": { "d1": { "Address": "http://app-legacy:80/" } }
      }
    }
  }
}
```

La ruta `legacy` es el comodín. Para migrar otra funcionalidad, basta con añadir una ruta y desplegar. Si algo sale mal, la vuelta atrás consiste en quitar esa línea.

## Migrar desde ASP.NET clásico

Si tu sistema es ASP.NET Framework, la migración incremental de Microsoft se apoya en esta misma técnica. La aplicación ASP.NET Core recibe todo el tráfico, y reenvía a la antigua lo que aún no sabe manejar. El paquete `Microsoft.AspNetCore.SystemWebAdapters` ayuda a compartir la sesión y la autenticación entre las dos.

## Lo difícil: lo compartido

El enrutado es la parte fácil. Los problemas reales surgen en lo que ambas aplicaciones comparten:

**Autenticación.** Un usuario que ha iniciado sesión en una no debería tener que hacerlo en la otra. Se suele resolver compartiendo la cookie, o con un proveedor de identidad externo al que accedan ambas.

**Base de datos.** Lo más habitual es que, al principio, las dos usen la misma base de datos. Es aceptable como paso intermedio. Eso sí, un cambio de esquema afecta a las dos, por lo que hay que coordinarlo. Separar los datos de cada módulo es otra migración, que conviene hacer más tarde y por partes.

**Interfaz.** Si un usuario pasa de una aplicación a la otra, la navegación y el estilo deben ser coherentes. Un menú compartido y un sistema de diseño común ayudan a que no se note el salto.

## Por dónde empezar

No lo hagas por lo más crítico ni lo más enrevesado. Busca algo que cumpla lo siguiente:

- valor real para el negocio, para que el esfuerzo se vea;
- pocas dependencias con el resto del sistema;
- una frontera clara, por URL o por funcionalidad.

Sirve también para probar toda la cadena: proxy, despliegue, autenticación compartida y observabilidad. Lo que aprendas se aplicará en todas las rutas siguientes.

## Verificar antes de cambiar

Puedes reducir el riesgo enviando a la nueva aplicación solo una parte del tráfico, o bien comparando respuestas. YARP permite filtrar rutas por cabeceras, lo que facilita que un grupo de usuarios internos pruebe primero:

```json
{
  "Match": {
    "Path": "/pedidos/{**resto}",
    "Headers": [
      { "Name": "X-Canary", "Values": [ "1" ] }
    ]
  }
}
```

## Medir el progreso

Mide el porcentaje de tráfico que atiende la aplicación nueva y añade logs con el destino de cada petición. Te servirá para saber qué queda, y también para identificar qué rutas antiguas ya no recibe nadie. Muchas veces descubrirás funcionalidad que se puede eliminar sin migrarla, lo que es la forma más barata de hacerlo.

## El peligro: quedarse a medias

El riesgo de este patrón es que se detenga a mitad de camino. Dos sistemas para siempre son peores que uno viejo. Define un objetivo y una fecha para apagar el antiguo, y no añadas funcionalidad nueva a la parte legacy. Cuando la última ruta se migre, retira también el proxy, si ya no aporta nada.

## Referencias

- [Patrón Strangler Fig](https://learn.microsoft.com/azure/architecture/patterns/strangler-fig)
- [YARP](https://learn.microsoft.com/aspnet/core/fundamentals/servers/yarp/getting-started)
- [Migración incremental de ASP.NET a ASP.NET Core](https://learn.microsoft.com/aspnet/core/migration/fx-to-core/)
