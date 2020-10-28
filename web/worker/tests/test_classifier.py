from datetime import datetime

import pytest

from tests.helpers import create_test_team
from worker.classifier import (
    Classifier,
    MissingModelException,
    NotEnoughClassesException,
    AlreadyTrainingException,
)


@pytest.mark.django_db
def test_no_training_data():
    team, team_dict = create_test_team()
    classifier = Classifier(team)
    with pytest.raises(NotEnoughClassesException):
        classifier.train()


@pytest.mark.django_db
def test_already_training():
    team, team_dict = create_test_team()
    team.is_training_dttm = datetime.now()  # force mark as training
    classifier = Classifier(team)
    with pytest.raises(AlreadyTrainingException):
        classifier.train()


@pytest.mark.django_db
def test_predict_with_no_model():
    team, team_dict = create_test_team()
    classifier = Classifier(team)
    with pytest.raises(MissingModelException):
        classifier.predict(None)
