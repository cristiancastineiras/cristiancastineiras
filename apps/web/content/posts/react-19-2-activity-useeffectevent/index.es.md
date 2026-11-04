---
title: "React 19.2: Activity y useEffectEvent, dos soluciones a problemas de siempre"
seoTitle: "React 19.2: Activity y useEffectEvent"
description: "Qué problemas resuelven Activity y useEffectEvent en React 19.2: conservar el estado de una pantalla oculta y leer valores en efectos sin añadirlos como dependencia."
date: 2025-11-24
tags: ["React", "TypeScript"]
---

React 19.2, publicado en octubre de 2025, añade dos piezas que responden a problemas que casi todo el mundo ha resuelto alguna vez con algún apaño.

## `<Activity>`: ocultar sin perder el estado

Hasta ahora, ocultar una parte de la interfaz tenía dos opciones, ninguna perfecta:

```tsx
// Se pierde el estado al ocultar
{visible && <Panel />}

// Conserva el estado, pero sus efectos siguen activos
<div hidden={!visible}><Panel /></div>
```

`Activity` ofrece un término medio:

```tsx
import { Activity } from "react";

<Activity mode={visible ? "visible" : "hidden"}>
  <Panel />
</Activity>;
```

En modo `hidden`:

- el componente se oculta con `display: none`;
- su estado y el DOM se conservan;
- sus efectos se limpian, de modo que suscripciones y temporizadores se detienen;
- sus actualizaciones se aplican con baja prioridad, cuando no haya otro trabajo.

Al volver a `visible`, los efectos se montan de nuevo.

Casos en que resulta muy útil:

- **Pestañas o pasos**: el usuario vuelve con el formulario tal como lo dejó.
- **Precarga**: renderizar la pantalla más probable antes de que se navegue hasta ella, sin efectos activos.

Conviene recordar que lo oculto sigue consumiendo memoria. No mantengas ocultas decenas de pantallas pesadas. Y revisa los efectos que no limpian correctamente: se ejecutarán ahora más veces, y Activity sacará a la luz errores que ya existían.

## `useEffectEvent`: valores recientes sin dependencia

Este problema tiene años:

```tsx
function Sala({ salaId, tema }: Props) {
  useEffect(() => {
    const conexion = conectar(salaId);

    conexion.on("conectado", () => {
      mostrarAviso("Conectado", tema);
    });

    return () => conexion.close();
  }, [salaId, tema]);
}
```

La regla exige `tema` como dependencia. Sin embargo, al cambiar el tema, el chat se desconecta y se reconecta sin necesidad. La gente solía resolverlo silenciando el linter o usando una referencia.

`useEffectEvent` separa lo reactivo de lo que no lo es:

```tsx
import { useEffect, useEffectEvent } from "react";

function Sala({ salaId, tema }: Props) {
  const alConectar = useEffectEvent(() => {
    mostrarAviso("Conectado", tema);
  });

  useEffect(() => {
    const conexion = conectar(salaId);
    conexion.on("conectado", alConectar);

    return () => conexion.close();
  }, [salaId]);
}
```

El efecto solo depende de `salaId`, y la función siempre ve el valor actual de `tema`.

Los límites que debes respetar:

- solo se puede llamar desde dentro de efectos;
- no se pasa a otros componentes o hooks;
- no es una forma de esquivar dependencias que sí deberían disparar el efecto.

La pregunta para decidir es esta: ¿debería volver a ejecutarse el efecto si cambia este valor? Si la respuesta es sí, es una dependencia. Si solo necesitas leer su valor actual, es un evento de efecto.

Actualiza `eslint-plugin-react-hooks`, para que la regla de dependencias lo entienda.

## Otras novedades de la versión

- **`cacheSignal`**, para Server Components: indica cuándo ha terminado la vida de una entrada de `cache()`, y permite cancelar trabajo.
- **Prerenderizado parcial**: prerenderiza la parte estática y reanuda en el servidor lo dinámico.
- **Pistas de rendimiento en Chrome DevTools**: se ve qué está haciendo el planificador de React.

## ¿Cuándo adoptarlo?

La actualización dentro de la versión 19 no debería suponer mucho trabajo. Revisa si tienes código con `eslint-disable` sobre dependencias: cada uno es un buen candidato para `useEffectEvent`. `Activity` puede esperar a que tengas un caso real, como un flujo de varios pasos en el que se pierde el estado.

## Referencias

- [Anuncio de React 19.2](https://react.dev/blog/2025/10/01/react-19-2)
- [Activity](https://react.dev/reference/react/Activity)
- [useEffectEvent](https://react.dev/reference/react/useEffectEvent)
