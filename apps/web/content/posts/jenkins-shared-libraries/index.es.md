---
title: "Jenkins Shared Libraries: deja de copiar el mismo Jenkinsfile en cada repositorio"
seoTitle: "Jenkins Shared Libraries"
description: "Cómo crear una biblioteca compartida de Jenkins, con pasos personalizados, versionado y pruebas, para unificar pipelines de muchos repositorios sin crear un framework interno."
date: 2025-06-12
tags: ["Jenkins", "CI/CD", "Groovy"]
---

Con veinte servicios y veinte `Jenkinsfile` casi idénticos, cada cambio implica veinte pull requests. Con el tiempo, cada uno se va desviando un poco, y ya nadie sabe cuál es la versión correcta. Las Shared Libraries permiten compartir esa lógica desde un único repositorio.

## Estructura

```text
jenkins-shared-library/
├── vars/
│   ├── dotnetBuild.groovy
│   └── pipelineDotnet.groovy
├── src/
│   └── com/empresa/ci/Versionado.groovy
└── resources/
    └── plantillas/deploy.yaml
```

- **`vars/`**: pasos globales, disponibles por su nombre de archivo. Es lo que más vas a usar.
- **`src/`**: clases Groovy normales, para la lógica más compleja.
- **`resources/`**: archivos que se pueden leer con `libraryResource`.

## Un paso personalizado

```groovy
// vars/dotnetBuild.groovy
def call(Map config = [:]) {
    def configuracion = config.configuration ?: 'Release'

    sh 'dotnet restore --locked-mode'
    sh "dotnet build --no-restore -c ${configuracion} -warnaserror"
}
```

## Registrar la biblioteca

En **Administrar Jenkins → Sistema → Global Pipeline Libraries**, añade el repositorio con un nombre, como `empresa-ci`, o decláralo con Configuration as Code para no depender de la interfaz.

Después, se usa en un `Jenkinsfile`:

```groovy
@Library('empresa-ci@v1.4.0') _

pipeline {
    agent { docker { image 'mcr.microsoft.com/dotnet/sdk:9.0' } }

    stages {
        stage('Compilar') {
            steps {
                dotnetBuild(configuration: 'Release')
            }
        }
    }
}
```

## Un pipeline completo como paso

Si muchos proyectos son iguales, se puede encapsular todo:

```groovy
// vars/pipelineDotnet.groovy
def call(Map config) {
    pipeline {
        agent {
            docker { image "mcr.microsoft.com/dotnet/sdk:${config.dotnetVersion ?: '9.0'}" }
        }

        options {
            timeout(time: config.timeoutMinutos ?: 20, unit: 'MINUTES')
        }

        stages {
            stage('Compilar') {
                steps {
                    dotnetBuild()
                }
            }
            stage('Probar') {
                steps {
                    sh 'dotnet test --no-build -c Release'
                }
            }
        }
    }
}
```

Y cada repositorio queda reducido a esto:

```groovy
@Library('empresa-ci@v1.4.0') _

pipelineDotnet(dotnetVersion: '9.0')
```

Es muy cómodo, pero la flexibilidad tiene un límite. Si cada proyecto empieza a pedir sus excepciones, la configuración de este paso se convertirá en un lenguaje propio y difícil de entender. Si un proyecto es diferente, deja que escriba su pipeline usando los pasos pequeños.

## Versionado

```groovy
@Library('empresa-ci@v1.4.0') _   // versión fija
@Library('empresa-ci@main') _     // última versión
```

Depender de `main` significa que un error en la biblioteca rompe todas las compilaciones a la vez. Yo fijaría una etiqueta, y permitiría una actualización controlada: se publica una versión nueva, la prueba un proyecto piloto y luego se extiende al resto. Renovate puede automatizar esas actualizaciones.

Respeta el versionado semántico. Quien usa esta biblioteca espera lo mismo que de cualquier otra dependencia, incluidas unas notas de cambios.

## Seguridad: bibliotecas de confianza

Una biblioteca global de confianza se ejecuta sin *sandbox*, con acceso a las API internas de Jenkins. Cualquiera que pueda hacer un push en ese repositorio puede ejecutar código con esos privilegios en el controlador. Protege esa rama con revisiones obligatorias. Tiene que tratarse como infraestructura crítica.

Tampoco imprimas secretos en los pasos, y usa `withCredentials` para que se enmascaren en los logs.

## Probar la biblioteca

Sin pruebas, cada cambio se valida rompiendo algo en un proyecto real. `JenkinsPipelineUnit` permite probar pasos con simulaciones:

```groovy
class DotnetBuildTest extends BasePipelineTest {
    @Test
    void 'usa la configuracion indicada'() {
        def paso = loadScript('vars/dotnetBuild.groovy')
        helper.registerAllowedMethod('sh', [String]) { }

        paso.call(configuration: 'Debug')

        assertTrue(helper.callStack.any {
            it.methodName == 'sh' && it.args[0].contains('-c Debug')
        })
    }
}
```

Mantén también un repositorio de ejemplo que use la versión candidata, como prueba de integración, antes de publicar.

## Trampas frecuentes

- **Serialización**: Jenkins guarda el estado del pipeline para poder reanudarlo, por lo que todo debe ser serializable. Evita objetos no serializables en variables locales, o marca los métodos con `@NonCPS`, teniendo en cuenta que estos no pueden llamar a pasos como `sh`.
- **Demasiada lógica en Groovy**: Groovy dentro de CPS no se comporta exactamente como el normal, y algunos métodos fallan de forma sorprendente. Lo que no sea orquestación llévalo a un script.
- **Herencia excesiva**: unas pocas funciones bien pensadas son mejor que un framework interno que solo entiende su autor.

## Referencias

- [Extender Pipeline con Shared Libraries](https://www.jenkins.io/doc/book/pipeline/shared-libraries/)
- [JenkinsPipelineUnit](https://github.com/jenkinsci/JenkinsPipelineUnit)
