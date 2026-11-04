---
title: "Probar componentes React con Vitest y Testing Library: qué probar y qué no"
seoTitle: "Vitest y Testing Library en React"
description: "Cómo configurar Vitest y Testing Library, escribir pruebas orientadas al usuario y evitar los tests frágiles que fallan al refactorizar sin que nada se haya roto."
date: 2025-09-15
tags: ["React", "Testing", "Vitest"]
---

Una prueba de frontend útil falla cuando el usuario se vería afectado. Una prueba frágil falla cuando cambias un nombre interno. La diferencia suele estar en si la prueba interactúa con la pantalla o con los detalles de implementación.

## Configuración

```bash
pnpm add -D vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom
```

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

```ts
// src/test/setup.ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
```

## Una prueba orientada al usuario

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

test("permite iniciar sesión con credenciales válidas", async () => {
  const usuario = userEvent.setup();
  const alEnviar = vi.fn();

  render(<FormularioLogin onSubmit={alEnviar} />);

  await usuario.type(screen.getByLabelText("Correo"), "ana@ejemplo.com");
  await usuario.type(screen.getByLabelText("Contraseña"), "secreta");
  await usuario.click(screen.getByRole("button", { name: "Entrar" }));

  expect(alEnviar).toHaveBeenCalledWith({
    correo: "ana@ejemplo.com",
    contrasena: "secreta",
  });
});
```

Esta prueba sobrevive a que cambies `useState` por una librería de formularios, porque no sabe nada de cómo se implementa.

## Consultar como lo haría una persona

El orden recomendado es:

1. `getByRole`, con su nombre accesible.
2. `getByLabelText`, para campos de formulario.
3. `getByText`, para contenido.
4. `getByTestId`, solo si no hay otra opción.

Tiene una ventaja adicional: si no puedes encontrar un botón por su rol y su nombre, puede que un lector de pantalla tampoco lo identifique. Las pruebas detectan así también algunos problemas de accesibilidad.

## Esperar sin `sleep`

- `getBy...`: el elemento debe estar ya; si no, falla.
- `queryBy...`: devuelve `null`; sirve para comprobar que algo **no** está.
- `findBy...`: espera a que aparezca.

```tsx
expect(await screen.findByText("Pedido enviado")).toBeInTheDocument();
expect(screen.queryByRole("alert")).not.toBeInTheDocument();
```

## Simular la red, no tus módulos

Si simulas directamente tu `useClientes`, la prueba no verifica la integración con el hook. Mock Service Worker intercepta las peticiones reales:

```ts
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const servidor = setupServer(
  http.get("/api/clientes/:id", ({ params }) =>
    HttpResponse.json({ id: Number(params.id), nombre: "Ana" }),
  ),
);
```

```ts
beforeAll(() => servidor.listen({ onUnhandledRequest: "error" }));
afterEach(() => servidor.resetHandlers());
afterAll(() => servidor.close());
```

También te permite probar los estados de error, que es donde suelen esconderse los fallos:

```ts
servidor.use(
  http.get("/api/clientes/:id", () => new HttpResponse(null, { status: 500 })),
);
```

## Qué merece una prueba

Prioriza:

- la lógica condicional: permisos, reglas de un formulario, estados vacíos y errores;
- los flujos que, si se rompen, afectan al negocio;
- los errores que ya has tenido, con una prueba por cada bug arreglado.

Puedes omitir:

- que un componente pase una prop a un hijo;
- clases CSS y detalles visuales;
- instantáneas grandes, que se aprueban sin mirar en cada cambio;
- código trivial o de la propia librería.

## Lo que jsdom no ve

jsdom no calcula el layout, no comprueba si algo es visible por CSS ni ejecuta un navegador de verdad. Para flujos críticos, o si el comportamiento depende del navegador, usa Playwright. Unas pocas pruebas end-to-end y muchas de componentes suelen ser un buen equilibrio.

## Referencias

- [Vitest](https://vitest.dev/)
- [Prioridad de consultas en Testing Library](https://testing-library.com/docs/queries/about/#priority)
- [Mock Service Worker](https://mswjs.io/)
