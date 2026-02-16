# remote_mixer

A Flask server with WebSocket support and CORS disabled for real-time communication.

## Features

- Flask web server with WebSocket support via flask-sock
- CORS disabled for all routes
- Static file serving for index.html at root route `/`
- WebSocket API endpoint at `/ws`
- Auto-reconnecting WebSocket client
- Simple message echo demo

## Prerequisites

- Python 3.11 or higher
- UV package manager

## Installation

Install dependencies using UV:

```bash
uv sync
```

## Running the Server

**Quick Start:**

```bash
./start_server.sh
```

**Or manually:**

```bash
uv run python app.py
```

The server will start on `http://localhost:5001`

## Usage

1. Open your browser and navigate to `http://localhost:5001`
2. The WebSocket connection will automatically establish
3. Type messages in the input field and click "Send" to test the WebSocket connection
4. The server will echo back your messages

## API Endpoints

- `GET /` - Serves the static index.html file
- `WebSocket /ws` - WebSocket endpoint for real-time bidirectional communication

## Project Structure

```
remote_mixer/
├── app.py              # Main Flask application
├── static/
│   └── index.html      # Frontend HTML with WebSocket client
├── pyproject.toml      # Project dependencies
├── .python-version     # Python version specification
└── README.md           # This file
```

## Development

The server runs in debug mode by default. Any changes to `app.py` will automatically reload the server.

To modify the WebSocket behavior, edit the `websocket()` function in `app.py`.

