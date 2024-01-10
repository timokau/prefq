"""Client for sending videos to Query Server and receiving feedback"""

import json
import os
import time

import requests


class QueryClient:
    """Client for sending videos to Query Server and receiving feedback"""

    def __init__(self, query_server_url):
        self.query_server_url = query_server_url

    def send_video_pair(self, query_id, left_filename, right_filename, video_dir):
        """POST-Request: Send videos to Query Server"""

        left_video_file_path = os.path.join(video_dir, left_filename)
        right_video_file_path = os.path.join(video_dir, right_filename)

        with open(left_video_file_path, "rb") as left_video_file, open(
            right_video_file_path, "rb"
        ) as right_video_file:
            # Read the file data into memory
            left_video_data = left_video_file.read()
            right_video_data = right_video_file.read()

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
