---
title: "Formularios accesibles: etiquetas, errores y foco bien hechos"
seoTitle: "Formularios accesibles en HTML y React"
description: "Lo imprescindible para que un formulario funcione con teclado y lector de pantalla: etiquetas reales, errores asociados al campo, autocompletado y gestión del foco."
date: 2025-01-30
tags: ["Accesibilidad", "HTML", "React"]
---

Los formularios son el punto donde un problema de accesibilidad deja de ser una molestia y se convierte en un bloqueo. Si una persona no puede completar un trámite, un pago o un registro, no puede usar el servicio. La mayoría de los fallos se arreglan con HTML correcto, sin librerías.

## Etiquetas reales

Un `placeholder` no es una etiqueta: desaparece al escribir, suele tener poco contraste y no siempre se anuncia.

```html
<!-- Mal -->
<input type="email" placeholder="Correo electrónico" />

<!-- Bien -->
<label for="correo">Correo electrónico</label>
<input id="correo" type="email" name="correo" autocomplete="email" />
```

La asociación con `for` e `id` tiene además una ventaja para todo el mundo: hacer clic en la etiqueta activa el campo, un objetivo táctil más grande en el móvil.

En React se escribe `htmlFor`, y `useId` genera identificadores únicos, lo que evita colisiones si el componente aparece varias veces:

```tsx
function CampoTexto({ etiqueta, ...props }: Props) {
  const id = useId();

  return (
    <>
      <label htmlFor={id}>{etiqueta}</label>
      <input id={id} {...props} />
    </>
  );
}
```

## Tipos y autocompletado

Cuesta muy poco y ayuda mucho:

```html
<input type="tel" autocomplete="tel" />
<input type="text" autocomplete="street-address" />
<input type="text" inputmode="numeric" autocomplete="postal-code" />
```

`type` e `inputmode` hacen que el móvil muestre el teclado adecuado. `autocomplete` evita volver a escribir datos, algo muy valioso para personas con dificultades motoras o cognitivas.

Para un número que no representa una cantidad, como un código postal o una tarjeta, no uses `type="number"`. Elimina los ceros iniciales y añade controles que no aportan nada.

## Agrupar opciones relacionadas

Los botones de opción necesitan un nombre para el grupo, no solo para cada opción:

```html
<fieldset>
  <legend>Tipo de cuenta</legend>

  <input type="radio" id="personal" name="tipo" value="personal" />
  <label for="personal">Personal</label>

  <input type="radio" id="empresa" name="tipo" value="empresa" />
  <label for="empresa">Empresa</label>
</fieldset>
```

Sin `legend`, un lector de pantalla solo anunciaría «Personal», sin decir a qué pregunta responde.

## Errores asociados al campo

Un texto rojo debajo del campo no se relaciona con él para un lector de pantalla, y el color por sí solo no sirve para quien no distingue los colores.

```tsx
<label htmlFor="correo">Correo electrónico</label>
<input
  id="correo"
  type="email"
  aria-invalid={!!error}
  aria-describedby={error ? "correo-error" : "correo-ayuda"}
/>
<p id="correo-ayuda">Te enviaremos aquí la confirmación.</p>
{error && <p id="correo-error">{error}</p>}
```

Escribe mensajes concretos que indiquen cómo solucionarlo. «Formato no válido» aporta poco. «Escribe el correo con el formato nombre@dominio.com» permite actuar.

## Qué hacer al enviar con errores

Si la validación falla, el foco debería ir a donde el usuario pueda actuar. Hay dos enfoques habituales:

- mover el foco al primer campo con error;
- mostrar un resumen de errores al principio, con enlaces a cada campo, y mover allí el foco.

```tsx
function alEnviarInvalido(errores: FieldErrors) {
  const primero = Object.keys(errores)[0];
  document.querySelector<HTMLElement>(`[name="${primero}"]`)?.focus();
}
```

React Hook Form lo hace por defecto con `shouldFocusError`. Para mensajes que aparecen sin mover el foco, como «Guardado», usa una región viva con `role="status"`.

## Botones deshabilitados

Desactivar «Enviar» hasta que todo esté correcto parece útil, pero tiene problemas: el botón deja de recibir el foco, suele tener poco contraste y el usuario no sabe qué falta. Es mejor dejarlo activo y mostrar los errores al pulsarlo.

## Campos obligatorios

No marques solo con un asterisco sin explicar. Indica al principio qué significa, usa el atributo `required` y, si casi todos son obligatorios, marca los opcionales:

```html
<label for="empresa">Empresa (opcional)</label>
<input id="empresa" name="empresa" />
```

## Cómo comprobarlo

1. Rellena el formulario solo con el teclado, usando Tab, Mayús+Tab, Enter y Espacio.
2. Provoca los errores y comprueba adónde va el foco.
3. Pruébalo con un lector de pantalla. NVDA en Windows es gratuito, y VoiceOver viene con macOS.
4. Amplía al 200 % y comprueba que nada se corta.

Las herramientas automáticas detectan parte de los problemas, como las etiquetas que faltan. No pueden saber si un mensaje de error realmente se entiende.

## Referencias

- [Tutorial de formularios de la WAI](https://www.w3.org/WAI/tutorials/forms/)
- [Entender los errores en WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html)
