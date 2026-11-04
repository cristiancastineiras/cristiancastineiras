---
title: "Zustand en aplicaciones reales: selectores, slices y persistencia"
seoTitle: "Zustand: selectores, slices y persist"
description: "Cómo evitar renders innecesarios con selectores en Zustand, organizar un store grande con slices y persistir solo lo necesario sin guardar datos sensibles."
date: 2025-04-07
tags: ["React", "Zustand", "TypeScript"]
---

Zustand es pequeño y se aprende en minutos. Precisamente por eso es fácil usarlo de una forma que provoca renders innecesarios o un store demasiado grande. Algunas pautas lo mantienen bajo control.

## Un store mínimo

```ts
import { create } from "zustand";

type EstadoInterfaz = {
  barraAbierta: boolean;
  alternarBarra: () => void;
};

export const useInterfaz = create<EstadoInterfaz>()((set) => ({
  barraAbierta: true,
  alternarBarra: () =>
    set((estado) => ({ barraAbierta: !estado.barraAbierta })),
}));
```

No hay proveedor, ni reductores ni acciones aparte.

## Selecciona solo lo que uses

```tsx
// Mal: se vuelve a renderizar con cualquier cambio del store
const { barraAbierta } = useInterfaz();

// Bien: solo cuando cambia este valor
const barraAbierta = useInterfaz((estado) => estado.barraAbierta);
```

Zustand compara el resultado del selector con `Object.is`. Si devuelve un objeto nuevo cada vez, se considerará distinto siempre:

```tsx
// Mal: objeto nuevo en cada ejecución.
// En Zustand 5 puede provocar un bucle infinito de renders.
const { nombre, email } = useUsuario((s) => ({ nombre: s.nombre, email: s.email }));
```

Para eso existe `useShallow`:

```tsx
import { useShallow } from "zustand/react/shallow";

const { nombre, email } = useUsuario(
  useShallow((s) => ({ nombre: s.nombre, email: s.email })),
);
```

## Exportar hooks con intención

Para evitar repetir selectores y que cada componente conozca la forma interna del store:

```ts
export const useBarraAbierta = () => useInterfaz((s) => s.barraAbierta);
export const useAlternarBarra = () => useInterfaz((s) => s.alternarBarra);
```

Las acciones no cambian nunca, de modo que seleccionarlas no causa renders.

## Dividir en slices

Si un store crece, puedes componerlo por partes:

```ts
import { create, type StateCreator } from "zustand";

type CarritoSlice = {
  lineas: Linea[];
  anadir: (linea: Linea) => void;
};

type InterfazSlice = {
  carritoVisible: boolean;
  mostrarCarrito: (visible: boolean) => void;
};

type Tienda = CarritoSlice & InterfazSlice;

const crearCarrito: StateCreator<Tienda, [], [], CarritoSlice> = (set) => ({
  lineas: [],
  anadir: (linea) => set((s) => ({ lineas: [...s.lineas, linea] })),
});

const crearInterfaz: StateCreator<Tienda, [], [], InterfazSlice> = (set) => ({
  carritoVisible: false,
  mostrarCarrito: (carritoVisible) => set({ carritoVisible }),
});

export const useTienda = create<Tienda>()((...a) => ({
  ...crearCarrito(...a),
  ...crearInterfaz(...a),
}));
```

Antes de dividir, pregúntate si necesitas un solo store. En Zustand, varios stores pequeños e independientes suelen ser más sencillos, salvo que necesiten actualizarse juntos.

## Persistir solo lo necesario

```ts
import { persist } from "zustand/middleware";

export const usePreferencias = create<Preferencias>()(
  persist(
    (set) => ({
      tema: "sistema",
      filas: 25,
      setTema: (tema) => set({ tema }),
    }),
    {
      name: "preferencias",
      version: 1,
      partialize: (s) => ({ tema: s.tema, filas: s.filas }),
    },
  ),
);
```

Tres recomendaciones:

- **`partialize`**: sin él se persiste todo lo serializable, incluido el estado temporal.
- **`version` y `migrate`**: lo que se guarda en el navegador sobrevive a tus despliegues. Si cambias la forma, necesitarás migrar.
- **No guardes secretos.** `localStorage` es accesible para cualquier script de la página, por lo que un XSS podría leer un token guardado ahí.

## Lo que no debería estar en el store

Las respuestas de la API suelen estar mejor en una librería de estado de servidor, y el estado que solo interesa a un componente debería quedarse en `useState`. Un store global con todo dentro hace que cualquier cambio tenga un alcance difícil de razonar.

## Probarlo

Un store también se puede usar fuera de React, lo que simplifica mucho las pruebas:

```ts
useTienda.setState({ lineas: [] });

useTienda.getState().anadir({ id: 1, cantidad: 2 });

expect(useTienda.getState().lineas).toHaveLength(1);
```

Como el store es global dentro del módulo, reinícialo entre pruebas para evitar dependencias entre ellas.

## Referencias

- [Documentación de Zustand](https://zustand.docs.pmnd.rs/)
- [Migración a Zustand v5](https://zustand.docs.pmnd.rs/migrations/migrating-to-v5)
