---
title: "JSONB en PostgreSQL: cuándo usarlo y cuándo es mejor crear columnas"
seoTitle: "JSONB en PostgreSQL: cuándo usarlo"
description: "Qué aporta JSONB frente a un esquema relacional, cómo indexarlo con GIN o índices de expresión y las señales de que estás usando un documento donde hace falta una tabla."
date: 2025-11-10
tags: ["PostgreSQL", "SQL", "Arquitectura"]
---

JSONB da la flexibilidad de un almacén de documentos dentro de una base de datos relacional. Es muy útil, y muy fácil de usar en exceso: una columna `datos jsonb` puede acabar conteniendo lo que debería ser un modelo bien definido.

## JSON o JSONB

`json` guarda el texto tal cual. `jsonb` lo guarda en formato binario, descarta duplicados y espacios, y permite indexar. Salvo que necesites conservar el texto exacto, usa `jsonb`.

## Cuándo encaja

- **Datos de estructura variable**: atributos de producto que dependen de la categoría.
- **Datos externos**: la respuesta de un proveedor o un webhook, que quieres conservar íntegros.
- **Configuraciones y preferencias**: se leen y escriben en bloque, sin consultas analíticas.
- **Instantáneas**: el contenido de una factura en el momento en que se emitió, aunque luego cambien los datos de referencia.

## Cuándo no

- Se filtra, ordena o agrupa por ese campo en muchas consultas.
- Hace falta integridad referencial: un JSON no admite claves foráneas.
- Se actualizan con frecuencia campos sueltos de un documento grande, porque se reescribe la fila completa.
- Todos los documentos tienen la misma estructura. Si es así, ya tienes un esquema: declara las columnas.

## Consultar

```sql
SELECT id, atributos ->> 'color' AS color
FROM productos
WHERE atributos @> '{"marca": "Acme"}';
```

- `->` devuelve JSONB.
- `->>` devuelve texto.
- `@>` comprueba si contiene un fragmento.

El tipo devuelto importa: `atributos ->> 'stock'` es texto, y comparar como texto da resultados incorrectos, como `'9' > '10'`. Hay que convertirlo:

```sql
WHERE (atributos ->> 'stock')::int > 10
```

## Indexar

Un índice GIN acelera `@>` y las comprobaciones de existencia de claves sobre todo el documento:

```sql
CREATE INDEX ix_productos_atributos
    ON productos USING GIN (atributos jsonb_path_ops);
```

`jsonb_path_ops` es más pequeño y rápido, pero solo admite operadores como `@>`. Sin esa opción, también admite `?`, que comprueba si existe una clave.

Si consultas con frecuencia una clave concreta, es mejor un índice de expresión:

```sql
CREATE INDEX ix_productos_marca
    ON productos ((atributos ->> 'marca'));
```

Solo se usará si la consulta contiene exactamente la misma expresión.

## Lo mejor de ambos mundos: columnas generadas

Si un campo del documento empieza a ser importante, promuévelo a columna sin duplicar la lógica en la aplicación:

```sql
ALTER TABLE productos
    ADD COLUMN marca text
    GENERATED ALWAYS AS (atributos ->> 'marca') STORED;

CREATE INDEX ix_productos_marca_col ON productos (marca);
```

Ten en cuenta que añadir una columna `STORED` reescribe la tabla y la bloquea mientras tanto, así que en tablas grandes hay que planificarlo.

## Validar

JSONB admite cualquier JSON válido, sin imponer ninguna forma. Una restricción `CHECK` protege lo imprescindible:

```sql
ALTER TABLE productos
    ADD CONSTRAINT ck_atributos_objeto
    CHECK (jsonb_typeof(atributos) = 'object' AND atributos ? 'marca');
```

Sin esto, la validación solo vive en la aplicación, y cualquier otro proceso puede escribir lo que quiera.

## Con EF Core

Npgsql permite mapear JSONB a tipos de .NET, y EF Core traduce las consultas a SQL:

```csharp
modelBuilder.Entity<Producto>()
    .OwnsOne(p => p.Atributos, b => b.ToJson());
```

Declarar un tipo en C# también da algo de estructura al documento, aunque los datos antiguos con otra forma pueden fallar al leerse. Planifica esos cambios como si fuesen una migración de esquema.

## Una señal de alarma

Si dentro de tu JSON hay un array de objetos que necesitas filtrar y unir con otras tablas, lo más probable es que sea una tabla. JSONB es para datos que viven dentro de una fila, no para modelar relaciones.

## Referencias

- [Tipos JSON en PostgreSQL](https://www.postgresql.org/docs/current/datatype-json.html)
- [Funciones y operadores JSON](https://www.postgresql.org/docs/current/functions-json.html)
