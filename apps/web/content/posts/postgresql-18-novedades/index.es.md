---
title: "PostgreSQL 18: E/S asíncrona, uuidv7 y lo que merece una actualización"
seoTitle: "Novedades de PostgreSQL 18"
description: "Las novedades prácticas de PostgreSQL 18: E/S asíncrona, uuidv7, columnas generadas virtuales, skip scan y estadísticas que se conservan al actualizar con pg_upgrade."
date: 2025-12-15
tags: ["PostgreSQL", "SQL", "Rendimiento"]
---

PostgreSQL 18 salió en septiembre de 2025. Como suele ocurrir en este proyecto, no hay una única novedad espectacular, sino varias mejoras que resuelven problemas cotidianos. Estas son las que más me interesan para aplicaciones normales.

## E/S asíncrona

Hasta ahora, cada proceso esperaba a que terminase cada lectura de disco. El nuevo subsistema de E/S asíncrona permite pedir varias a la vez, lo que mejora recorridos secuenciales, *bitmap heap scans* y `VACUUM`, sobre todo en almacenamiento en red.

Se controla con el parámetro `io_method`:

```text
io_method = worker    # valor por defecto
io_method = io_uring  # Linux, según cómo se haya compilado
io_method = sync      # comportamiento anterior
```

La mejora depende mucho de la carga y del tipo de disco, así que mide con tus propios datos antes de prometer cifras.

## uuidv7

Los UUID v4 son aleatorios, de modo que cada inserción acaba en un punto cualquiera del índice. Esto fragmenta y empeora la localidad en tablas grandes. `uuidv7()` empieza con una marca de tiempo, por lo que los valores son aproximadamente crecientes:

```sql
CREATE TABLE pedidos (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    total numeric NOT NULL
);
```

Tiene una contrapartida: el identificador revela cuándo se creó el registro. Si eso es sensible, no lo expongas directamente en URLs públicas.

## Columnas generadas virtuales

Las columnas generadas ahora son virtuales por defecto: se calculan al leerlas y no ocupan espacio.

```sql
ALTER TABLE lineas
    ADD COLUMN total numeric GENERATED ALWAYS AS (cantidad * precio);
```

Sus ventajas son evidentes: añadirlas no reescribe la tabla. A cambio, en esta versión no se pueden indexar. Si necesitas un índice, sigue usando `STORED`.

## Skip scan

Antes, un índice `(region, fecha)` servía de poco en una consulta que filtrase solo por `fecha`. Ahora, si `region` tiene pocos valores distintos, PostgreSQL puede saltar entre ellos y aprovecharlo.

Esto puede ahorrar algún índice, pero no sustituye a uno bien diseñado.

## `RETURNING` con valores antiguos y nuevos

Se puede acceder a ambos en la misma sentencia:

```sql
UPDATE cuentas
SET saldo = saldo - 100
WHERE id = 1
RETURNING old.saldo AS antes, new.saldo AS despues;
```

Es útil para auditoría, sin necesidad de un `SELECT` previo ni de un disparador.

## Restricciones temporales

Las claves primarias y únicas admiten `WITHOUT OVERLAPS`, para impedir periodos solapados:

```sql
CREATE TABLE reservas (
    sala_id int,
    periodo tstzrange,
    PRIMARY KEY (sala_id, periodo WITHOUT OVERLAPS)
);
```

Necesita la extensión `btree_gist`. Antes, esto había que resolverlo con una restricción `EXCLUDE`.

## Actualizaciones más suaves

Tras una actualización mayor, las consultas podían ir lentas hasta que `ANALYZE` regeneraba las estadísticas. Ahora, `pg_upgrade` conserva gran parte de ellas.

Hay que revisar una novedad: `initdb` activa por defecto las sumas de comprobación de datos, y `pg_upgrade` exige que coincidan en el clúster antiguo y el nuevo. Si tu clúster antiguo no las tiene, inicializa el nuevo con `--no-data-checksums`.

También cambia la autenticación: MD5 queda obsoleto y SCRAM es el camino. Si aún lo usas, migra antes de que se retire.

## ¿Actualizar ya?

Antes de hacerlo:

1. comprueba compatibilidad de extensiones y drivers;
2. repite la actualización en un entorno de pruebas con una copia real;
3. compara el rendimiento de las consultas críticas;
4. lee las notas de migración, especialmente la sección de incompatibilidades.

Si tu versión actual aún tiene soporte, no hay prisa. Cada versión mayor recibe correcciones durante cinco años.

## Referencias

- [Anuncio de PostgreSQL 18](https://www.postgresql.org/about/news/postgresql-18-released-3142/)
- [Notas de la versión 18](https://www.postgresql.org/docs/18/release-18.html)
