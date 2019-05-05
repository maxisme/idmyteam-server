def virtualenv = "~/.virtualenvs/idmyteam-server/${env.BUILD_ID}"

pipeline {
  agent any
  environment {
    CONF='/conf/test_travis.conf'
    PYTHONPATH="$WORKSPACE/settings/:$WORKSPACE/web/:$PYTHONPATH"
  }
  stages {
    stage('venv-setup') {
      steps {
        sh """
        virtualenv ${virtualenv}
        . ${virtualenv}/bin/activate
        pip3 install -r test_requirements.txt --cache-dir ~/.pip-cache
        """
      }
    }
    stage('test') {
      steps {
        sh """
        . ${virtualenv}/bin/activate
        pytest
        """
      }
    }
  }
  post {
    always {
        sh "rm -rf ${virtualenv}"
    }
}