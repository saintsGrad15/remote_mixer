from flask import Flask, send_from_directory
from flask_sock import Sock
from flask_cors import CORS

app = Flask(__name__, static_folder='static')

# Disable CORS completely
CORS(app, resources={r"/*": {"origins": []}})

# Initialize WebSocket support
sock = Sock(app)


@app.route('/')
def index():
    """Serve the index.html file"""
    return send_from_directory('static', 'index.html')


@sock.route('/ws')
def websocket(ws):
    """WebSocket endpoint for real-time communication"""
    while True:
        try:
            # Receive message from client
            message = ws.receive()

            if message is None:
                break

            print(f"Received: {message}")

            # Echo the message back to the client
            ws.send(f"Server received: {message}")

        except Exception as e:
            print(f"WebSocket error: {e}")
            break


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)


