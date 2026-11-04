---
title: "Funciones de ventana en SQL: rankings, acumulados y comparaciones sin subconsultas"
seoTitle: "Funciones de ventana en SQL"
description: "Aprende ROW_NUMBER, RANK, LAG y sumas acumuladas con ejemplos reales: último registro por grupo, comparación con el periodo anterior y deduplicación de filas en SQL."
date: 2025-09-01
tags: ["SQL", "PostgreSQL"]
---

`GROUP BY` agrupa filas y pierde el detalle. Con frecuencia necesitas lo contrario: mantener cada fila y añadirle un dato calculado sobre un conjunto relacionado. Para eso están las funciones de ventana, soportadas por PostgreSQL, SQL Server y los demás motores habituales.

## La sintaxis

```sql
función() OVER (PARTITION BY columna ORDER BY otra_columna)
```

- `PARTITION BY` define los grupos, sin colapsarlos.
- `ORDER BY` define el orden dentro de cada grupo.

## Último registro por grupo

Es uno de los problemas más comunes: el último pedido de cada cliente.

```sql
SELECT id, cliente_id, fecha, total
FROM (
    SELECT id, cliente_id, fecha, total,
           ROW_NUMBER() OVER (
               PARTITION BY cliente_id
               ORDER BY fecha DESC, id DESC
           ) AS orden
    FROM pedidos
) t
WHERE orden = 1;
```

Una función de ventana no puede aparecer directamente en `WHERE`, porque este se evalúa antes. Por eso se usa una subconsulta o un `WITH`.

En PostgreSQL, `DISTINCT ON` es una alternativa concisa:

```sql
SELECT DISTINCT ON (cliente_id) id, cliente_id, fecha, total
FROM pedidos
ORDER BY cliente_id, fecha DESC, id DESC;
```

## `ROW_NUMBER`, `RANK` y `DENSE_RANK`

Se diferencian en cómo tratan los empates:

| Ventas | `ROW_NUMBER` | `RANK` | `DENSE_RANK` |
|---|---|---|---|
| 100 | 1 | 1 | 1 |
| 100 | 2 | 1 | 1 |
| 80 | 3 | 3 | 2 |

Para deduplicar o paginar, usa `ROW_NUMBER`. Para clasificaciones, `RANK` o `DENSE_RANK` según quieras dejar huecos o no.

## Comparar con la fila anterior

`LAG` y `LEAD` acceden a filas vecinas sin una autounión:

```sql
SELECT mes, ingresos,
       ingresos - LAG(ingresos) OVER (ORDER BY mes) AS variacion
FROM ventas_mensuales;
```

La primera fila no tiene anterior, así que devuelve `NULL`. Para indicar un valor por defecto, se usa un tercer argumento: `LAG(ingresos, 1, 0)`.

## Acumulados y medias móviles

```sql
SELECT fecha, importe,
       SUM(importe) OVER (ORDER BY fecha) AS acumulado,
       AVG(importe) OVER (
           ORDER BY fecha
           ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       ) AS media_7_filas
FROM movimientos;
```

Con `ORDER BY`, el marco por defecto de una ventana es `RANGE`, y agrupa las filas con el mismo valor de ordenación. Si dos movimientos comparten fecha, ambos muestran el mismo acumulado. Si quieres una progresión fila a fila, indica `ROWS` explícitamente y añade un desempate:

```sql
SUM(importe) OVER (
    ORDER BY fecha, id
    ROWS UNBOUNDED PRECEDING
)
```

## Porcentaje sobre el total

```sql
SELECT producto, ventas,
       ROUND(100.0 * ventas / SUM(ventas) OVER (), 1) AS porcentaje
FROM ventas_por_producto;
```

`OVER ()`, sin nada dentro, toma todo el resultado como ventana.

## Eliminar duplicados conservando uno

```sql
WITH numeradas AS (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY email ORDER BY creado_en) AS orden
    FROM usuarios
)
DELETE FROM usuarios
WHERE id IN (SELECT id FROM numeradas WHERE orden > 1);
```

Lánzalo primero como `SELECT` para ver qué se va a borrar, y hazlo dentro de una transacción.

## Rendimiento

Las ventanas suelen requerir ordenación, que puede ser costosa con muchas filas. Un índice en el orden de `PARTITION BY` y `ORDER BY` puede evitarla. Si la consulta filtra, hazlo antes de la ventana. Y revisa siempre el plan: en tablas grandes, «último registro por grupo» puede resolverse mejor con otro enfoque, según la cantidad de filas de cada grupo.

## Referencias

- [Funciones de ventana en PostgreSQL](https://www.postgresql.org/docs/current/tutorial-window.html)
- [Cláusula OVER en SQL Server](https://learn.microsoft.com/sql/t-sql/queries/select-over-clause-transact-sql)
