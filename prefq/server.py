"""A webserver that asks the user preference queries."""

import os
from urllib.parse import unquote

import flask
import requests
from flask import Flask, jsonify, request

QUERY_CLIENT_URL = "http://127.0.0.1:5001/"

app = Flask(__name__)
app.config["VIDEO_FOLDER"] = "videos"


def load_web_interface(video_filename_left=None, video_filename_right=None):
    """Renders updated .html interface"""

    if video_filename_left is not None and video_filename_right is not None:
        print("\nServer: Reached recursive call of load_web_interface()")

        video_filepath_left = "videos/" + video_filename_left
        video_filepath_right = "videos/" + video_filename_right

        print("Server: Rendering " + os.path.join(app.root_path, video_filepath_left))
        print("Server: Rendering " + os.path.join(app.root_path, video_filepath_right))

        return flask.render_template(
            "web_interface.html",
            video_filepath_left=video_filepath_left,
            video_filepath_right=video_filepath_right,
        )

    # Request new videos from queryClient & receive filepaths
    response = requests.get(QUERY_CLIENT_URL + "request_videos")
    filepaths_json = response.json()

    print("Server: Get Request Successful")

    return flask.render_template(
        "web_interface.html",
        video_filepath_left=filepaths_json["left_filepath"],
        video_filepath_right=filepaths_json["right_filepath"],
    )


@app.route("/videos/<path:filename>")
def serve_video(filename):
    """Make videos accessible for feedback client (web_interface.html)"""

    video_folder = os.path.join(os.getcwd(), app.config["VIDEO_FOLDER"])
    return flask.send_from_directory(video_folder, filename)


@app.route("/", methods=["GET"])
def index():
    """Define GET-Request behavior"""

    response_data = load_web_interface()  # Load new Interface
    response = app.make_response(response_data)

    return response  # Update Client Interface


@app.route("/", methods=["POST"])
def receive_data():
    """Receive evaluations from client"""

    data = flask.request.json  # Represents incoming client http request in json format
    is_left_preferred = data["is_left_preferred"]  # Extract JSON data
    print("Left Preferred: ", is_left_preferred)

    # check for defective msg transfer
    if is_left_preferred is None:
        return jsonify({"success": False})

    return jsonify({"success": True})


@app.route("/receive_videos", methods=["POST"])
def receive_videos():
    """Receive requested videos"""

    print("\nServer: /receive_videos triggered")

    left_video = request.files.get("left_video")
    right_video = request.files.get("right_video")
    print("Server: Successfully received videos")

    # unquote() decodes url-encoded characters - .filename needs to be called to access json text data - strip('"') removes decoded quotation marks
    left_filename = unquote(request.files.get("left_filepath").filename).strip('"')
    right_filename = unquote(request.files.get("right_filepath").filename).strip('"')
    print("Server: Filepaths received")

    left_video.save(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    right_video.save(os.path.join(app.config["VIDEO_FOLDER"], right_filename))
    print("Server: Successfully stored videos in local folder")
    print("Server: Successfully terminated /receive_videos")

    return "Server: Success in /receive_videos"


@app.route("/stop")
def delete_session_url():
    """Define behavior when client closes browser window"""

    response = flask.make_response()

    response.set_cookie("session", "", expires=0)  # Delete cookies
    flask.session.clear()  # Delete session

    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
