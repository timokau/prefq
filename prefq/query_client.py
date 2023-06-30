"""Query Client: A webserver for receiving RL-Feedback & sending videos"""

import os
import json
import requests
from flask import Flask, jsonify, request

query_client = Flask(__name__)

HOST_URL = "http://127.0.0.1:5000/"
VIDEOS_SENT = 0
VIDEO_BUFFERSIZE = 10

video_filepaths = [f"{str(i).zfill(2)}.mp4" for i in range(1, VIDEO_BUFFERSIZE + 1)]
feedback_booleans = []

@query_client.route("/request_videos", methods=["GET"])
def send_query_to_server():
    """Send videos to server"""

    global VIDEOS_SENT

    print("\nClient: /request_videos triggered")

    # Prepare POST-Request Content
    payload = {
        # Send filepaths as .json
        'left_filepath': (json.dumps(video_filepaths[VIDEOS_SENT]), 'application/json'),
        'right_filepath': (json.dumps(video_filepaths[VIDEOS_SENT+1]), 'application/json'),
        # Open videos in binary read mode
        'left_video': (video_filepaths[VIDEOS_SENT], open(os.path.join(query_client.root_path, "static/lunarlander_random/", video_filepaths[VIDEOS_SENT]), "rb"), 'application/octet-stream'),
        'right_video': (video_filepaths[VIDEOS_SENT+1], open(os.path.join(query_client.root_path, "static/lunarlander_random/", video_filepaths[VIDEOS_SENT+1]), "rb"), 'application/octet-stream')
    }

    # Prepare response for GET-Request in load_web_interface()
    filepaths = {
        'left_filepath': video_filepaths[VIDEOS_SENT], 
        'right_filepath': video_filepaths[VIDEOS_SENT+1]
    }

    # Send POST-Request to server
    response = requests.post(HOST_URL + "receive_videos", files=payload)
    VIDEOS_SENT += 2
    print("\nClient: Successfully transferred payload")

    if response.status_code >= 200 & response.status_code < 400:
        print("Client: Successfully terminated /request_videos\n")
        return jsonify(filepaths)
    
    print("Client: Error at /request_videos    Status code:")
    print(response.status_code)
    return "Failed to send query"

@query_client.route("/receive_feedback", methods=["POST"])
def receive_feedback_boolean():
    """Receives client feedback from Server"""

    data = request.json  # Access the JSON data from the request
    is_left_preferred = data["is_left_preferred"]  # Extract specific data from JSON
    print("Client: Received Preference Boolean from Server: " + str(is_left_preferred))

    feedback_booleans.append(is_left_preferred)
    print("Client: Successfully Received Preference Boolean from Server")
    print("Client: Boolean Array:", end= ' ')
    for boolean in feedback_booleans:
        print(boolean, end=' ')

    return "Client: Success: /receive_feedback"


if __name__ == "__main__":
    query_client.run(host="127.0.0.1", port=5001, debug=True)
