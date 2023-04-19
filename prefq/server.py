"""A webserver that asks the user preference queries."""

import flask
from flask import Flask

app = Flask(__name__)


# defines the path of index
@app.route("/")
def index():
    """Serve the webinterface."""
    return flask.render_template("web_interface.html")


if __name__ == "__main__":
    app.run(debug=True)
