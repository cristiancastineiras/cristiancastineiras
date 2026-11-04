---
title: "Acciones en React 19: useActionState, useOptimistic y formularios sin tanto estado"
seoTitle: "Acciones en React 19"
description: "Cómo funcionan las acciones de React 19 con useActionState, useFormStatus y useOptimistic, qué estado manual eliminan y cuándo sigue compensando una librería."
date: 2025-02-10
tags: ["React", "TypeScript", "Formularios"]
---

Enviar un formulario en React siempre ha requerido el mismo código: un estado para saber si está cargando, otro para el error, un `try/finally` y `preventDefault`. React 19 convierte este patrón en una función del framework.

## El antes

```tsx
const [cargando, setCargando] = useState(false);
const [error, setError] = useState<string | null>(null);

async function alEnviar(e: FormEvent<HTMLFormElement>) {
  e.preventDefault();
  setCargando(true);
  setError(null);
  try {
    await guardarNombre(nombre);
  } catch {
    setError("No se ha podido guardar");
  } finally {
    setCargando(false);
  }
}
```

## `useActionState`

Recibe una función de acción y un estado inicial, y devuelve el estado, la acción para el formulario y si está en curso:

```tsx
type Estado = { error: string | null };

async function guardar(_previo: Estado, datos: FormData): Promise<Estado> {
  const nombre = String(datos.get("nombre") ?? "").trim();

  if (!nombre) return { error: "El nombre es obligatorio" };

  try {
    await guardarNombre(nombre);
    return { error: null };
  } catch {
    return { error: "No se ha podido guardar" };
  }
}

export function FormularioNombre() {
  const [estado, accion, pendiente] = useActionState(guardar, { error: null });

  return (
    <form action={accion}>
      <label htmlFor="nombre">Nombre</label>
      <input id="nombre" name="nombre" required />
      {estado.error && <p role="alert">{estado.error}</p>}
      <button disabled={pendiente}>
        {pendiente ? "Guardando…" : "Guardar"}
      </button>
    </form>
  );
}
```

No hay `preventDefault`, ni estados por separado. La lógica se puede probar sin renderizar nada, porque `guardar` es una función normal.

Un detalle que sorprende al principio: cuando la acción termina sin lanzar una excepción, React restablece los campos no controlados del formulario, también si has devuelto un error en el estado. Para no perder lo escrito, devuelve los valores en el estado y rellena los campos con `defaultValue`.

## `useFormStatus`

Permite que un botón sepa si su formulario se está enviando, sin pasarle props:

```tsx
import { useFormStatus } from "react-dom";

function BotonEnviar() {
  const { pending } = useFormStatus();
  return <button disabled={pending}>{pending ? "Enviando…" : "Enviar"}</button>;
}
```

Debe ser un componente hijo del `<form>`: llamado en el mismo componente que lo renderiza, no encuentra ningún formulario.

## `useOptimistic`

Muestra el resultado esperado mientras la petición está en marcha:

```tsx
function Comentarios({ comentarios }: { comentarios: Comentario[] }) {
  const [optimistas, anadir] = useOptimistic(
    comentarios,
    (actuales, texto: string) => [
      ...actuales,
      { id: crypto.randomUUID(), texto, enviando: true },
    ],
  );

  async function accion(datos: FormData) {
    const texto = String(datos.get("texto"));
    anadir(texto);
    await publicarComentario(texto);
  }

  return (
    <>
      <ul>
        {optimistas.map((c) => (
          <li key={c.id} aria-busy={c.enviando}>{c.texto}</li>
        ))}
      </ul>
      <form action={accion}>
        <input name="texto" aria-label="Comentario" />
        <button>Publicar</button>
      </form>
    </>
  );
}
```

Cuando la acción termina, React vuelve al valor real. Si la petición ha fallado, el comentario desaparece, así que hay que avisar al usuario de que no se publicó.

Solo debe usarse si el fallo es poco probable y el usuario puede entender el retroceso. No lo uses para confirmar un pago.

## ¿Sustituye esto a React Hook Form?

Para formularios sencillos, sí. Si necesitas validación por campo mientras se escribe, campos dinámicos, dependencias entre campos o un rendimiento fino en formularios enormes, una librería sigue ahorrando mucho trabajo.

Tampoco resuelve la validación en el servidor: lo que llega al backend se valida siempre, sea cual sea la técnica.

## Otras mejoras de la versión

Otras novedades útiles de React 19 son que `ref` ya se puede pasar como una prop normal, sin `forwardRef`, y `<Context>` puede usarse directamente como proveedor. La herramienta `react-codemod` automatiza gran parte de la migración.

## Referencias

- [useActionState](https://react.dev/reference/react/useActionState)
- [useOptimistic](https://react.dev/reference/react/useOptimistic)
- [Anuncio de React 19](https://react.dev/blog/2024/12/05/react-19)
