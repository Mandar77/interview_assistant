"""
WebSocket Streaming Test - Test the real-time speech streaming endpoint
Location: backend/tests/test_websocket_stream.py

Run with: python tests/test_websocket_stream.py
Requires: pip install websockets
"""

import asyncio
import json
import uuid
import sys
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets


async def test_websocket_connection():
    """Test basic WebSocket connection and protocol."""
    
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/api/v1/speech/stream?session_id={session_id}"
    
    print(f"Connecting to: {uri}")
    print(f"Session ID: {session_id}")
    print("-" * 50)
    
    try:
        async with websockets.connect(uri) as websocket:
            # Wait for connection acknowledgment
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Connected: {data}")
            
            # Test ping/pong
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Ping/Pong: {data}")
            
            # Test status
            await websocket.send(json.dumps({"type": "get_status"}))
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Status: {data}")
            
            # Send some dummy audio bytes (this won't produce valid transcription
            # but tests the binary message handling)
            print("\nSending test audio chunks...")
            for i in range(3):
                dummy_audio = bytes([0] * 1000)  # 1KB of silence
                await websocket.send(dummy_audio)
                print(f"  Sent chunk {i+1}")
                await asyncio.sleep(0.1)
            
            # End session
            print("\nEnding session...")
            await websocket.send(json.dumps({"type": "end_session"}))
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Session ended: {data}")
            
            print("\n" + "=" * 50)
            print("WebSocket connection test PASSED!")
            print("=" * 50)
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"✗ Connection closed: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_with_real_audio(audio_file_path: str):
    """Test WebSocket with actual audio file."""
    
    if not Path(audio_file_path).exists():
        print(f"Audio file not found: {audio_file_path}")
        return
    
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/api/v1/speech/stream?session_id={session_id}"
    
    print(f"Testing with audio file: {audio_file_path}")
    print(f"Session ID: {session_id}")
    print("-" * 50)
    
    # Read audio file
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    # Split into chunks (simulate streaming)
    chunk_size = 8000  # ~250ms of audio at typical bitrates
    chunks = [audio_data[i:i+chunk_size] for i in range(0, len(audio_data), chunk_size)]
    
    print(f"Audio size: {len(audio_data)} bytes")
    print(f"Chunks: {len(chunks)}")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Wait for connection
            response = await websocket.recv()
            print(f"Connected: {json.loads(response)}")
            
            # Send chunks with timing
            for i, chunk in enumerate(chunks):
                await websocket.send(chunk)
                print(f"Sent chunk {i+1}/{len(chunks)}")
                
                # Check for any responses (non-blocking)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    data = json.loads(response)
                    if data.get("type") == "partial_transcript":
                        print(f"  → Transcript: {data.get('partial_transcript', '')[:50]}...")
                except asyncio.TimeoutError:
                    pass
                
                await asyncio.sleep(0.25)  # Simulate real-time streaming
            
            # Wait for final transcripts
            print("\nWaiting for final processing...")
            await asyncio.sleep(2)
            
            # End session
            await websocket.send(json.dumps({"type": "end_session"}))
            
            # Collect remaining messages
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1)
                    data = json.loads(response)
                    print(f"Received: {data.get('type', 'unknown')}")
                    if data.get("type") == "session_ended":
                        break
                except asyncio.TimeoutError:
                    break
            
            print("\n✓ Test completed!")
            print(f"\nRetrieve session data at:")
            print(f"  GET http://localhost:8000/api/v1/speech/session/{session_id}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 50)
    print("Interview Assistant - WebSocket Streaming Test")
    print("=" * 50)
    print("\nMake sure the backend is running:")
    print("  cd backend && python app.py\n")
    
    # Basic connection test
    asyncio.run(test_websocket_connection())
    
    # If you have an audio file to test with:
    # asyncio.run(test_with_real_audio("path/to/test.webm"))