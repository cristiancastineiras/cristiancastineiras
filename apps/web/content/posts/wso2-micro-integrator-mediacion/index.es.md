---
title: "WSO2 Micro Integrator: transformar e integrar sistemas sin tocar el backend"
seoTitle: "WSO2 Micro Integrator: mediación"
description: "Qué aporta WSO2 Micro Integrator y cuándo usarlo: API de integración con Synapse, transformación de SOAP a JSON, enrutado, manejo de errores y buenas prácticas."
date: 2026-03-23
tags: ["WSO2", "Arquitectura", "Integración"]
---

En una organización grande no todo habla REST y JSON. Hay servicios SOAP de hace quince años, sistemas que solo intercambian archivos y colas de mensajes. Modificar cada sistema para que se entienda con los demás no suele ser una opción. WSO2 Micro Integrator es un motor de integración, pensado para resolver esas diferencias en una capa intermedia.

## Gateway o integrador

Es una distinción importante:

- **API Manager**: gobierna el acceso. Quién puede llamar, con qué límites y con qué credenciales.
- **Micro Integrator**: implementa la integración. Transformar, orquestar y conectar sistemas.

Se suelen usar juntos: el Gateway expone la API y aplica sus políticas, y por detrás, el Micro Integrator habla con los sistemas antiguos.

## Una API de integración

Las integraciones se definen de forma declarativa, con el lenguaje de configuración de Synapse:

```xml
<api xmlns="http://ws.apache.org/ns/synapse" name="ClientesAPI" context="/clientes">
  <resource methods="GET" uri-template="/{id}">
    <inSequence>
      <log level="custom">
        <property name="clienteId" expression="$ctx:uri.var.id"/>
      </log>
      <call>
        <endpoint>
          <http method="get"
                uri-template="https://legado.ejemplo.com/clientes/{uri.var.id}"/>
        </endpoint>
      </call>
      <respond/>
    </inSequence>
    <faultSequence>
      <sequence key="ErrorComun"/>
    </faultSequence>
  </resource>
</api>
```

Cada paso es un *mediador*: `log`, `call`, `respond`, `payloadFactory`, `filter`, etc.

## De SOAP a JSON

Es el caso típico. Tus clientes quieren JSON, y el sistema antiguo solo entiende SOAP:

```xml
<resource methods="GET" uri-template="/{id}">
  <inSequence>
    <payloadFactory media-type="xml">
      <format>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                          xmlns:cli="http://legado.ejemplo.com/clientes">
          <soapenv:Body>
            <cli:ObtenerCliente>
              <cli:Id>$1</cli:Id>
            </cli:ObtenerCliente>
          </soapenv:Body>
        </soapenv:Envelope>
      </format>
      <args>
        <arg evaluator="xml" expression="$ctx:uri.var.id"/>
      </args>
    </payloadFactory>

    <header name="Action" scope="default" value="ObtenerCliente"/>

    <call>
      <endpoint key="ClientesLegadoEP"/>
    </call>

    <property name="messageType" value="application/json" scope="axis2"/>
    <respond/>
  </inSequence>
</resource>
```

La propiedad `messageType` indica al motor cómo debe serializar la respuesta. Para transformaciones más complejas, hay opciones como XSLT, *data mapper* o scripts.

## Enrutar según el contenido

```xml
<switch source="json-eval($.tipo)">
  <case regex="empresa">
    <call>
      <endpoint key="EmpresasEP"/>
    </call>
  </case>
  <case regex="particular">
    <call>
      <endpoint key="ParticularesEP"/>
    </call>
  </case>
  <default>
    <payloadFactory media-type="json">
      <format>{"error": "Tipo no soportado"}</format>
      <args/>
    </payloadFactory>
    <property name="HTTP_SC" value="400" scope="axis2"/>
    <respond/>
  </default>
</switch>
```

Con varias llamadas en paralelo, `clone` y `aggregate` permiten combinar respuestas. Con ello puedes ofrecer una API sencilla sobre sistemas que nunca se diseñaron para trabajar juntos.

## Errores

Sin un manejo específico, un fallo en un sistema antiguo puede acabar como una respuesta extraña en un formato que nadie espera:

```xml
<sequence name="ErrorComun" xmlns="http://ws.apache.org/ns/synapse">
  <log level="custom">
    <property name="error" expression="get-property('ERROR_MESSAGE')"/>
  </log>
  <payloadFactory media-type="json">
    <format>{"title": "Servicio no disponible", "status": 502}</format>
    <args/>
  </payloadFactory>
  <property name="HTTP_SC" value="502" scope="axis2"/>
  <property name="messageType" value="application/problem+json" scope="axis2"/>
  <respond/>
</sequence>
```

Registra el detalle, pero no lo devuelvas al cliente: el error original puede contener URLs internas o trazas de pila.

## Endpoints reutilizables

Las direcciones no deben ir dentro de cada API:

```xml
<endpoint name="ClientesLegadoEP" xmlns="http://ws.apache.org/ns/synapse">
  <address uri="$FILE:clientes.legado.url">
    <timeout>
      <duration>5000</duration>
      <responseAction>fault</responseAction>
    </timeout>
    <suspendOnFailure>
      <errorCodes>101503,101504,101505</errorCodes>
      <initialDuration>2000</initialDuration>
      <progressionFactor>2.0</progressionFactor>
      <maximumDuration>60000</maximumDuration>
    </suspendOnFailure>
  </address>
</endpoint>
```

Un tiempo de espera bien definido es imprescindible. Sin él, un sistema lento puede agotar los hilos del integrador. `suspendOnFailure` actúa como un *circuit breaker*: tras un fallo, deja de llamar durante un tiempo creciente.

## Buenas prácticas

- **Lógica mínima.** Transforma y enruta. Si empiezas a poner reglas de negocio aquí, nadie sabrá dónde están, y serán difíciles de probar.
- **Control de versiones.** Los artefactos se empaquetan en un *Carbon Application* (`.car`) y se despliegan por CI/CD. Nunca edites directamente en el servidor.
- **Configuración externa.** Usa valores por entorno, no URLs dentro del código.
- **Observabilidad.** Propaga un identificador de correlación por todos los sistemas, y registra en un formato uniforme.
- **Pruebas.** Micro Integrator admite pruebas unitarias de sus artefactos, con simulación de endpoints. Úsalas en las transformaciones importantes.

## Cuándo no usarlo

Si tus sistemas ya hablan HTTP y JSON, y solo necesitas llamar a una API, añadir una capa de integración solo crea latencia y otro punto de fallo. Una llamada directa con `HttpClient` es más sencilla y fácil de seguir. Reserva el integrador para situaciones de transformación real, protocolos antiguos u orquestaciones que no pertenecen a ningún sistema.

## Referencias

- [Documentación de WSO2 Micro Integrator](https://mi.docs.wso2.com/)
- [Referencia de mediadores](https://mi.docs.wso2.com/en/latest/reference/mediators/about-mediators/)
