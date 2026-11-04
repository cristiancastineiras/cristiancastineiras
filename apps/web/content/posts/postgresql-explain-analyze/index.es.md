---
title: "Cómo leer EXPLAIN ANALYZE en PostgreSQL sin perderse"
seoTitle: "Leer EXPLAIN ANALYZE en PostgreSQL"
description: "Guía para interpretar EXPLAIN ANALYZE en PostgreSQL: nodos, costes, estimaciones erróneas, buffers y las señales que indican dónde está realmente el problema."
date: 2025-09-29
tags: ["PostgreSQL", "SQL", "Rendimiento"]
---

Un plan de ejecución intimida la primera vez, pero la mayoría de las veces solo hay que hacerse tres preguntas: dónde se va el tiempo, si las estimaciones coinciden con la realidad y cuántos datos se leen para nada.

## El comando

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT p.id, c.nombre
FROM pedidos p
JOIN clientes c ON c.id = p.cliente_id
WHERE p.fecha >= '2025-01-01';
```

`ANALYZE` ejecuta la consulta de verdad. Con un `UPDATE` o `DELETE`, los cambios se aplican, así que envuélvelo en una transacción:

```sql
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) DELETE FROM sesiones WHERE expira_en < now();
ROLLBACK;
```

## Cómo se lee

El plan es un árbol, y los nodos más indentados se ejecutan primero:

```text
Hash Join  (cost=25.1..812.4 rows=120 width=36)
           (actual time=0.4..48.2 rows=98210 loops=1)
  Hash Cond: (p.cliente_id = c.id)
  ->  Seq Scan on pedidos p  (cost=0.0..760.0 rows=120 width=12)
                             (actual time=0.01..31.7 rows=98210 loops=1)
        Filter: (fecha >= '2025-01-01')
        Rows Removed by Filter: 1402
  ->  Hash  (...)
```

- `cost` es una estimación en unidades arbitrarias: sirve para comparar planes, no son milisegundos.
- `actual time` son milisegundos reales: inicio y final **por bucle**.
- `rows` estimadas frente a reales, y `loops`: el tiempo y las filas se multiplican por el número de bucles.

Es un error habitual leer `actual time=0.5` con `loops=10000` como si fuese rápido. Son 5 segundos.

## Señal 1: estimaciones muy alejadas

Aquí el planificador esperaba 120 filas y llegaron 98 210. Con una estimación así de mala, puede elegir un plan pésimo, por ejemplo un *nested loop* que funciona bien con 100 filas y fatal con 100 000.

Suele resolverse actualizando estadísticas:

```sql
ANALYZE pedidos;
```

Si persiste, puede ser porque las columnas están correlacionadas, y el planificador supone que son independientes. Las estadísticas extendidas lo cubren:

```sql
CREATE STATISTICS st_pedidos (dependencies)
    ON provincia, ciudad FROM pedidos;
ANALYZE pedidos;
```

## Señal 2: `Rows Removed by Filter` muy alto

Si se leen muchas filas para descartar casi todas, el acceso no es el apropiado. Un índice sobre la columna del filtro puede ayudar.

Eso sí, un `Seq Scan` no siempre es un problema. Si la consulta devuelve gran parte de la tabla, recorrerla entera es lo más barato. En el ejemplo se devuelve casi todo, de modo que un índice no aportaría nada.

## Señal 3: ordenaciones en disco

```text
Sort Method: external merge  Disk: 45120kB
```

La ordenación no cabe en `work_mem` y va a disco. Antes de aumentar ese parámetro, comprueba si un índice podría dar los datos ya ordenados, o si se puede ordenar menos.

## Señal 4: lecturas con `BUFFERS`

```text
Buffers: shared hit=120 read=48000
```

- `hit`: páginas encontradas en la caché de PostgreSQL.
- `read`: páginas leídas fuera de ella, generalmente más lentas.

Un valor alto de `read` explica por qué una consulta es lenta la primera vez y rápida la segunda. Conviene tenerlo en cuenta al medir: ejecutar dos veces puede engañarte.

## Un método para empezar

1. Compara el tiempo total con el de cada nodo y localiza el más costoso, recordando multiplicar por `loops`.
2. Busca diferencias grandes entre `rows` estimadas y reales, de abajo arriba.
3. Comprueba filas descartadas y lecturas.
4. Cambia una sola cosa y vuelve a medir.

Prueba siempre con datos similares a los de producción: con una tabla de mil filas, PostgreSQL usará un plan que no se parece al que usará con cincuenta millones.

Herramientas como [explain.dalibo.com](https://explain.dalibo.com/) ayudan a visualizar planes grandes. Ten cuidado con los planes que contengan datos sensibles antes de pegarlos en un servicio externo.

## Referencias

- [Uso de EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [Estadísticas extendidas](https://www.postgresql.org/docs/current/planner-stats.html#PLANNER-STATS-EXTENDED)
