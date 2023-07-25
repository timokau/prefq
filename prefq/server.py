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


@app.before_first_request
def before_first_request():
    """Define starting routine"""

    # Create video folder (if necessary)
    if not os.path.exists(app.config["VIDEO_FOLDER"]):
        os.mkdir(app.config["VIDEO_FOLDER"])

app = Flask(__name__)
app.config["VIDEO_FOLDER"] = "videos"

@app.route("/", methods=["GET"])
def index():
    """Define GET-Request behavior"""

    response_data = load_web_interface()  # Load new Interface
    response = app.make_response(response_data)

    return response  # Update Client Interface


def load_web_interface():
    """Render .html interface for Feedback Client"""

    # should be replaced by flask session object
    # pylint: disable=global-statement
    global video_evals

    available_videos = len(video_filenames) - video_evals
    is_video_available = available_videos > 0 and len(video_filenames) != 0

    print("\n\nServer: Starting load_web_interface() [...] ")
    print("Server: Video Evals: " + str(video_evals))
    print("Server: Available Videos: " + str(available_videos))

    if is_video_available:
        video_evals += 2

        print("Server: [...] Terminating load_web_interface()")
        return flask.render_template(
            "web_interface.html",
            video_filepath_left=video_filenames[video_evals - 2],
            video_filepath_right=video_filenames[video_evals - 1],
        )

    print("Server: Rendering Easteregg")
    return flask.render_template("easteregg.html")


@app.route("/receive_videos", methods=["POST"])
def receive_videos():
    """Receive requested videos"""

    print("\n\nServer: Starting receive_videos() [...] ")

    # unquote() decodes url-encoded characters
    # .filename needs to be called to access json text data
    # strip('"') removes decoded quotation marks
    left_filename = unquote(request.files.get("left_filepath").filename).strip('"')
    right_filename = unquote(request.files.get("right_filepath").filename).strip('"')
    print("filenames received")
    left_video = request.files.get("left_video")
    right_video = request.files.get("right_video")
    print(
        "Server: Videos Received: "
        + "\n    (Left): "
        + left_filename
        + "\n   (Right): "
        + right_filename
    )

    print("Server: Storing videos locally... ")
    left_video.save(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    right_video.save(os.path.join(app.config["VIDEO_FOLDER"], right_filename))
    video_filenames.append(left_filename)
    video_filenames.append(right_filename)
    print("Server: ...Videos stored locally")

    print("Server: [...] Terminating receive_videos()")
    return "Server: [...] Terminating receive_videos()"


@app.route("/feedback", methods=["POST"])
def receive_feedback():
    """Receive and store feedback from feedback client"""

    # should be replaced by flask session object
    # pylint: disable=global-statement
    global feedback_array

    print("\n\nServer: Starting receive_feedback() [...]")
    data = flask.request.json  # Represents incoming client http request in json format
    is_left_preferred = data["is_left_preferred"]  # Extract JSON data

    # check for defective msg transfer
    if is_left_preferred is None:
        return jsonify({"success": False})

    feedback_array.append(is_left_preferred)
    print(feedback_array)
    print("Server: [...] Terminating receive_feedback()")

    return jsonify({"success": True})


@app.route("/feedback", methods=["GET"])
def send_feedback():
    """Sends feedback to Query Client"""

    print("\n\nServer: Starting send_feedback() [...]")
    feedback_json = {"feedback_array": feedback_array}

    print("Server: [...] Terminating send_feedback()")
    return jsonify(feedback_json)


@app.route("/videos/<path:filename>")
def serve_video(filename):
    """Make videos accessible for feedback client (web_interface.html)"""

    video_folder = os.path.join(os.getcwd(), app.config["VIDEO_FOLDER"])
    return flask.send_from_directory(video_folder, filename)


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
