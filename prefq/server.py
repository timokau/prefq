"""A webserver that asks the user preference queries."""

import flask
from flask import Flask, jsonify

VIDEO_BUFFERSIZE = 10
FINISHED_EVALS = 0

app = Flask(__name__, static_url_path="/static")


is_evaluated = [False] * VIDEO_BUFFERSIZE
video_filepaths = [
    f"/lunarlander_random/{str(i).zfill(2)}.mp4" for i in range(1, VIDEO_BUFFERSIZE + 1)
]


def load_web_interface():
    """Renders updated .html interface"""

    # should be replaced by flask session object
    # pylint: disable=global-statement
    global FINISHED_EVALS

    if is_evaluated[(FINISHED_EVALS) % VIDEO_BUFFERSIZE] is False:
        is_evaluated[(FINISHED_EVALS) % VIDEO_BUFFERSIZE] = True
        is_evaluated[(FINISHED_EVALS + 1) % VIDEO_BUFFERSIZE] = True

        video_filepath_left = video_filepaths[(FINISHED_EVALS) % VIDEO_BUFFERSIZE]
        video_filepath_right = video_filepaths[(FINISHED_EVALS + 1) % VIDEO_BUFFERSIZE]

        FINISHED_EVALS += 2 % VIDEO_BUFFERSIZE

        return flask.render_template(
            "web_interface.html",
            video_filepath_left=video_filepath_left,
            video_filepath_right=video_filepath_right,
        )

    return flask.render_template("easteregg.html")


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


@app.route("/stop")
def delete_session_url():
    """Define behavior when client closes browser window"""

    response = flask.make_response()

    response.set_cookie("session", "", expires=0)  # Delete cookies
    flask.session.clear()  # Delete session

    return response


if __name__ == "__main__":
    app.run(debug=True)
