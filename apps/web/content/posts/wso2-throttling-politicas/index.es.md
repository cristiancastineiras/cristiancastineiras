---
title: "Límites de uso en WSO2 API Manager: qué política aplicar en cada nivel"
seoTitle: "Límites de uso en WSO2 API Manager"
description: "Las políticas de límite de uso de WSO2 API Manager: API, aplicación, suscripción y operación, cómo se combinan, y cómo elegir valores sin bloquear a usuarios legítimos."
date: 2026-08-31
tags: ["WSO2", "Rendimiento", "Seguridad"]
---

Sin límites de uso, un cliente con un bucle mal escrito puede dejar sin servicio a todos los demás. Con límites mal diseñados, bloqueas a tus mejores usuarios. WSO2 API Manager permite aplicar políticas en varios niveles a la vez, y entender cómo se combinan evita muchas sorpresas.

## Los niveles

**Suscripción.** Define lo que una aplicación puede hacer con una API según su plan: `Gold`, `Silver`, `Bronze`. Es el nivel comercial o de acuerdo: qué se ha comprometido cada consumidor.

**Aplicación.** Limita a cada usuario de una aplicación, o a la aplicación en su conjunto. Evita que un único usuario consuma toda la cuota asignada.

**API avanzada.** Protege un recurso concreto, para todos los consumidores. Puede aplicarse a toda la API o por operación, y admite condiciones como IP, cabecera o parámetro. Sirve para proteger al backend.

**Límite del backend.** Se configura para respetar la capacidad real del servicio, sin importar quién llame.

**Personalizada y denegación.** Las reglas personalizadas cubren casos a medida, y las listas de denegación permiten bloquear un usuario, una aplicación o una IP de inmediato.

## Cómo se combinan

Los límites no se suman, sino que se aplican todos. Una petición debe superar todas las comprobaciones, y la más restrictiva es la que decide:

```text
Plan Gold:              1000 peticiones/minuto
Política de aplicación: 500 por usuario/minuto
API avanzada:           2000/minuto en esta operación
```

Si un usuario llega a 500, queda bloqueado por la política de aplicación, aunque su plan permita más. Cuando alguien se queja de que recibe un 429 antes de lo esperado, suele deberse a esto.

## Peticiones y ancho de banda

Una política puede contar peticiones o datos transferidos. Contar peticiones es sencillo, pero no todas cuestan lo mismo: una consulta de un registro y una exportación de 100 MB son una sola petición en ambos casos. Para operaciones costosas, añade una política por operación o por ancho de banda.

## Protección frente a picos

Un límite por minuto no evita que todas las peticiones lleguen en el mismo segundo. Las políticas de suscripción admiten restricciones de ráfaga, por segundo o por minuto, que suavizan esos picos:

```text
Cuota:   10 000 peticiones por hora
Ráfaga:  50 peticiones por segundo
```

Sin esta restricción, un cliente podría consumir toda su cuota en unos pocos segundos, y saturar el backend aunque esté dentro de su límite.

## Elegir los valores

No lo hagas sin datos:

1. **Mide el uso real.** Las analíticas de API muestran el patrón de cada consumidor. Fija los límites por encima de los picos normales.
2. **Mide la capacidad del backend.** Con una prueba de carga, averigua el punto en el que se degrada, y deja un margen. El límite de la API protege si la suma de todos los planes pudiera superarlo.
3. **Empieza por valores holgados** y ajusta. Es mucho más fácil reducir un límite que explicar un bloqueo a un cliente en producción.
4. **Avisa antes de aplicar cambios**, y deja a los consumidores tiempo para adaptarse.

## Qué debe hacer el cliente

Cuando se supera el límite, la API devuelve `429 Too Many Requests`. El consumidor debe respetarlo, usando espera exponencial con *jitter*, en lugar de reintentar de inmediato:

```ts
async function conReintentos(peticion: () => Promise<Response>, intentos = 5) {
  for (let i = 0; i < intentos; i++) {
    const respuesta = await peticion();

    if (respuesta.status !== 429) return respuesta;

    const cabecera = Number(respuesta.headers.get("Retry-After"));
    const espera = cabecera > 0
      ? cabecera * 1000
      : Math.min(1000 * 2 ** i, 30_000) * Math.random();

    await new Promise((resolver) => setTimeout(resolver, espera));
  }

  throw new Error("Límite de uso superado tras varios intentos");
}
```

Documenta el comportamiento en el portal de desarrolladores: cuotas, qué código se devuelve y cómo se debe reaccionar. Así reduces mucho las consultas al equipo.

## Claves de agrupación

Una decisión importante es qué se está contando. Con clientes detrás de un proxy corporativo, muchas personas comparten la misma IP. Si limitas por IP, una oficina entera puede quedarse sin servicio. Es preferible limitar por identidad, siempre que sea posible, y dejar la IP para el tráfico anónimo o para bloquear abusos evidentes.

Comprueba además que el Gateway obtiene la IP real, y no la de tu balanceador, usando la cabecera `X-Forwarded-For` con los proxys de confianza.

## Es protección, no seguridad

Un límite de uso frena el abuso accidental y los picos, pero no sustituye a la autenticación ni a la autorización. Tampoco resuelve un ataque de denegación de servicio distribuido, que debe detenerse antes de llegar al Gateway. Por lo tanto, coloca las defensas por capas: en el borde, en el Gateway y en el propio servicio, ya que este último puede tener otros caminos de entrada.

## Observarlo

Vigila cuántas peticiones se rechazan, y a quién. Un aumento en 429 puede deberse a un cliente con un error, a un plan que se le ha quedado pequeño a alguien o a un abuso. Conviene tener alertas para los consumidores importantes, y no esperar a que te llamen.

## Referencias

- [Límites de uso en WSO2 API Manager](https://apim.docs.wso2.com/en/latest/design/rate-limiting/introducing-throttling-use-cases/)
- [RFC 6585: código 429](https://www.rfc-editor.org/rfc/rfc6585)
