---
title: "Retención de logs en Elasticsearch con ILM: no pagues por lo que nadie consulta"
seoTitle: "Retención de logs con ILM"
description: "Cómo diseñar una política ILM para logs en Elasticsearch: rollover, fases hot, warm, cold y delete, tamaño de shards y cómo calcular cuánto almacenamiento necesitas."
date: 2026-01-05
tags: ["Elasticsearch", "Observabilidad", "Operaciones"]
---

Los logs crecen sin parar, pero casi todas las consultas van a los datos de los últimos días. Mantener todo en discos rápidos, y sin ninguna fecha de caducidad, es caro. Y se acaba notando, porque el disco se llena en el peor momento. *Index Lifecycle Management* automatiza qué le pasa a los datos con el tiempo.

## Las fases

- **Hot**: se escribe y se consulta con frecuencia, en almacenamiento rápido.
- **Warm**: ya no se escribe, y se consulta menos.
- **Cold**: se consulta rara vez, y en un almacenamiento más barato.
- **Frozen**: consultas muy poco frecuentes, en almacenamiento de objetos.
- **Delete**: se elimina.

No hace falta usarlas todas. Un sistema pequeño puede funcionar perfectamente con hot y delete.

## Una política

```text
PUT _ilm/policy/logs-retencion
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_primary_shard_size": "50gb",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "forcemerge": { "max_num_segments": 1 },
          "shrink": { "number_of_shards": 1 }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

## El detalle de `min_age`

Es lo que más confusión genera: cuando hay rollover, la edad se cuenta **desde el rollover**, no desde el primer documento. Con esta política, un dato se elimina a los 30 días después de que su índice haya rotado. Si un índice tarda un día en rotar, algunos datos pueden vivir 31 días.

Este matiz es importante si tienes requisitos legales de retención máxima. Si borrar a tiempo es una obligación, deja un margen, o comprueba cuándo se elimina de verdad.

## Rollover: por qué no un índice por día

El formato clásico `logs-2026.01.05` crea un índice por día, sin importar el volumen. Un servicio tranquilo generará muchos índices minúsculos, y uno muy activo, índices enormes. Con el rollover, se rota por tamaño o por edad, lo que ocurra primero, y los índices quedan más homogéneos.

La regla práctica de Elastic es mantener los shards entre 10 y 50 GB aproximadamente, y evitar el *oversharding*. Cada shard consume recursos del clúster, aunque esté casi vacío, y uno de los problemas de rendimiento más comunes es tener demasiados shards pequeños.

## Aplicar la política

Se referencia en la plantilla de índice:

```text
PUT _index_template/logs-api
{
  "index_patterns": ["logs-api-*"],
  "data_stream": {},
  "template": {
    "settings": {
      "index.lifecycle.name": "logs-retencion",
      "number_of_shards": 1,
      "number_of_replicas": 1
    }
  }
}
```

Con *data streams*, la rotación funciona sin tener que crear alias a mano.

## Comprobar que funciona

```text
GET logs-api-*/_ilm/explain
```

Muestra la fase de cada índice, la acción actual y los errores. Por ejemplo, un `shrink` puede atascarse si no hay un nodo con espacio suficiente. Una política bloqueada puede pasar desapercibida durante semanas, hasta que el disco se llene:

```text
POST logs-api-000042/_ilm/retry
```

Vigila también `filter_path=**.step_info` si hay fallos. Crea una alerta para los índices en estado `ERROR`.

## Calcular el almacenamiento

```text
Volumen diario × días de retención × (1 + réplicas) × factor de índice
```

Por ejemplo, 50 GB diarios, 30 días y una réplica: 50 × 30 × 2 = 3 TB, antes de contar el efecto de la compresión y la sobrecarga. Elasticsearch deja de asignar shards en un nodo al alcanzar la marca de agua del 85 % de disco, de modo que hay que dejar margen. Mide lo que ocupa un índice real, porque el factor depende mucho de tus datos y tu mapping.

## Reducir antes de retener

La mayor mejora de coste no suele estar en ILM, sino en no guardar lo que nadie va a mirar:

- ajustar niveles de log, porque `Debug` en producción puede representar la mayor parte del volumen;
- filtrar las comprobaciones de salud y otras peticiones repetitivas;
- políticas distintas según el valor de los datos: 90 días para auditoría, 7 para logs de acceso;
- métricas en lugar de logs para lo que solo se cuenta.

Puedes tener varias políticas, una por tipo de dato. No todos los logs valen lo mismo.

## Búsqueda de snapshots

Para retenciones largas por requisitos legales, las fases cold y frozen pueden montar *searchable snapshots* desde almacenamiento de objetos, lo que abarata mucho el coste. Tienen requisitos de licencia, así que compruébalo. Si solo necesitas conservar los datos sin consultarlos, una exportación a un *bucket* con ciclo de vida puede bastar.

También debes asegurarte de tener snapshots de lo que necesites recuperar. Las réplicas protegen frente a la caída de un nodo, pero no frente a un borrado accidental.

## La retención como decisión

¿Cuánto tiempo guardar logs? No es solo una cuestión técnica. Puede haber obligaciones legales, y a la vez, los datos personales no deben conservarse más de lo necesario. Decídelo con quien corresponda, y documéntalo: ILM es lo que hace que esa decisión se cumpla.

## Referencias

- [Index Lifecycle Management](https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management)
- [Dimensionar shards](https://www.elastic.co/docs/deploy-manage/production-guidance/optimize-performance/size-shards)
