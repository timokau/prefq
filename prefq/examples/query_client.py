"""Query Client: A webserver for receiving RL-Feedback & sending videos"""

import json
import os
from pprint import pprint

import requests

QUERY_SERVER_URL = "http://127.0.0.1:5000/"
VIDEO_BUFFERSIZE = 10


root_path = os.path.dirname(os.path.abspath(__file__))
video_filenames = [f"{str(i).zfill(2)}.mp4" for i in range(1, VIDEO_BUFFERSIZE + 1)]
feedback_array = []


def send_videos():
    """POST-Request: Send videos to Query Server"""

    videos_sent = 0

    print("\n\nClient: Starting send_videos() [...]\n")

    for i in range(1, VIDEO_BUFFERSIZE // 2 + 1):
        # Prepare POST-Request Content
        left_video_file_path = os.path.join(
            root_path, "videos/lunarlander_random/", video_filenames[videos_sent]
        )
        right_video_file_path = os.path.join(
            root_path, "videos/lunarlander_random/", video_filenames[videos_sent + 1]
        )

        with open(left_video_file_path, "rb") as left_video_file, open(
            right_video_file_path, "rb"
        ) as right_video_file:
            # Read the file data into memory
            left_video_data = left_video_file.read()
            right_video_data = right_video_file.read()

        payload = {
            # Send filepaths as .json
            "left_filepath": (
                json.dumps(video_filenames[videos_sent]),
                "application/json",
            ),
            "right_filepath": (
                json.dumps(video_filenames[videos_sent + 1]),
                "application/json",
            ),
            # Use the file data directly
            "left_video": (
                video_filenames[videos_sent],
                left_video_data,
                "application/octet-stream",
            ),
            "right_video": (
                video_filenames[videos_sent + 1],
                right_video_data,
                "application/octet-stream",
            ),
        }

        videos_sent += 2

        print("Client: " + f"{i:02}" + " Sending POST-Request to server ")
        response = requests.post(
            QUERY_SERVER_URL + "receive_videos", files=payload, timeout=10
        )
        print("Client: " + f"{i:02}" + " Payload Transferred")

        if response.status_code >= 200 & response.status_code < 400:
            print("Client: " + f"{i:02}" + " Video Pair Sent")
        else:
            print("Client: Error: send_videos()    Status code:")
            print(response.status_code)
        print("")

    print("Client: [...] Terminating send_videos()\n")


def request_feedback():
    """GET-Request: Receive client feedback from Server"""

    global feedback_array
    print("\n\nClient: Starting request_feedback() [...]")

    response = requests.get(QUERY_SERVER_URL + "request_feedback", timeout=10)

    if response.status_code == 200:
        print("Client: Receiving feedback data...")
        feedback_data = response.json()
        print("Client: Storing feedback data...")
        feedback_array = feedback_data["feedback_array"]
        print("Client: ...feedback data stored")

        print("Client: Feedback Data:", feedback_array)
        print("Client: [...] Terminating request_feedback()")
        return "Client: [...] Terminating request_feedback()"

    print("Client: Request failed with status code: ", response.status_code)
    return "Client: Reqeuest in request_feedback() failed"


if __name__ == "__main__":
    send_videos()
    request_feedback()
