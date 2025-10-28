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
    with workflow_event_lock:
        # Remove dead queues and broadcast to active ones
        dead_queues = []
        for i, q in enumerate(workflow_event_queues):
            try:
                q.put_nowait(event_data)
            except queue.Full:
                # Queue is full, mark for removal
                dead_queues.append(i)

        # Remove dead queues in reverse order to maintain indices
        for i in reversed(dead_queues):
            workflow_event_queues.pop(i)


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

    try:
        print(f"Running transcription command: {' '.join(command)}")
        # Execute the script
        result = subprocess.run(command, check=True, capture_output=True, text=True)

        # Get all output
        output = result.stdout.strip()
        print(f"Transcription output:\n{output}")

        # The transcription text is typically the last line or contains "Transcription:"
        if "Transcription:" in output:
            # Extract the text after "Transcription: "
            for line in output.splitlines():
                if line.startswith('Transcription:'):
                    return line.split(':', 1)[1].strip()

        # If no "Transcription:" prefix, combine all non-empty lines
        # Remove "##" prefixes that Parakeet adds to intermediate results
        lines = []
        for line in output.splitlines():
            line = line.strip()
            if line:
                # Remove "##" prefix from Parakeet intermediate transcriptions
                if line.startswith('##'):
                    line = line[2:].strip()
                lines.append(line)

        if lines:
            # Join all lines to get the complete transcript
            return ' '.join(lines)

        return "ASR script executed, but no transcription text was found in the output."

    except subprocess.CalledProcessError as e:
        print(f"NVIDIA Script Error: {e.stderr}")
        return f"ASR Error: Failed to run NVIDIA transcription script. {e.stderr}"
    except Exception as e:
        print(f"Unexpected ASR Error: {e}")
        import traceback
        traceback.print_exc()
        return f"ASR Error: An unexpected error occurred. {e}"


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

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to workflow stream'})}\n\n"

            # Stream events from the queue
            while True:
                try:
                    # Get event from queue with timeout
                    event = client_queue.get(timeout=30)  # 30 second timeout for keep-alive
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send keep-alive heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            # Clean up when client disconnects
            with workflow_event_lock:
                if client_queue in workflow_event_queues:
                    workflow_event_queues.remove(client_queue)

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
        if 'audioFile' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audioFile']
        filename = secure_filename(audio_file.filename)
        uploaded_path = os.path.join(temp_dir, filename)

        # 1. Save the uploaded file
        print(f"Saving uploaded audio file: {filename}")
        audio_file.save(uploaded_path)

        # 2. Convert to required format (mono, 16kHz) with fallback
        converted_path = uploaded_path
        converted_path_target = os.path.join(temp_dir, TEMP_WAV_FILE)

        # Try FFmpeg first
        print("Attempting FFmpeg conversion...")
        if convert_to_nvidia_format(uploaded_path, converted_path_target):
            converted_path = converted_path_target
            print("✓ FFmpeg conversion successful")
        else:
            # Fallback to pydub
            print("FFmpeg conversion failed. Attempting pydub conversion...")
            if convert_audio_with_pydub(uploaded_path, converted_path_target):
                converted_path = converted_path_target
                print("✓ Pydub conversion successful")
            else:
                print("⚠ All conversions failed. Attempting direct transcription with original file...")
                # Continue with original file as last resort

        # 3. Run NVIDIA ASR with converted audio
        print(f"Starting NVIDIA ASR transcription...")
        transcription_result = run_nvidia_transcription(converted_path)

        # 4. Return the result
        if transcription_result.startswith("ASR Error"):
            return jsonify({"error": transcription_result}), 500

        return jsonify({"transcription": transcription_result}), 200

    except Exception as e:
        print(f"Server-side error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        # 5. Clean up the temporary folder and all its contents
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


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
    print(f"Starting ASR Backend Server on http://localhost:5000. Ensure ffmpeg is installed and API_KEY is set.")
    app.run(port=5000, debug=True)