---
title: "Error boundaries en React: que un fallo no deje la pantalla en blanco"
seoTitle: "Error boundaries en React"
description: "Dónde colocar error boundaries en una aplicación React, qué errores capturan y cuáles no, cómo reintentar y cómo enviar los fallos a tu sistema de observabilidad."
date: 2025-06-09
tags: ["React", "TypeScript", "Observabilidad"]
---

Si un componente lanza una excepción durante el render y nadie la captura, React desmonta todo el árbol. El usuario ve una pantalla en blanco. Un error en un pequeño widget se lleva por delante toda la aplicación.

Los *error boundaries* limitan ese daño.

## Lo básico

Aún tienen que ser componentes de clase, ya que no existe una versión con hooks:

```tsx
import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { alternativa: ReactNode; children: ReactNode };
type Estado = { hayError: boolean };

export class LimiteDeError extends Component<Props, Estado> {
  state: Estado = { hayError: false };

  static getDerivedStateFromError(): Estado {
    return { hayError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    registrarError(error, info.componentStack);
  }

  render() {
    return this.state.hayError ? this.props.alternativa : this.props.children;
  }
}
```

La librería `react-error-boundary` lo ofrece ya hecho, incluida la opción de reiniciar, y es lo que yo usaría:

```tsx
import { ErrorBoundary } from "react-error-boundary";

<ErrorBoundary
  fallback={<p role="alert">No se ha podido cargar el panel.</p>}
  onError={(error, info) => registrarError(error, info.componentStack)}
>
  <PanelDeVentas />
</ErrorBoundary>;
```

## Qué capturan y qué no

Capturan errores durante el render, en los métodos de ciclo de vida y en los efectos de sus descendientes.

**No** capturan:

- errores en manejadores de eventos;
- código asíncrono, como una promesa rechazada en un `setTimeout`;
- errores en el propio boundary;
- renderizado en el servidor.

Los errores de eventos y de código asíncrono hay que tratarlos con `try/catch`, o enviarlos a un boundary de forma explícita:

```tsx
import { useErrorBoundary } from "react-error-boundary";

const { showBoundary } = useErrorBoundary();

async function alExportar() {
  try {
    await exportar();
  } catch (error) {
    showBoundary(error);
  }
}
```

No todos los fallos deben llegar a un boundary. Si un guardado falla, un mensaje junto al botón es mejor que sustituir toda la sección.

## Dónde colocarlos

Una estrategia razonable tiene tres niveles:

```tsx
<ErrorBoundary fallback={<PantallaDeError />}>
  <Layout>
    <ErrorBoundary fallback={<ErrorDeRuta />}>
      <Rutas />
    </ErrorBoundary>
  </Layout>
</ErrorBoundary>
```

1. **Raíz**: último recurso, para que nunca haya una pantalla en blanco.
2. **Ruta**: un fallo en una página conserva la navegación y permite ir a otra.
3. **Widget**: en paneles con partes independientes, una gráfica rota no debería afectar a las demás.

No envuelvas cada componente. Si un formulario tiene un fallo a medias, ocultar un trozo y dejar el resto activo puede ser más confuso, o incluso peligroso.

## Permitir reintentar

Un fallo transitorio merece un botón de reintento:

```tsx
function ErrorDePanel({ resetErrorBoundary }: FallbackProps) {
  return (
    <div role="alert">
      <p>No se ha podido cargar este panel.</p>
      <button onClick={resetErrorBoundary}>Reintentar</button>
    </div>
  );
}

<ErrorBoundary FallbackComponent={ErrorDePanel} resetKeys={[filtro]}>
  <Panel filtro={filtro} />
</ErrorBoundary>;
```

Con `resetKeys`, el boundary se reinicia automáticamente si cambian esos valores, por ejemplo al navegar. Esto evita quedarse atascado en la pantalla de error.

## Registrar los errores

Un error que no llega a tus sistemas no existe para ti. Envía `error.message`, la pila y `componentStack` a tu herramienta de observabilidad, junto con la versión desplegada, para saber si un fallo empezó con un despliegue. Sube los *source maps* a esa herramienta, y sin publicarlos si no quieres que sean accesibles, para ver las pilas originales.

Ten cuidado con los datos personales en los mensajes de error.

## Errores de carga de chunks

Tras un despliegue, un usuario con la aplicación abierta puede pedir un fichero que ya no existe, y `lazy` falla. Es un caso muy habitual. Un boundary con la opción de recargar la página suele ser suficiente, ya que el usuario obtendrá la versión nueva.

## Referencias

- [Capturar errores con un error boundary](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [react-error-boundary](https://github.com/bvaughn/react-error-boundary)
