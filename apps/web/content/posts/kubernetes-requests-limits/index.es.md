---
title: "Requests y limits en Kubernetes: asignar CPU y memoria sin desperdiciar ni sufrir OOMKills"
seoTitle: "Requests y limits en Kubernetes"
description: "Qué significan requests y limits en Kubernetes, qué ocurre al superarlos, cómo elegir valores con datos reales y cómo se comporta .NET con los límites de un contenedor."
date: 2025-12-18
tags: ["Kubernetes", ".NET", "Rendimiento"]
---

Estos valores se suelen copiar de otro servicio, o inflar por si acaso. Luego, unos pods mueren sin motivo aparente, otros van lentos con la CPU en apariencia libre, y el clúster está medio vacío mientras la factura sigue creciendo. Para corregirlo, hay que entender qué hace cada uno.

## Requests y limits

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    memory: "512Mi"
```

- **Request**: lo que se reserva. El planificador lo usa para elegir un nodo con hueco suficiente.
- **Limit**: el máximo que se permite usar.

`250m` son 250 milicores, un cuarto de CPU.

## La CPU y la memoria se comportan de forma muy distinta

**CPU: comprimible.** Al superar el límite, el contenedor se ralentiza, pero sigue vivo. Es el llamado *throttling*.

**Memoria: no comprimible.** Si la superas, el núcleo mata el proceso: `OOMKilled`. No hay ralentización ni aviso previo.

## El debate del límite de CPU

Un límite de CPU puede causar un problema difícil de ver. La cuota se aplica por periodos de 100 ms. Un servicio con varios hilos puede agotarla en los primeros milisegundos, y quedarse parado el resto del periodo, con el nodo lleno de CPU sin usar. Se manifiesta como latencia alta en los percentiles superiores, sin una causa aparente.

Por eso, muchos equipos ponen `requests` de CPU y omiten su `limit`. Así, el reparto por `requests` protege a los demás cuando hay contención, y cuando no la hay, el servicio aprovecha lo que está libre. Para memoria, en cambio, siempre debe haber un límite.

Si tu organización exige límites, compruébalo con esta métrica:

```promql
rate(container_cpu_cfs_throttled_periods_total[5m])
  / rate(container_cpu_cfs_periods_total[5m])
```

## Clases de QoS

Kubernetes usa estos valores para decidir qué expulsar cuando un nodo se queda sin memoria:

| Clase | Condición | Expulsión |
|---|---|---|
| Guaranteed | requests igual a limits | La última |
| Burstable | requests por debajo de limits | Intermedia |
| BestEffort | Sin requests ni limits | La primera |

Nunca dejes un servicio importante sin requests: sería el primero en caer.

## Cómo elegir los valores

No lo adivines: mide. Observa el consumo real durante varios días, incluyendo los picos:

```bash
kubectl top pods -n produccion
```

Si tienes Prometheus, mejor aún:

```promql
quantile_over_time(0.95, container_memory_working_set_bytes{container="api"}[7d])
```

Una regla de partida:

- **Request de memoria**: el uso típico, con algo de margen.
- **Limit de memoria**: el pico observado, más un margen del 20-30 %.
- **Request de CPU**: el consumo habitual.

El *Vertical Pod Autoscaler* en modo `Off` no cambia nada, y puede darte recomendaciones basadas en datos históricos, lo cual resulta muy útil para empezar.

## .NET y los límites del contenedor

.NET respeta los límites del contenedor, y ajusta su comportamiento según ellos:

- `Environment.ProcessorCount` tiene en cuenta el límite de CPU, redondeado al alza. Esto influye en el grupo de hilos y en el recolector de basura.
- El GC limita por defecto su heap al 75 % del límite de memoria.

Sin límite de CPU, .NET usa todos los núcleos del nodo, de modo que un servicio con `request` de medio núcleo en un nodo de 64 puede crear muchos heaps de Server GC, y consumir bastante más memoria. Puedes indicar cuántos procesadores ve el runtime:

```yaml
env:
  - name: DOTNET_PROCESSOR_COUNT
    value: "2"
```

Para contenedores pequeños, también puedes probar `DOTNET_gcServer=0`, o apoyarte en el modo DATAS del recolector, activo por defecto desde .NET 9, que adapta el tamaño del heap a la carga.

No uses esto a ciegas. Mide con `dotnet-counters`, y con métricas del contenedor, antes y después de cada ajuste.

## Investigar un OOMKilled

```bash
kubectl describe pod api-7c9d8 | grep -A5 "Last State"
```

```text
Last State:   Terminated
  Reason:     OOMKilled
  Exit Code:  137
```

Antes de aumentar el límite, comprueba si la memoria crece sin parar, lo que indicaría una fuga, en cuyo caso más memoria solo retrasaría el problema. También puede ser un pico por cargar datos demasiado grandes en memoria.

Y no te fíes solo de la memoria del proceso. El contador `working_set` incluye también la caché de páginas activa, y es el que usa Kubernetes.

## Barreras a nivel de namespace

Un `LimitRange` asigna valores por defecto, y un `ResourceQuota` limita el total por namespace. Son útiles en clústeres compartidos, porque evitan que un equipo despliegue sin requests o consuma todo el clúster.

## Referencias

- [Gestión de recursos de contenedores](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Clases de QoS](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)
- [Configuración del GC de .NET](https://learn.microsoft.com/dotnet/core/runtime-config/garbage-collector)
