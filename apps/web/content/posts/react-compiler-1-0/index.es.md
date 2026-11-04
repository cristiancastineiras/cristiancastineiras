---
title: "React Compiler 1.0: memoización automática sin llenar el código de useMemo"
seoTitle: "React Compiler 1.0: guía práctica"
description: "Qué hace React Compiler, cómo activarlo en Vite de forma gradual, qué reglas debe cumplir tu código y qué pasa con el useMemo y useCallback que ya tienes."
date: 2025-11-17
tags: ["React", "Vite", "Rendimiento"]
---

Durante años, optimizar React ha significado decidir a mano qué memoizar. Es tedioso y fácil de hacer mal: una dependencia olvidada produce datos obsoletos, y un objeto sin memoizar anula un `React.memo`. React Compiler, estable desde octubre de 2025, automatiza esa tarea en tiempo de compilación.

## Qué hace exactamente

El compilador analiza tus componentes y hooks, y añade la memoización necesaria en el resultado. Puede hacer cosas que no se pueden escribir a mano con `useMemo`, como memoizar un valor después de una rama condicional.

```tsx
function Pedidos({ pedidos, filtro }: Props) {
  const visibles = pedidos.filter((p) => p.estado === filtro);

  return (
    <ul>
      {visibles.map((p) => (
        <FilaPedido key={p.id} pedido={p} onAbrir={() => abrir(p.id)} />
      ))}
    </ul>
  );
}
```

Sin tocar este código, el compilador evita recalcular `visibles`, y estabiliza los valores cuyas entradas no han cambiado.

## Activarlo en Vite

```bash
pnpm add -D babel-plugin-react-compiler eslint-plugin-react-hooks
```

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: ["babel-plugin-react-compiler"],
      },
    }),
  ],
});
```

Funciona con React 17 en adelante, aunque por debajo de la versión 19 necesita además `react-compiler-runtime`.

## Las reglas de React dejan de ser opcionales

El compilador supone que tu código cumple las reglas: los componentes son funciones puras, y no se modifican props ni estado durante el render. Lo que incumple esto puede funcionar por casualidad sin compilador, y romperse con él.

```tsx
// Modifica una prop durante el render
function Lista({ items }: Props) {
  items.sort(ordenar);
  return <Tabla filas={items} />;
}

// Correcto
function Lista({ items }: Props) {
  const ordenados = items.toSorted(ordenar);
  return <Tabla filas={ordenados} />;
}
```

Cuando detecta algo que no puede optimizar con seguridad, omite ese componente y continúa. No rompe la compilación, solo pierde la mejora. Las reglas de `eslint-plugin-react-hooks` te lo muestran mientras programas, así que actívalas primero y corrige lo que señalen.

## Adopción gradual

En una aplicación grande yo no lo activaría de golpe. Puedes empezar por un directorio:

```ts
["babel-plugin-react-compiler", {
  sources: (nombre: string) => nombre.includes("src/features/pedidos"),
}]
```

También puedes usar un modo de anotación, con el que solo se compilan los componentes marcados:

```tsx
function Panel() {
  "use memo";
  // ...
}
```

Y si un componente concreto da problemas tras activarlo:

```tsx
function GraficaLegada() {
  "use no memo";
  // ...
}
```

Esa directiva debería ser temporal: deja un comentario y resuelve la causa.

## Qué hacer con useMemo y useCallback

No hace falta quitarlos: el compilador los tiene en cuenta. En código nuevo, puedes dejar de añadirlos por defecto, y usarlos si lo necesitas por una razón específica, como garantizar que un valor sea estable porque es dependencia de un efecto.

Su eliminación masiva no suele merecer la pena por sí sola. El riesgo de introducir errores es mayor que lo que se gana en limpieza.

## Lo que no resuelve

- Una consulta lenta o un componente con 10 000 filas: sigue siendo necesario paginar o virtualizar.
- Un estado colocado demasiado arriba: la estructura importa, aunque el impacto se reduzca.
- Un cálculo muy costoso la primera vez: la memoización solo ayuda en renders posteriores.

## Medir el resultado

Mide antes y después las interacciones más importantes con React Profiler. En DevTools, los componentes optimizados aparecen con una marca, lo que permite confirmar qué se ha compilado. El tamaño del bundle puede aumentar un poco.

## Referencias

- [Introducción a React Compiler](https://react.dev/learn/react-compiler)
- [Anuncio de React Compiler 1.0](https://react.dev/blog/2025/10/07/react-compiler-1)
- [Reglas de React](https://react.dev/reference/rules)
