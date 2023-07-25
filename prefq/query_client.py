"""Query Client: A webserver for receiving RL-Feedback & sending videos"""

import json
import os

import requests

HOST_URL = "http://127.0.0.1:5000/"
VIDEOS_SENT = 0
VIDEO_BUFFERSIZE = 10


root_path = os.path.dirname(os.path.abspath(__file__))
video_filepaths = [f"{str(i).zfill(2)}.mp4" for i in range(1, VIDEO_BUFFERSIZE + 1)]
feedback_array = []


def send_videos():
    """POST-Request: Send videos to server"""

    global VIDEOS_SENT

    print("\n\nClient: Started send_videos()")

    for i in range(1, VIDEO_BUFFERSIZE // 2 + 1):
        # Prepare POST-Request Content
        payload = {
            # Send filepaths as .json
            "left_filepath": (
                json.dumps(video_filepaths[VIDEOS_SENT]),
                "application/json",
            ),
            "right_filepath": (
                json.dumps(video_filepaths[VIDEOS_SENT + 1]),
                "application/json",
            ),
            # Open videos in binary read mode
            "left_video": (
                video_filepaths[VIDEOS_SENT],
                open(
                    os.path.join(
                        root_path,
                        "static/lunarlander_random/",
                        video_filepaths[VIDEOS_SENT],
                    ),
                    "rb",
                ),
                "application/octet-stream",
            ),
            "right_video": (
                video_filepaths[VIDEOS_SENT + 1],
                open(
                    os.path.join(
                        root_path,
                        "static/lunarlander_random/",
                        video_filepaths[VIDEOS_SENT + 1],
                    ),
                    "rb",
                ),
                "application/octet-stream",
            ),
        }

        # Prepare response for GET-Request in load_web_interface()
        filepaths = {
            "left_filepath": video_filepaths[VIDEOS_SENT],
            "right_filepath": video_filepaths[VIDEOS_SENT + 1],
        }

        VIDEOS_SENT += 2

        # Send POST-Request to server
        print("Client: " + f"{i:02}" + " Sending Video POST-Request")
        response = requests.post(HOST_URL + "receive_videos", files=payload)
        print("Client: " + f"{i:02}" + " Payload Transferred")

        if response.status_code >= 200 & response.status_code < 400:
            print("Client: " + f"{i:02}" + " Video Pair Sent\n")
        else:
            print("Client: Error: send_videos()    Status code:")
            print(response.status_code)
            return "Failed to send query"

        print("Client: Terminated send_videos()")


def request_feedback():
    """GET-Request: Receive client feedback from Server"""

    global feedback_array
    print("\n\nClient: Started request_feedback()")

    response = requests.get(HOST_URL + "request_feedback")

    if response.status_code == 200:
        print("Client: Receiving feedback data...")
        feedback_data = response.json()
        print("Client: Storing feedback data...")
        feedback_array = feedback_data["feedback_array"]

        print("Client: Feedback Data:", feedback_array)
        print("Client: Terminated request_feedback()")
        return "Client: Terminated request_feedback()"

    print("Client: Request failed with status code: ", response.status_code)


if __name__ == "__main__":
    send_videos()
    request_feedback()
