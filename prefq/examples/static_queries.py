"""An example Query Client that sends static queries to the server and polls results."""

import argparse

from prefq.query_client import QueryClient

AVAILABLE_VIDEOS = 10
DEFAULT_SERVER_URL = "http://localhost:5000/"
VIDEO_DIR = "prefq/examples/video-examples"
VIDEO_PAIRS = [
    (f"{str(i).zfill(2)}.mp4", f"{str(i+1).zfill(2)}.mp4")
    for i in range(1, AVAILABLE_VIDEOS + 1, 2)
]


def generate_query_id(left_filename, right_filename):
    """Define unique query identifier"""

    # Remove file extension
    left_filename = left_filename.split(".")[0]
    right_filename = right_filename.split(".")[0]

    # Combine filenames to query_id
    query_id = left_filename + "-" + right_filename

    return query_id


def main():
    """Send the example queries and poll for feedback."""

    # parse server url
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_SERVER_URL,
        help="Specify the server url (default: http://localhost:5000/)",
    )

    args = parser.parse_args()
    server_url = args.url

    query_client = QueryClient(server_url)

    for left_filename, right_filename in VIDEO_PAIRS:
        query_id = generate_query_id(left_filename, right_filename)
        query_client.send_video_pair(query_id, left_filename, right_filename, VIDEO_DIR)

    feedback_data = query_client.request_feedback()
    for q_id, boolean in feedback_data.items():
        preference = "left" if boolean else "right"
        print(f"Query ID: {q_id}    Preference: {preference}")


if __name__ == "__main__":
    main()
