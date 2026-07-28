pipeline {
  environment {
    RANCHER_STACKID = ""
    RANCHER_ENVID = ""
    GIT_NAME = "danswer"
    registry = "eeacms/danswer"
    template = ""
    dockerImage = ''
    tagName = ''
  }

  agent any

  stages {

    stage('Build & Push ( on tag )') {
      when {
        anyOf {
          buildingTag()
          branch 'eea'
        }
      }
      steps {
        parallel(

          "WEB": {
            node(label: 'docker-big-jobs') {
            script {
              checkout scm
              if (env.BRANCH_NAME == 'eea') {
                tagNameW = 'web'
              } else {
                tagNameW = "web-$BRANCH_NAME"
              }
              try {
                dir('web') {
                  dockerImage = docker.build("$registry:$tagNameW", "--no-cache .")
                  docker.withRegistry( '', 'eeajenkins' ) {
                  dockerImage.push()
                  }    
                }
              } finally {
                sh "docker rmi $registry:$tagNameW"
              }
            }
          }
          },

          "BACKEND": {
            node(label: 'docker-big-jobs') {
            script {
              checkout scm
              if (env.BRANCH_NAME == 'eea') {
                tagNameB = 'backend'
              } else {
                tagNameB = "backend-$BRANCH_NAME"
              }
              // Two-stage build: the upstream Dockerfile stays untouched (avoids
              // silent reversion of EEA-specific bits on the next upstream sync -
              // see plans/hf-cache-eea-overlay.md), and Dockerfile.eea layers the
              // HF cache bake on top. Only the overlay image gets pushed.
              try {
                dir('backend') {
                  baseImage = docker.build("$registry:$tagNameB-base", "-f Dockerfile --no-cache .")
                  dockerImage = docker.build("$registry:$tagNameB", "-f Dockerfile.eea --build-arg BASE_IMAGE=$registry:$tagNameB-base --no-cache .")
                  docker.withRegistry( '', 'eeajenkins' ) {
                  dockerImage.push()
                  }
                }
              } finally {
                sh "docker rmi $registry:$tagNameB || true"
                sh "docker rmi $registry:$tagNameB-base || true"
              }
            }
          }
          },

          "MODEL_SERVER": {
            node(label: 'docker-big-jobs') {
            script {
              checkout scm
              if (env.BRANCH_NAME == 'eea') {
                tagNameM = 'model_server'
              } else {
                tagNameM = "model_server-$BRANCH_NAME"
              }
              // Two-stage build: see BACKEND stage comment above.
              try {
                dir('backend') {
                  baseImage = docker.build("$registry:$tagNameM-base", "-f Dockerfile.model_server --no-cache .")
                  dockerImage = docker.build("$registry:$tagNameM", "-f Dockerfile.model_server.eea --build-arg BASE_IMAGE=$registry:$tagNameM-base --no-cache .")
                  docker.withRegistry( '', 'eeajenkins' ) {
                  dockerImage.push()
                  }
                }
              } finally {
                sh "docker rmi $registry:$tagNameM || true"
                sh "docker rmi $registry:$tagNameM-base || true"
              }
            }
          }
          },
        )
      }
    }


    stage('Release catalog ( on tag )') {
      when {
        buildingTag()
      }
      steps{
        node(label: 'docker') {
          withCredentials([string(credentialsId: 'eea-jenkins-token', variable: 'GITHUB_TOKEN'),  usernamePassword(credentialsId: 'jekinsdockerhub', usernameVariable: 'DOCKERHUB_USER', passwordVariable: 'DOCKERHUB_PASS')]) {
            sh '''docker pull eeacms/gitflow; docker run -i --rm --name="$BUILD_TAG-release"  -e GIT_BRANCH="$BRANCH_NAME" -e GIT_NAME="$GIT_NAME" -e DOCKERHUB_REPO="$registry" -e GIT_TOKEN="$GITHUB_TOKEN" -e DOCKERHUB_USER="$DOCKERHUB_USER" -e DOCKERHUB_PASS="$DOCKERHUB_PASS"  -e DEPENDENT_DOCKERFILE_URL="$DEPENDENT_DOCKERFILE_URL" -e RANCHER_CATALOG_PATHS="$template" -e DOCKERHUB_REPO_PREFIX="web\\-\\|backend\\-\\|model_server\\-" -e GITFLOW_BEHAVIOR="RUN_ON_TAG" eeacms/gitflow'''
         }
        }
      }
    }


  }

  post {
    changed {
      script {
        def url = "${env.BUILD_URL}/display/redirect"
        def status = currentBuild.currentResult
        def subject = "${status}: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'"
        def details = """<h1>${env.JOB_NAME} - Build #${env.BUILD_NUMBER} - ${status}</h1>
                         <p>Check console output at <a href="${url}">${env.JOB_BASE_NAME} - #${env.BUILD_NUMBER}</a></p>
                      """
        emailext (subject: '$DEFAULT_SUBJECT', to: '$DEFAULT_RECIPIENTS', body: details)
      }
    }
  }
}
