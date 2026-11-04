---
title: "Intl en JavaScript: formatea fechas, monedas y plurales sin una librería"
seoTitle: "Intl en JavaScript: fechas y monedas"
description: "La API Intl del navegador cubre fechas, monedas, porcentajes, tiempos relativos, listas y plurales: cómo usarla bien y evitar errores con las zonas horarias."
date: 2025-11-13
tags: ["JavaScript", "i18n", "Rendimiento"]
---

Es habitual instalar una librería de fechas o una función propia para formatear un precio. El navegador incluye una API muy completa para esto, `Intl`, que no añade nada al bundle y conoce las reglas de cientos de idiomas.

## Fechas

```js
const fecha = new Date("2025-11-13T09:30:00Z");

new Intl.DateTimeFormat("es-ES", { dateStyle: "long" }).format(fecha);
// "13 de noviembre de 2025"

new Intl.DateTimeFormat("es-ES", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "Europe/Madrid",
}).format(fecha);
// "13/11/25, 10:30"
```

Indica siempre `timeZone` si importa dónde está el usuario. Si no lo haces, se usa la zona del dispositivo, y un servidor en UTC y un navegador en Madrid mostrarán valores diferentes. Esto causa errores de hidratación si renderizas en el servidor.

## Una trampa con fechas sin hora

```js
new Date("2025-11-13");
// Se interpreta como medianoche UTC
```

Para alguien en América, eso cae el 12 de noviembre. Si lo que tienes es una fecha de calendario, como un cumpleaños, no pases por una marca de tiempo:

```js
const [anio, mes, dia] = "2025-11-13".split("-").map(Number);
const local = new Date(anio, mes - 1, dia);
```

La API `Temporal` resolverá esto de forma más limpia con `PlainDate` cuando su soporte sea general. Comprueba su estado en tus navegadores objetivo.

## Monedas

```js
const euros = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

euros.format(1234.5);
// "1234,50 €"
```

Fíjate en que no hay separador de miles: en español, por defecto, no se aplica a números de cuatro cifras. Si tu diseño lo necesita, usa la opción `useGrouping: "always"`.

La moneda no depende del idioma. Un usuario de habla inglesa que paga en euros necesita `en-IE` con `EUR`, no una conversión a dólares. Guarda ambos datos por separado.

## Números, porcentajes y unidades

```js
new Intl.NumberFormat("es-ES").format(1234567.89);
// "1.234.567,89"

new Intl.NumberFormat("es-ES", { style: "percent" }).format(0.256);
// "26 %"

new Intl.NumberFormat("es-ES", {
  style: "unit",
  unit: "kilometer-per-hour",
}).format(90);
// "90 km/h"

new Intl.NumberFormat("es-ES", { notation: "compact" }).format(1500000);
// "1,5 M"
```

## Tiempos relativos

```js
const relativo = new Intl.RelativeTimeFormat("es", { numeric: "auto" });

relativo.format(-1, "day");  // "ayer"
relativo.format(2, "week");  // "dentro de 2 semanas"
```

La diferencia y la unidad las eliges tú. Es una función de pocas líneas:

```js
const UNIDADES = [
  ["year", 31536000],
  ["month", 2592000],
  ["day", 86400],
  ["hour", 3600],
  ["minute", 60],
];

function haceTiempo(fecha, ahora = Date.now()) {
  const segundos = Math.round((fecha.getTime() - ahora) / 1000);

  for (const [unidad, tamano] of UNIDADES) {
    if (Math.abs(segundos) >= tamano) {
      return relativo.format(Math.round(segundos / tamano), unidad);
    }
  }

  return relativo.format(segundos, "second");
}
```

## Listas

```js
new Intl.ListFormat("es", { type: "conjunction" }).format(["Ana", "Luis", "Marta"]);
// "Ana, Luis y Marta"

new Intl.ListFormat("es", { type: "disjunction" }).format(["hoy", "mañana"]);
// "hoy o mañana"
```

Resuelve hasta casos que se suelen olvidar: en español, la «y» cambia a «e» delante de ciertas palabras, como en «Ana e Irene».

## Plurales

```js
const reglas = new Intl.PluralRules("es");

reglas.select(1); // "one"
reglas.select(5); // "other"

const textos = { one: "archivo", other: "archivos" };
`${n} ${textos[reglas.select(n)]}`;
```

También permite ordinales con `{ type: "ordinal" }`. Si ya usas una librería de i18n, seguramente te lo proporciona.

## Ordenar correctamente

`sort()` por defecto compara códigos Unicode, de modo que «Álvaro» aparece después de «Zoe»:

```js
const nombres = ["Zoe", "Álvaro", "ana"];

nombres.sort(new Intl.Collator("es").compare);
// ["Álvaro", "ana", "Zoe"]
```

Con `{ numeric: true }`, ordena de manera natural «archivo2» antes de «archivo10».

## Rendimiento

Crear un formateador es relativamente costoso; usarlo, no. Reutilízalo en lugar de crear uno por cada fila de una tabla:

```js
const formateador = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });

const importes = filas.map((f) => formateador.format(f.total));
```

## Cuándo sigue haciendo falta una librería

Para operar con fechas, sumar meses, calcular diferencias o manejar zonas horarias de forma compleja, `date-fns` o `Temporal` siguen siendo necesarias, porque `Intl` solo se ocupa de formatear.

Ten presente que el resultado puede variar entre navegadores y versiones. No hagas pruebas que comparen exactamente la cadena con espacios incluidos: algunos caracteres son espacios duros.

## Referencias

- [Intl en MDN](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl)
- [Temporal en MDN](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Temporal)
