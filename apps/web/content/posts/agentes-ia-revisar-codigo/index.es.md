---
title: "Revisar código generado por IA: qué mirar cuando tú no lo has escrito"
seoTitle: "Revisar código generado por IA"
description: "Los errores típicos del código generado por agentes de IA y una forma de revisarlo: comprobar la intención, buscar lo que falta, desconfiar de las pruebas y limitar el tamaño."
date: 2026-07-06
tags: ["Agentes", "IA", "Revisión de código"]
---

Un agente puede producir en minutos un diff que tardarías una hora en leer bien. Esa asimetría es el verdadero problema. El código generado suele tener buen aspecto: compila, sigue tus convenciones y viene con pruebas. Eso hace que sus errores sean más fáciles de pasar por alto que los de una persona.

## Tú sigues siendo responsable

Si fusionas algo, es tuyo, también si no lo has escrito. Una regla útil: no aprobar nada que no serías capaz de explicar a un compañero. Si no entiendes por qué funciona, tampoco sabrás qué hacer cuando deje de hacerlo.

## Revisa primero la intención

Antes de leer cada línea, pregúntate:

- ¿Resuelve el problema que le pedí, o uno parecido?
- ¿Ha cambiado solo lo necesario?
- ¿Es la solución más sencilla?

Comprobar esto primero te ahorra tiempo. Si el enfoque está mal, no vale la pena revisar los detalles.

Lee también lo que el agente dice haber hecho, y compáralo con el diff. A veces, el resumen afirma algo que el código no refleja.

## Errores que aparecen con frecuencia

**Soluciones que silencian el síntoma.** Cuando una prueba falla, un agente puede cambiar la aserción, añadir un `try/catch` vacío, usar `any` o saltarse la prueba. El resultado es verde, y el problema sigue ahí.

```diff
- expect(total).toBe(121);
+ expect(total).toBe(100);
```

Cualquier cambio en una prueba existente debe tener una razón clara. Busca también `skip`, `@ts-ignore`, `eslint-disable` o `#pragma warning disable`.

**Código de más.** Abstracciones para casos que no existen, opciones que nadie ha pedido o un manejo de errores para situaciones imposibles. Es trabajo que tendrás que mantener. Cuestiona todo lo que no se ha solicitado.

**Duplicación de lo que ya existe.** El agente no siempre encuentra la función que ya tienes, y escribe otra parecida. Con el tiempo, habrá tres formas de hacer lo mismo.

**Librerías y API inventadas o anticuadas.** Puede usar un método que no existe, una opción de una versión anterior o un paquete con un nombre plausible. Comprueba cualquier dependencia nueva: que exista, que esté mantenida y que sea la que crees. Un nombre inventado podría registrarlo un atacante.

**Solo el camino feliz.** Revisa lo que falta, que es más difícil de ver que lo que hay: valores nulos, listas vacías, errores de red, concurrencia, permisos o reintentos.

**Reglas implícitas que no conoce.** Lo que tu equipo sabe y no está escrito en ninguna parte, como que esa tabla es enorme o que ese servicio cuesta dinero por llamada.

## Seguridad

Merece una lectura específica, sobre todo en lo que toca datos de usuarios:

- **Autorización**: es lo que más se olvida. ¿Se comprueba que este usuario puede acceder a *este* recurso?
- **Entrada**: consultas con parámetros, rutas de archivo, contenido que se muestra en HTML.
- **Secretos**: credenciales en código, en logs o en ejemplos.
- **Permisos excesivos** en configuraciones, roles o CORS, a menudo añadidos para que algo funcione.

## No confíes solo en sus pruebas

Si las pruebas las ha escrito el mismo agente, comparten los mismos supuestos que el código. Pueden pasar y no demostrar nada. Comprueba que:

- fallan si rompes el código a propósito;
- comprueban comportamiento, no detalles internos;
- no se limitan a verificar que se ha llamado a una simulación;
- incluyen los casos difíciles, no solo el más evidente.

Introducir un fallo deliberado en la lógica y ver si las pruebas lo detectan lleva menos de un minuto, y dice mucho.

Y ejecútalo. Muchas veces, usar la funcionalidad durante unos minutos revela lo que ninguna lectura de diff hubiera encontrado.

## Hacer la revisión viable

Lo que más ayuda ocurre antes de la revisión:

1. **Tareas pequeñas.** Un diff de 2000 líneas no se revisa, solo se aprueba o se rechaza. Pide cambios por partes.
2. **Acordar el plan primero.** Corregir el enfoque antes de que escriba es mucho más barato.
3. **Commits separados.** Una refactorización y un cambio de comportamiento no deben ir juntos.
4. **Comprobaciones automáticas.** Tipos, linter, pruebas y análisis de seguridad en CI. No gastes atención humana en lo que una máquina puede comprobar.
5. **Otra revisión con contexto limpio.** Un segundo agente, sin la conversación anterior, puede detectar cosas. Es un complemento, no un sustituto.

## Cuánto revisar

No todo requiere la misma atención. Un script de un solo uso en tu máquina puede pasar con una lectura rápida. Autenticación, pagos, migraciones de datos o código de concurrencia merecen una revisión lenta y línea a línea. Ajusta el esfuerzo a lo que costaría que estuviera mal.

Y si te encuentras aprobando sin leer porque va todo bien últimamente, es el mejor momento para frenar un poco. La confianza crece más deprisa de lo que debería, y los errores más caros son los que parecen correctos.

## Referencias

- [Top 10 de OWASP para aplicaciones LLM](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
