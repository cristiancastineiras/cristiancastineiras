---
title: "Los errores de async/await que siguen llegando a producción en C#"
seoTitle: "Errores comunes de async/await en C#"
description: "Bloqueos con .Result, async void, tareas sin esperar y paralelismo mal entendido: los fallos de async/await en C# que más cuesta diagnosticar y cómo evitarlos."
date: 2025-03-10
tags: [".NET", "C#", "Rendimiento"]
---

`async` y `await` hacen que el código asíncrono parezca secuencial. Es su gran ventaja y también el motivo por el que sus errores pasan desapercibidos: compilan, funcionan en local y solo fallan cuando hay carga.

## Bloquear con `.Result` o `.Wait()`

Es el error más caro. Bloquear un hilo mientras se espera una tarea desperdicia el recurso que `async` intenta ahorrar.

```csharp
// Mal: ocupa un hilo del pool mientras espera
var cliente = _repositorio.ObtenerAsync(id).Result;

// Bien
var cliente = await _repositorio.ObtenerAsync(id);
```

En ASP.NET Core no hay contexto de sincronización, así que no suele aparecer el interbloqueo clásico de ASP.NET Framework o WPF. Lo que aparece es peor de detectar: agotamiento del thread pool. Bajo carga, las peticiones se quedan esperando hilos, la latencia se dispara y la CPU sigue baja.

Si ves latencias altas con poca CPU, `dotnet-counters` te permite mirar `threadpool-queue-length`. Una cola creciente es una pista clara.

## `async void`

Un método `async void` no devuelve nada que se pueda esperar. Sus excepciones no se pueden capturar con un `try/catch` en el llamador y suelen tirar el proceso.

```csharp
// Mal
public async void Enviar() => await _smtp.SendAsync(mensaje);

// Bien
public async Task EnviarAsync() => await _smtp.SendAsync(mensaje);
```

Solo tiene sentido en manejadores de eventos, donde la firma lo exige.

## Tareas lanzadas y olvidadas

Quitar el `await` para «responder antes» parece inofensivo:

```csharp
_ = _auditoria.RegistrarAsync(evento);
return Ok();
```

Tiene tres problemas: las excepciones se pierden, el trabajo puede cortarse si la aplicación se detiene y, si usa un `DbContext` con ámbito de petición, este puede estar ya eliminado cuando se ejecute.

Si el trabajo tiene que sobrevivir a la petición, debe ir a una cola con un servicio en segundo plano.

## Esperar en secuencia lo que podría ir en paralelo

```csharp
// Tarda la suma de ambas
var pedidos = await ObtenerPedidosAsync(id);
var facturas = await ObtenerFacturasAsync(id);

// Tarda lo que la más lenta
var pedidosTask = ObtenerPedidosAsync(id);
var facturasTask = ObtenerFacturasAsync(id);
await Task.WhenAll(pedidosTask, facturasTask);

var pedidos2 = await pedidosTask;
var facturas2 = await facturasTask;
```

Ojo con un caso concreto: un `DbContext` no admite operaciones simultáneas. Si ambas funciones usan la misma instancia, EF Core lanzará una excepción. Se necesita un contexto por operación, por ejemplo con `IDbContextFactory`.

## `Task.Run` en un servidor

`Task.Run` no convierte una llamada en asíncrona: mueve el trabajo a otro hilo. En una petición web, envolver una llamada síncrona de esta forma libera un hilo ocupando otro, y encima añade coste. Tiene sentido para trabajo intensivo de CPU en aplicaciones de escritorio, no como arreglo general en un backend.

## `ConfigureAwait(false)`

En aplicaciones ASP.NET Core no aporta nada, porque no hay contexto de sincronización que capturar. Sigue siendo recomendable en librerías que puedan ejecutarse en aplicaciones con contexto, como WPF o WinForms.

## Dejar que el analizador ayude

El paquete `Microsoft.VisualStudio.Threading.Analyzers` detecta bloqueos y otros patrones peligrosos. Activar estas reglas en CI cuesta poco y evita revisar lo mismo una y otra vez en cada pull request.

## Referencias

- [Programación asíncrona con async y await](https://learn.microsoft.com/dotnet/csharp/asynchronous-programming/)
- [ASP.NET Core Async Guidance, de David Fowler](https://github.com/davidfowl/AspNetCoreDiagnosticScenarios/blob/master/AsyncGuidance.md)
