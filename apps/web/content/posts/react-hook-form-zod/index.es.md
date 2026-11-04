---
title: "Formularios complejos en React con React Hook Form y Zod"
seoTitle: "React Hook Form y Zod"
description: "Cómo construir formularios tipados y accesibles con React Hook Form y Zod: esquema único, campos dinámicos, errores del servidor y rendimiento."
date: 2025-05-12
tags: ["React", "TypeScript", "Formularios"]
---

Cuando un formulario tiene veinte campos, validaciones cruzadas y filas dinámicas, el estado manual se vuelve inmanejable. React Hook Form y Zod lo resuelven con un reparto sencillo: uno gestiona el formulario, y el otro define qué es válido.

## El esquema como fuente de verdad

```ts
import { z } from "zod";

export const clienteSchema = z
  .object({
    nombre: z.string().trim().min(1, "El nombre es obligatorio"),
    email: z.string().email("Introduce un correo válido"),
    tipo: z.enum(["particular", "empresa"]),
    nif: z.string().optional(),
  })
  .refine((datos) => datos.tipo !== "empresa" || !!datos.nif, {
    message: "El NIF es obligatorio para empresas",
    path: ["nif"],
  });

export type ClienteFormulario = z.infer<typeof clienteSchema>;
```

El tipo de TypeScript se deriva del esquema, así que no se pueden separar.

## El formulario

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

export function FormularioCliente({ onGuardar }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ClienteFormulario>({
    resolver: zodResolver(clienteSchema),
    defaultValues: { nombre: "", email: "", tipo: "particular" },
  });

  return (
    <form onSubmit={handleSubmit(onGuardar)} noValidate>
      <label htmlFor="nombre">Nombre</label>
      <input
        id="nombre"
        aria-invalid={!!errors.nombre}
        aria-describedby={errors.nombre ? "nombre-error" : undefined}
        {...register("nombre")}
      />
      {errors.nombre && (
        <p id="nombre-error" role="alert">{errors.nombre.message}</p>
      )}

      <button disabled={isSubmitting}>Guardar</button>
    </form>
  );
}
```

`register` usa inputs no controlados, de modo que escribir en un campo no vuelve a renderizar todo el formulario. Es la razón de su buen rendimiento en formularios grandes.

Los atributos `aria-invalid` y `aria-describedby` no son un extra: son lo que permite a un lector de pantalla anunciar el error de cada campo.

## Componentes controlados

Si un selector o un calendario de una librería no expone un `ref` de input, usa `Controller`:

```tsx
<Controller
  control={control}
  name="tipo"
  render={({ field }) => (
    <Selector value={field.value} onChange={field.onChange} opciones={tipos} />
  )}
/>
```

## Filas dinámicas

```tsx
const { fields, append, remove } = useFieldArray({ control, name: "lineas" });

return fields.map((campo, indice) => (
  <div key={campo.id}>
    <input {...register(`lineas.${indice}.concepto`)} />
    <input
      type="number"
      {...register(`lineas.${indice}.cantidad`, { valueAsNumber: true })}
    />
    <button type="button" onClick={() => remove(indice)}>Quitar</button>
  </div>
));
```

Usa `campo.id` como `key`, no el índice. Si borras una fila intermedia, con el índice los valores acabarían en la fila equivocada.

## Errores del servidor

El servidor siempre tiene la última palabra. Puedes asociar sus errores a los campos con `setError`:

```tsx
async function alGuardar(datos: ClienteFormulario) {
  const respuesta = await crearCliente(datos);

  if (!respuesta.ok) {
    const problema = await respuesta.json();

    for (const [campo, mensajes] of Object.entries(problema.errors ?? {})) {
      setError(campo as keyof ClienteFormulario, {
        message: (mensajes as string[])[0],
      });
    }
  }
}
```

Esto encaja de forma natural con los errores de validación con el formato `ValidationProblemDetails` de ASP.NET Core. Solo cuidado con el nombre de las propiedades, ya que deben coincidir con el camino del campo.

## Rendimiento

Evita `watch()` sin argumentos en el componente raíz, porque provoca un render por cada tecla. Si un componente necesita un solo valor, usa `useWatch` en un componente hijo pequeño.

## Validar también en el backend

La validación del cliente mejora la experiencia, pero no es una medida de seguridad, porque cualquiera puede llamar directamente a tu API. Si tu backend es .NET, el esquema de Zod no se comparte, de modo que algunas reglas existirán en ambos sitios. Mantén en el cliente las reglas de forma y deja las de negocio a la API.

## Referencias

- [React Hook Form](https://react-hook-form.com/)
- [Zod](https://zod.dev/)
