---
title: "Jenkins Configuration as Code: un controlador que se puede reconstruir en minutos"
seoTitle: "Jenkins Configuration as Code (JCasC)"
description: "Cómo describir un controlador Jenkins con JCasC, plugins versionados y una imagen Docker propia, para evitar una instalación artesanal que nadie se atreve a actualizar."
date: 2025-09-25
tags: ["Jenkins", "CI/CD", "Docker"]
---

Muchos controladores Jenkins son piezas únicas: años de clics en la interfaz, plugins instalados a mano y una configuración que nadie podría reproducir. Por eso nadie se atreve a actualizarlos, y entonces se quedan con vulnerabilidades conocidas. Tratar la configuración como código convierte ese servidor en algo reemplazable.

## La imagen

Parte de la imagen oficial, y fija los plugins que necesitas:

```dockerfile
FROM jenkins/jenkins:2.516.3-lts-jdk21

ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/casc.yaml

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY casc.yaml /usr/share/jenkins/casc.yaml
```

```text
# plugins.txt
configuration-as-code:latest
workflow-aggregator:latest
git:latest
credentials-binding:latest
docker-workflow:latest
```

En producción, sustituye `latest` por versiones concretas. Con `jenkins-plugin-cli --list` puedes ver lo instalado para fijarlas. Si no lo haces, la misma imagen puede dar resultados distintos en cada construcción.

El archivo `casc.yaml` queda fuera de `/var/jenkins_home` a propósito: esa ruta suele ser un volumen, y en una instancia existente ocultaría lo que venga en la imagen.

## La configuración

```yaml
# casc.yaml
jenkins:
  systemMessage: "Configurado con JCasC. Los cambios manuales se perderán."
  numExecutors: 0
  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: admin
          password: ${ADMIN_PASSWORD}
  authorizationStrategy:
    roleBased:
      roles:
        global:
          - name: admin
            permissions:
              - Overall/Administer
            entries:
              - user: admin
          - name: lector
            permissions:
              - Overall/Read
              - Job/Read
            entries:
              - group: authenticated

credentials:
  system:
    domainCredentials:
      - credentials:
          - usernamePassword:
              scope: GLOBAL
              id: registro-docker
              username: ${REGISTRO_USUARIO}
              password: ${REGISTRO_CLAVE}

unclassified:
  location:
    url: https://jenkins.ejemplo.com/
  globalLibraries:
    libraries:
      - name: empresa-ci
        retriever:
          modernSCM:
            scm:
              git:
                remote: https://git.ejemplo.com/ci/jenkins-shared-library.git
```

Fíjate en `numExecutors: 0`: las compilaciones no deben ejecutarse en el controlador. Es tanto una medida de seguridad como de estabilidad.

`roleBased` requiere el plugin Role Strategy. Si no sabes qué nombre usar para una opción, una instancia configurada a mano puede exportar su YAML desde la página de JCasC, lo que da un buen punto de partida. El resultado suele contener mucho ruido, así que límpialo antes de guardarlo.

## Secretos

El archivo de configuración va a Git; los secretos, no. Las variables `${...}` se resuelven al arrancar desde el entorno, o desde archivos si defines `SECRETS`. También existen integraciones con Vault o con otros gestores.

```yaml
# Fragmento de compose.yaml
services:
  jenkins:
    build: .
    ports:
      - "8080:8080"
    secrets:
      - ADMIN_PASSWORD
    volumes:
      - jenkins_home:/var/jenkins_home

secrets:
  ADMIN_PASSWORD:
    file: ./secretos/admin_password
```

Los secretos que Docker monta en `/run/secrets/` están disponibles para JCasC por su nombre de archivo.

No expongas el puerto 8080 directamente a Internet. Colócalo detrás de un proxy con TLS y, si puedes, de una VPN o de un control de acceso.

## Crear los trabajos también como código

JCasC configura el controlador, y para los trabajos existe Job DSL:

```yaml
jobs:
  - script: |
      multibranchPipelineJob('api-facturacion') {
        branchSources {
          git {
            id('api-facturacion')
            remote('https://git.ejemplo.com/equipo/api-facturacion.git')
          }
        }
      }
```

Ahora, lo único que queda en el volumen es el historial de compilaciones. Si lo pierdes, tienes un disgusto, pero no un desastre.

## Actualizar sin miedo

Con esto, una actualización se parece a cualquier otro despliegue:

1. crea una rama y cambia la versión de la imagen o de los plugins;
2. construye la imagen en CI; si un plugin es incompatible, fallará aquí;
3. arráncala en un entorno de prueba con datos de ejemplo;
4. comprueba un pipeline representativo;
5. despliega durante una ventana tranquila, y vuelve a la imagen anterior si algo va mal.

Conviene seguir la línea LTS y actualizar con frecuencia, porque las actualizaciones pequeñas son menos arriesgadas. Los avisos de seguridad de Jenkins y de sus plugins son frecuentes y merece la pena tenerlos presentes.

## Qué seguir respaldando

Aunque la configuración esté en Git, sigue habiendo cosas que copiar: el historial y artefactos si los necesitas, y los secretos que Jenkins cifre con su clave maestra. Haz una prueba real: destruye una instancia de prueba, recréala desde cero y comprueba que todo funciona. Esa es la mejor prueba de que no dependes de nada oculto.

## Referencias

- [Configuration as Code](https://www.jenkins.io/projects/jcasc/)
- [Plugin de JCasC](https://github.com/jenkinsci/configuration-as-code-plugin)
- [Imagen oficial de Jenkins](https://github.com/jenkinsci/docker)
