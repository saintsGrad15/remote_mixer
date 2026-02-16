from flask import Flask, send_from_directory, jsonify
from flask_sock import Sock
from flask_cors import CORS
import json
import rtmidi

app = Flask(__name__, static_folder='static')

# Disable CORS completely
CORS(app, resources={r"/*": {"origins": []}})

# Initialize WebSocket support
sock = Sock(app)

# Load configuration and initialize MIDI
config = None
midi_out = None

def init_midi():
    """Initialize MIDI output"""
    global config, midi_out

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)

        midi_out = rtmidi.MidiOut()
        available_ports = midi_out.get_ports()

        print(f"Available MIDI ports: {available_ports}")

        # Find the configured MIDI interface
        midi_interface = config.get('midi_interface', 'Remote Mixer IAC Driver')
        port_index = None

        for i, port_name in enumerate(available_ports):
            if midi_interface in port_name:
                port_index = i
                break

        if port_index is not None:
            midi_out.open_port(port_index)
            print(f"Opened MIDI port: {available_ports[port_index]}")
        else:
            print(f"Warning: MIDI interface '{midi_interface}' not found. Available ports: {available_ports}")
            # Open virtual port as fallback
            midi_out.open_virtual_port(midi_interface)
            print(f"Opened virtual MIDI port: {midi_interface}")

    except Exception as e:
        print(f"Error initializing MIDI: {e}")
        midi_out = None

# Initialize MIDI on startup
init_midi()


@app.route('/')
def index():
    """Serve the index.html file"""
    return send_from_directory('static', 'index.html')


@app.route('/config')
def get_config():
    """Serve the configuration file"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sock.route('/ws')
def websocket(ws):
    """WebSocket endpoint for real-time communication"""
    while True:
        try:
            # Receive message from client
            message = ws.receive()

            if message is None:
                break

            # Parse JSON message
            try:
                data = json.loads(message)

                print(data)

                if data.get('type') == 'cc':
                    cc = data.get('cc')
                    value = data.get('value')

                    if cc is not None and value is not None:
                        # Send MIDI Control Change message
                        if midi_out is not None:
                            # MIDI CC message format: [0xB0 | channel, cc, value]
                            # Using channel 0 (0xB0)
                            midi_message = [0xB0, cc, value]
                            midi_out.send_message(midi_message)
                            print(f"Sent MIDI CC: channel=0, cc={cc}, value={value}")
                        else:
                            print(f"MIDI not initialized, would send CC {cc}={value}")

                        # Acknowledge receipt
                        ws.send(json.dumps({"status": "ok", "cc": cc, "value": value}))
                    else:
                        ws.send(json.dumps({"status": "error", "message": "Missing cc or value"}))
                else:
                    print(f"Unknown message type: {data.get('type')}")

            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
                ws.send(json.dumps({"status": "error", "message": "Invalid JSON"}))

        except Exception as e:
            print(f"WebSocket error: {e}")
            break


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)


