
## Introduction

This REST API is designed to help you understand how communication between our PrefQ Server and a Query/Feedback Client works. The API allows the Query Client to send video queries to the server, and the Feedback Client to provide feedback on the query results.

## Base URL

The base URL for this API by is either `http://localhost:5000` by default, or specified as commandline argument during server initialization.

## Endpoints

### 1. GET /

- **Description:** Reacts to a GET request from the Feedback Client. Intended to be accessed in a web browser. The Server then  - if available - returns a HTML template for the evaluation of the next query. If no query is available, the Server instead sends a html template, that (1) notifies the Feedback Client and (2) automatically sends GET-requests to this route, until new queries become available.
- **Request Parameters**: None
- **Request Type:** GET
- **Response:** (1) HTML template containing queries **or** (2) HTML template notifying the user, that no queries are available. Periodically sends GET requests until new queries become available.
- **Used by**: Feedback Client

### 2. POST /videos

- **Description:** Receives new video queries from a Query Client, stores them locally, and fills the queue with the new queries.
- **Request Parameters:**
    - `query_id`: Unique query ID
    - `left_video`: Left video file (binary data (precisely: octet-stream))
    - `right_video`: Right video file (binary data (precisely: octet-stream))
- **Request Type:** POST
- **Response:** Request status code including success message indicating the successful receipt of videos
- **Used by**: Query Client

### 3. GET /videos/<path:filename>

- **Description:** Enables embedding videos into the html template, before sending it to the feedback client. This route is automatically called by our provided `web_interface.html`, which uses flask's utility function `url_for('serve_video', filename)` in order to access this route. This happens, whenever `flask.render_template('web_interface.html', ..., ...)` is called.
- **Request Parameters:** 
	- `filename`: Name of the requested video
- **Request Type:** GET
- **Response:** Video file.
- **Used by:** Server

### 4. POST /feedback

- **Description:** Receives and stores feedback from the Feedback Client, then removes the query from the queue & deletes associated videos.
- **Request Parameters:** None
- **Request Type:** POST
- **Request Body:**    
    `{   "is_left_preferred": boolean,   "video_filename_left": string,   "video_filename_right": string }`
- **Response:** JSON object indicating success or failure.
- **Used by:** Feedback Client

### 5. GET /feedback

- **Description:** Sends feedback values back to the Query Client, once all queries have been evaluated.
- **Request Parameters:** None
- **Request Type:** GET
- **Response:** JSON dictionary containing `{query_id, feedback_value}`. Due to the implementation of flask, this dictionary will be ordered alphanumerically.
- **Used by:** Query Client

## Example Usage

1. **Query Client:** Send POST requests to `/videos` with video files and unique query IDs.
2. **Feedback Client:** Send GET request to `/` to receive HTML interface for evaluating queries.
3. **Feedback Client:** Send POST requests to `/feedback` with feedback data.
4. **Query Client:** Send GET requests to `/feedback`. Receive Server answers indicating incomplete evaluation.
5. **Feedback Client:** Repeat steps (2.), (3.) until all queries have been evaluated
6. **Query Client:** Send GET request to `/feedback`. Receive Server answer containing evaluated queries