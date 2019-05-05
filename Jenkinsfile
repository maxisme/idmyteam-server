
def virtualenv = "~/.virtualenvs/idmyteam-server/"

pipeline {
  agent none

  stages {
    stage('venv-setup') {
      steps {
        sh """
        virtualenv ${virtualenv}
        . ${virtualenv}/bin/activate
        pip3 install -r test_requirements.txt --user --cache-dir $HOME/.pip-cache
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