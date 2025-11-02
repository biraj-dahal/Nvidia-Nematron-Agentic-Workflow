import os
import subprocess
import json
import asyncio
import base64
import httpx
import wave
import queue
import threading
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import shutil # Used for file cleanup

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Import orchestrator for meeting analysis
from orchestrator_agent import run_orchestrator

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
TEMP_WAV_FILE = 'recording_16k_mono.wav'

# Global event queue for SSE streaming
# Each client gets its own queue when connecting
workflow_event_queues = []
workflow_event_lock = threading.Lock()
# Full path to the NVIDIA script (adjust if your structure is different)
TRANSCRIPTION_SCRIPT_PATH = os.path.join(
    'python-clients', 'scripts', 'asr', 'transcribe_file.py'
)
# NVIDIA NIM details (Parakeet ASR)
NIM_SERVER = "grpc.nvcf.nvidia.com:443"
NIM_FUNCTION_ID = "1598d209-5e27-4d3c-8079-4751568b1081"  # Parakeet function ID

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Ensure API Key is set
NVIDIA_API_KEY = os.environ.get("API_KEY", "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")
if not NVIDIA_API_KEY:
    raise EnvironmentError("The API_KEY environment variable is not set. Please set it as per NVIDIA instructions.")


def broadcast_workflow_event(event_data: dict):
    """Broadcast a workflow event to all connected SSE clients"""
    print(f"🔌 [broadcast_workflow_event] Broadcasting {event_data.get('type')} for {event_data.get('agent')} to {len(workflow_event_queues)} clients")
    with workflow_event_lock:
        # Remove dead queues and broadcast to active ones
        dead_queues = []
        for i, q in enumerate(workflow_event_queues):
            try:
                q.put_nowait(event_data)
                print(f"   ✓ Broadcasted to client {i}")
            except queue.Full:
                # Queue is full, mark for removal
                print(f"   ❌ Queue full for client {i}, removing...")
                dead_queues.append(i)

        # Remove dead queues in reverse order to maintain indices
        for i in reversed(dead_queues):
            workflow_event_queues.pop(i)

        print(f"   ✓ Broadcast complete: {len(workflow_event_queues)} active clients")


def convert_to_nvidia_format(input_path, output_path):
    """Converts audio to 16kHz, 16-bit, mono WAV using ffmpeg."""
    # -ar 16000 (sample rate), -ac 1 (mono), -f wav (format), -c:a pcm_s16le (16-bit encoding)
    command = [
        'ffmpeg', '-i', input_path,
        '-ar', '16000',
        '-ac', '1',
        '-y', # Overwrite output files without asking
        '-f', 'wav',
        '-c:a', 'pcm_s16le',
        output_path
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: ffmpeg is not installed or not in your PATH.")
        return False


def convert_audio_with_pydub(input_path, output_path):
    """Converts audio to 16kHz, 16-bit, mono WAV using pydub (pure Python fallback)."""
    try:
        if not PYDUB_AVAILABLE:
            print("Pydub not available for audio conversion")
            return False

        # Load the audio file (pydub auto-detects format)
        print(f"Loading audio from {input_path}...")
        audio = AudioSegment.from_file(input_path)

        # Convert to mono
        if audio.channels > 1:
            print(f"Converting {audio.channels} channels to mono...")
            audio = audio.set_channels(1)

        # Resample to 16000 Hz
        if audio.frame_rate != 16000:
            print(f"Resampling from {audio.frame_rate} Hz to 16000 Hz...")
            audio = audio.set_frame_rate(16000)

        # Export as WAV with 16-bit PCM
        print(f"Exporting to {output_path}...")
        audio.export(output_path, format="wav", bitrate="16k", parameters=["-q:a", "9"])

        print("Audio conversion successful")
        return True

    except Exception as e:
        print(f"Pydub conversion error: {e}")
        return False

def run_nvidia_transcription(filepath):
    """Executes the NVIDIA ASR script using gRPC and captures the transcription."""

    print(f"\n   {'─'*76}")
    print(f"   NVIDIA TRANSCRIPTION DETAILS")
    print(f"   {'─'*76}")
    print(f"   Input file: {filepath}")
    print(f"   File exists: {os.path.exists(filepath)}")
    if os.path.exists(filepath):
        print(f"   File size: {os.path.getsize(filepath)} bytes")

    # Construct the command to execute the NVIDIA script with correct parameters
    command = [
        'python', TRANSCRIPTION_SCRIPT_PATH,
        '--server', NIM_SERVER,
        '--use-ssl',
        '--metadata', 'function-id', NIM_FUNCTION_ID,
        '--metadata', 'authorization', f'Bearer {NVIDIA_API_KEY}',
        '--language-code', 'en-US',
        '--input-file', filepath
    ]

    print(f"   Script path: {TRANSCRIPTION_SCRIPT_PATH}")
    print(f"   Script exists: {os.path.exists(TRANSCRIPTION_SCRIPT_PATH)}")
    print(f"   Command: {' '.join(command[:3])} ... (API key redacted)")

    try:
        print(f"\n   Executing command...")
        # Execute the script with timeout
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)

        # Get all output
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        print(f"   ✓ Script executed successfully")
        print(f"   STDOUT length: {len(stdout)} chars")
        print(f"   STDERR length: {len(stderr)} chars")

        if stderr:
            print(f"   STDERR preview: {stderr[:200]}")
        print(f"   STDOUT preview: {stdout[:200]}")

        # The transcription text is typically the last line or contains "Transcription:"
        if "Transcription:" in stdout:
            # Extract the text after "Transcription: "
            for line in stdout.splitlines():
                if line.startswith('Transcription:'):
                    result_text = line.split(':', 1)[1].strip()
                    print(f"   Result found in 'Transcription:' line")
                    return result_text

        # If no "Transcription:" prefix, combine all non-empty lines
        # Remove "##" prefixes that Parakeet adds to intermediate results
        lines = []
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                # Remove "##" prefix from Parakeet intermediate transcriptions
                if line.startswith('##'):
                    line = line[2:].strip()
                if line:  # Only add non-empty lines
                    lines.append(line)

        if lines:
            # Join all lines to get the complete transcript
            result_text = ' '.join(lines)
            print(f"   Result found by combining {len(lines)} lines")
            return result_text

        print(f"   ⚠ No transcription text found in output")
        return "ASR script executed, but no transcription text was found in the output."

    except subprocess.TimeoutExpired:
        err_msg = f"ASR Error: Transcription script timed out (>60s)"
        print(f"   ✗ {err_msg}")
        return err_msg

    except subprocess.CalledProcessError as e:
        err_msg = f"ASR Error: Script failed with exit code {e.returncode}. STDERR: {e.stderr[:200]}"
        print(f"   ✗ {err_msg}")
        return err_msg

    except FileNotFoundError as e:
        err_msg = f"ASR Error: Script file not found: {TRANSCRIPTION_SCRIPT_PATH}"
        print(f"   ✗ {err_msg}")
        return err_msg

    except Exception as e:
        err_msg = f"ASR Error: An unexpected error occurred. {type(e).__name__}: {str(e)}"
        print(f"   ✗ {err_msg}")
        import traceback
        traceback.print_exc()
        return err_msg
    finally:
        print(f"   {'─'*76}\n")


@app.route('/stream-workflow', methods=['GET'])
def stream_workflow():
    """SSE endpoint for streaming workflow progress events"""
    def event_generator():
        # Create a queue for this client
        client_queue = queue.Queue(maxsize=100)

        # Register the queue
        with workflow_event_lock:
            workflow_event_queues.append(client_queue)

        # Track if client is still connected
        client_id = id(client_queue)
        print(f"✓ [/stream-workflow] Client connected (ID: {client_id}), total clients: {len(workflow_event_queues)}")

        try:
            # Send initial connection message
            print(f"✓ [/stream-workflow] Sending connection confirmation to client {client_id}")
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to workflow stream'})}\n\n"

            # Stream events from the queue
            while True:
                try:
                    # Get event from queue with timeout
                    event = client_queue.get(timeout=30)  # 30 second timeout for keep-alive
                    print(f"📨 [/stream-workflow] Sending event to client {client_id}: {event.get('type')} {event.get('agent')}")
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send keep-alive heartbeat
                    print(f"💓 [/stream-workflow] Sending heartbeat to client {client_id}")
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            # Clean up when client disconnects
            with workflow_event_lock:
                if client_queue in workflow_event_queues:
                    workflow_event_queues.remove(client_queue)
            print(f"❌ [/stream-workflow] Client disconnected (ID: {client_id}), remaining clients: {len(workflow_event_queues)}")

    return Response(event_generator(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })


@app.route('/transcribe', methods=['POST'])
def transcribe():
    # Temporary files are stored in the 'uploads' folder
    temp_dir = os.path.join(UPLOAD_FOLDER, os.urandom(8).hex())
    os.makedirs(temp_dir)

    uploaded_path = None

    try:
        print(f"\n{'='*80}")
        print("TRANSCRIBE REQUEST RECEIVED")
        print(f"{'='*80}")

        if 'audioFile' not in request.files:
            print("ERROR: No audioFile in request.files")
            print(f"Available files: {request.files.keys()}")
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audioFile']
        print(f"1. File received: {audio_file.filename} (type: {audio_file.content_type})")

        filename = secure_filename(audio_file.filename)
        uploaded_path = os.path.join(temp_dir, filename)

        # 1. Save the uploaded file
        print(f"2. Saving to: {uploaded_path}")
        audio_file.save(uploaded_path)

        if not os.path.exists(uploaded_path):
            raise RuntimeError(f"File failed to save: {uploaded_path}")

        file_size = os.path.getsize(uploaded_path)
        print(f"   ✓ File saved successfully ({file_size} bytes)")

        # 2. Convert to required format (mono, 16kHz) with fallback
        converted_path = uploaded_path
        converted_path_target = os.path.join(temp_dir, TEMP_WAV_FILE)

        # Try FFmpeg first
        print(f"3. Attempting FFmpeg conversion...")
        print(f"   Input: {uploaded_path}")
        print(f"   Output: {converted_path_target}")

        if convert_to_nvidia_format(uploaded_path, converted_path_target):
            converted_path = converted_path_target
            print(f"   ✓ FFmpeg conversion successful")
        else:
            # Fallback to pydub
            print(f"   ✗ FFmpeg conversion failed. Attempting pydub conversion...")
            if convert_audio_with_pydub(uploaded_path, converted_path_target):
                converted_path = converted_path_target
                print(f"   ✓ Pydub conversion successful")
            else:
                print(f"   ⚠ All conversions failed. Attempting direct transcription with original file...")
                # Continue with original file as last resort

        if not os.path.exists(converted_path):
            raise RuntimeError(f"Converted audio file not found: {converted_path}")

        converted_size = os.path.getsize(converted_path)
        print(f"   Converted file size: {converted_size} bytes")

        # 3. Run NVIDIA ASR with converted audio
        print(f"4. Starting NVIDIA ASR transcription...")
        print(f"   Script path: {TRANSCRIPTION_SCRIPT_PATH}")
        print(f"   Audio file: {converted_path}")
        transcription_result = run_nvidia_transcription(converted_path)
        print(f"   Transcription result: {transcription_result[:100]}...")

        # 4. Return the result
        if transcription_result.startswith("ASR Error"):
            print(f"ERROR: {transcription_result}")
            return jsonify({"error": transcription_result}), 500

        print(f"SUCCESS: Transcription completed")
        print(f"{'='*80}\n")
        return jsonify({"transcription": transcription_result}), 200

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"EXCEPTION in /transcribe: {type(e).__name__}: {str(e)}")
        print(f"{'='*80}")
        import traceback
        traceback.print_exc()
        print(f"{'='*80}\n")
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

    finally:
        # 5. Clean up the temporary folder and all its contents
        print(f"5. Cleaning up temporary directory: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"   ✓ Cleanup complete")


@app.route('/orchestrate', methods=['POST'])
def orchestrate():
    """
    Run the meeting orchestrator workflow on a transcript.

    Expects JSON body:
    {
        "transcript": "meeting transcript text",
        "auto_execute": true/false (optional, defaults to true)
    }

    Returns:
    {
        "planned_actions": [...],
        "execution_results": [...],
        "summary": "...",
        "calendar_events_count": N,
        "related_meetings_count": N
    }
    """
    try:
        # Parse request body
        data = request.get_json()

        if not data or 'transcript' not in data:
            return jsonify({"error": "No transcript provided in request body"}), 400

        transcript = data['transcript']
        auto_execute = data.get('auto_execute', True)  # Default to True

        if not transcript or len(transcript.strip()) == 0:
            return jsonify({"error": "Transcript is empty"}), 400

        print(f"Running orchestrator (auto_execute={auto_execute}, transcript length={len(transcript)})")

        # Run the orchestrator workflow (async) with event broadcasting
        result = asyncio.run(run_orchestrator(transcript, auto_execute, event_callback=broadcast_workflow_event))

        print(f"Orchestrator completed: {len(result['planned_actions'])} actions planned")

        return jsonify(result), 200

    except Exception as e:
        print(f"Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Orchestrator failed: {str(e)}",
            "details": traceback.format_exc()
        }), 500


if __name__ == '__main__':
    print(f"Starting ASR Backend Server on http://0.0.0.0:4000. Ensure ffmpeg is installed and API_KEY is set.")
    app.run(host='0.0.0.0', port=4000, debug=True, use_reloader=False)