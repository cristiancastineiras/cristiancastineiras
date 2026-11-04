---
title: "Adiós a ingress-nginx: cómo migrar a Gateway API en Kubernetes"
seoTitle: "De ingress-nginx a Gateway API"
description: "ingress-nginx se retiró en marzo de 2026 y ya no recibe parches. Qué significa para tu clúster, cómo funciona Gateway API y cómo migrar paso a paso con ingress2gateway."
date: 2026-04-20
tags: ["Kubernetes", "Seguridad", "Arquitectura"]
---

El mantenimiento de `ingress-nginx` terminó en marzo de 2026. Sigue funcionando, y nadie va a retirarlo de tu clúster, pero no recibirá más correcciones de errores ni parches de seguridad. Dado que es un componente expuesto a Internet, conviene no quedarse ahí.

## Qué se retira y qué no

Hay bastante confusión con los nombres:

- **Se retira**: el controlador `kubernetes/ingress-nginx`.
- **No se retira**: la API `Ingress`, que sigue siendo compatible aunque está congelada.
- **No se retira**: NGINX como servidor web.
- **No es lo mismo**: el controlador de F5/NGINX Inc. (`nginxinc/kubernetes-ingress`) es un proyecto distinto, y sigue activo.

Para comprobar si lo usas:

```bash
kubectl get pods --all-namespaces \
  --selector app.kubernetes.io/name=ingress-nginx
```

## Dos caminos

Puedes cambiar a otro controlador de `Ingress`, lo que suele ser más rápido, aunque las anotaciones son específicas de cada uno y no se trasladan sin más. O bien aprovechar para ir a Gateway API, la opción recomendada por el proyecto Kubernetes. Es más trabajo inicial, pero es el camino de futuro.

## Por qué Gateway API

`Ingress` era demasiado limitado, y casi todo lo interesante se añadía con anotaciones específicas de cada controlador. Por eso, las configuraciones no son portables. Gateway API convierte esas funciones en campos estándar, y separa las responsabilidades:

```text
GatewayClass   → qué implementación se usa (plataforma)
Gateway        → puntos de entrada, puertos y TLS (operaciones)
HTTPRoute      → cómo se enruta a cada servicio (equipos)
```

Cada equipo gestiona sus rutas sin poder tocar el Gateway compartido.

## Un ejemplo

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: principal
  namespace: infraestructura
spec:
  gatewayClassName: nginx
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      hostname: "*.ejemplo.com"
      tls:
        mode: Terminate
        certificateRefs:
          - name: certificado-ejemplo
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              gateway-permitido: "true"
```

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-pedidos
  namespace: pedidos
spec:
  parentRefs:
    - name: principal
      namespace: infraestructura
  hostnames:
    - api.ejemplo.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /pedidos
      backendRefs:
        - name: api-pedidos
          port: 8080
```

## Migrar paso a paso

**1. Inventario.** Lista todos los `Ingress` y, sobre todo, sus anotaciones:

```bash
kubectl get ingress -A -o json \
  | jq -r '.items[].metadata.annotations // {} | keys[]' \
  | sort | uniq -c | sort -rn
```

Es lo que marcará el esfuerzo. Presta atención a `configuration-snippet` y `server-snippet`, que contienen configuración NGINX arbitraria sin traducción directa. Además, esas anotaciones han sido el origen de vulnerabilidades graves, como las de IngressNightmare en 2025.

**2. Elegir una implementación.** Hay varias, como NGINX Gateway Fabric, Envoy Gateway, Istio, Cilium o las de los proveedores de nube. Compara lo que necesitas de verdad: conformidad con la especificación, funcionalidades, cómo se opera y si tu equipo ya conoce esa tecnología.

**3. Convertir con ingress2gateway.** La herramienta oficial traduce recursos y avisa de lo que no puede traducir:

```bash
ingress2gateway print --providers=ingress-nginx --namespace=pedidos
```

Revisa el resultado. No es una migración automática, sino un punto de partida. Busca esos avisos, porque lo que no se traduce suele ser lo que causa los incidentes.

**4. Ejecutar en paralelo.** Instala el controlador nuevo, y déjalo con su propia IP mientras el antiguo sigue sirviendo el tráfico. Prueba con un `curl` directo:

```bash
curl --resolve api.ejemplo.com:443:IP_DEL_NUEVO_GATEWAY \
  https://api.ejemplo.com/pedidos/health
```

**5. Comparar.** Compara códigos de estado, cabeceras, redirecciones, límites de tamaño, tiempos de espera y cómo se ven las IP de cliente. Los valores por defecto no coinciden entre controladores. Si tus logs se analizan con paneles y alertas, también tendrás otro formato.

**6. Cambiar el tráfico poco a poco.** Reduce antes el TTL del DNS, y mueve primero los servicios de menos riesgo. Mantén el controlador antiguo un tiempo, para poder volver atrás.

**7. Retirar.** Elimina el controlador antiguo y sus recursos. Uno que siga ahí sin usarse continúa siendo una superficie de ataque.

## Lo que no te da gratis

Revisa lo que hacían tus anotaciones, ya que puede no tener un equivalente directo: autenticación externa, *rate limiting*, reescrituras con expresiones regulares o WAF. Algunas tienen campos estándar o políticas de la implementación elegida. Y hay implementaciones que resuelven el resto con sus propios recursos, lo que reduce un poco la portabilidad.

## Si no puedes migrar pronto

Reduce el riesgo mientras tanto: no permitas *snippets*, limita quién puede crear `Ingress`, protege el *webhook* de admisión y restringe el acceso de red al controlador. Existen forks de mantenimiento y soporte comercial, que pueden darte tiempo, pero no son una solución definitiva.

## Referencias

- [Anuncio de la retirada de Ingress NGINX](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [ingress2gateway](https://github.com/kubernetes-sigs/ingress2gateway)
