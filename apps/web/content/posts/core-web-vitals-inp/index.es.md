---
title: "Mejorar INP: por qué tu web responde lento aunque cargue rápido"
seoTitle: "Mejorar INP en React y JavaScript"
description: "Qué mide Interaction to Next Paint, cómo identificar interacciones lentas con datos reales y cómo mejorarlo: dividir tareas largas, ceder el hilo y renderizar menos."
date: 2025-12-29
tags: ["Rendimiento", "React", "JavaScript"]
---

Una página puede cargar en un segundo y aun así sentirse lenta: haces clic en un filtro y nada cambia durante medio segundo. *Interaction to Next Paint* (INP) mide justo eso, y es una de las tres Core Web Vitals, junto con LCP y CLS.

## Qué mide

INP observa las interacciones durante toda la visita, como clics, toques y pulsaciones de teclas, y mide el tiempo hasta que el navegador puede pintar el resultado. Reporta un valor cercano a la peor interacción:

| INP | Valoración |
|---|---|
| Hasta 200 ms | Bueno |
| De 200 a 500 ms | Necesita mejorar |
| Más de 500 ms | Malo |

Google lo evalúa en el percentil 75 de las visitas reales, separando móvil y escritorio.

## Sus tres partes

```text
Clic → [retraso de entrada] → [tus manejadores] → [render y pintado] → Pantalla
```

1. **Retraso de entrada**: el hilo principal está ocupado con otra cosa.
2. **Procesamiento**: tu código responde al evento.
3. **Presentación**: el navegador calcula estilos, diseño y pinta.

Saber cuál domina indica qué hay que arreglar.

## Medir con usuarios reales

Tu portátil no se parece al móvil de un usuario medio. Con la librería `web-vitals`, puedes saber qué interacción lo causa:

```ts
import { onINP } from "web-vitals/attribution";

onINP(({ value, rating, attribution }) => {
  navigator.sendBeacon(
    "/metricas",
    JSON.stringify({
      valor: value,
      valoracion: rating,
      elemento: attribution.interactionTarget,
      retraso: attribution.inputDelay,
      procesamiento: attribution.processingDuration,
      presentacion: attribution.presentationDelay,
    }),
  );
});
```

Para investigar en local, abre el panel *Performance* de Chrome DevTools, activa una limitación de CPU de 4× y graba la interacción. Las tareas largas aparecen marcadas en rojo.

## Dividir las tareas largas

El navegador no puede responder mientras se ejecuta JavaScript. Cualquier tarea de más de 50 ms puede retrasar una interacción. La solución general es ceder el control de vez en cuando:

```ts
async function procesar(filas: Fila[]) {
  for (const [indice, fila] of filas.entries()) {
    calcular(fila);

    if (indice % 200 === 0) {
      await cederControl();
    }
  }
}

function cederControl() {
  if ("scheduler" in globalThis && "yield" in scheduler) {
    return scheduler.yield();
  }
  return new Promise((resolver) => setTimeout(resolver, 0));
}
```

`scheduler.yield()` da paso a lo pendiente y conserva la prioridad de tu tarea. Si el navegador no lo admite, `setTimeout` funciona como alternativa.

## Dar respuesta antes de hacer el trabajo

Lo que el usuario necesita es ver que algo ocurre. Muestra primero lo inmediato, y deja lo costoso para después del pintado:

```ts
boton.addEventListener("click", async () => {
  boton.setAttribute("aria-busy", "true");

  await cederControl(); // permite pintar el estado

  const resultado = calcularInforme();
  mostrar(resultado);

  boton.removeAttribute("aria-busy");
});
```

## En React

Las actualizaciones que renderizan mucho se pueden marcar como no urgentes:

```tsx
const [filtro, setFiltro] = useState("");
const [isPending, startTransition] = useTransition();
const [resultados, setResultados] = useState(productos);

function alCambiar(valor: string) {
  setFiltro(valor); // urgente: el input responde ya

  startTransition(() => {
    setResultados(filtrar(productos, valor)); // puede interrumpirse
  });
}
```

Si el usuario escribe otra letra durante el render, React lo descarta y empieza de nuevo. `useDeferredValue` logra lo mismo, cuando no controlas el origen del valor.

La otra palanca es renderizar menos. Mueve el estado hacia abajo, y virtualiza las listas largas. Sin esto, `startTransition` no hace más que aplazar el problema.

## Mover el trabajo fuera del hilo principal

Los cálculos intensivos que no necesitan el DOM, como procesar un archivo o transformar muchos datos, pueden ir a un Web Worker:

```ts
const trabajador = new Worker(new URL("./calculo.worker.ts", import.meta.url), {
  type: "module",
});

trabajador.postMessage(filas);
trabajador.onmessage = ({ data }) => mostrar(data);
```

## Otras causas habituales

- **Scripts de terceros**: analítica, chat o anuncios. Mide cuánto ocupan, y carga solo lo necesario.
- **DOM enorme**: cuantos más elementos, más caro es recalcular estilos.
- **Lectura y escritura alternas del DOM**: leer `offsetHeight` tras cambiar un estilo obliga a recalcular de inmediato. Agrupa las lecturas.
- **Hidratación**: durante la carga, una aplicación con mucho JavaScript no responde. Reduce lo que se hidrata.
- **Manejadores en `input` y `scroll`**: se ejecutan continuamente; aplica *debounce* si hacen trabajo pesado.

La propiedad CSS `content-visibility: auto` puede evitar el trabajo de renderizar lo que queda fuera de pantalla.

## Orden de trabajo

1. Obtén datos de campo, y localiza las interacciones lentas.
2. Reprodúcelas con limitación de CPU.
3. Determina qué parte domina.
4. Aplica una sola mejora, y mide de nuevo.

## Referencias

- [Interaction to Next Paint](https://web.dev/articles/inp)
- [Optimizar INP](https://web.dev/articles/optimize-inp)
- [web-vitals](https://github.com/GoogleChrome/web-vitals)
