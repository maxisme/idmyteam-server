def virtualenv = "~/.virtualenvs/idmyteam-server/${env.BUILD_ID}"

void setBuildStatus(String message, String state) {
  step([
      $class: "GitHubCommitStatusSetter",
      reposSource: [$class: "ManuallyEnteredRepositorySource", url: "https://github.com/maxisme/idmyteam-server"],
      contextSource: [$class: "ManuallyEnteredCommitContextSource", context: "ci/jenkins/build-status"],
      errorHandlers: [[$class: "ChangingBuildStatusErrorHandler", result: "UNSTABLE"]],
      statusResultSource: [ $class: "ConditionalStatusResultSource", results: [[$class: "AnyBuildResult", message: message, state: state]] ]
  ]);
}

pipeline {
  agent any
  environment {
    CONF='/conf/test_jenkins.conf'
    PYTHONPATH="$WORKSPACE/settings/:$WORKSPACE/web/:$PYTHONPATH"
  }
  stages {
    stage('venv-setup') {
      steps {
        sh """
        pip3 install -r test_requirements.txt # install globally as sort of cache
        virtualenv ${virtualenv} --system-site-packages
        . ${virtualenv}/bin/activate
        pip3 install -r test_requirements.txt
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
    success {
      setBuildStatus("Build succeeded", "SUCCESS");
    }
    failure {
        setBuildStatus("Build failed", "FAILURE");
    }
  }
}