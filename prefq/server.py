"""A webserver that asks the user preference queries."""

import os
from urllib.parse import unquote

import flask
from flask import Flask, jsonify, request

QUERY_CLIENT_URL = "http://127.0.0.1:5001/"

app = Flask(__name__)
app.config["VIDEO_FOLDER"] = "videos"

feedback_array = [True, False, False, True, True]
video_filenames = []
video_evals = 0


def load_web_interface():
    """Render .html interface for Feedback Client"""

    global video_evals

    available_videos = len(video_filenames) - video_evals

    print("\n\nServer: starting load_web_interface()...")
    print("Server: Video Evals: " + str(video_evals))
    print("Server: Availible Videos: " + str(available_videos))

    if video_evals < len(video_filenames) & len(video_filenames) > 0:
        # render interface, if unevaluated videos exist

        video_evals += 2

        print("Server: ...terminated load_web_interface()")
        return flask.render_template(
            "web_interface.html",
            video_filepath_left=video_filenames[video_evals - 2],
            video_filepath_right=video_filenames[video_evals - 1],
        )

    print("Server: Rendering Easteregg")
    return flask.render_template("easteregg.html")


@app.route("/", methods=["GET"])
def index():
    """Define GET-Request behavior"""

    response_data = load_web_interface()  # Load new Interface
    response = app.make_response(response_data)

    return response  # Update Client Interface


@app.route("/receive_feedback", methods=["POST"])
def receive_feedback():
    """Receive and store feedback from feedback client"""

    global feedback_array

    print("\n\nServer: Starting receive_feedback()")
    data = flask.request.json  # Represents incoming client http request in json format
    is_left_preferred = data["is_left_preferred"]  # Extract JSON data

    # check for defective msg transfer
    if is_left_preferred is None:
        return jsonify({"success": False})

    feedback_array.append(is_left_preferred)
    print(feedback_array)
    print("Server: Terminated receive_feedback()")

    return jsonify({"success": True})


@app.route("/request_feedback", methods=["GET"])
def send_feedback():
    """Sends feedback to Query Client"""

    print("\n\nServer: Starting send_feedback()")
    feedback_json = {"feedback_array": feedback_array}

    print("Server: Terminated send_feedback()")
    return jsonify(feedback_json)


@app.route("/receive_videos", methods=["POST"])
def receive_videos():
    """Receive requested videos"""

    print("\n\nServer: Started receive_videos() ")

    # unquote() decodes url-encoded characters
    # .filename needs to be called to access json text data
    # strip('"') removes decoded quotation marks
    left_filename = unquote(request.files.get("left_filepath").filename).strip('"')
    right_filename = unquote(request.files.get("right_filepath").filename).strip('"')
    left_video = request.files.get("left_video")
    right_video = request.files.get("right_video")
    print(
        "Server: Videos Received: "
        + "\n    (Left): "
        + left_filename
        + "\n   (Right): "
        + right_filename
    )

    print("Server: Storing videos locally...")
    left_video.save(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    right_video.save(os.path.join(app.config["VIDEO_FOLDER"], right_filename))
    video_filenames.append(left_filename)
    video_filenames.append(right_filename)
    print("Server: ...Videos stored locally")

    print("Server: Terminated receive_videos()")
    return "Server: Terminated receive_videos()"


@app.route("/stop")
def delete_session_url():
    """Define behavior when client closes browser window"""

    response = flask.make_response()

    response.set_cookie("session", "", expires=0)  # Delete cookies
    flask.session.clear()  # Delete session

    return response


@app.route("/videos/<path:filename>")
def serve_video(filename):
    """Make videos accessible for feedback client (web_interface.html)"""

    video_folder = os.path.join(os.getcwd(), app.config["VIDEO_FOLDER"])
    return flask.send_from_directory(video_folder, filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
