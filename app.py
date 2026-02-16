from flask import \
    Flask, \
    send_from_directory, \
    jsonify
from flask_sock import \
    Sock
from flask_cors import \
    CORS
import \
    json
import \
    rtmidi
import \
    threading
import \
    time

app = Flask(
    __name__,
    static_folder='static')

# Disable CORS completely
CORS(
    app,
    resources={
        r"/*": {
            "origins": []}})

# Initialize WebSocket support
sock = Sock(
    app)

# Load configuration and initialize MIDI
config = None
midi_out = None
midi_in = None
connected_clients = set()


def init_midi():
    """Initialize MIDI output and input"""
    global config, midi_out, midi_in

    try:
        with open(
                'config.json',
                'r') as f:
            config = json.load(
                f)

        midi_out = rtmidi.MidiOut()
        available_ports = midi_out.get_ports()

        print(
            f"Available MIDI output ports: {available_ports}")

        # Find the configured MIDI output interface
        midi_interface_out = config.get(
            'midi_interface_out',
            'Remote Mixer IAC Driver')
        port_index = None

        for i, port_name in enumerate(
                available_ports):
            if midi_interface_out in port_name:
                port_index = i
                break

        if port_index is not None:
            midi_out.open_port(
                port_index)
            print(
                f"Opened MIDI output port: {available_ports[port_index]}")
        else:
            print(
                f"Warning: MIDI output interface '{midi_interface_out}' not found. Available ports: {available_ports}")
            # Open virtual port as fallback
            midi_out.open_virtual_port(
                midi_interface_out)
            print(
                f"Opened virtual MIDI output port: {midi_interface_out}")

        # Initialize MIDI Input
        midi_in = rtmidi.MidiIn()
        available_in_ports = midi_in.get_ports()

        print(
            f"Available MIDI input ports: {available_in_ports}")

        # Find the configured MIDI input interface
        midi_interface_in = config.get(
            'midi_interface_in')
        if midi_interface_in:
            port_index = None

            for i, port_name in enumerate(
                    available_in_ports):
                if midi_interface_in in port_name:
                    port_index = i
                    break

            if port_index is not None:
                midi_in.open_port(
                    port_index)
                print(
                    f"Opened MIDI input port: {available_in_ports[port_index]}")
            else:
                print(
                    f"Warning: MIDI input interface '{midi_interface_in}' not found. Available ports: {available_in_ports}")
                # Open virtual port as fallback
                midi_in.open_virtual_port(
                    midi_interface_in)
                print(
                    f"Opened virtual MIDI input port: {midi_interface_in}")
        else:
            print(
                "No MIDI input interface configured in config.json")

    except Exception as e:
        print(
            f"Error initializing MIDI: {e}")
        midi_out = None
        midi_in = None


# Initialize MIDI on startup
init_midi()


def midi_listener_thread():
    """Listen for incoming MIDI events and broadcast to connected clients"""
    global midi_in, config

    # Build a map of CC values to channel info
    cc_map = {}
    if config:
        for channel in config.get(
                'channels',
                []):
            cc = channel.get(
                'cc')
            if cc is not None:
                if cc not in cc_map:
                    cc_map[
                        cc] = []
                cc_map[
                    cc].append(
                    channel)

    print(
        f"MIDI CC map: {cc_map}")

    while True:
        try:
            if midi_in is None:
                time.sleep(
                    0.1)
                continue

            # Poll for MIDI messages
            msg = midi_in.get_message()

            if msg:
                message, deltatime = msg

                # Check if this is a Control Change message (0xB0 - 0xBF)
                if len(message) >= 3 and (
                        message[
                            0] & 0xF0) == 0xB0:
                    cc = \
                        message[
                            1]
                    value = \
                        message[
                            2]

                    # Check if this CC matches any configured channel
                    if cc in cc_map:
                        print(
                            f"Received MIDI CC: {cc=}, {value=}")

                        # Send update to all connected clients
                        update_message = json.dumps(
                            {
                                "type": "midi_cc_update",
                                "cc": cc,
                                "value": value
                            })

                        for client in list(
                                connected_clients):
                            try:
                                client.send(
                                    update_message)
                            except Exception as e:
                                print(
                                    f"Error sending to client: {e}")
                                connected_clients.discard(
                                    client)
            else:
                time.sleep(
                    0.01)

        except Exception as e:
            print(
                f"MIDI listener error: {e}")
            time.sleep(
                0.1)


# Start MIDI listener thread
midi_listener = threading.Thread(
    target=midi_listener_thread,
    daemon=True)
midi_listener.start()


@app.route(
    '/')
def index():
    """Serve the index.html file"""
    return send_from_directory(
        'static',
        'index.html')


@app.route(
    '/config')
def get_config():
    """Serve the configuration file"""
    try:
        with open(
                'config.json',
                'r') as f:
            config = json.load(
                f)
        return jsonify(
            config)
    except Exception as e:
        return jsonify(
            {
                "error": str(
                    e)}), 500


@sock.route(
    '/ws')
def websocket(
        ws):
    """WebSocket endpoint for real-time communication"""
    # Add client to connected clients set
    connected_clients.add(
        ws)
    print(
        f"Client connected. Total clients: {len(connected_clients)}")

    while True:
        try:
            # Receive message from client
            message = ws.receive()

            if message is None:
                break

            # Parse JSON message
            try:
                data = json.loads(
                    message)

                if data.get(
                        'type') == 'cc':
                    cc = data.get(
                        'cc')
                    value = data.get(
                        'value')

                    if cc is not None and value is not None:
                        # Send MIDI Control Change message
                        if midi_out is not None:
                            # MIDI CC message format: [0xB0 | channel, cc, value]
                            # Using channel 0 (0xB0)
                            midi_message = [
                                0xB0,
                                cc,
                                value]
                            midi_out.send_message(
                                midi_message)
                            print(
                                f"Sent MIDI CC: channel=0, cc={cc}, value={value}")
                        else:
                            print(
                                f"MIDI not initialized, would send CC {cc}={value}")

                        # Acknowledge receipt
                        ws.send(
                            json.dumps(
                                {
                                    "status": "ok",
                                    "cc": cc,
                                    "value": value}))
                    else:
                        ws.send(
                            json.dumps(
                                {
                                    "status": "error",
                                    "message": "Missing cc or value"}))
                elif data.get(
                        'type') == 'healthcheck':
                    ws.send(
                        json.dumps(
                            {
                                "status": "ok",
                                "message": "Server is healthy"
                            }
                        )
                    )
                else:
                    print(
                        f"Unknown message type: {data.get('type')}")

            except json.JSONDecodeError:
                print(
                    f"Invalid JSON received: {message}")
                ws.send(
                    json.dumps(
                        {
                            "status": "error",
                            "message": "Invalid JSON"}))

        except Exception as e:
            print(
                f"WebSocket error: {e}")
            break

    # Remove client from connected clients set
    connected_clients.discard(
        ws)
    print(
        f"Client disconnected. Total clients: {len(connected_clients)}")


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True)
