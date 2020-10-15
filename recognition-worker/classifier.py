import ast
import datetime
import json
import os
from typing import Tuple

import joblib
import numpy as np
from django.db.models import Q
from sklearn.svm import SVC

from idmyteamserver.models import Team, Feature
from idmyteamserver.upload import TRAIN_Q_TIMEOUT
from utils import functions, config
from utils.logs import logger


class Classifier(object):
    def __init__(self, team_username: str):
        self.clf = self._load_model(team_username)
        self.team_username = team_username

    def predict(self, features: np.array) -> Tuple[int, float]:
        if not self.clf:
            raise Exception(f"Missing model for: {self.team_username}")

        # predict member id based on face_coords
        member_id = 0
        max_prob = config.MIN_PROB
        members = self.clf.classes_
        probabilities = self.clf.predict_proba(np.array(features))
        for i, prob in enumerate(probabilities[0]):
            if prob >= max_prob:
                member_id = members[i]
                max_prob = prob

        return member_id, max_prob

    def train(self, team: Team):
        timeout_training_dttm = datetime.datetime.now() - datetime.timedelta(
            seconds=TRAIN_Q_TIMEOUT
        )
        if team.is_training_dttm and team.is_training_dttm >= timeout_training_dttm:
            raise Exception("Already training classifier for team")

        # mark team as currently training the classifier
        # TODO defer an is_training False
        team.is_training_dttm = datetime.datetime.now()
        team.save()

        socket = functions.create_local_socket(config.LOCAL_SOCKET_URL)

        logger.info(f"Creating new model for {self.team_username}")

        # create a new model using ALL the team training data
        training_input, training_output, sample_weight = self._get_training_data()

        if training_input is not None:
            # make sure there are more than 1 classes to train model
            if len(np.unique(training_output)) <= 1:
                return functions.send_to_client(
                    socket,
                    self.team_username,
                    {
                        "type": "error",
                        "mess": "You must train with more than one team member!",
                    },
                )
            else:
                clf = SVC(probability=True)
        else:
            return functions.send_to_client(
                socket,
                self.team_username,
                {
                    "type": "error",
                    "mess": f"You must train with at least {config.MIN_CLASSIFIER_TRAINING_IMAGES} members!",
                },
            )

        clf.fit(training_input, training_output, sample_weight=sample_weight)

        new_output = [o for o in training_output if o > 0]
        unique_outputs = np.bincount(new_output)
        num_outputs = np.nonzero(unique_outputs)[0]
        cnt_uni = list(zip(num_outputs, unique_outputs[num_outputs]))

        logger.info(
            f"fitted {len(training_input)} features from {len(set(training_output))} classes"
        )

        model_path = self.get_model_path(self.team_username, True)
        joblib.dump(clf, model_path)  # save model to
        self.clf = clf  # reload the new model

        # mark all features as not new
        Feature.objects.filter(team__username=self.team_username).update(processed=True)

        # mark team as finished training
        team.is_training_dttm = None
        team.save()

        # send message to client with who has been trained
        functions.send_to_client(
            socket,
            self.team_username,
            {
                "type": "trained",
                "trained_members": json.dumps(cnt_uni, default=functions.json_helper),
            },
        )

    def _load_model(self, team_username: str):
        model_path = self.get_model_path(team_username)
        if model_path:
            return joblib.load(model_path)
        return None

    # def _should_update_model(self, clf, x, y, conn):
    #     cv = ShuffleSplit(n_splits=30)
    #     scores = cross_val_score(clf, x, y, cv=cv)
    #     logger.info(f"{scores.mean()} -- +/- {scores.std()}")
    #
    #     mb_size = sys.getsizeof(clf) * 1e6
    #     logger.info(
    #         f"{mb_size}MB {self.hashed_username}", mb_size, self.hashed_username
    #     )
    #
    #     if mb_size < config.MAX_CLASSIFIER_SIZE_MB:
    #         # check if this mean score is better than the last within margin
    #         cur = conn.cursor(MySQLdb.cursors.DictCursor)
    #         cur.execute(
    #             """SELECT `value`
    #                     FROM `Logs`
    #                     WHERE `method` = 'Mean Accuracy'
    #                     AND username= %s
    #                     ORDER BY `id`
    #                     DESC LIMIT 1
    #                     """,
    #             (self.hashed_username,),
    #         )
    #
    #         last_mean = 0
    #         for row in cur.fetchall():
    #             last_mean = row["value"]
    #
    #         # log scores
    #         functions.log_data(
    #             conn,
    #             "Classifier",
    #             "Model",
    #             "Mean Accuracy",
    #             str(scores.mean()),
    #             self.hashed_username,
    #         )
    #         functions.log_data(
    #             conn,
    #             "Classifier",
    #             "Model",
    #             "Std Accuracy",
    #             str(scores.std()),
    #             self.hashed_username,
    #         )
    #         cur.close()
    #
    #         if last_mean == 0 or float(last_mean - 0.1) < float(scores.mean()):
    #             return True
    #     return True

    def _get_training_data(self):
        training_input, training_output, weight = [], [], []
        results = Feature.objects.filter(
            Q(team__username=self.team_username)
            | Q(team__username=Feature.INIT_team_username)
        )

        num_new = 0
        for row in results:
            features = functions.decompress_string(str.encode(row.features))
            training_input.append(ast.literal_eval(features))
            training_output.append(int(row.member))

            if row.is_manual:
                weight.append(1)
            else:
                weight.append(0.1)  # 1/10th as reliable if data acquired from model

            if not row.has_processed:
                num_new = num_new + 1

        if training_input == [] or num_new < config.MIN_CLASSIFIER_TRAINING_IMAGES:
            return None, None, None
        return (
            np.array(training_input)[:, 0],
            np.array(training_output),
            np.array(weight),
        )

    def has_trained_model(self) -> bool:
        return bool(self.clf)

    @classmethod
    def get_model_path(cls, hashed_username, expected_path=False):
        """
        Returns the team models path if there is a model there
        :param hashed_username:
        :param expected_path: returns the path of where the teams model should be stored even if there isn't a model already
        :return:
        """
        path = config.CLIENT_MODEL_DIR + hashed_username + ".model"
        if os.path.isfile(path):
            return path
        return path if expected_path else None

    @classmethod
    def exists(cls, hashed_username):
        return bool(cls.get_model_path(hashed_username))

    @classmethod
    def delete(cls, hashed_username):
        model_path = cls.get_model_path(hashed_username)
        if model_path:
            return os.remove(model_path)
        return False