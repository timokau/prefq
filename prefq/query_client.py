"""Client for sending videos to Query Server and receiving feedback"""

import base64
import json
import os
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class QueryClient:
    """Client for sending videos to Query Server and receiving feedback"""

    def __init__(self, query_server_url, sshkey, server_pw):
        if sshkey is not None:
            # read ssh key
            with open(sshkey, "rb") as key_file:
                sshkey = serialization.load_ssh_public_key(
                    key_file.read(),
                )

        self.server_pw = server_pw
        self.sshkey = sshkey
        self.query_server_url = query_server_url

    # pylint: disable=R0914
    def send_video_pair(self, query_id, left_filename, right_filename, video_dir):
        """POST-Request: Send videos to Query Server"""

        def encrypt(message):
            encrypted_message = self.sshkey.encrypt(
                message.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            encrypted_message = base64.b64encode(encrypted_message).decode("utf8")
            return encrypted_message

        left_video_file_path = os.path.join(video_dir, left_filename)
        right_video_file_path = os.path.join(video_dir, right_filename)

        with open(left_video_file_path, "rb") as left_video_file, open(
            right_video_file_path, "rb"
        ) as right_video_file:
            # Read the file data into memory
            left_video_data = left_video_file.read()
            right_video_data = right_video_file.read()

        if self.sshkey is not None:
            password = encrypt(self.server_pw)
        else:
            password = None

        payload = {
            "left_video": (
                left_filename,
                left_video_data,
                "application/octet-stream",
            ),
            "right_video": (
                right_filename,
                right_video_data,
                "application/octet-stream",
            ),
            "query_id": (
                json.dumps(query_id),
                "application/json",
            ),
            "password": (
                json.dumps(password),
                "application/json",
            ),
        }

        try:
            response = requests.post(
                self.query_server_url + "videos", files=payload, timeout=10
            )
            if 200 <= response.status_code < 400:
                print(f"Query Client: Payload transferred   Query ID: {query_id}")

        except requests.exceptions.RequestException as exception:
            print("Query Client: Error: send_videos()")
            print(f"    Exception: {exception}\n")

    def request_feedback(self):
        """
        Retrieve Feedback Data from Server

          - Enter Blocking State until feedback is fully evaluated
          - Then return feedback data
        """

        while True:
            time.sleep(5)
            try:
                response = requests.get(self.query_server_url + "feedback", timeout=5)
                response.raise_for_status()
                feedback_data = response.json()
                if feedback_data == {}:
                    print("Query Client: Waiting for feedback...")
                    continue
                print("Query Client: Feedback received\n")
                break

            except requests.exceptions.RequestException as exception:
                print("Query Client: Error: send_videos()")
                print(f"    Exception: {exception}\n")
                feedback_data = exception
                break
        return feedback_data
