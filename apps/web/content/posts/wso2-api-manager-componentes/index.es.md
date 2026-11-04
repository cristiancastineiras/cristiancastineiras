---
title: "WSO2 API Manager: qué hace cada componente y cómo se relacionan"
seoTitle: "WSO2 API Manager: componentes"
description: "Una introducción práctica a WSO2 API Manager: Publisher, Developer Portal, Gateway, Key Manager y Traffic Manager, y el recorrido de una petición de principio a fin."
date: 2025-09-18
tags: ["WSO2", "Arquitectura", "REST"]
---

Cuando una organización tiene decenas de APIs, cada una con su propia autenticación, sus límites y su documentación, el problema deja de ser técnico y pasa a ser de gobierno. Un gestor de APIs lo centraliza. WSO2 API Manager es una de las opciones de código abierto más completas, pero su documentación es extensa, y al principio cuesta ver cómo encajan sus piezas.

## Los componentes

**API Publisher.** Es donde los equipos crean y gestionan sus APIs: importan la especificación OpenAPI, definen el backend, la seguridad y las políticas, y las publican. También controla el ciclo de vida: `Created`, `Published`, `Deprecated`, `Retired`.

**Developer Portal.** Es lo que ven los consumidores: un catálogo con la documentación, donde pueden crear aplicaciones, suscribirse a una API y obtener credenciales. Permite el autoservicio, sin que cada integración requiera un correo a otro equipo.

**API Gateway.** Es el componente por el que pasa el tráfico real. Valida los tokens, aplica las políticas y enruta las peticiones hacia el backend. Es la pieza más crítica en tiempo de ejecución, y la que debe escalar.

**Key Manager.** Gestiona las claves y los tokens. Puede ser el componente integrado, o bien un proveedor externo como Keycloak, Okta o Microsoft Entra.

**Traffic Manager.** Calcula y aplica las políticas de límite de uso en tiempo real, a partir de eventos que recibe del Gateway. También propaga las revocaciones de tokens y otros cambios.

## El recorrido de una petición

```text
Cliente
   │  Authorization: Bearer <token>
   ▼
API Gateway
   ├─ 1. Valida el token (firma, caducidad, alcance)
   ├─ 2. Comprueba la suscripción de la aplicación
   ├─ 3. Consulta los límites de uso
   ├─ 4. Aplica mediación y políticas
   ▼
Backend
```

Lo interesante es que el Gateway sigue funcionando aunque el Publisher o el portal no estén disponibles. Recibe los artefactos desplegados y valida los JWT de forma local, de modo que no necesita consultar cada petición. Separar el plano de control del de datos es lo que permite escalar el Gateway sin escalar el resto.

## El ciclo de trabajo de un equipo

1. Importar la especificación OpenAPI en el Publisher, o generarla desde el código.
2. Configurar el backend por entorno, la seguridad y los *scopes* de cada operación.
3. Crear una revisión y desplegarla en un Gateway.
4. Publicarla en el Developer Portal.
5. El consumidor crea una aplicación, se suscribe y genera un token.

Las revisiones son inmutables, lo que permite volver atrás rápidamente.

## Gestionar como código

Hacer esto con clics en cada entorno es propenso a errores. La herramienta `apictl` permite exportar e importar APIs, y usarlas en un pipeline de CI/CD:

```bash
apictl add env produccion \
  --apim https://apim.ejemplo.com

apictl login produccion -k

apictl import api \
  --file ./PedidosAPI_1.0.0.zip \
  --environment produccion \
  --update
```

Los valores que cambian entre entornos, como la URL del backend, van en un archivo de parámetros, y así un mismo artefacto se puede promover entre entornos sin modificarlo.

## Tokens: lo que debes saber

Los JWT se validan sin consultar al servidor, por lo que son eficientes, aunque su revocación necesita propagarse. WSO2 lo gestiona enviando eventos a los gateways. Ajusta bien su tiempo de vida: una hora puede ser razonable para un cliente con refresco de token.

A menudo, también quieres que el backend sepa quién llama. El Gateway puede generar un JWT interno, con los datos del usuario y de la aplicación, y enviarlo en una cabecera. Tu backend tiene que validar ese token y su firma. No debe confiar en esa cabecera sin más, y además debería ser inaccesible salvo a través del Gateway.

## Despliegue

Se puede empezar con un único nodo que lo incluya todo, algo suficiente para desarrollo o una carga pequeña. Para producción, lo habitual es separar el Gateway del plano de control, y desplegar varias réplicas de cada uno, con una base de datos externa, porque la base de datos embebida no es apta para producción.

Hay charts de Helm oficiales para Kubernetes. Las configuraciones se centralizan en `deployment.toml`, un archivo que conviene mantener bajo control de versiones.

## Cuándo merece la pena

Un gestor completo tiene sentido si necesitas gobernar muchas APIs, dar acceso a consumidores externos o aplicar suscripciones y límites por plan. Si tienes unos pocos servicios internos, y un solo equipo, un proxy inverso o un *ingress* con autenticación puede ser suficiente. Es otro sistema más que mantener y actualizar, y solo se justifica si realmente aprovechas lo que ofrece.

## Referencias

- [Documentación de WSO2 API Manager](https://apim.docs.wso2.com/)
- [Arquitectura de API Manager](https://apim.docs.wso2.com/en/latest/get-started/apim-architecture/)
- [apictl](https://apim.docs.wso2.com/en/latest/install-and-setup/setup/api-controller/getting-started-with-wso2-api-controller/)
