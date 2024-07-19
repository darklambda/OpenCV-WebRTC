## Running the Websocket Server

### Pre-requisites
* Docker
* Python 3.10.0

### Running locally
* Run ``pip install --no-cache-dir --upgrade -r requirements.txt``
* Run ``python app/server.py``
* Close the server "gracefully" with <kbd>Ctrl</kbd> + <kbd>C</kbd>

### Running with dockers
* Run ``docker build -t webrtc .``
* Run ``docker run -d --network host webrtc``

### Notes
This repo is originally based on the [aiortc server example](https://github.com/aiortc/aiortc/tree/main/examples/server).



  
