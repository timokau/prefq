"""A webserver that asks the user preference queries."""

import os
from urllib.parse import unquote

import flask
from flask import Flask, jsonify, request

app = Flask(__name__)

app.config["VIDEO_FOLDER"] = "videos"

# Global counter variable needed for keeping track of evaluated videos
# In future alternative solution shall be implemented (eg session variable)
# Pylint does not like globals and thinks every global variabl should be a constant
# (all uppercase). Therefore we need to ignore invalid-name here
# pylint: disable=invalid-name
video_evals = 0
feedback_array = []
filenames_array = []


@app.before_first_request
def before_first_request():
    """Define starting routine"""

    # Create video folder (if necessary)
    if not os.path.exists(app.config["VIDEO_FOLDER"]):
        os.mkdir(app.config["VIDEO_FOLDER"])


@app.route("/", methods=["GET"])
def index():
    """Define GET-Request behavior"""

    response_data = load_web_interface()
    response = app.make_response(response_data)

    return response  # Update Client Interface


def load_web_interface():
    """Send HTML interface to Feedback Client"""

    # should be replaced by flask session object
    # pylint: disable=global-statement
    global video_evals

    available_videos = len(filenames_array) - video_evals
    is_video_available = available_videos > 0 and len(filenames_array) != 0

    print("\n\nServer: Starting load_web_interface() [...] ")
    print("Server: Evaluated Videos: " + str(video_evals))
    print("Server: Available Videos: " + str(available_videos))

    if is_video_available:
        video_evals += 2

        print("Server: [...] Terminating load_web_interface()")
        return flask.render_template(
            "web_interface.html",
            video_filename_left=filenames_array[video_evals - 2],
            video_filename_right=filenames_array[video_evals - 1],
        )

    print("Server: [...] Rendering Easteregg")
    return flask.render_template("easteregg.html")


@app.route("/videos", methods=["POST"])
def receive_videos():
    """Receive new queries from a Query Client."""

    print("\n\nServer: Starting receive_videos() [...]")

    # unquote() decodes url-encoded characters
    # .filename needs to be called to access json text data
    # strip('"') removes decoded quotation marks
    print("Server: Receiving videos...")
    left_filename = unquote(request.files.get("left_filepath").filename).strip('"')
    right_filename = unquote(request.files.get("right_filepath").filename).strip('"')
    left_video = request.files.get("left_video")
    right_video = request.files.get("right_video")
    print("    (Left): " + left_filename + "\n   (Right): " + right_filename)
    print("Server: ...Videos received")

    left_video.save(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    right_video.save(os.path.join(app.config["VIDEO_FOLDER"], right_filename))
    filenames_array.append(left_filename)
    filenames_array.append(right_filename)
    # Add empty feedback value for newly received, unevaluated data
    feedback_array.append(None)

    print("Server: ...Videos stored locally")

    print("Server: [...] Terminating receive_videos()")
    return "Server: [...] Terminating receive_videos()"


@app.route("/videos/<path:filename>", methods=["GET"])
def serve_video(filename):
    """Make videos accessible for feedback client (web_interface.html)"""

    video_folder = os.path.join(os.getcwd(), app.config["VIDEO_FOLDER"])
    return flask.send_from_directory(video_folder, filename)


@app.route("/feedback", methods=["POST"])
def receive_feedback():
    """Receive and store feedback from feedback client"""

    print("\n\nServer: Starting receive_feedback() [...]")

    print("Server: Receiving feedback")
    data = flask.request.json  # Represents incoming client http request in json format

    # Extract received JSON data
    is_left_preferred = data["is_left_preferred"]
    video_filename_left = data["video_filename_left"]
    video_index_left = int(video_filename_left.split(".")[0]) - 1
    batch_index = video_index_left // 2

    # Check for defective msg transfer
    if is_left_preferred is None:
        return jsonify({"success": False})

    # Save feedback at corresponding index
    feedback_array[batch_index] = is_left_preferred
    print("Server: Feedback stored")
    print("        Feedback Values: " + str(feedback_array))

    print("Server: [...] Terminating receive_feedback()")

    return jsonify({"success": True})


@app.route("/feedback", methods=["GET"])
def send_feedback():
    """Sends feedback to Query Client"""

    print("\n\nServer: Starting send_feedback() [...]")

    feedback_copy = feedback_array[:]
    feedback_array.clear()
    feedback_json = {"feedback_array": feedback_copy}

    print("Server: [...] Terminating send_feedback()")

    return jsonify(feedback_json)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
