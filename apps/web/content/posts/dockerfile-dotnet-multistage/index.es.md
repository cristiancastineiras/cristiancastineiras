---
title: "Un buen Dockerfile para .NET: multi-stage, caché de capas e imágenes pequeñas"
seoTitle: "Dockerfile multi-stage para .NET"
description: "Cómo escribir un Dockerfile para ASP.NET Core con compilación por etapas, restauración en caché, usuario sin privilegios e imágenes chiseled, o sin Dockerfile con el SDK."
date: 2025-02-06
tags: ["Docker", ".NET", "CI/CD"]
---

Una imagen de .NET mal construida puede ocupar más de un gigabyte, contener el SDK completo en producción y volver a descargar todos los paquetes por cambiar una línea. Arreglar eso solo requiere unas pocas decisiones.

## Compilación por etapas

```dockerfile
# Etapa de compilación: tiene el SDK
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Primero, los proyectos: esta capa solo cambia si cambian las dependencias
COPY Api/Api.csproj Api/
COPY Dominio/Dominio.csproj Dominio/
RUN dotnet restore Api/Api.csproj

# Después, el resto del código
COPY . .
RUN dotnet publish Api/Api.csproj -c Release -o /app --no-restore

# Etapa final: solo el runtime
FROM mcr.microsoft.com/dotnet/aspnet:9.0-noble-chiseled AS final
WORKDIR /app
COPY --from=build /app .
USER $APP_UID
ENTRYPOINT ["dotnet", "Api.dll"]
```

La imagen final no incluye ni el SDK ni el código fuente, solo la salida de `publish`. Es más pequeña, y tiene una superficie de ataque mucho menor.

## El orden de las capas

Docker reutiliza una capa si ella y todas las anteriores no han cambiado. Por eso, el orden importa:

```dockerfile
# Mal: cualquier cambio en el código repite la restauración
COPY . .
RUN dotnet restore

# Bien: restaurar solo se repite si cambia un .csproj
COPY Api/Api.csproj Api/
RUN dotnet restore Api/Api.csproj
COPY . .
```

Copiar cada `.csproj` a mano resulta tedioso en soluciones grandes. Si las dependencias usan `Directory.Packages.props` o `global.json`, no olvides copiarlos también, porque afectan a la restauración.

## `.dockerignore`

Sin él, `COPY . .` envía todo al contexto de compilación, incluidos secretos y carpetas de compilación local:

```text
**/bin/
**/obj/
.git/
.vs/
**/*.user
.env
**/node_modules/
```

Además de acelerar la compilación, evita que tus `bin/obj` locales se mezclen con los del contenedor, y provoquen errores extraños.

## Imágenes chiseled

Las imágenes *chiseled* de Ubuntu son extremadamente reducidas: no tienen gestor de paquetes ni shell, y se ejecutan sin privilegios de administrador. Eso elimina mucha superficie de ataque y mucho ruido en los análisis de vulnerabilidades.

La contrapartida es que no tienen shell para depurar. Tampoco tienen ICU por defecto, de forma que si tu aplicación necesita globalización completa debes usar la variante `-extra`:

```dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:9.0-noble-chiseled-extra
```

Otra cuestión: al usar `USER $APP_UID`, la aplicación debe escuchar en un puerto sin privilegios. Por defecto, las imágenes desde .NET 8 escuchan en el 8080.

## Publicar sin Dockerfile

El SDK puede construir imágenes directamente, sin necesidad de escribir nada:

```bash
dotnet publish Api/Api.csproj -c Release \
  /t:PublishContainer \
  -p:ContainerRepository=registro.ejemplo.com/api \
  -p:ContainerImageTag=1.4.0
```

Y puedes configurarlo en el proyecto:

```xml
<PropertyGroup>
  <ContainerBaseImage>mcr.microsoft.com/dotnet/aspnet:9.0-noble-chiseled</ContainerBaseImage>
</PropertyGroup>
```

Es muy cómodo si no necesitas nada especial en la imagen, ya que ni siquiera requiere Docker instalado en CI. Si quieres más control, como instalar paquetes del sistema, sigue siendo mejor un Dockerfile.

## Lo que no debe ir en la imagen

Las capas son permanentes: un secreto que copias y borras después sigue en una capa anterior. Para usar un token durante la compilación, por ejemplo con un NuGet privado, usa los secretos de BuildKit:

```dockerfile
RUN --mount=type=secret,id=nuget_token \
    NUGET_TOKEN=$(cat /run/secrets/nuget_token) \
    dotnet restore Api/Api.csproj
```

```bash
docker build --secret id=nuget_token,env=NUGET_TOKEN -t api .
```

La configuración va en variables de entorno al arrancar, y los secretos de ejecución los aporta el entorno de despliegue.

## Etiquetas

Evita `latest`. Etiqueta con el SHA del commit, para saber exactamente qué código hay en producción:

```bash
docker build -t registro.ejemplo.com/api:"$(git rev-parse --short HEAD)" .
```

Fija también las versiones de las imágenes base en tu `Dockerfile`, y actualízalas con Dependabot o Renovate para recibir los parches de seguridad.

## Referencias

- [Imágenes de contenedor de .NET](https://learn.microsoft.com/dotnet/core/docker/container-images)
- [Publicar sin Dockerfile con el SDK](https://learn.microsoft.com/dotnet/core/containers/sdk-publish)
- [Buenas prácticas de Dockerfile](https://docs.docker.com/build/building/best-practices/)
