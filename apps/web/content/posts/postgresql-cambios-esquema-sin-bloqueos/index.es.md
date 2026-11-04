---
title: "Cambiar un esquema de PostgreSQL en producción sin bloquear la aplicación"
seoTitle: "Cambios de esquema sin bloqueos"
description: "Cómo evitar colas de bloqueos al alterar tablas en PostgreSQL: lock_timeout, CREATE INDEX CONCURRENTLY, restricciones NOT VALID y cambios en dos fases."
date: 2026-06-22
tags: ["PostgreSQL", "SQL", "CI/CD"]
---

Un `ALTER TABLE` que tarda 5 ms puede tumbar una aplicación. No por lo que hace, sino por lo que espera: si necesita un bloqueo exclusivo y hay una consulta larga en curso, se queda esperando, y cualquier consulta nueva sobre esa tabla se pone en cola detrás.

## La trampa de la cola de bloqueos

```text
Transacción larga (SELECT, 2 min)  → tiene ACCESS SHARE
ALTER TABLE                        → espera ACCESS EXCLUSIVE
Todas las demás consultas          → esperan detrás del ALTER
```

Una tabla con mucho tráfico puede quedar inaccesible durante toda la consulta larga, aunque la modificación sea instantánea.

## Siempre con `lock_timeout`

Limitar la espera evita ese efecto dominó. Es preferible fallar y reintentar:

```sql
SET lock_timeout = '2s';
SET statement_timeout = '30s';

ALTER TABLE pedidos ADD COLUMN notas text;
```

Si no consigue el bloqueo a tiempo, falla sin haber hecho daño, y se puede reintentar en bucle desde el script del despliegue.

## Añadir columnas

Desde PostgreSQL 11, añadir una columna con valor por defecto constante no reescribe la tabla:

```sql
ALTER TABLE pedidos ADD COLUMN activo boolean NOT NULL DEFAULT true;
```

Cuidado con los valores no constantes, como `random()`. Estos sí reescriben toda la tabla, y `now()` se evalúa una vez, así que no provoca una reescritura.

## Índices

Un `CREATE INDEX` normal bloquea las escrituras durante la creación. La alternativa es:

```sql
CREATE INDEX CONCURRENTLY ix_pedidos_fecha ON pedidos (fecha);
```

Es más lento, no admite una transacción y, si falla, deja un índice inválido que hay que eliminar:

```sql
SELECT indexrelid::regclass
FROM pg_index
WHERE NOT indisvalid;

DROP INDEX CONCURRENTLY ix_pedidos_fecha;
```

Después, compruébalo antes de darlo por terminado. Un índice inválido no se usa en las consultas, pero sigue teniendo coste en las escrituras.

## Claves foráneas y CHECK

Validar una restricción sobre una tabla grande lleva tiempo. Se puede dividir en dos pasos:

```sql
ALTER TABLE pedidos
    ADD CONSTRAINT fk_pedidos_cliente
    FOREIGN KEY (cliente_id) REFERENCES clientes (id)
    NOT VALID;

ALTER TABLE pedidos VALIDATE CONSTRAINT fk_pedidos_cliente;
```

El primer paso es rápido y ya exige la restricción a las filas nuevas. El segundo revisa las existentes con un bloqueo mucho más suave, que permite leer y escribir.

## Hacer una columna NOT NULL

`SET NOT NULL` recorre la tabla entera con un bloqueo exclusivo. Pero si existe una restricción `CHECK` válida que garantiza lo mismo, PostgreSQL se ahorra ese recorrido:

```sql
ALTER TABLE pedidos
    ADD CONSTRAINT ck_notas_not_null CHECK (notas IS NOT NULL) NOT VALID;

ALTER TABLE pedidos VALIDATE CONSTRAINT ck_notas_not_null;

ALTER TABLE pedidos ALTER COLUMN notas SET NOT NULL;

ALTER TABLE pedidos DROP CONSTRAINT ck_notas_not_null;
```

## Cambiar el tipo de una columna

Muchos cambios de tipo reescriben la tabla, con bloqueo exclusivo mientras dura. Algunos no, como ampliar `varchar(50)` a `varchar(100)`. Para el resto, el método seguro es el habitual:

1. añadir la columna nueva;
2. escribir en ambas desde la aplicación o con un disparador;
3. rellenar por lotes;
4. cambiar las lecturas;
5. eliminar la antigua.

## Rellenar por lotes

Un único `UPDATE` de millones de filas genera una transacción larga, mucha actividad de WAL y retraso en las réplicas. Es mejor actualizar por tramos:

```sql
UPDATE pedidos
SET estado_nuevo = estado
WHERE id BETWEEN 1 AND 10000
  AND estado_nuevo IS NULL;
```

Haz una transacción por cada lote, con una pausa entre ellos si la carga es alta.

## Probar antes

Prueba sobre una copia con volumen real y vigila `pg_stat_activity` durante el cambio. Un script que tarda milisegundos con 100 filas puede comportarse de forma muy distinta con 100 millones.

## Referencias

- [Modos de bloqueo en PostgreSQL](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Creación de índices concurrentes](https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY)
- [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
