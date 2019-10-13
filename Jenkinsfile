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
    PYTHONPATH="$WORKSPACE:$WORKSPACE/settings/:$WORKSPACE/web/:$PYTHONPATH"
  }

  stages {
    stage('test-setup') {
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
    stage('deploy') {
      steps {
        sh 'ssh -o StrictHostKeyChecking=no jenk@idmy.team "sudo /bin/bash /var/www/idmyteam-server/deploy.sh"'
      }
    }
  }
  post {
    always {
        sh "rm -rf ${virtualenv}"
        deleteDir()
    }
    success {
      setBuildStatus("Build succeeded", "SUCCESS");
    }
    failure {
        setBuildStatus("Build failed", "FAILURE");
    }
  }
}