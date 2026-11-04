---
title: "Cómo montar tu propia mini nube con Linux, Docker y Cloudflare Tunnel"
description: "Una guía práctica para publicar servicios desde un ordenador doméstico con Docker Compose, Cloudflare Tunnel y Linux, sin abrir puertos y con un coste cercano a cero."
date: 2026-11-04
tags: ["Docker", "Linux", "Cloudflare", "Homelab"]
---

La nube parece algo reservado a grandes proveedores: máquinas virtuales, redes privadas, balanceadores, almacenamiento y facturas difíciles de predecir.

Pero para alojar una web personal, una pequeña API, un panel interno o una herramienta de desarrollo no necesitas reproducir toda la infraestructura de AWS. Un ordenador con Linux, Docker y Cloudflare Tunnel puede cubrir una parte importante de esas necesidades.

La idea es sencilla:

```text
Internet
   │
   ▼
Cloudflare
   │
   │ túnel cifrado saliente
   ▼
Servidor Linux
   │
   ▼
Docker Compose
   ├── web
   ├── api
   └── base de datos
```

El servidor inicia una conexión saliente hacia Cloudflare. Las visitas entran por esa conexión y llegan al contenedor correspondiente. No hace falta abrir los puertos `80` o `443` en el router ni disponer de una IP pública fija.

No es una alternativa completa a AWS. Es una infraestructura doméstica pequeña, útil para aprender y suficiente para servicios con poco tráfico.

## Qué significa realmente «coste cero»

El software utilizado en esta arquitectura puede ser gratuito:

- una distribución Linux
- Docker Engine
- Docker Compose
- Cloudflare Tunnel
- certificados HTTPS gestionados por Cloudflare

Aun así, coste cero no significa ausencia total de costes. Necesitas una máquina, electricidad y normalmente un dominio propio. Si ya tienes un ordenador que no utilizas y un dominio, el coste adicional puede ser prácticamente cero.

Los dominios, el consumo eléctrico, las copias externas y cualquier ampliación de hardware siguen teniendo un coste. Tampoco existe una garantía de que los planes gratuitos de terceros mantengan para siempre las mismas condiciones.

## El hardware

No necesitas un servidor profesional. Para empezar puede servir:

- un mini PC antiguo
- un portátil que ya no utilices
- una Raspberry Pi
- un ordenador de sobremesa
- una máquina virtual dentro de otro equipo

Para varias aplicaciones pequeñas, una configuración razonable sería:

```text
CPU:          2 núcleos
Memoria:      4 GB de RAM
Almacenamiento: 40 GB SSD
Red:          conexión por cable
```

Un SSD mejora mucho la experiencia frente a una tarjeta SD o un disco mecánico. Si utilizas un portátil, su batería puede actuar como un pequeño sistema de alimentación ininterrumpida, aunque no sustituye a una estrategia real de respaldo eléctrico.

## Instalar un Linux sencillo

Ubuntu Server o Debian son buenas opciones porque tienen documentación abundante, actualizaciones estables y soporte directo para Docker.

Durante la instalación conviene:

1. crear un usuario normal
2. activar el servidor SSH
3. asignar una dirección IP local estable
4. evitar instalar un entorno gráfico
5. aplicar todas las actualizaciones disponibles

Después de entrar por SSH:

```bash
sudo apt update
sudo apt upgrade -y
```

Activa también el cortafuegos y permite únicamente SSH desde la red local:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp
sudo ufw enable
```

Debes sustituir `192.168.1.0/24` por el rango real de tu red doméstica.

No expongas SSH directamente a Internet. Si necesitas administración remota, utiliza Cloudflare Access, una VPN como WireGuard o Tailscale, y autenticación mediante claves.

## Instalar Docker

La instalación debe realizarse desde el repositorio oficial de Docker para evitar paquetes antiguos. Una vez instalado Docker Engine junto con el complemento de Compose, comprueba ambos comandos:

```bash
docker --version
docker compose version
```

Puedes permitir que tu usuario ejecute Docker sin `sudo`:

```bash
sudo usermod -aG docker "$USER"
```

La pertenencia al grupo `docker` equivale prácticamente a tener privilegios de administrador. No añadas usuarios que no sean de confianza y vuelve a iniciar sesión para aplicar el cambio.

## Crear el primer servicio

Voy a utilizar Nginx como ejemplo porque permite comprobar la arquitectura sin depender de una aplicación concreta.

Crea esta estructura:

```text
/opt/mini-nube/
├── compose.yaml
├── cloudflared/
│   └── config.yml
└── web/
    └── index.html
```

El archivo `compose.yaml` define la aplicación y el túnel:

```yaml
services:
  web:
    image: nginx:1.27-alpine
    restart: unless-stopped
    volumes:
      - ./web:/usr/share/nginx/html:ro
    networks:
      - privada

  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run
    environment:
      TUNNEL_TOKEN: ${TUNNEL_TOKEN}
    depends_on:
      - web
    networks:
      - privada

networks:
  privada:
```

El contenedor `web` no publica ningún puerto en el servidor. Solo puede recibir tráfico desde otros contenedores conectados a la red `privada`.

Esta diferencia es importante. Lo siguiente expondría Nginx en toda la red local:

```yaml
ports:
  - "8080:80"
```

Como Cloudflare Tunnel puede comunicarse directamente con `web:80`, esa publicación no es necesaria.

## Crear el túnel en Cloudflare

Necesitas tener el dominio gestionado por Cloudflare. Desde el panel de Zero Trust:

1. abre **Networks**
2. entra en **Tunnels**
3. crea un túnel de tipo Cloudflared
4. selecciona Docker como entorno
5. copia el token generado
6. añade un hostname público

Por ejemplo:

```text
Hostname: app.midominio.com
Service:  http://web:80
```

Cloudflare crea el registro DNS y dirige el tráfico hacia el túnel. La conexión se origina desde tu servidor, por lo que no necesitas configurar redirecciones de puertos en el router.

Guarda el token en un archivo `.env`:

```dotenv
TUNNEL_TOKEN=el-token-generado-por-cloudflare
```

Protege el archivo para que solo pueda leerlo su propietario:

```bash
chmod 600 .env
```

No subas `.env` al repositorio. Si el token se filtra, debes revocarlo y generar uno nuevo.

Inicia los servicios:

```bash
docker compose up -d
```

Comprueba su estado:

```bash
docker compose ps
docker compose logs cloudflared
```

Cuando el túnel esté conectado, la aplicación debería estar disponible mediante HTTPS en el hostname configurado.

## Desplegar aplicaciones reales

Puedes sustituir Nginx por cualquier aplicación que escuche dentro de un contenedor:

```yaml
services:
  app:
    image: ghcr.io/usuario/aplicacion:latest
    restart: unless-stopped
    env_file:
      - .env
    expose:
      - "3000"
    networks:
      - privada
```

En Cloudflare configurarías:

```text
Hostname: app.midominio.com
Service:  http://app:3000
```

Para añadir otra aplicación, crea otro servicio y otro hostname:

```text
blog.midominio.com      → http://blog:1313
api.midominio.com       → http://api:3000
panel.midominio.com     → http://panel:8080
```

No necesitas un túnel distinto para cada contenedor. Un mismo túnel puede enrutar varios hostnames hacia diferentes servicios.

## Datos persistentes

Los contenedores son reemplazables. Los datos importantes deben permanecer fuera de ellos mediante volúmenes.

Una base de datos PostgreSQL podría definirse así:

```yaml
services:
  database:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: aplicacion
      POSTGRES_USER: aplicacion
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - privada

volumes:
  postgres_data:
```

La base de datos no necesita `ports` ni un hostname público. Solo la aplicación debería poder alcanzarla dentro de la red privada de Docker.

Una variable de entorno evita escribir la contraseña directamente en `compose.yaml`, pero no la convierte en un secreto seguro por sí sola. Para proyectos sensibles conviene utilizar secretos de Docker o un gestor específico.

## Copias de seguridad

Un volumen persistente evita perder datos al reemplazar un contenedor, pero no es una copia de seguridad. Si el disco falla, el volumen también desaparece.

Como mínimo, conserva:

- una copia de `compose.yaml`
- las variables necesarias para reconstruir el entorno
- exportaciones periódicas de las bases de datos
- una copia de los archivos generados por los usuarios
- una copia fuera del propio servidor

Para PostgreSQL, una exportación básica sería:

```bash
docker compose exec -T database \
  pg_dump -U aplicacion aplicacion > backup.sql
```

Las copias deben automatizarse, cifrarse si contienen información sensible y probarse mediante una restauración. Una copia que nunca se ha restaurado es solo una suposición.

La regla `3-2-1` sigue siendo una referencia útil: tres copias, en dos soportes distintos y una fuera de la ubicación principal.

## Proteger servicios privados

Que una aplicación sea accesible mediante HTTPS no significa que deba ser pública. Paneles de administración, métricas y herramientas internas deberían quedar detrás de Cloudflare Access.

Access permite exigir una identidad antes de que la petición llegue al túnel. Puedes restringir el acceso a:

- una dirección de correo concreta
- usuarios de una organización
- un proveedor de identidad
- dispositivos que cumplan determinadas reglas

La autenticación de Cloudflare complementa la autenticación de la aplicación, pero no debería sustituirla cuando el propio servicio maneja permisos o datos sensibles.

## Actualizaciones

Las imágenes fijadas a una versión concreta son más predecibles que `latest`. Por ejemplo:

```yaml
image: nginx:1.27-alpine
```

Actualizar automáticamente todo puede romper una aplicación sin previo aviso. Para una instalación pequeña resulta más seguro revisar y desplegar los cambios conscientemente:

```bash
docker compose pull
docker compose up -d
docker image prune
```

También hay que actualizar el sistema operativo:

```bash
sudo apt update
sudo apt upgrade
```

Antes de una actualización importante, comprueba que las copias de seguridad existen y pueden restaurarse.

## Observabilidad mínima

No necesitas desplegar una plataforma completa de monitorización desde el primer día. Empieza comprobando cuatro cosas:

```bash
docker compose ps
docker compose logs --tail=100
df -h
free -h
```

Esto permite detectar contenedores reiniciándose, errores recientes, discos llenos y falta de memoria.

Cuando el número de servicios crezca, puedes añadir alertas de disponibilidad, métricas y centralización de logs. Hacerlo antes de tener una necesidad real añade más sistemas que mantener que problemas resueltos.

## Qué se parece a AWS

Esta arquitectura reproduce de forma sencilla varios conceptos habituales de una nube pública:

| Nube pública | Mini nube doméstica |
|---|---|
| Máquina virtual | Servidor Linux |
| Servicio de contenedores | Docker Compose |
| Red privada | Red interna de Docker |
| Balanceador o proxy público | Cloudflare Tunnel |
| DNS y HTTPS | Cloudflare |
| Disco persistente | Volúmenes de Docker |
| Control de acceso | Cloudflare Access |
| Infraestructura declarativa | `compose.yaml` |

La comparación sirve como modelo mental, no como equivalencia técnica. AWS ofrece redundancia, regiones, escalado, servicios gestionados y acuerdos de disponibilidad que un servidor doméstico no puede proporcionar.

## Límites de esta arquitectura

Esta solución no es adecuada para todo.

El servicio dejará de estar disponible si:

- se corta la electricidad
- falla la conexión doméstica
- el proveedor aplica CGNAT con restricciones adicionales
- el disco o el servidor se averían
- Cloudflare tiene una incidencia
- una actualización rompe los contenedores

Tampoco es una buena opción para información especialmente sensible, cargas críticas, grandes volúmenes de tráfico o aplicaciones que necesiten garantías contractuales.

Si una caída implica pérdidas económicas, incumplimientos legales o daños a usuarios, necesitas una infraestructura diseñada para ese nivel de responsabilidad.

## Resultado

Con un servidor Linux, Docker Compose y Cloudflare Tunnel puedes alojar aplicaciones desde casa sin abrir puertos públicos, sin administrar certificados manualmente y sin depender de una IP fija.

La parte importante no es copiar una configuración concreta. Es entender las piezas:

- Linux mantiene la máquina
- Docker aísla y reproduce los servicios
- las redes internas limitan la exposición
- Cloudflare conecta Internet con los contenedores
- Access protege las herramientas privadas
- las copias de seguridad protegen los datos

Es una forma económica de aprender redes, despliegues, contenedores, seguridad y operación de servicios reales. No sustituye a una nube pública, pero sí permite construir una nube pequeña que entiendes de principio a fin.