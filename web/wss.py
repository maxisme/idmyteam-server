import json
from collections import defaultdict

import tornado.websocket

import logging
from settings import functions, config, db
from ML.classifier import Classifier
import upload, authed


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    hashed_username = None
    local_ip = None

    def check_origin(self, origin):
        if origin == "wss://idmy.team":
            return True

    def open(self):
        try:
            headers = self.request.headers
            credentials = headers["credentials"]
            local_ip = headers["local-ip"]
            username = headers["username"]
        except KeyError as e:
            return self.close(1003, "Invalid headers: {}".format(e))

        if not functions.is_valid_ip(local_ip):
            return self.close(1003, "Invalid IP")

        self.hashed_username = functions.hash(username)
        if self.hashed_username not in authed.clients:
            conn = db.pool.raw_connection()
            if functions.Team.valid_credentials(
                conn, self.hashed_username, credentials, config.SECRETS["crypto"]
            ):
                # add classifier to worker
                upload.high_q.enqueue_call(
                    func=".",
                    kwargs={"type": "add", "hashed_username": self.hashed_username},
                )

                if Classifier.exists(self.hashed_username):
                    self.write_message(json.dumps({"type": "connected"}))
                else:
                    self.write_message(json.dumps({"type": "no_model"}))

                self.local_ip = local_ip
                authed.clients[self.hashed_username] = self
                print("%s connected to socket", self.hashed_username)

                # send all pending messages to client
                if self.hashed_username in pending_messages:
                    for message in pending_messages[self.hashed_username]:
                        self.write_message(message)
            else:
                self.write_message(json.dumps({"type": "invalid_credentials"}))
                conn.close()
                return self.close(1003, "Invalid credentials")
            conn.close()
        else:
            return self.close(1003, "Already connected")

    def on_close(self):
        if self.hashed_username and self.hashed_username in authed.clients:
            authed.clients.pop(self.hashed_username)

            # remove classifier from worker
            upload.high_q.enqueue_call(
                func=".",
                kwargs={"type": "remove", "hashed_username": self.hashed_username},
            )
            print("%s disconnected from socket", self.hashed_username)

    def on_message(self, message):
        """
        :param message: integer value representing the pending message id
        :return:
        """
        try:
            message = int(message)
        except:
            self.close(1004, "Invalid Message")

        # incoming messages contain an id to confirm received
        if self.hashed_username in pending_messages:
            for m in pending_messages[self.hashed_username]:
                if json.loads(m)["id"] == message:
                    return pending_messages[self.hashed_username].remove(m)
        self.close(1004, "Invalid Message")

    def close(self, code=None, reason=None):
        logging.error(
            "Close socket reason:%s - %s : %s",
            reason,
            self.hashed_username,
            self.request.headers.get("X-Real-Ip"),
        )
        self.write_message("Invalid request")
        super(WebSocketHandler, self).close(code)


class LocalWebSocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        if origin == config.LOCAL_SOCKET_URL.replace("ws", "http"):
            return True

    def on_message(self, message):
        """
        Only comes from classifier with classification response
        :param message:
        :return:
        """
        send_local_message(message)


pending_messages = defaultdict(list)  # TODO monitor size of this variable


def send_local_message(message):
    try:
        message = json.loads(message)
    except:
        logging.error("Invalid local message sent %s", message)
        return False

    hashed_username = message.pop("hashed_username")
    if hashed_username in authed.clients:
        arr = pending_messages[hashed_username]
        arr.append(json.dumps({"id": len(arr), "message": message}))

        # client connected
        ws = authed.clients[hashed_username]  # type: WebSocketHandler
        ws.write_message(pending_messages[hashed_username][-1])
    return True
