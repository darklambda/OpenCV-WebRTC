## Running the fastapi instance

### Pre-requisites
* Docker
* Python 3.10.0

### Running locally
* Run ``pip install --no-cache-dir --upgrade -r requirements.txt``
* Run ``python app/server.py``
* Close the server "gracefully" with <kbd>Ctrl</kbd> + <kbd>C</kbd>

### Running with dockers
* Run ``docker build -t webrtc .``
* Run ``docker run -d -p 8764:8764 fastapi``



  
