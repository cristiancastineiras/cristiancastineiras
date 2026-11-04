---
title: "Docker Compose: orden de arranque real con healthcheck y depends_on"
seoTitle: "Compose: healthcheck y depends_on"
description: "Por qué depends_on no espera a que tu base de datos esté lista, y cómo usar healthchecks, migraciones como servicio y perfiles para un entorno local que siempre arranca."
date: 2025-04-03
tags: ["Docker", "Docker Compose", "PostgreSQL"]
---

La API arranca, intenta conectar con PostgreSQL y falla porque todavía no está listo. La solución de siempre: `sleep 10`. Funciona hasta que un equipo más lento necesita 11 segundos. Compose tiene una herramienta mejor.

## Lo que hace `depends_on` por defecto

```yaml
services:
  api:
    depends_on:
      - db
```

Esto solo garantiza que el contenedor `db` se **inicia** antes que `api`. Que un contenedor haya iniciado no significa que el servicio dentro acepte conexiones. PostgreSQL puede tardar varios segundos.

## Con healthcheck

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: aplicacion
      POSTGRES_USER: aplicacion
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Falta POSTGRES_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aplicacion -d aplicacion"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
    volumes:
      - datos:/var/lib/postgresql/data

  api:
    build: ./api
    depends_on:
      db:
        condition: service_healthy

volumes:
  datos:
```

Ahora `api` no arranca hasta que `db` esté sano. La sintaxis `${VAR:?mensaje}` hace que Compose se detenga con un mensaje claro si falta esa variable.

Las opciones:

- `interval`: cada cuánto se comprueba.
- `timeout`: cuánto puede tardar la comprobación.
- `retries`: fallos consecutivos para considerarlo no sano.
- `start_period`: durante este tiempo, un fallo no cuenta.

## Comprobaciones habituales

```yaml
# Redis
test: ["CMD", "redis-cli", "ping"]

# Una API con su endpoint
test: ["CMD-SHELL", "curl -f http://localhost:8080/health/ready || exit 1"]

# SQL Server
test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P \"$$SA_PASSWORD\" -Q 'SELECT 1'"]
```

Las imágenes mínimas no suelen tener `curl`. En una imagen *chiseled* de .NET no hay ni shell, de modo que no puedes usar esto. Una alternativa es añadir a tu aplicación un pequeño comando de comprobación, o publicar una imagen de desarrollo con esas herramientas.

## Las migraciones como servicio

No tiene sentido que cada API aplique migraciones al arrancar. Un servicio que se ejecuta una vez lo deja claro:

```yaml
services:
  migraciones:
    build:
      context: ./api
      target: migraciones
    depends_on:
      db:
        condition: service_healthy

  api:
    build: ./api
    depends_on:
      db:
        condition: service_healthy
      migraciones:
        condition: service_completed_successfully
```

`service_completed_successfully` hace esperar a `api` hasta que `migraciones` termine con código 0. Si fallan, la API no arranca y verás el error directamente.

## Esperar desde scripts y CI

`--wait` hace que el comando no termine hasta que todo esté sano, lo que es perfecto para ejecutar pruebas después:

```bash
docker compose up -d --wait
dotnet test
docker compose down -v
```

Si algún servicio no llega a estar sano, el comando falla con un error. Sin esto, tendrías que escribir un bucle de espera a mano.

## Tu aplicación también debe reintentar

Un `healthcheck` soluciona el arranque del entorno local, pero nada más. En producción, una base de datos se puede reiniciar en cualquier momento, y tu aplicación debe tolerarlo. Con EF Core:

```csharp
options.UseNpgsql(cadena, npgsql => npgsql.EnableRetryOnFailure());
```

En Kubernetes tampoco existe `depends_on`: el modelo son los reintentos y las sondas de disponibilidad. Si tu aplicación solo funciona porque Compose la arranca en orden, el problema aparecerá después.

## Perfiles para lo opcional

No todos necesitan todo a la vez:

```yaml
services:
  kibana:
    image: docker.elastic.co/kibana/kibana:8.18.0
    profiles: [observabilidad]

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.18.0
    profiles: [observabilidad]
```

```bash
docker compose up -d                            # lo esencial
docker compose --profile observabilidad up -d   # con observabilidad
```

Así, el entorno por defecto es ligero, y lo opcional no ralentiza a quien no lo necesita.

## Comprobar el estado

```bash
docker compose ps
docker inspect --format '{{json .State.Health}}' mi-contenedor
```

El segundo comando muestra los últimos resultados de la comprobación, algo muy útil para saber por qué un servicio no llega a estar sano.

## Referencias

- [Orden de arranque en Compose](https://docs.docker.com/compose/how-tos/startup-order/)
- [Referencia de healthcheck](https://docs.docker.com/reference/compose-file/services/#healthcheck)
- [Perfiles de Compose](https://docs.docker.com/compose/how-tos/profiles/)
