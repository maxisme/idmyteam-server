import json
import os
import sys
import time

import MySQLdb
import ast
import numpy as np
import logging

from sklearn.model_selection import ShuffleSplit, cross_val_score
from sklearn.externals import joblib
from sklearn.svm import SVC

from creme.linear_model import LogisticRegression
from creme.multiclass import OneVsRestClassifier
from creme.preprocessing import StandardScaler
from creme.compose import Pipeline
from creme.metrics import Accuracy
from creme import stream

from settings import functions, config, db


class Classifier(object):
    def __init__(self, hashed_team_username):
        """
        :type socket: server.authed.WebSocketHandler
        """
        self.hashed_username = hashed_team_username
        self.clf = self._load_model()

    def predict(self, features, file_name, face_coords, store_features):
        if self.clf:
            t = time.time()
            conn = db.pool.connect()

            # predict member id based on face_coords
            member_id = 0
            max_prob = config.MIN_PROB
            classes = self.clf.classes_
            probabilities = self.clf.predict_proba(np.array(features))
            for i, prob in enumerate(probabilities[0]):
                logging.info(
                    "User: %s\nClass: %s\nProb: %s",
                    self.hashed_username,
                    str(classes[i]),
                    str(prob),
                )
                if prob >= max_prob:
                    member_id = classes[i]
                    max_prob = prob

            # send member classification back to user
            socket = functions.create_local_socket(config.LOCAL_SOCKET_URL)
            functions.send_classification(
                json.dumps(face_coords),
                member_id,
                max_prob,
                file_name,
                self.hashed_username,
                socket,
            )

            # log how long it took to predict class
            functions.log_data(
                conn,
                "Classifier",
                "Model",
                "Predict",
                str(time.time() - t),
                self.hashed_username,
            )

            if member_id > 0:
                functions.Team.increase_num_classifications(conn, self.hashed_username)
                if store_features:
                    # store features in db for further training of model
                    functions.store_feature(
                        conn,
                        self.hashed_username,
                        member_id,
                        features,
                        manual=False,
                        score=max_prob,
                    )
        else:
            logging.error("Missing model for: %s", self.hashed_username)

    def train(self, conn):
        t = time.time()
        socket = functions.create_local_socket(config.LOCAL_SOCKET_URL)

        # mark team as currently training
        functions.toggle_team_training(conn, self.hashed_username)

        logging.info("Creating new model for %s", self.hashed_username)

        # create a new model using ALL the team training data
        training_input, training_output, sample_weight, results = self._get_training_data(
            conn
        )

        if training_input is not None:
            # make sure there are more than 1 classes to train model
            if len(np.unique(training_output)) <= 1:
                return functions.send_json_socket(
                    socket,
                    self.hashed_username,
                    {
                        "type": "error",
                        "mess": "You must train with more than one team member!",
                    },
                )
            else:
                clf = Pipeline([
                    ("scale", StandardScaler()),
                    ("learn", OneVsRestClassifier(binary_classifier=LogisticRegression()))
                ])
        else:
            return functions.send_json_socket(
                socket,
                self.hashed_username,
                {
                    "type": "error",
                    "mess": "You must train with at least %d members!"
                    % (config.MIN_CLASSIFIER_TRAINING_IMAGES,),
                },
            )

        for i, X in enumerate(training_input):
            clf.fit_one(X, training_output[i])

        functions.log_data(
            conn,
            "Classifier",
            "Model",
            "Train",
            str(time.time() - t),
            self.hashed_username,
        )

        new_output = [o for o in training_output if o > 0]
        unique_outputs = np.bincount(new_output)
        num_outputs = np.nonzero(unique_outputs)[0]
        cnt_uni = list(zip(num_outputs, unique_outputs[num_outputs]))

        print(
            "fitted %d features from %d classes"
            % (len(training_input), len(set(training_output)))
        )

        # send message to client with who has been trained
        functions.send_json_socket(
            socket,
            self.hashed_username,
            {
                "type": "trained",
                "trained_members": json.dumps(cnt_uni, default=functions.json_helper),
            },
        )

        if not self.exists(self.hashed_username) or self._should_update_model(
            clf, training_input, training_output, conn
        ):
            model_path = self.get_model_path(self.hashed_username, True)
            joblib.dump(clf, model_path)  # save model
            self.clf = clf  # reload the new model
        else:
            print("no improvement in model")

        # mark all features as not new
        cur = conn.cursor()
        cur.execute(
            "UPDATE `Features` SET `new` = '0' WHERE username = %s",
            (self.hashed_username,),
        )
        conn.commit()
        cur.close()

        # mark team as finished training
        functions.toggle_team_training(conn, self.hashed_username, training=False)
        conn.close()

    def _load_model(self):
        model_path = self.get_model_path(self.hashed_username)
        if model_path:
            t = time.time()
            conn = db.pool.connect()
            model = joblib.load(model_path)

            # log how long it took to load model
            functions.log_data(
                conn,
                "Classifier",
                "Model",
                "Load",
                str(time.time() - t),
                self.hashed_username,
            )
            functions.purge_log(
                conn, "Classifier", "Model", "Predict", self.hashed_username
            )
            return model
        return None

    def _should_update_model(self, clf, x, y, conn):
        cv = ShuffleSplit(n_splits=30)
        scores = cross_val_score(clf, x, y, cv=cv)
        print(str(scores.mean()) + " -- +/-" + str(scores.std()))

        mb_size = sys.getsizeof(clf) * 1e6
        logging.info("%s %sMB", mb_size, self.hashed_username)

        if mb_size < config.MAX_CLASSIFIER_SIZE_MB:
            # check if this mean score is better than the last within margin
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            cur.execute(
                """SELECT `value` 
                        FROM `Logs` 
                        WHERE `method` = 'Mean Accuracy' 
                        AND username= %s 
                        ORDER BY `id` 
                        DESC LIMIT 1
                        """,
                (self.hashed_username,),
            )

            last_mean = 0
            for row in cur.fetchall():
                last_mean = row["value"]

            # log scores
            functions.log_data(
                conn,
                "Classifier",
                "Model",
                "Mean Accuracy",
                str(scores.mean()),
                self.hashed_username,
            )
            functions.log_data(
                conn,
                "Classifier",
                "Model",
                "Std Accuracy",
                str(scores.std()),
                self.hashed_username,
            )
            cur.close()

            if last_mean == 0 or float(last_mean - 0.1) < float(scores.mean()):
                return True
        return True

    def _get_training_data(self, conn):
        """
        :param conn: database connection.
        :return: the training input, output and sample weights for a team.
        """
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(
            """SELECT `features`, `class`, `type`, `new` 
                    FROM `Features`
                    WHERE username = %s
                    OR username = 'init'""",
            (self.hashed_username,),
        )

        training_input, training_output, weight = [], [], []
        results = cur.fetchall()

        num_new = 0
        for row in results:
            features = functions.decompress_string(str.encode(row["features"]))
            training_input.append(ast.literal_eval(features))
            training_output.append(int(row["class"]))

            if row["type"] == "MANUAL":
                weight.append(1)
            else:
                weight.append(0.1)  # 1/10th as reliable if data acquired from model

            if row["new"] == 1:
                num_new = num_new + 1
        cur.close()

        if training_input == [] or num_new < config.MIN_CLASSIFIER_TRAINING_IMAGES:
            return None, None, None
        return (
            np.array(training_input)[:, 0],
            np.array(training_output),
            np.array(weight),
        )

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
