---
title: "Tipos unión y jerarquías cerradas en C# 15: adiós a los resultados ambiguos"
seoTitle: "Tipos unión en C# 15"
description: "Cómo funcionan union y closed en C# 15, qué aportan al switch exhaustivo y dónde encajan frente a los records, las excepciones y las jerarquías de siempre."
date: 2026-10-19
tags: ["C#", ".NET", "Arquitectura"]
---

Llevamos años simulando uniones en C#: una clase base con un constructor privado, una librería como OneOf o un resultado con varias propiedades que pueden ser nulas. C# 15, que llega con .NET 11, por fin lo incorpora al lenguaje.

En el momento de escribir esto, el SDK de .NET 11 sigue en versión preliminar, así que los detalles aún pueden cambiar. Aun así, estas funciones ya no necesitan `<LangVersion>preview</LangVersion>` cuando el proyecto apunta a `net11.0`.

## Qué es una unión

Una unión representa un valor que puede ser exactamente uno de varios tipos:

```csharp
public record class Pagado(string Recibo);
public record class Rechazado(string Motivo);
public record class Pendiente(DateTime Revisar);

public union ResultadoPago(Pagado, Rechazado, Pendiente);
```

Cada caso se convierte de forma implícita al tipo unión, y el compilador comprueba que el `switch` los cubra todos:

```csharp
ResultadoPago resultado = new Pagado("R-1042");

string mensaje = resultado switch
{
    Pagado p => $"Recibo {p.Recibo}",
    Rechazado r => $"Rechazado: {r.Motivo}",
    Pendiente p => $"Revisar el {p.Revisar:d}",
};
```

No hace falta un brazo `_` por defecto. Esa es la ventaja importante: si mañana añades un caso a la unión, cada `switch` que no lo contemple aparecerá señalado, en lugar de caer en silencio en una rama genérica.

## Jerarquías cerradas

Las uniones agrupan tipos que pueden no tener nada en común. Cuando sí forman una familia, el modificador `closed` es la alternativa:

```csharp
public closed record class EstadoPuerta;
public record class Cerrada : EstadoPuerta;
public record class Abierta(float Porcentaje) : EstadoPuerta;

string Describir(EstadoPuerta estado) => estado switch
{
    Cerrada => "cerrada",
    Abierta(var porcentaje) => $"{porcentaje} % abierta",
};
```

Una clase `closed` solo admite derivadas en su propio ensamblado, y es implícitamente `abstract`. La restricción no es transitiva: un descendiente que no sea `closed` puede heredarse desde fuera, así que para extender la exhaustividad hacia abajo hay que marcar también los intermedios.

## Union, closed o herencia normal

| Necesidad | Opción |
|---|---|
| Combinar tipos no relacionados | `union` |
| Familia propia con datos o comportamiento común | `closed` |
| Extensible por terceros | herencia normal o interfaz |

## Dónde encaja frente a las excepciones

El caso más claro es modelar resultados de negocio esperados. Un pago rechazado no es excepcional: forma parte del flujo. Con una unión, la firma del método lo declara y quien llama no puede ignorarlo con facilidad.

Las excepciones siguen siendo adecuadas para lo que el código no puede resolver en ese punto: un fallo de red, un error de programación o una base de datos caída. No conviertas cada posible fallo en un caso de la unión; obtendrías firmas enormes que solo trasladan el problema.

## Cómo adoptarlo

Yo no migraría nada de forma masiva por ahora. .NET 11 es una versión STS, y muchos proyectos seguirán en .NET 10 LTS, donde esta sintaxis no está disponible por defecto. Un camino sensato:

1. identificar métodos que devuelven resultados con varias propiedades opcionales;
2. probar uniones en código nuevo cuando el proyecto ya esté en `net11.0`;
3. mantener fuera de los contratos públicos hasta confirmar cómo se serializan en tu caso.

Ese último punto importa: un tipo que cruza una API HTTP necesita una representación JSON estable. Comprueba cómo lo trata tu serializador antes de exponerlo.

## Referencias

- [Novedades de C# 15](https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-15)
