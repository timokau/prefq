"""
This module provides a Flask-based webserver that serves a web interface for

    (1) Query Clients:
        (a) send queries to the server
        (b) request feedback from the server

    (2) Feedback Clients:
        (a) receive queries
        (b) evaluate queries
        (c) send feedback to the server

Seperating the Query Client from the server allows for flexible design, as the
Query Client can be implemented in any programming language & any desired behavior.

By implementing a server architecture, that only reacts to incoming requests,
without performing computationally expensive tasks, the server can be run
with minimal hardware requirements, e.g. on a Raspberry Pi or a cloud server.

Additionally, the Query Client script could for example be run from a laptop, and
can be disconnected from the web at any given moment, without affecting the server.

Aspects to be taken into consideration, for a customized Query Client implementation:
    (1) Query Client sends a POST request with a unique query ID & a pair of queries
    (2) Query Client sends a GET request to receive feedback from the server
        (a) if feedback is not yet fully availible, resend GET request later
        (b) if feedback is fully availible, return to (1) whenever desired

Examples for both static & dynamic queries are provided within this project.

By implementing a queue, that only deletes queries after receiving feedback,
the server can ensure, that unevaluated Queries due to unexpected events
(e.g. Feedback Client crash) can be evaluated in the future.
"""

import argparse
import base64
import os
import queue
from urllib.parse import unquote

import flask
import waitress
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from flask import Flask, jsonify, request

app = Flask(__name__)

app.config["VIDEO_FOLDER"] = "videos"
app.config["PRIVATE_KEY"] = None
app.config["PUBLIC_KEY"] = None
app.config["SERVER_PW"] = None

feedback_data = {}
query_queue = queue.Queue()
queries_pending_response = []

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5000
DEFAULT_DEBUG = False


def before_first_request(ssh_pub, ssh_priv, server_pw):
    """Define starting routine"""

    if (ssh_pub, ssh_priv, server_pw) != (None, None, None):
        app.config["SERVER_PW"] = server_pw

        with open(ssh_priv, "rb") as key_file:
            app.config["PRIVATE_KEY"] = serialization.load_ssh_private_key(
                key_file.read(),
                password=None,
            )

        with open(ssh_pub, "rb") as key_file:
            app.config["PUBLIC_KEY"] = serialization.load_ssh_public_key(
                key_file.read(),
            )

    # Create video folder (if necessary)
    if not os.path.exists(app.config["VIDEO_FOLDER"]):
        os.mkdir(app.config["VIDEO_FOLDER"])


def decrypt(encrypted_message):
    """Decrypt SSH encrypted strings"""

    decrypted_message = app.config["PRIVATE_KEY"].decrypt(
        encrypted_message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return decrypted_message.decode()


@app.route("/", methods=["GET"])
def index():
    """
    React to GET request, when server URL is called in a browser.

    This function is only called by the Feedback Client, to receive an
    HTML interface, that allows the user to evaluate the query.

    After evaluation & subsequent POST request containing the feedback,
    this function is automatically triggered again by the javascript
    code running within the HTML interface, reloading the HTML interface
    with new queries, if availible.
            (behavior can be modified in web_interface.js)

    Whenever no data is availible, the corresponding HTML interface
    autoamtically reloads every 2 seconds, until new data is availible.
            (behavior can be modified in no_data_availible.html)
    """

    response_data = load_web_interface()
    response = app.make_response(response_data)

    return response  # Update Feedback Client Interface


def load_web_interface():
    """Send HTML interface to Feedback Client"""

    print("\n\nServer: Starting load_web_interface() [...] ")

    is_queue_empty = query_queue.empty()
    is_pending_queries_empty = len(queries_pending_response) == 0

    is_video_available = not (is_queue_empty and is_pending_queries_empty)

    if is_video_available:
        print("Server: [...] Terminating load_web_interface()")
        if not is_queue_empty:
            # Get query from queue
            query = query_queue.get()
            queries_pending_response.append(query)
        else:
            # Get query from list
            query = queries_pending_response[0]

            # Put query at last position in list
            queries_pending_response.pop(0)
            queries_pending_response.append(query)

        video_filename_left, video_filename_right = query

        return flask.render_template(
            "web_interface.html",
            video_filename_left=video_filename_left,
            video_filename_right=video_filename_right,
        )

    print("Server: [...] No data available")
    return flask.render_template("no_data_availible.html")


@app.route("/videos", methods=["POST"])
def receive_videos():
    """
    (1) Receive new queries from a Query Client.
    (2) Store queries locally.
    (3) Fill queue with new queries.

    This function can be called by the Query Client, whenever a new batch of queries
    is availible. The Query Client sends a POST request, containing a unique query ID
    and a pair of queries as binary data (octet-stream).

    This is done in order to implement this server in the spirit
    of a REST-API, which requires .json encoded data.
    """

    print("\n\nServer: Starting receive_videos() [...]")

    if app.config["PRIVATE_KEY"] is not None:
        encrypted_password = unquote(request.files.get("password").filename).strip('"')
        encrypted_password = base64.b64decode(encrypted_password)
        decrypted_password = decrypt(encrypted_password)
        if decrypted_password != app.config["SERVER_PW"]:
            print("Server: [...] Request Rejected (incorrect password)")
            return "Server: [...] Terminating receive_videos()"

    print("Server: Storing videos...")
    query_id = unquote(request.files.get("query_id").filename).strip('"')
    left_video = request.files.get("left_video")
    right_video = request.files.get("right_video")
    file_extension = left_video.filename.split(".")[1]
    left_filename = query_id + "-left." + file_extension
    right_filename = query_id + "-right." + file_extension
    query = (left_filename, right_filename)
    print(f"    Query ID: {query_id}")
    print("Server: ...Videos received")

    left_video.save(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    right_video.save(os.path.join(app.config["VIDEO_FOLDER"], right_filename))
    query_queue.put(query)
    print("Server: ...Videos stored locally")

    payload = {
        "password": (
            app.config["QUERY_CLIENT_PASSWORD"],
            "application/json",
        ),
    }

    print("Server: [...] Terminating receive_videos()")
    return jsonify(payload)


@app.route("/videos/<path:filename>", methods=["GET"])
def serve_video(filename):
    """Make videos accessible for feedback client (web_interface.html)"""

    video_folder = os.path.join(os.getcwd(), app.config["VIDEO_FOLDER"])
    return flask.send_from_directory(video_folder, filename)


@app.route("/feedback", methods=["POST"])
def receive_feedback():
    """Receive and store client feedback"""

    print("\n\nServer: Starting receive_feedback() [...]")

    data = flask.request.json  # Represents incoming client http request in json format

    # Extract received JSON data
    is_left_preferred = data["is_left_preferred"]
    left_filename = data["video_filename_left"]
    right_filename = data["video_filename_right"]
    query_id = left_filename.split("-left")[0]

    query = (left_filename, right_filename)

    # Check if received query is contained in query list
    if query not in queries_pending_response:
        print("Server: Query already evaluated")
        print("Server: [...] Terminating receive_feedback()")
        return jsonify({"success": True})

    # Remove query from query list & delete locally stored videos
    queries_pending_response.remove(query)
    os.remove(os.path.join(app.config["VIDEO_FOLDER"], left_filename))
    os.remove(os.path.join(app.config["VIDEO_FOLDER"], right_filename))

    new_data = {query_id: is_left_preferred}
    feedback_data.update(new_data)
    print("Server: Feedback stored")
    for q_id, boolean in feedback_data.items():
        print(f"    Query ID: {q_id}    Left Preferred: {boolean}")

    print("\nServer: [...] Terminating receive_feedback()")
    return jsonify({"success": True})


@app.route("/feedback", methods=["GET"])
def send_feedback():
    """Sends feedback to Query Client"""

    print("\n\nServer: Starting send_feedback() [...]")

    is_queue_empty = query_queue.empty()
    is_pending_queries_empty = len(queries_pending_response) == 0

    if is_queue_empty and is_pending_queries_empty:
        print("Feedback fully evaluated")
        feedback_data_copy = feedback_data.copy()
        feedback_data.clear()
        print("Server: [...] Terminating send_feedback()")
        return jsonify(feedback_data_copy)

    print("Feedback not fully evaluated")
    print(
        "Remaining Queries: "
        + str(len(query_queue.queue) + len(queries_pending_response))
    )
    print("Server: [...] Terminating send_feedback()")
    empty_dict = {}
    return jsonify(empty_dict)


def main():
    """Start server"""

    # parse host, port and server mode from command line
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help="Specify the host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Specify the port (default: 5000)",
    )
    parser.add_argument(
        "--debug",
        type=bool,
        default=DEFAULT_DEBUG,
        help="Specify debug mode (default: False)",
    )
    # pylint: disable=R0801
    parser.add_argument(
        "--sshpub",
        type=str,
        default=None,
        help="Specify SSH public-key filepath (default: None)",
    )
    # pylint: disable=R0801
    parser.add_argument(
        "--sshpriv",
        type=str,
        default=None,
        help="Specify SSH private-key filepath (default: None)",
    )
    # pylint: disable=R0801
    parser.add_argument(
        "--pw",
        type=str,
        default=None,
        help="Specify Password for request authentication (default: None)",
    )

    args = parser.parse_args()

    host = args.host
    port = args.port
    debug = args.debug
    ssh_pub = args.sshpub
    ssh_priv = args.sshpriv
    server_pw = args.pw

    is_encryption_desired = (server_pw, ssh_pub, ssh_priv) != (None, None, None)
    is_encryption_not_desired = (server_pw, ssh_pub, ssh_priv) == (None, None, None)

    is_correctly_initialized = is_encryption_desired or is_encryption_not_desired

    if not is_correctly_initialized:
        raise ValueError("SSH keys and PW must be either all present or all None")

    before_first_request(ssh_pub, ssh_priv, server_pw)
    print(f"Host: {host}, Port: {port},   Debug: {debug}\n\n")

    # A detailled explanation of the benefits and drawbacks of using the
    # development server can be found in the PrefQ documentation
    if debug:
        app.run(host=host, port=port, debug=debug)
    else:
        waitress.serve(app, host=host, port=port)


if __name__ == "__main__":
    main()
