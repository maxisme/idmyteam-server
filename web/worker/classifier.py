import ast
import datetime
import logging
import os
from typing import Tuple, List

import joblib
import numpy as np
from sklearn.svm import SVC
from multiprocessing import Lock

from idmyteamserver.models import Team, Feature
from web.settings import TRAIN_Q_TIMEOUT, TEAM_CLASSIFIER_BASE_DIR
from worker import functions

NO_TRAINING_DATA_MSG = "No training data!"
ALREADY_TRAINING_MSG = "Already training classifier for team!"


class Classifier(object):
    def __init__(self, team: Team):
        self._clf_mutex = Lock()
        self.team = team
        self.clf: SVC = self._get_model()

    def predict(self, features: np.array) -> Tuple[int, float]:
        if not self.clf:
            raise MissingModelException(f"Missing model for: {self.team}")

        # predict member id based on face_coords
        with self._clf_mutex:
            members = self.clf.classes_
            probabilities = self.clf.predict_proba(np.array(features))

        # choose member with highest probability
        member_id, max_prob = 0, 0
        for i, prob in enumerate(probabilities[0]):
            if prob >= max_prob:
                member_id = members[i]
                max_prob = prob
        return member_id, max_prob

    def train(self) -> List[Tuple[int, int]]:
        timeout_training_dttm = datetime.datetime.now() - datetime.timedelta(
            seconds=TRAIN_Q_TIMEOUT
        )
        if (
            self.team.is_training_dttm
            and self.team.is_training_dttm >= timeout_training_dttm
        ):
            raise AlreadyTrainingException(ALREADY_TRAINING_MSG)

        # todo limit number of training events per hour

        # mark team as currently training the classifier
        # TODO defer an is_training False
        self.team.is_training_dttm = datetime.datetime.now()
        self.team.save()

        logging.info(f"Creating new model for {self.team}")

        # create a new model using ALL the team training data
        training_features, training_classes, sample_weight = self._get_training_data()

        if training_features is not None:
            num_training_members = len(np.unique(training_classes))
            # there must be at least 2 classes/members to train
            if num_training_members <= 2:
                raise NotEnoughClassesException(
                    "You must train with more than one team member!"
                )
            clf = SVC(probability=True)  # initialise teams model
        else:
            raise NotEnoughClassesException(NO_TRAINING_DATA_MSG)

        clf.fit(training_features, training_classes, sample_weight=sample_weight)

        logging.info(
            f"fitted {len(training_features)} features from {len(set(training_classes))} classes"
        )

        model_path = TEAM_CLASSIFIER_BASE_DIR + self.team
        joblib.dump(clf, model_path)  # store model
        with self._clf_mutex:
            self.clf = clf  # reload the new model

        # mark all features as not new
        Feature.objects.get(team_id=self.team.id).update(processed=True)

        # mark team as finished training and the location of the model path
        self.team.is_training_dttm = None
        self.team.classifier_model_path = model_path
        self.team.save()

        # fetch number of unique
        unique_outputs = np.bincount([o for o in training_classes if o > 0])
        num_outputs = np.nonzero(unique_outputs)[0]
        # zip class against number trained of class
        return list(zip(num_outputs, unique_outputs[num_outputs]))

    def _get_model(self):
        if not self.team.classifier_model_path:
            return None

        try:
            return joblib.load(self.team.classifier_model_path)
        except FileNotFoundError:
            return None

    def _get_training_data(self) -> (np.array, np.array, np.array):
        training_features, training_classes, weight = [], [], []

        # fetch features from db
        features = Feature.objects.filter(team_id=self.team.id)
        if features:
            for feature in features:
                features = functions.decompress_string(feature.features)

                training_features.append(ast.literal_eval(features))
                training_classes.append(int(feature.member))

                if feature.is_manual:
                    weight.append(1)
                else:
                    weight.append(
                        0.1
                    )  # 1/10th as reliable if data acquired via online learning

        if not training_features:
            return None, None, None
        return (
            np.array(training_features)[:, 0],
            np.array(training_classes),
            np.array(weight),
        )

    def has_trained_model(self) -> bool:
        return bool(self.clf)

    def delete(self) -> bool:
        """
        delete file at teams classifier_model_path
        @return: if file was successfully deleted
        """
        return bool(os.remove(self.team.classifier_model_path))


class AlreadyTrainingException(Exception):
    pass


class MissingModelException(Exception):
    pass


class NotEnoughClassesException(Exception):
    pass
