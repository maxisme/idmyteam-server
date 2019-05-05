def virtualenv = "~/.virtualenvs/idmyteam-server/${env.BUILD_ID}"

pipeline {
  agent any

  stages {
    stage('venv-setup') {
      steps {
        sh """
        echo $(pwd)
        virtualenv ${virtualenv}
        . ${virtualenv}/bin/activate
        pip3 install -r test_requirements.txt --cache-dir ~/.pip-cache
        """
      }
    }
    stage('test') {
      steps {
        sh 'pytest'
      }
      post {
        always {
          junit 'test-reports/*.xml'
        }
      }
    }
  }
}