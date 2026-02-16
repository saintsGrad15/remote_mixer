#!/usr/bin/env python3
"""
Simple WebSocket client to test the server
"""
import asyncio
import websockets
import sys

async def test_websocket():
    uri = "ws://localhost:5001/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket server")

            # Send a test message
            test_message = "Hello from test client!"
            await websocket.send(test_message)
            print(f"→ Sent: {test_message}")

            # Receive the response
            response = await websocket.recv()
            print(f"← Received: {response}")

            if "Server received:" in response and test_message in response:
                print("\n✓ WebSocket test PASSED!")
                return 0
            else:
                print("\n✗ WebSocket test FAILED - unexpected response")
                return 1

    except Exception as e:
        print(f"\n✗ WebSocket test FAILED - {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_websocket())
    sys.exit(exit_code)

