---
title: "Paginación por offset o por cursor: cuál elegir en una API"
seoTitle: "Paginación offset o cursor en APIs"
description: "Por qué OFFSET se vuelve lento y cómo implementar paginación por cursor en SQL y EF Core sin saltarse filas, además de cuándo offset sigue siendo la mejor opción."
date: 2025-12-01
tags: ["SQL", "REST", "Rendimiento"]
---

La paginación parece un detalle hasta que una tabla crece. `LIMIT 20 OFFSET 200000` funciona, pero obliga a la base de datos a recorrer 200 020 filas para devolver 20. Y si se insertan filas mientras alguien navega, pueden aparecer duplicados o saltos.

## Offset: simple y flexible

```sql
SELECT id, fecha, importe
FROM pedidos
ORDER BY fecha DESC, id DESC
LIMIT 20 OFFSET 40;
```

Ventajas: permite saltar a cualquier página y es trivial de implementar. Inconvenientes: el coste crece con la profundidad y es inestable ante cambios concurrentes.

Sigue siendo la opción correcta en muchos casos: listados administrativos con pocos miles de filas, resultados con números de página o conjuntos que rara vez cambian.

## Cursor: estable y constante

También se conoce como *keyset pagination*. En vez de decir «salta 40 filas», se dice «dame lo que viene después de esta fila»:

```sql
SELECT id, fecha, importe
FROM pedidos
WHERE (fecha, id) < ('2025-11-20 10:30:00+00', 8123)
ORDER BY fecha DESC, id DESC
LIMIT 20;
```

Con un índice en `(fecha DESC, id DESC)`, la base de datos va directamente al punto de partida. El coste es casi igual en la página 2 y en la 20 000, y una inserción concurrente no desplaza nada.

La columna `id` es imprescindible como desempate. Si varias filas comparten fecha y el orden no es total, algunas se repetirán o se perderán entre páginas.

## Implementarlo en EF Core

La comparación de filas no siempre se traduce directamente, así que se escribe de forma expandida:

```csharp
var consulta = db.Pedidos.AsNoTracking();

if (cursor is not null)
{
    consulta = consulta.Where(p =>
        p.Fecha < cursor.Fecha ||
        (p.Fecha == cursor.Fecha && p.Id < cursor.Id));
}

var pagina = await consulta
    .OrderByDescending(p => p.Fecha)
    .ThenByDescending(p => p.Id)
    .Take(tamano + 1)
    .ToListAsync(ct);

var hayMas = pagina.Count > tamano;
```

Pedir `tamano + 1` indica si hay más resultados sin un `COUNT` adicional, que puede ser caro.

## El cursor como valor opaco

No expongas sus columnas al cliente como contrato. Devuélvelo codificado:

```json
{
  "items": [],
  "nextCursor": "eyJmIjoiMjAyNS0xMS0yMFQxMDozMDowMFoiLCJpIjo4MTIzfQ"
}
```

```csharp
public static string Codificar(Cursor cursor) =>
    Base64Url.EncodeToString(JsonSerializer.SerializeToUtf8Bytes(cursor));
```

Si el formato es opaco, puedes cambiarlo más adelante sin romper a nadie. Eso sí, el cursor llega del cliente, así que hay que validarlo y tratarlo como cualquier otra entrada no fiable. Un valor mal formado debe devolver un 400, no un 500.

## Lo que se pierde

- **Saltar a una página concreta.** Encaja con «cargar más» o scroll infinito, pero no con una lista de números de página.
- **Total de resultados.** Es independiente del método, y un `COUNT(*)` en tablas grandes es costoso. Considera aproximarlo o eliminarlo de la interfaz.
- **Ordenación arbitraria.** Cada ordenación necesita su índice y su cursor. Si tu tabla permite ordenar por diez columnas, el coste es alto.

## Cómo decidir

- Tablas pequeñas o listados con páginas numeradas: offset.
- Feeds, exportaciones, APIs públicas o tablas que crecen sin límite: cursor.

También puedes limitar la profundidad en offset, como hacen muchos buscadores, en lugar de soportar `OFFSET 5000000`.

## Referencias

- [LIMIT y OFFSET en PostgreSQL](https://www.postgresql.org/docs/current/queries-limit.html)
- [Paginación en EF Core](https://learn.microsoft.com/ef/core/querying/pagination)
