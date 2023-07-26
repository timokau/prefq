"""An example of a query client that sends queries to the server and polls the results."""

import json
import os

import requests

AVAILABLE_VIDEOS = 10
QUERY_SERVER_URL = "http://127.0.0.1:5000/"
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
VIDEO_FILENAMES = [f"{str(i).zfill(2)}.mp4" for i in range(1, AVAILABLE_VIDEOS + 1)]


def send_videos():
    """POST-Request: Send videos to Query Server"""

    print("\n\nClient: Starting send_videos() [...]\n")

    videos_sent = 0

    for i in range(1, AVAILABLE_VIDEOS // 2 + 1):
        # Prepare POST-Request Content
        left_video_file_path = os.path.join(
            ROOT_PATH, "videos/lunarlander_random/", VIDEO_FILENAMES[videos_sent]
        )
        right_video_file_path = os.path.join(
            ROOT_PATH, "videos/lunarlander_random/", VIDEO_FILENAMES[videos_sent + 1]
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
                json.dumps(VIDEO_FILENAMES[videos_sent]),
                "application/json",
            ),
            "right_filepath": (
                json.dumps(VIDEO_FILENAMES[videos_sent + 1]),
                "application/json",
            ),
            # Use the file data directly
            "left_video": (
                VIDEO_FILENAMES[videos_sent],
                left_video_data,
                "application/octet-stream",
            ),
            "right_video": (
                VIDEO_FILENAMES[videos_sent + 1],
                right_video_data,
                "application/octet-stream",
            ),
        }

        videos_sent += 2

        print("Client: " + f"{i:02}" + " Sending data to Server")
        response = requests.post(QUERY_SERVER_URL + "videos", files=payload, timeout=10)

        if response.status_code >= 200 & response.status_code < 400:
            print("Client: " + f"{i:02}" + " Payload transferred")
        else:
            print("Client: Error: send_videos()    Status code:")
            print(response.status_code)
        print("")

    print("Client: [...] Terminating send_videos()")


def request_feedback():
    """GET-Request: Receive client feedback from Server"""

    print("\n\nClient: Starting request_feedback() [...]")

    response = requests.get(QUERY_SERVER_URL + "feedback", timeout=10)

    if response.status_code == 200:
        print("Client: Receiving feedback data...")
        feedback_data = response.json()
        print("Client: Storing Feedback Data")
        feedback_array = feedback_data["feedback_array"]
        print("        Feedback Data:", feedback_array)

        print("Client: [...] Terminating request_feedback()\n")
        return "Client: [...] Terminating request_feedback()"

    print("Client: Request failed with status code: ", response.status_code)
    return "Client: Reqeuest in request_feedback() failed"


def main():
    """Send the example queries and poll for feedback."""
    send_videos()
    request_feedback()


if __name__ == "__main__":
    main()
