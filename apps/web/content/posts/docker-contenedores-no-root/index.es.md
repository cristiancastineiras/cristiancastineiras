---
title: "Contenedores sin root: endurecer tus imágenes Docker paso a paso"
seoTitle: "Contenedores Docker sin root"
description: "Por qué tus contenedores no deberían ejecutarse como root y cómo reducir su superficie de ataque: usuario sin privilegios, solo lectura, capacidades y análisis de imágenes."
date: 2025-08-21
tags: ["Docker", "Seguridad", "Linux"]
---

Un contenedor no es una máquina virtual. Comparte el núcleo con el host, y si ejecuta su proceso como `root`, es el mismo `root` de la máquina, aunque con limitaciones. Si un atacante consigue ejecutar código y encuentra una vulnerabilidad para salir del contenedor, ya parte con los máximos privilegios.

Por defecto, muchos contenedores se ejecutan como `root`. Es fácil de corregir.

## Comprobarlo

```bash
docker run --rm mi-imagen id
# uid=0(root) gid=0(root)

docker inspect --format '{{.Config.User}}' mi-imagen
```

Si el resultado está vacío, se ejecuta como `root`.

## Añadir un usuario

```dockerfile
FROM node:22-alpine

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --prod --frozen-lockfile
COPY . .

USER node
CMD ["node", "server.js"]
```

La imagen de Node incluye el usuario `node`. Las de .NET ofrecen `app`, y la variable `$APP_UID`. En otras imágenes, créalo tú:

```dockerfile
FROM debian:12-slim
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --no-create-home app
USER 1001:1001
```

Es mejor usar el número que el nombre: Kubernetes solo puede comprobar `runAsNonRoot` si el usuario es numérico.

## Dos problemas habituales

**Puertos bajos.** Un usuario normal no suele poder abrir puertos por debajo del 1024. Escucha en el 8080, y publícalo en el puerto que necesites:

```yaml
ports:
  - "80:8080"
```

**Permisos de archivos.** Si escribes en una carpeta que es propiedad de `root`, fallará. Asigna el propietario antes de cambiar de usuario:

```dockerfile
RUN mkdir /app/datos && chown 1001:1001 /app/datos
USER 1001:1001
```

Con volúmenes enlazados desde el host, el UID del contenedor debe coincidir con el del directorio en el host, o no tendrá permisos de escritura.

## Sistema de archivos de solo lectura

Si la aplicación no debería cambiar sus propios archivos, impídelo. Un atacante que logre entrar lo tendrá mucho más difícil para dejar herramientas:

```yaml
services:
  api:
    image: registro.ejemplo.com/api:1.4.0
    read_only: true
    tmpfs:
      - /tmp
```

`tmpfs` ofrece un directorio temporal en memoria, necesario para muchas aplicaciones. Lo que necesite persistir va en un volumen.

## Quitar capacidades

Linux divide los privilegios de `root` en capacidades, y Docker concede varias por defecto. La mayoría de las aplicaciones web no necesitan ninguna:

```yaml
services:
  api:
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
```

`no-new-privileges` evita que el proceso obtenga más privilegios, por ejemplo con binarios `setuid`. Si algo deja de funcionar, añade solo la capacidad concreta que necesita, con `cap_add`.

## Limitar recursos

Un contenedor sin límites puede consumir toda la memoria de la máquina y afectar a los demás:

```yaml
services:
  api:
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 200
```

`pids_limit` contiene las bombas de procesos.

## En Kubernetes

Lo mismo se declara en el `securityContext`:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
```

Y puedes exigirlo en todo un namespace con Pod Security Admission, nivel `restricted`.

## El socket de Docker

Montar `/var/run/docker.sock` en un contenedor equivale a darle el control de la máquina: puede crear otro contenedor privilegiado que monte el disco del host. Evítalo salvo que no haya alternativa, y si lo necesitas, usa un proxy que limite las llamadas permitidas.

## Imágenes base pequeñas

Lo que no está en la imagen no puede ser explotado. Una imagen sin shell ni gestor de paquetes, como las *distroless* o las *chiseled* de .NET, limita mucho lo que un atacante puede hacer, y genera menos alertas en los análisis.

## Analizar

```bash
trivy image registro.ejemplo.com/api:1.4.0
```

Añádelo a CI. Hay herramientas similares, como Docker Scout o Grype. Ten en cuenta que no todo lo que señalan es explotable en tu caso. Establece una política razonable, por ejemplo bloquear los críticos con solución disponible, para no acostumbrarte a ignorar las alertas.

## Por dónde empezar

1. `USER` no root, y puerto alto.
2. `no-new-privileges` y `cap_drop: ALL`.
3. Límites de memoria.
4. Sistema de archivos de solo lectura, comprobando dónde escribe la aplicación.
5. Análisis de imágenes en CI.

## Referencias

- [Seguridad en Docker Engine](https://docs.docker.com/engine/security/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
