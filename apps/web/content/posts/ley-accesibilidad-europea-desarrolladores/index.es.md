---
title: "Ley Europea de Accesibilidad: lo que debe saber un equipo de desarrollo"
seoTitle: "Ley Europea de Accesibilidad para devs"
description: "Qué supone la Ley Europea de Accesibilidad desde el 28 de junio de 2025 para productos digitales, qué estándares técnicos se usan y cómo organizar el trabajo."
date: 2025-06-26
tags: ["Accesibilidad", "Legal", "Frontend"]
---

El 28 de junio de 2025 empieza a aplicarse la Ley Europea de Accesibilidad (la Directiva UE 2019/882, conocida como EAA, y en España la Ley 11/2023). Para muchos productos digitales, la accesibilidad deja de ser una buena práctica opcional y pasa a ser un requisito legal.

Esto es una lectura técnica, no asesoramiento jurídico. El alcance exacto de cada caso debe revisarlo alguien especializado.

## A quién afecta

Entre otros, cubre productos y servicios dirigidos a consumidores, como:

- comercio electrónico;
- servicios bancarios para consumidores;
- libros electrónicos y su software;
- servicios de comunicaciones y algunos de medios audiovisuales;
- servicios de transporte de viajeros, como la venta de billetes;
- terminales, cajeros y ordenadores de consumo.

Existe una exención para microempresas que presten servicios: menos de 10 empleados y un volumen de negocio o balance que no supere los 2 millones de euros. Las aplicaciones internas o los productos solo entre empresas pueden quedar fuera, aunque si tu cliente vende a consumidores, puede exigirte el cumplimiento por contrato.

El sector público ya tiene sus propias obligaciones desde antes, por una directiva anterior.

## Qué estándar técnico se usa

La directiva no menciona una lista de comprobaciones. En la práctica, la referencia es la norma armonizada EN 301 549, que para la web incorpora WCAG 2.1 nivel AA. Trabajar con **WCAG 2.2 AA** es una buena decisión, porque incluye esos requisitos y añade algunos más, y además es lo que seguramente se exigirá en el futuro.

Los principios de WCAG son cuatro:

- **Perceptible**: textos alternativos, contraste, subtítulos.
- **Operable**: teclado, foco visible, tiempo suficiente.
- **Comprensible**: lenguaje claro, comportamiento predecible, errores que se entienden.
- **Robusto**: HTML correcto, compatible con tecnologías de asistencia.

## No es solo el código

La ley también incluye obligaciones que no se resuelven en un pull request:

- una declaración de cómo el servicio cumple los requisitos, disponible para los usuarios;
- información sobre accesibilidad de cara al público;
- que los documentos y procesos de soporte también lo sean;
- PDF y otros formatos descargables, que suelen olvidarse.

## Por dónde empezar

Un plan realista, para un producto ya existente:

1. **Inventario**: flujos críticos, como registro, búsqueda, compra y atención al cliente.
2. **Auditoría de esos flujos**: combina herramientas automáticas y pruebas manuales con teclado y lector de pantalla.
3. **Priorización**: primero los bloqueos, los que impiden terminar una tarea. Un contraste bajo en un pie de página puede esperar a un formulario que no se puede enviar.
4. **Corrección en origen**: arregla el componente compartido, no cada pantalla. Un `Boton` accesible corrige cientos de usos.
5. **Protección**: automatiza pruebas para que no se vuelvan a introducir los fallos.

## Qué automatizar

Las herramientas como axe detectan una parte de los problemas: atributos que faltan, contrastes o estructuras incorrectas. No pueden juzgar si un texto alternativo tiene sentido, ni si un flujo se entiende. Por eso conviene que entren en CI, pero sin suponer que un resultado verde significa que todo está bien.

```bash
pnpm add -D @axe-core/playwright
```

## Incorporarlo al proceso

La accesibilidad cuesta mucho menos si está presente desde el principio:

- **Diseño**: contraste, estados de foco y orden de lectura se definen antes de programar.
- **Definición de terminado**: incluir pruebas con teclado en cada historia de usuario con interfaz.
- **Sistema de diseño**: componentes accesibles por defecto, documentados.
- **Revisión de código**: mira también los roles, las etiquetas y el foco.
- **Compras**: exige información sobre accesibilidad a los proveedores de componentes externos.

## El contenido también cuenta

Un sistema accesible puede dejar de serlo por lo que se publica en él: imágenes sin descripción o enlaces con el texto «pincha aquí». Si tu producto incluye un gestor de contenidos, facilita y exige lo correcto a quien publica.

## Más allá de la ley

Una interfaz accesible es mejor para todo el mundo: quien usa el móvil al sol, con una mano o con el brazo escayolado, o quien navega con conexión lenta. Además, un marcado correcto ayuda a los buscadores y hace que las pruebas sean más estables. Si lo tratas solo como un trámite, lo harás al final y caro. Si forma parte de la calidad, cuesta bastante menos.

## Referencias

- [Directiva (UE) 2019/882](https://eur-lex.europa.eu/eli/dir/2019/882/oj)
- [Ley 11/2023 en el BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2023-11022)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
