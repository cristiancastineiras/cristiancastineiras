---
title: "Mappings en Elasticsearch para logs: evitar la explosión de campos"
seoTitle: "Mappings de Elasticsearch para logs"
description: "Cómo definir plantillas de índice para logs: text frente a keyword, mapeo dinámico, campos flattened, data streams y cómo evitar la explosión de mappings en un clúster."
date: 2025-10-30
tags: ["Elasticsearch", "Observabilidad"]
---

Elasticsearch acepta cualquier JSON y deduce los tipos por sí mismo. Es cómodo para empezar, y un riesgo con el tiempo: los campos crecen sin control, un mismo campo recibe tipos diferentes y empiezan a rechazarse documentos. Definir el mapping evita estos problemas y reduce el coste de almacenamiento.

## `text` o `keyword`

Es lo primero que hay que entender:

- **`text`**: se analiza y se divide en términos. Sirve para búsqueda de texto completo.
- **`keyword`**: se guarda tal cual. Sirve para filtros exactos, agregaciones y ordenación.

```json
{
  "mappings": {
    "properties": {
      "message": { "type": "match_only_text" },
      "service": { "type": "keyword" },
      "level": { "type": "keyword" },
      "http_status": { "type": "short" },
      "duration_ms": { "type": "float" },
      "@timestamp": { "type": "date" }
    }
  }
}
```

`match_only_text` es una variante de `text` que ocupa bastante menos a cambio de hacer algo más lentas ciertas búsquedas, lo que suele ser aceptable en logs.

Por defecto, una cadena de texto nueva se indexa con los dos tipos: `text` y un subcampo `.keyword`. Es práctico pero duplica el almacenamiento. Para un identificador, como `trace_id`, solo necesitas `keyword`.

## Plantillas de índice

Los logs se escriben en índices que rotan, por lo que hay que definir el mapping en una plantilla:

```text
PUT _index_template/logs-api
{
  "index_patterns": ["logs-api-*"],
  "data_stream": {},
  "priority": 200,
  "template": {
    "settings": {
      "index.lifecycle.name": "logs-retencion",
      "index.mapping.total_fields.limit": 500
    },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "@timestamp": { "type": "date" },
        "message": { "type": "match_only_text" },
        "service": { "type": "keyword" },
        "level": { "type": "keyword" },
        "trace_id": { "type": "keyword" }
      }
    }
  }
}
```

Lo ideal es que las plantillas residan en el control de versiones, y se apliquen de forma automática.

## Controlar el mapeo dinámico

La opción `dynamic` determina lo que ocurre con los campos no declarados:

| Valor | Comportamiento |
|---|---|
| `true` | Crea el campo (predeterminado) |
| `false` | Se guarda en `_source`, pero no se indexa |
| `strict` | Rechaza el documento |
| `runtime` | Crea un campo que se calcula al consultar |

En logs, yo optaría por `false`: los datos no se pierden y se pueden ver, pero no disparan el crecimiento del mapping. `strict` puede costarte logs justo cuando alguien añade un campo sin avisar, y `true` es el problema del que estamos hablando.

## Explosión de campos

Se produce cuando los nombres de campo se generan a partir de datos:

```json
{
  "cabeceras": {
    "x-request-id-8f14": "valor"
  },
  "usuarios": {
    "ana@ejemplo.com": { "accesos": 3 }
  }
}
```

Cada clave nueva es un campo nuevo. Eso significa un estado del clúster más grande, más memoria y consultas más lentas. Al llegar al límite, 1000 campos por defecto, los documentos se rechazan.

Es un problema frecuente cuando se registran objetos enteros con `{@Objeto}` o cabeceras HTTP sin filtrar. La solución es cambiar el diseño: los valores deben ir en los valores, no en los nombres.

Si realmente necesitas guardar un objeto con claves arbitrarias, usa `flattened`, que lo indexa como un único campo:

```json
{
  "cabeceras": { "type": "flattened" }
}
```

Todos sus valores se tratan como texto sin analizar, y se puede filtrar por `cabeceras.x-request-id`.

## Conflictos de tipos

Si un servicio envía `"usuario": 123` y otro `"usuario": { "id": 123 }`, el segundo será rechazado. El tipo de un campo se fija con el primer documento. Por eso, es importante acordar un esquema común. *Elastic Common Schema* (ECS) define nombres estándar, como `service.name` o `http.response.status_code`, lo que permite cruzar datos de distintos servicios y usar paneles existentes.

## Data streams

Para datos que solo se añaden, como los logs, un *data stream* simplifica las cosas: escribes en un único nombre, y Elasticsearch gestiona los índices subyacentes y su rotación.

```text
POST logs-api-produccion/_doc
{
  "@timestamp": "2025-10-30T10:00:00Z",
  "message": "Pedido confirmado",
  "service": "api-pedidos",
  "level": "Information"
}
```

Es importante recordar que los datos ya indexados no cambian si modificas la plantilla. Se aplica a los índices nuevos. Para cambiar el tipo de un campo existente en datos antiguos, hay que reindexar.

## Ahorrar espacio

- `"index": false`: el campo se guarda pero no se puede buscar, útil si solo lo consultas al ver el documento.
- `"doc_values": false`: en campos en los que nunca agregas ni ordenas.
- Evita duplicar el mensaje en varios campos.
- `index.mode: logsdb` en versiones recientes puede reducir considerablemente el almacenamiento.

## Comprobar el estado

```text
GET logs-api-*/_mapping/field/usuario
GET _cat/indices/logs-api-*?v&s=store.size:desc
```

## Referencias

- [Tipos de campo](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/field-data-types)
- [Mapping dinámico](https://www.elastic.co/docs/manage-data/data-store/mapping/dynamic-mapping)
- [Data streams](https://www.elastic.co/docs/manage-data/data-store/data-streams)
