def branch = "${BRANCH_NAME}".replaceAll('-', '_').replaceAll('/', '_')
def virtualenv = "~/.virtualenvs/${branch}"

pipeline {
  stages {
    stage('venv-setup') {
      steps {
        sh """
        virtualenv ${virtualenv}
        . ${virtualenv}/bin/activate
        echo ${@}
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