---
title: "De .NET Framework a .NET moderno: un plan de migración realista"
seoTitle: "Migrar de .NET Framework a .NET"
description: "Cómo planificar la salida de .NET Framework: inventario, librerías compatibles con netstandard, WCF y Web Forms, Upgrade Assistant y migración incremental por partes."
date: 2025-10-09
tags: [".NET", "Refactorización", "Arquitectura"]
---

.NET Framework 4.8 sigue teniendo soporte mientras lo tenga el Windows en el que se ejecuta, así que nadie te obliga a migrar mañana. Las razones para hacerlo son otras: no recibe funcionalidades nuevas, solo se ejecuta en Windows, no aprovecha las mejoras de rendimiento y cada vez hay menos librerías y gente que lo conozca.

Lo que suele fallar es tratarlo como un único proyecto gigante.

## Empezar por un inventario

Antes de estimar nada, averigua qué tienes:

- proyectos y dependencias entre ellos;
- paquetes NuGet, y si existen en versiones compatibles;
- tecnologías sin equivalente directo: Web Forms, WCF de servidor, WF, Remoting, AppDomains;
- llamadas a APIs exclusivas de Windows, como el registro, y a `System.Web`;
- dónde se usa `HttpContext.Current`, que es un punto problemático habitual.

Puedes usar `dotnet-apiport` (ya sin mantenimiento) o `upgrade-assistant analyze` para obtener una primera idea, y revisar los resultados con ojo crítico.

## Lo que no se migra directamente

| Tecnología | Camino habitual |
|---|---|
| Web Forms | Reescribir las pantallas (React, Blazor, Razor) |
| WCF servidor | CoreWCF, o pasar a REST o gRPC |
| WCF cliente | `System.ServiceModel.*` para .NET |
| Windows Workflow | Rediseñar, o mantener aislado |
| Remoting | gRPC o HTTP |
| `System.Web` | Reescribir sobre ASP.NET Core |
| EF 6 | Ejecutar EF 6 en .NET o migrar a EF Core |

Si tienes Web Forms, ten en cuenta que no hay una ruta de migración: es una reescritura de esas pantallas. Suele ser donde más se tarda.

## Empezar por abajo

El orden natural es el del grafo de dependencias: primero lo que no depende de nada.

1. **Separar la lógica** de `System.Web` en librerías de clases.
2. **Convertir los proyectos al formato SDK**, que ya sirve para .NET Framework, y es un paso seguro por sí mismo.
3. **Compilar para varios destinos** a la vez, lo que permite que el código funcione en ambos mundos durante la transición:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net48;net8.0</TargetFrameworks>
  </PropertyGroup>
</Project>
```

Si hay diferencias concretas, compilación condicional:

```csharp
#if NET8_0_OR_GREATER
    return JsonSerializer.Deserialize<Pedido>(texto);
#else
    return JsonConvert.DeserializeObject<Pedido>(texto);
#endif
```

Limita estos casos al mínimo. Si se extienden por todo el código, es señal de que falta una abstracción, o de que conviene terminar antes la migración.

## Paquetes obsoletos

Mira cada dependencia y decide: actualizar, sustituir o eliminar. Algunas tenían sentido hace diez años y hoy están incluidas en la plataforma. Reducir la lista antes de migrar ahorra trabajo, porque no hay que pelearse con la compatibilidad de lo que ya no hace falta.

## Migrar la aplicación web por partes

Para aplicaciones ASP.NET, lo más seguro es la migración incremental mediante un proxy: una aplicación ASP.NET Core al frente, que atiende lo ya migrado y reenvía el resto a la aplicación antigua. Se explica en [el artículo sobre Strangler Fig]({{< relref "/posts/strangler-fig-yarp" >}}). La herramienta `.NET Upgrade Assistant` ayuda con la parte mecánica, y `SystemWebAdapters` ofrece una forma de compartir sesión y autenticación.

## Diferencias de comportamiento

Lo que compila puede comportarse distinto. Revísalo con pruebas:

- **Globalización**: en Linux se usa ICU, y las comparaciones de cadenas o el orden pueden cambiar.
- **Cifrado**: algunos algoritmos o cifrados antiguos no están disponibles.
- **Sensibilidad a mayúsculas**: en Linux, las rutas de archivo sí distinguen entre mayúsculas y minúsculas.
- **`HttpClient`** y las conexiones se gestionan de forma distinta.
- **Serialización**: `BinaryFormatter` se elimina; `System.Text.Json` tiene otros valores por defecto que `Newtonsoft.Json`.
- **Configuración**: de `web.config` a `appsettings.json` y a las variables de entorno.

Si cambias también a contenedores y Linux, hazlo en un paso separado. Migrar el framework, el sistema operativo y la forma de desplegar al mismo tiempo hace muy difícil saber qué ha causado un problema.

## Elegir la versión de destino

Elige una LTS. A fecha de hoy, .NET 8 está en LTS, y .NET 10 llegará como LTS en noviembre de 2025. Si tu migración va a durar meses, apunta directamente a la siguiente LTS, para no tener que repetir el salto al poco de terminar.

## Cómo justificarlo

Solo «es tecnología antigua» no suele convencer. Datos que sí sirven: coste de las licencias de Windows frente a contenedores en Linux, tiempo de CI, rendimiento medido, dificultad para contratar y riesgos de seguridad de dependencias sin mantenimiento. Y conviene presentarlo como un trabajo por partes, en el que cada fase ya aporta algo, y no como un proyecto de dos años sin resultados hasta el final.

## Referencias

- [Portar de .NET Framework a .NET](https://learn.microsoft.com/dotnet/core/porting/)
- [.NET Upgrade Assistant](https://learn.microsoft.com/dotnet/core/porting/upgrade-assistant-overview)
- [CoreWCF](https://github.com/CoreWCF/CoreWCF)
