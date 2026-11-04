---
title: "Encontrar renders innecesarios con React Profiler en lugar de adivinar"
seoTitle: "React Profiler: renders innecesarios"
description: "Cómo usar React DevTools Profiler para localizar el componente lento, entender por qué se renderiza y decidir si memo, mover estado o virtualizar es la solución."
date: 2025-08-18
tags: ["React", "Rendimiento"]
---

Cuando una interfaz va lenta, la reacción habitual es llenarla de `useMemo` y `React.memo`. Sin medir primero, solo se añade complejidad sin saber si ayuda. Las herramientas de React indican exactamente qué pasa.

## Antes de nada

Un render no es un problema por sí mismo. React renderiza, compara y solo toca el DOM si algo cambia. Un render de 0,2 ms no merece ninguna atención. Lo que importa es que la interacción se note lenta.

Además, mide en una compilación de producción o usando el perfilador sobre una acción concreta. El modo de desarrollo es bastante más lento, y `StrictMode` duplica ciertos renders a propósito.

## Grabar una interacción

En React DevTools, abre la pestaña **Profiler**:

1. en la configuración, activa *Record why each component rendered while profiling*;
2. pulsa grabar;
3. haz la acción lenta, solo esa;
4. detén la grabación.

El gráfico muestra cada componente en un *commit*, con su tiempo. Los colores más cálidos indican que tarda más. Si seleccionas uno, verás por qué se ha renderizado: cambio de props, cambio de estado, un hook, o porque se ha renderizado su padre.

## Causa 1: el estado está demasiado arriba

```tsx
function Pagina() {
  const [busqueda, setBusqueda] = useState("");

  return (
    <>
      <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
      <TablaEnorme />
    </>
  );
}
```

Cada tecla renderiza `TablaEnorme`, aunque no dependa de `busqueda`. La mejor solución no requiere memoización, sino mover el estado hacia abajo:

```tsx
function Buscador() {
  const [busqueda, setBusqueda] = useState("");
  return <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />;
}

function Pagina() {
  return (
    <>
      <Buscador />
      <TablaEnorme />
    </>
  );
}
```

## Causa 2: props nuevas en cada render

`React.memo` compara las props de forma superficial, por lo que un objeto o una función nueva lo invalidan:

```tsx
// memo no sirve: `opciones` es un objeto nuevo en cada render
<Tabla filas={filas} opciones={{ compacta: true }} onSeleccionar={(id) => seleccionar(id)} />
```

Hay que estabilizarlas si de verdad lo necesitas:

```tsx
const opciones = useMemo(() => ({ compacta: true }), []);
const alSeleccionar = useCallback((id: number) => seleccionar(id), [seleccionar]);
```

Y la constante podría definirse fuera del componente, que es aún más simple.

## Causa 3: un contexto demasiado amplio

Cualquier consumidor de un contexto se vuelve a renderizar cuando cambia su valor. Si metes el usuario, el tema y los filtros en un mismo contexto, cada cambio de filtro renderiza todo lo que muestra el nombre de usuario. Sepáralo en varios contextos, o usa un store con selectores.

## Causa 4: demasiados elementos

Si el problema es que hay 10 000 filas, no lo arregla ninguna memoización. La solución es renderizar menos: paginar o virtualizar con una librería como TanStack Virtual, que solo mantiene en el DOM lo visible.

## Causa 5: trabajo costoso que puede esperar

A veces la operación es cara y se puede priorizar. `useDeferredValue` permite que el input responda mientras la lista se actualiza después:

```tsx
const busquedaDiferida = useDeferredValue(busqueda);
const resultados = useMemo(
  () => filtrar(productos, busquedaDiferida),
  [productos, busquedaDiferida],
);
```

## Medir en producción

Lo que notan los usuarios es lo que cuenta. Mide INP con datos de campo, y usa el perfilador para encontrar la causa de lo que esos datos indican.

También existe el componente `<Profiler>`, que permite medir programáticamente, aunque está desactivado en las compilaciones normales de producción.

## Un orden de trabajo

1. Reproduce y graba la interacción lenta.
2. Identifica el componente que consume más tiempo.
3. Comprueba por qué se ha renderizado.
4. Prueba en este orden: mover estado, dividir componentes, renderizar menos y, por último, memoizar.
5. Vuelve a grabar para confirmar la mejora.

## Referencias

- [Referencia de Profiler](https://react.dev/reference/react/Profiler)
- [useDeferredValue](https://react.dev/reference/react/useDeferredValue)
