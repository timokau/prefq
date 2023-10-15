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
n_pending_queries = 0
videos_rendered = 0
videos_evaluated = 0
feedback_data = {}
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
    global videos_rendered

    available_videos = len(filenames_array) - videos_rendered
    is_video_available = available_videos > 0 and len(filenames_array) != 0

    print("\n\nServer: Starting load_web_interface() [...] ")
    print("Server: Evaluated Videos: " + str(videos_rendered))
    print("Server: Available Videos: " + str(available_videos))

    if is_video_available:
        videos_rendered += 2

        print("Server: [...] Terminating load_web_interface()")
        return flask.render_template(
            "web_interface.html",
            video_filename_left=filenames_array[videos_rendered - 2],
            video_filename_right=filenames_array[videos_rendered - 1],
        )

    print("Server: [...] No data available")
    return flask.render_template("no_data_availible.html")


@app.route("/videos", methods=["POST"])
def receive_videos():
    """Receive new queries from a Query Client."""

    print("\n\nServer: Starting receive_videos() [...]")

    global n_pending_queries
    
    if n_pending_queries == 0:
        data = flask.request.json
        n_pending_queries = data["n_pending_queries"]
        print("Server: Pending Queries: " + str(n_pending_queries))
        return "Server: [...] Terminating receive_videos()"

    # unquote() decodes url-encoded characters
    # .filename needs to be called to access json text data
    # strip('"') removes decoded quotation marks
    print("Server: Receiving videos...")
    left_filename = unquote(request.files.get("left_filename").filename).strip('"')
    right_filename = unquote(request.files.get("right_filename").filename).strip('"')
    left_video = request.files.get("left_video")
    right_video = request.files.get("right_video")
    print("    (Left): " + left_filename + "\n   (Right): " + right_filename)
    print("Server: ...Videos received")

    left_video.save(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    right_video.save(os.path.join(app.config["VIDEO_FOLDER"], right_filename))
    filenames_array.append(left_filename)
    filenames_array.append(right_filename)
    # Add empty feedback value for newly received, unevaluated data

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

    # should be replaced by flask session object
    # pylint: disable=global-statement
    global feedback_data
    global videos_evaluated
    global n_pending_queries

    data = flask.request.json  # Represents incoming client http request in json format
    videos_evaluated += 2  # Incoming request indicates new batch evaluation
    print(data)

    # Extract received JSON data
    is_left_preferred = data["is_left_preferred"]
    left_filename = data["video_filename_left"]

    query_id = left_filename[: -len("-left.webm")]

    # Check for defective msg transfer
    if is_left_preferred is None:
        return jsonify({"success": False})

    # Save feedback
    new_data = {query_id: is_left_preferred}
    feedback_data.update(new_data)
    n_pending_queries -= 1

    # Remove videos
    os.remove(os.path.join(app.config["VIDEO_FOLDER"], f"{query_id}-left.webm"))
    os.remove(os.path.join(app.config["VIDEO_FOLDER"], f"{query_id}-right.webm"))

    print("\nServer: Feedback stored")
    print("     Feedback Data:")
    for qID, boolean in feedback_data.items():
        print(f"    Query ID: {qID}    Left Preferred: {boolean}")

    print("\nServer: [...] Terminating receive_feedback()")

    return jsonify({"success": True})


@app.route("/feedback", methods=["GET"])
def send_feedback():
    """Sends feedback to Query Client"""

    global n_pending_queries

    print("\n\nServer: Starting send_feedback() [...]")

    if n_pending_queries == 0:
        print("Feddback fully evaluated")
        print("Server: [...] Terminating send_feedback()")
        return jsonify(feedback_data)
    else:
        print("Feedback not fully evaluated")
        print("Remaining Queries: " + str(n_pending_queries))
        print("Server: [...] Terminating send_feedback()")
        empty_dict = {}
        return jsonify(empty_dict)
                

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)