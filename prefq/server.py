"""A webserver that asks the user preference queries."""

import flask
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/", methods=["POST"])
def receive_data():
    """Receives labels from the client (web_interface.js)"""
    # Request.json object represents incoming client http request in json format
    data = flask.request.json
    # Extract JSON data sent by the client (web_interface.js)
    is_left_preferred = data["is_left_preferred"]

    print("Left Preferred: ", is_left_preferred)

    return jsonify({"success": True})


@app.route("/", methods=["GET"])
def index():
    """Defines index path (url) and renders html template"""
    return flask.render_template("web_interface.html")


if __name__ == "__main__":
    app.run(debug=True)
