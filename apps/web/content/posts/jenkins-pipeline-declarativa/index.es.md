---
title: "Jenkins Pipeline declarativo: un Jenkinsfile mantenible para un proyecto .NET"
seoTitle: "Jenkinsfile declarativo para .NET"
description: "Cómo escribir un Jenkinsfile declarativo para .NET: agentes en contenedor, etapas paralelas, publicación de resultados, credenciales y prácticas que evitan pipelines frágiles."
date: 2025-03-13
tags: ["Jenkins", "CI/CD", ".NET"]
---

Jenkins lleva muchos años funcionando en muchas empresas, y sigue siendo muy capaz. Sus peores problemas no suelen venir de la herramienta, sino de la configuración manual en la interfaz, los agentes con software instalado a mano y los scripts que solo entiende una persona. Tener el pipeline en el repositorio resuelve gran parte de ello.

## Un Jenkinsfile de partida

```groovy
pipeline {
    agent {
        docker {
            image 'mcr.microsoft.com/dotnet/sdk:9.0'
            args '-v nuget-cache:/home/jenkins/.nuget/packages -e HOME=/home/jenkins'
        }
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds(abortPrevious: true)
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timestamps()
    }

    environment {
        DOTNET_CLI_TELEMETRY_OPTOUT = '1'
        DOTNET_NOLOGO = '1'
    }

    stages {
        stage('Restaurar') {
            steps {
                sh 'dotnet restore --locked-mode'
            }
        }

        stage('Compilar') {
            steps {
                sh 'dotnet build --no-restore -c Release -warnaserror'
            }
        }

        stage('Probar') {
            steps {
                sh 'dotnet test --no-build -c Release --logger trx --results-directory resultados'
            }
            post {
                always {
                    mstest testResultsFile: 'resultados/*.trx', keepLongStdio: true
                }
            }
        }
    }

    post {
        cleanup {
            cleanWs()
        }
    }
}
```

El paso `mstest` procede del plugin MSTest, y permite que Jenkins muestre el resultado de cada prueba.

## Lo que aporta cada opción

- **`timeout`**: sin esto, un proceso colgado retiene un agente para siempre.
- **`disableConcurrentBuilds(abortPrevious: true)`**: un nuevo commit cancela la compilación anterior de esa rama.
- **`buildDiscarder`**: evita que el disco del controlador se llene, un problema muy habitual.
- **`cleanWs`**: deja el espacio de trabajo limpio. Requiere el plugin Workspace Cleanup.

## Por qué agentes en contenedor

Un agente con SDK instalado a mano acaba siendo un servidor único e irreproducible, con versiones acumuladas y dependencias ocultas. Con `agent { docker { ... } }`, cada compilación parte de una imagen conocida. La versión del SDK queda además en el repositorio, junto al código que la necesita.

Hace falta el plugin Docker Pipeline y, en el agente, acceso a Docker. Si esto te preocupa por seguridad, los agentes efímeros en Kubernetes son una alternativa.

## Etapas en paralelo

```groovy
stage('Verificar') {
    parallel {
        stage('Pruebas unitarias') {
            steps {
                sh 'dotnet test tests/Unitarias --no-build -c Release'
            }
        }
        stage('Formato') {
            steps {
                sh 'dotnet format --verify-no-changes --no-restore'
            }
        }
    }
}
```

## Publicar solo desde la rama principal

```groovy
stage('Publicar imagen') {
    when {
        branch 'main'
    }
    steps {
        withCredentials([usernamePassword(
            credentialsId: 'registro-docker',
            usernameVariable: 'USUARIO',
            passwordVariable: 'CLAVE'
        )]) {
            sh '''
                echo "$CLAVE" | docker login registro.ejemplo.com -u "$USUARIO" --password-stdin
                docker push registro.ejemplo.com/api:"$GIT_COMMIT"
            '''
        }
    }
}
```

Fíjate en las comillas: `'''` hace que el shell expanda las variables, no Groovy. Si usas `"""` con `${CLAVE}`, Groovy interpola el secreto dentro del comando, y puede aparecer en los logs o en el proceso. Jenkins incluso avisa de ello, y conviene no ignorarlo.

## Aprobación manual

```groovy
stage('Desplegar en producción') {
    when { branch 'main' }
    steps {
        input message: '¿Desplegar en producción?', ok: 'Desplegar', submitter: 'responsables'
        sh './desplegar.sh produccion'
    }
}
```

Una compilación en `input` no debería ocupar un agente. Para eso, puedes declarar `agent none` en el pipeline y asignar agentes por etapa, de forma que la espera no bloquee recursos.

## Multibranch

Un *Multibranch Pipeline* detecta automáticamente las ramas y los pull requests que tienen un `Jenkinsfile`. Con esto, cada rama lleva su propio pipeline, sin crear trabajos a mano. El webhook de tu servidor Git evita tener que consultar periódicamente.

## Buenas prácticas

- **Lógica fuera de Groovy**: si puedes, deja la lógica en scripts del repositorio. Es más fácil de probar en local, y menos dependiente de Jenkins.
- **Validar antes de hacer commit**: la herramienta de línea de comandos de Jenkins incluye `declarative-linter`.
- **Pocos plugins**: cada uno es una dependencia que puede romperse en una actualización y una posible vulnerabilidad.
- **Sin ejecutores en el controlador**: las compilaciones deben ejecutarse en agentes. Un trabajo en el controlador puede acceder a sus archivos, y eso incluye credenciales.
- **Código repetido**: si varios proyectos repiten lo mismo, muévelo a una biblioteca compartida.

## Referencias

- [Sintaxis de Pipeline](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Usar Docker con Pipeline](https://www.jenkins.io/doc/book/pipeline/docker/)
- [Credenciales en Pipeline](https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#handling-credentials)
