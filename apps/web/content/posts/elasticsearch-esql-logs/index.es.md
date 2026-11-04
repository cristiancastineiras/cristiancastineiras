---
title: "ES|QL para investigar logs: consultas más legibles en Elasticsearch"
seoTitle: "ES|QL para investigar logs"
description: "Cómo usar ES|QL en un incidente real: filtrar, agregar, extraer campos de texto y cruzar datos con LOOKUP JOIN, con consultas fáciles de leer y modificar."
date: 2026-10-05
tags: ["Elasticsearch", "Observabilidad"]
---

Durante un incidente necesitas hacer preguntas rápidas y encadenadas: ¿qué servicio falla?, ¿desde cuándo?, ¿a qué clientes afecta? El Query DSL de Elasticsearch es muy potente, pero un JSON con varios niveles de anidación no ayuda en ese momento. ES|QL es un lenguaje de consulta basado en tuberías, que se lee de arriba abajo y se puede ampliar línea a línea.

## Lo básico

Cada línea recibe el resultado de la anterior:

```text
FROM logs-api-*
| WHERE @timestamp > NOW() - 1 hour AND level == "Error"
| STATS errores = COUNT(*) BY service
| SORT errores DESC
| LIMIT 10
```

Se puede ejecutar en Kibana Discover, en la consola o por la API:

```text
POST /_query?format=txt
{
  "query": "FROM logs-api-* | WHERE level == \"Error\" | LIMIT 10"
}
```

## Investigar un incidente paso a paso

La forma natural de trabajar es ir añadiendo líneas.

**¿Cuándo empezó?**

```text
FROM logs-api-*
| WHERE @timestamp > NOW() - 6 hours AND level == "Error"
| STATS errores = COUNT(*) BY minuto = BUCKET(@timestamp, 5 minutes)
| SORT minuto
```

**¿Qué ha cambiado?** Agrupa por versión desplegada, si la registras:

```text
FROM logs-api-*
| WHERE @timestamp > NOW() - 1 hour AND service == "api-pedidos"
| STATS total = COUNT(*), errores = COUNT(CASE(level == "Error", 1, null)) BY service.version
| EVAL porcentaje = ROUND(100.0 * errores / total, 1)
```

**¿Qué rutas son más lentas?**

```text
FROM logs-api-*
| WHERE @timestamp > NOW() - 1 hour
| STATS p95 = PERCENTILE(duration_ms, 95), peticiones = COUNT(*) BY http.route
| WHERE peticiones > 100
| SORT p95 DESC
```

## Extraer de textos sin estructura

No todos los logs tienen campos bien definidos. `DISSECT` y `GROK` permiten extraerlos en la propia consulta, sin reindexar:

```text
FROM logs-legacy-*
| WHERE message LIKE "*timeout*"
| DISSECT message "Timeout calling %{destino} after %{ms} ms"
| EVAL ms = TO_INTEGER(ms)
| STATS maximo = MAX(ms), total = COUNT(*) BY destino
```

Es perfecto para explorar. Si haces la misma extracción con frecuencia, es mejor extraer el campo durante la ingesta.

Fíjate en la conversión con `TO_INTEGER`. Lo extraído es texto, y si no lo conviertes, una comparación numérica no funcionará como esperas.

## Cruzar datos con `LOOKUP JOIN`

Disponible de forma general desde la versión 9.1, es una de las novedades más útiles. Permite enriquecer resultados con otro índice, sin desnormalizarlo todo al ingerir:

```text
FROM logs-api-*
| WHERE level == "Error"
| LOOKUP JOIN servicios-catalogo ON service
| STATS errores = COUNT(*) BY equipo
| SORT errores DESC
```

El índice de la derecha debe crearse con el modo `lookup`:

```text
PUT servicios-catalogo
{
  "settings": { "index.mode": "lookup" },
  "mappings": {
    "properties": {
      "service": { "type": "keyword" },
      "equipo": { "type": "keyword" }
    }
  }
}
```

Con esto, ves directamente qué equipo debe atender cada error. Las versiones más recientes han ido ampliando sus posibilidades, por ejemplo con más comparaciones y varios campos.

## Consultas de series temporales

Las últimas versiones han añadido también funciones para métricas, como `TBUCKET` o `RATE`, y un comando de origen `TS`. Antes había que hacer esto en otras herramientas. Comprueba qué tienes disponible en tu versión, porque es una parte que está evolucionando rápidamente.

## Parámetros en lugar de concatenar

Si envías consultas desde código, no concatenes valores del usuario:

```text
POST /_query
{
  "query": "FROM logs-api-* | WHERE service == ?servicio | LIMIT 100",
  "params": [{ "servicio": "api-pedidos" }]
}
```

Evita errores y que alguien inyecte algo en tu consulta.

## Lo que hay que vigilar

- **Límite de resultados**: por defecto, devuelve un número limitado de filas. Si una agregación parece incompleta, revisa `LIMIT`.
- **Valores múltiples**: un campo con varios valores se comporta de forma distinta en algunas funciones, y las comparaciones pueden devolver `null` con un aviso.
- **Coste**: `FROM logs-*` sobre años de datos es caro. Empieza siempre por acotar el tiempo y el índice.
- **Campos no mapeados**: un campo solo en `_source` no estará disponible en todas las versiones. Revisa el mapping si no aparece.

## ¿Sustituye a Query DSL o KQL?

No del todo. KQL sigue siendo muy práctico para filtrar en Kibana, y Query DSL sigue siendo la opción adecuada para búsquedas complejas con relevancia desde una aplicación. ES|QL brilla sobre todo en exploración y agregaciones, justo lo que se necesita durante un incidente.

Una recomendación: guarda las consultas que resuelvan un incidente, en un runbook o como una búsqueda guardada. La próxima vez que algo falle, y a las tres de la madrugada, lo agradecerás.

## Referencias

- [ES|QL en Elastic](https://www.elastic.co/docs/reference/query-languages/esql)
- [LOOKUP JOIN](https://www.elastic.co/docs/reference/query-languages/esql/esql-lookup-join)
