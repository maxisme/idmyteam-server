
def virtualenv = "~/.virtualenvs/idmyteam-server/"

pipeline {
  agent any

  stages {
    stage('venv-setup') {
      steps {
        sh """
        virtualenv ${virtualenv}
        . ${virtualenv}/bin/activate
        pip3 install -r test_requirements.txt
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