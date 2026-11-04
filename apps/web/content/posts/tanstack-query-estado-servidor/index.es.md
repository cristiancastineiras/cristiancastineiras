---
title: "Estado de servidor y de cliente: por qué TanStack Query simplifica tu frontend"
seoTitle: "TanStack Query: estado de servidor"
description: "Separar estado de servidor y de cliente elimina mucho código: caché, deduplicación, invalidación y actualizaciones optimistas con TanStack Query y TypeScript."
date: 2025-03-17
tags: ["React", "TanStack Query", "TypeScript"]
---

Muchas aplicaciones React guardan en un store global lo que devuelve la API, y luego escriben a mano los indicadores de carga, los errores, la caché, la recarga y la invalidación. Casi todo ese código desaparece si se separan dos tipos de estado muy distintos.

## Dos tipos de estado

- **Estado de cliente**: pertenece al navegador. Un menú abierto, la pestaña activa, un filtro antes de aplicarlo.
- **Estado de servidor**: pertenece a otro sistema. Lo que tienes es una copia que puede quedarse obsoleta, y que otras personas pueden cambiar.

Tratar el segundo como el primero obliga a reimplementar una caché, y las cachés son difíciles.

## Una consulta

```tsx
import { useQuery } from "@tanstack/react-query";

function Cliente({ id }: { id: number }) {
  const { data, isPending, isError } = useQuery({
    queryKey: ["clientes", id],
    queryFn: ({ signal }) => obtenerCliente(id, signal),
    staleTime: 60_000,
  });

  if (isPending) return <p>Cargando…</p>;
  if (isError) return <p role="alert">No se ha podido cargar el cliente.</p>;

  return <h2>{data.nombre}</h2>;
}
```

Con esas líneas ya tienes:

- caché por clave: si dos componentes piden lo mismo, solo sale una petición;
- recarga en segundo plano y al volver a la ventana;
- reintentos ante errores;
- cancelación mediante `signal`, y sin condiciones de carrera entre respuestas.

## Dos tiempos que conviene distinguir

- **`staleTime`**: cuánto tiempo se considera fresco un dato. Por defecto es 0, por lo que se revalida a menudo.
- **`gcTime`**: cuánto se conserva en memoria cuando nadie lo usa. Por defecto, 5 minutos.

Si ves demasiadas peticiones, normalmente la solución es un `staleTime` mayor.

## Las claves son dependencias

Todo lo que afecta a la respuesta debe estar en la clave:

```tsx
useQuery({
  queryKey: ["pedidos", { clienteId, estado, pagina }],
  queryFn: () => listarPedidos({ clienteId, estado, pagina }),
});
```

Si falta un filtro, verás datos del filtro anterior. Centraliza las claves con `queryOptions` para no repetirlas:

```ts
import { queryOptions } from "@tanstack/react-query";

export const clienteQuery = (id: number) =>
  queryOptions({
    queryKey: ["clientes", id],
    queryFn: ({ signal }) => obtenerCliente(id, signal),
  });
```

## Escribir e invalidar

Tras una mutación, invalida lo afectado, y las consultas activas se recargarán:

```tsx
const queryClient = useQueryClient();

const guardar = useMutation({
  mutationFn: actualizarCliente,
  onSuccess: (_datos, variables) =>
    queryClient.invalidateQueries({ queryKey: ["clientes", variables.id] }),
});
```

Las claves son jerárquicas: invalidar `["clientes"]` también afecta a `["clientes", 7]`. Es la manera sencilla de no tener que saber exactamente qué listas contienen qué registros.

## Paginación sin parpadeos

Mantén los datos anteriores en pantalla mientras llegan los siguientes:

```tsx
import { keepPreviousData } from "@tanstack/react-query";

useQuery({
  queryKey: ["pedidos", pagina],
  queryFn: () => listarPedidos(pagina),
  placeholderData: keepPreviousData,
});
```

## Qué queda para el store global

Después de esto, el store global suele quedar muy pequeño: tema, preferencias de la interfaz y algún estado compartido entre pantallas. Para eso basta algo ligero, como Zustand.

Lo que debes evitar es copiar la respuesta de `useQuery` a un store o a un `useState`: tendrías otra vez dos fuentes de verdad, y la copia dejaría de recibir actualizaciones.

## Con clientes generados

Si generas el cliente desde OpenAPI, el tipo de `data` viene del contrato. Algunos generadores pueden crear también las opciones de consulta, lo que reduce todavía más el código repetido.

## Referencias

- [TanStack Query](https://tanstack.com/query/latest)
- [Important Defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults)
