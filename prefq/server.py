"""A webserver that asks the user preference queries."""

# disable pylint warning for similar lines in server.py and imitation_server.py
# on a long term both files shall be merged
# pylint: disable=R0801

import os
from urllib.parse import unquote

import flask
import queue
from flask import Flask, jsonify, request

app = Flask(__name__)

app.config["VIDEO_FOLDER"] = "videos"

feedback_data = {}
pending_queries = queue.Queue()


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

    print("\n\nServer: Starting load_web_interface() [...] ")
    
    is_video_available = not pending_queries.empty()

    if is_video_available:
        print("Server: [...] Terminating load_web_interface()")
        video_filename_left, video_filename_right = pending_queries.get()
        return flask.render_template(
            "web_interface.html",
            video_filename_left=video_filename_left,
            video_filename_right=video_filename_right,
        )

    print("Server: [...] No data available")
    return flask.render_template("no_data_availible.html")


@app.route("/videos", methods=["POST"])
def receive_videos():
    """Receive new queries from a Query Client."""

    print("\n\nServer: Starting receive_videos() [...]")

    print("Server: Receiving videos...")
    query_id = unquote(request.files.get("query_id").filename).strip('"')
    left_filename = query_id + "-left.webm"
    right_filename = query_id + "-right.webm"
    left_video = request.files.get("left_video")
    right_video = request.files.get("right_video")
    query_pair = (left_filename, right_filename)
    print(f"    Query ID: {query_id}")
    print("Server: ...Videos received")

    left_video.save(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    right_video.save(os.path.join(app.config["VIDEO_FOLDER"], right_filename))
    pending_queries.put(query_pair)
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

    data = flask.request.json  # Represents incoming client http request in json format

    # Extract received JSON data
    is_left_preferred = data["is_left_preferred"]
    left_filename = data["video_filename_left"]
    right_filename = data["video_filename_right"]

    query_id = left_filename[: -len("-left.webm")]

    print("Server: Received feedback")
    print(f"    Query ID: {query_id}")
    print(f"    Left Preferred: {is_left_preferred}")

    # Check if feedback was given - if not, refill queue
    if is_left_preferred is None:
        print("Server: No feedback received")
        right_filename = query_id + "-right.webm"
        pending_queries.put(left_filename)
        pending_queries.put(right_filename)
        print("Server: [...] Terminating receive_feedback()")
        return jsonify({"success": True})

    # Save feedback
    new_data = {query_id: is_left_preferred}
    feedback_data.update(new_data)

    # Remove videos
    os.remove(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    os.remove(os.path.join(app.config["VIDEO_FOLDER"], right_filename))

    print("Server: Feedback stored")
    for qID, boolean in feedback_data.items():
        print(f"    Query ID: {qID}    Left Preferred: {boolean}")

    print("\nServer: [...] Terminating receive_feedback()")
    return jsonify({"success": True})



@app.route("/feedback", methods=["GET"])
def send_feedback():
    """Sends feedback to Query Client"""

    print("\n\nServer: Starting send_feedback() [...]")

    if len(pending_queries.queue) == 0:
        print("Feddback fully evaluated")
        feedback_data_copy = feedback_data.copy()
        feedback_data.clear()
        print("Server: [...] Terminating send_feedback()")
        return jsonify(feedback_data_copy)

    print("Feedback not fully evaluated")
    print("Remaining Queries: " + str(len(pending_queries.queue)))
    print("Server: [...] Terminating send_feedback()")
    empty_dict = {}
    return jsonify(empty_dict)


if __name__ == "__main__":
    before_first_request()
    app.run(host="127.0.0.1", port=5000, debug=True)
