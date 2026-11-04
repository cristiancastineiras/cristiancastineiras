---
title: "Índices compuestos en SQL: por qué importa el orden de las columnas"
seoTitle: "Índices compuestos: orden de columnas"
description: "Cómo funciona un índice compuesto, qué consultas puede servir, por qué el orden es decisivo y cómo evitar índices redundantes en SQL Server y PostgreSQL."
date: 2025-07-28
tags: ["SQL", "PostgreSQL", "Rendimiento"]
---

Un índice sobre `(cliente_id, fecha)` y otro sobre `(fecha, cliente_id)` contienen los mismos datos, pero no sirven para lo mismo. Saber por qué permite diseñar menos índices, y mejores.

## La analogía de la guía telefónica

Una guía está ordenada por apellido y, dentro de cada apellido, por nombre. Encontrar «García, Ana» es inmediato, y también listar todos los García. Pero encontrar a todas las Anas obliga a recorrer la guía entera.

Un índice compuesto funciona de la misma forma: ordena por la primera columna y, a igualdad de esta, por la segunda.

```sql
CREATE INDEX ix_pedidos_cliente_fecha ON pedidos (cliente_id, fecha);
```

## Qué consultas aprovechan este índice

```sql
-- Sí: búsqueda directa por ambas columnas
SELECT * FROM pedidos WHERE cliente_id = 7 AND fecha >= '2025-01-01';

-- Sí: usa la primera columna
SELECT * FROM pedidos WHERE cliente_id = 7;

-- Sí, y sin ordenar después: el índice ya está en ese orden
SELECT * FROM pedidos WHERE cliente_id = 7 ORDER BY fecha DESC LIMIT 20;

-- Mal: la primera columna no se filtra
SELECT * FROM pedidos WHERE fecha >= '2025-01-01';
```

PostgreSQL 18, todavía en beta, incorpora *skip scan*, que en algunos casos aprovecha el índice aunque falte la primera columna, si esta tiene pocos valores distintos. SQL Server y otros motores pueden recorrer el índice completo. Son mejoras útiles, pero no sustituyen un índice adecuado.

## La regla práctica para el orden

1. Primero, las columnas filtradas por **igualdad**.
2. Después, las de **rango** u **ordenación**.
3. Lo que venga después de un rango ya no ayuda a acotar la búsqueda.

```sql
-- Consulta
SELECT id, total FROM pedidos
WHERE estado = 'pendiente' AND cliente_id = 7 AND fecha >= '2025-01-01';

-- Bien: igualdades primero, rango al final
CREATE INDEX ix_a ON pedidos (cliente_id, estado, fecha);

-- Peor: tras el rango en fecha, las demás no acotan la búsqueda
CREATE INDEX ix_b ON pedidos (fecha, cliente_id, estado);
```

Con varias igualdades, se dice a menudo que hay que empezar por la más selectiva. Influye menos de lo que parece. Es más importante pensar qué otras consultas podrían compartir el índice: si muchas filtran por `cliente_id` en solitario, esa columna debería ir primero.

## Índices de cobertura

Si el índice contiene todas las columnas que pide la consulta, no hace falta visitar la tabla:

```sql
-- PostgreSQL 11 o superior y SQL Server
CREATE INDEX ix_pedidos_cliente_cobertura
    ON pedidos (cliente_id, fecha) INCLUDE (total);
```

Las columnas de `INCLUDE` no forman parte de la clave de ordenación. Se guardan solo para devolverse. Este truco es muy efectivo en listados frecuentes, aunque hace el índice más grande.

## Índices redundantes

Si existe `(cliente_id, fecha)`, un índice aparte sobre `(cliente_id)` es normalmente redundante. Cada índice ocupa espacio y ralentiza las escrituras, así que conviene eliminar los innecesarios.

En PostgreSQL puedes ver los que no se usan:

```sql
SELECT relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY relname;
```

Antes de borrarlo, recuerda que estas estadísticas son desde el último reinicio de contadores, y que no cubren las réplicas. Un índice también puede sostener una restricción de unicidad o usarse solo en un informe mensual.

## Comprobar siempre

La teoría indica qué debería pasar. El plan de ejecución dice qué pasa de verdad, y depende de tus datos: una columna con muy pocos valores distintos puede hacer que el motor prefiera recorrer la tabla. Compara los planes, con un volumen de datos parecido al de producción, antes de dar un índice por bueno.

## Referencias

- [Índices multicolumna en PostgreSQL](https://www.postgresql.org/docs/current/indexes-multicolumn.html)
- [Use The Index, Luke](https://use-the-index-luke.com/)
