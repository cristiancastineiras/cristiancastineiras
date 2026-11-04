---
title: "Sondas en Kubernetes: liveness, readiness y startup sin reinicios en cadena"
seoTitle: "Sondas de Kubernetes: guía práctica"
description: "Cómo configurar liveness, readiness y startup en Kubernetes, qué no comprobar en cada una, y cómo evitar reinicios en cadena durante despliegues y picos de carga."
date: 2025-10-23
tags: ["Kubernetes", "Observabilidad", "ASP.NET Core"]
---

Una sonda mal configurada puede tumbar un servicio que estaba sano. El caso clásico: una dependencia responde despacio, la comprobación de vida falla, Kubernetes reinicia los pods, los que quedan reciben aún más carga, y empiezan a fallar también. Saber qué pregunta responde cada sonda evita casi todos estos problemas.

## Las tres sondas

| Sonda | Pregunta | Si falla |
|---|---|---|
| **Startup** | ¿Ha terminado de arrancar? | Se reinicia al agotar los intentos |
| **Readiness** | ¿Puede atender tráfico ahora? | Se retira del servicio, sin reinicio |
| **Liveness** | ¿Está bloqueado sin remedio? | Se reinicia |

## Una configuración de partida

```yaml
containers:
  - name: api
    image: registro.ejemplo.com/api:1.4.0
    ports:
      - containerPort: 8080
    startupProbe:
      httpGet:
        path: /health/live
        port: 8080
      periodSeconds: 5
      failureThreshold: 30
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8080
      periodSeconds: 10
      timeoutSeconds: 3
      failureThreshold: 3
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8080
      periodSeconds: 20
      timeoutSeconds: 3
      failureThreshold: 3
```

La sonda de arranque concede aquí hasta 150 segundos (5 × 30). Mientras no tenga éxito, las otras dos no se ejecutan. Esto permite un arranque lento sin tener que relajar la comprobación de vida.

## Qué debe comprobar cada una

**Liveness: solo el proceso.** Debe devolver un resultado rápido y sin consultar nada externo. Si tu sonda de vida consulta la base de datos, cuando esta tenga un problema, reiniciarás todos los pods sin resolver nada.

```csharp
app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false,
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready"),
});
```

Hay quien recomienda directamente no tener sonda de vida si no tienes un caso claro, y es un consejo razonable. Si tu proceso termina cuando algo va mal, Kubernetes ya lo reinicia. Esta sonda solo aporta valor para los bloqueos en los que el proceso sigue vivo pero no responde.

**Readiness: lo imprescindible para atender.** Puede comprobar dependencias, con cuidado: si la base de datos falla, y todos tus pods se marcan como no listos, el servicio devolverá errores de conexión en lugar de los tuyos. Esto puede ser peor que una respuesta 503 con un mensaje claro y con las partes que aún funcionan. Decide de forma explícita lo que ocurre si una dependencia afecta a todas las réplicas a la vez.

## Apagado sin errores

Cuando se elimina un pod, ocurren dos cosas en paralelo: recibe `SIGTERM`, y se retira de los *endpoints*. Durante un instante puede llegarle tráfico, aunque ya esté apagándose. Un pequeño retraso lo soluciona:

```yaml
spec:
  terminationGracePeriodSeconds: 45
  containers:
    - name: api
      lifecycle:
        preStop:
          sleep:
            seconds: 5
```

La acción `sleep` en `preStop` es reciente. Si tu versión de Kubernetes no la admite, usa `exec` con el comando `sleep`, aunque esto requiere que la imagen tenga un shell o un binario `sleep`.

ASP.NET Core termina las peticiones en curso al recibir la señal. Comprueba que `terminationGracePeriodSeconds` sea mayor que el tiempo de espera de la aplicación.

## Despliegues sin cortes

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

Con `maxUnavailable: 0`, Kubernetes no retira un pod antiguo hasta que el nuevo esté listo. Aquí la sonda de disponibilidad es esencial: sin ella, considera listo cualquier pod que haya iniciado.

Para mantener un mínimo de pods durante el mantenimiento de los nodos, añade un `PodDisruptionBudget`.

## Errores frecuentes

- **`timeoutSeconds: 1`, valor por defecto**: bajo carga, un endpoint sano puede tardar más de un segundo, y lo contarías como un fallo. Conviene aumentarlo.
- **Lanzar una consulta costosa en cada sonda**: multiplica su frecuencia por el número de réplicas.
- **Usar el mismo endpoint para las sondas**: pierdes justo lo que las diferencia.
- **Exigir autenticación**: el `kubelet` no tiene credenciales. Exclúyelo, en un puerto interno si es necesario.
- **Ignorar el contador de reinicios**: cualquier reinicio repetido es síntoma de algo, también si el servicio parece ir bien.

## Diagnosticar

```bash
kubectl describe pod api-7c9d8
kubectl get events --field-selector involvedObject.name=api-7c9d8
kubectl logs api-7c9d8 --previous
```

`describe` muestra los eventos de las sondas fallidas, y `--previous` los logs del contenedor anterior al reinicio, que suelen contener el motivo real.

## Referencias

- [Configurar sondas](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Ciclo de vida de un Pod](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
