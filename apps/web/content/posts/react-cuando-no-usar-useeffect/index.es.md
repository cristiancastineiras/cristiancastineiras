---
title: "Cuándo no necesitas useEffect en React"
seoTitle: "Cuándo no usar useEffect en React"
description: "Estado derivado, respuestas a eventos, reinicios de estado y cargas de datos: los usos de useEffect que sobran y el código más sencillo que los sustituye."
date: 2025-01-06
tags: ["React", "TypeScript"]
---

`useEffect` sirve para sincronizar un componente con algo externo a React: una suscripción, un temporizador, una API del navegador. Sin embargo, gran parte de los efectos que se escriben no sincronizan nada externo. Solo añaden un render de más y otra fuente de errores.

## Estado derivado

Si un valor se puede calcular a partir de las props o del estado, no lo guardes en otro estado:

```tsx
// Mal: un render extra y dos fuentes de verdad
const [filtrados, setFiltrados] = useState<Producto[]>([]);

useEffect(() => {
  setFiltrados(productos.filter((p) => p.activo));
}, [productos]);

// Bien: se calcula durante el render
const filtrados = productos.filter((p) => p.activo);
```

Si el cálculo es costoso de verdad, envuélvelo en `useMemo`, y mídelo antes de hacerlo:

```tsx
const filtrados = useMemo(
  () => productos.filter((p) => p.activo),
  [productos],
);
```

## Responder a un evento

Si algo ocurre porque el usuario ha hecho clic, ponlo en el manejador:

```tsx
// Mal: el efecto reacciona a un estado que el evento acaba de cambiar
useEffect(() => {
  if (enviado) {
    mostrarAviso("Pedido enviado");
  }
}, [enviado]);

// Bien
async function alEnviar() {
  await enviarPedido(datos);
  mostrarAviso("Pedido enviado");
}
```

El efecto también se ejecutaría si el componente se monta con `enviado` a `true`, por ejemplo al recuperar el estado. El manejador expresa la causa real.

## Reiniciar estado cuando cambia una prop

En vez de un efecto que vacía el estado, usa `key` para que React cree una instancia nueva:

```tsx
<FormularioPerfil key={usuarioId} usuarioId={usuarioId} />
```

Al cambiar `usuarioId`, React desmonta el componente y monta otro con el estado limpio. Se acabó tener que recordar qué campos había que limpiar.

## Encadenar efectos

Un efecto que cambia un estado que dispara otro efecto es difícil de seguir, y produce varios renders:

```tsx
useEffect(() => setCiudad(null), [provincia]);
useEffect(() => setCodigoPostal(null), [ciudad]);
```

Resuelve todos los cambios en el evento:

```tsx
function alCambiarProvincia(valor: string) {
  setProvincia(valor);
  setCiudad(null);
  setCodigoPostal(null);
}
```

## Notificar al padre

```tsx
// Mal
useEffect(() => {
  onChange(valor);
}, [valor]);

// Bien
function alCambiar(nuevo: string) {
  setValor(nuevo);
  onChange(nuevo);
}
```

React agrupa ambas actualizaciones en un único render. Con el efecto, el padre se actualiza un render más tarde, lo que puede dejar la interfaz momentáneamente inconsistente.

## Cargar datos

Es técnicamente un uso válido, pero un `fetch` dentro de `useEffect` se deja atrás varias cosas: condiciones de carrera, caché, reintentos y estados de carga.

Si lo haces así, al menos cancela la petición anterior:

```tsx
useEffect(() => {
  const controlador = new AbortController();

  fetch(`/api/clientes/${id}`, { signal: controlador.signal })
    .then((r) => r.json())
    .then(setCliente)
    .catch((e) => {
      if (e.name !== "AbortError") setError(e);
    });

  return () => controlador.abort();
}, [id]);
```

En una aplicación real, una librería como TanStack Query resuelve todo esto mejor.

## Cuándo sí usarlo

- Suscribirse a un evento del navegador o a un WebSocket.
- Integrarse con un widget que no es de React, como un mapa.
- Iniciar y limpiar un temporizador.
- Sincronizar con una API externa cuando el componente aparece en pantalla.

Una pregunta rápida: ¿este código se ejecuta porque el componente se ha mostrado? Entonces puede ser un efecto. ¿Se ejecuta porque el usuario ha hecho algo? Entonces va en un manejador.

## La regla de dependencias

No silencies `react-hooks/exhaustive-deps`. Si la lista de dependencias te molesta, probablemente el efecto hace demasiado, o incluye algo que debería estar fuera.

## Referencias

- [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- [useEffect](https://react.dev/reference/react/useEffect)
