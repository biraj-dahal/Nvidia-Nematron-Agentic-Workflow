import os
import subprocess
import json
import asyncio
import base64
import httpx
import wave
import queue
import threading
import logging
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import shutil # Used for file cleanup

# Import orchestrator for meeting analysis
from orchestrator_agent import run_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
    logger.debug(f"Broadcasting {event_data.get('type')} for {event_data.get('agent')} to {len(workflow_event_queues)} clients")
    with workflow_event_lock:
        # Remove dead queues and broadcast to active ones
        dead_queues = []
        for i, q in enumerate(workflow_event_queues):
            try:
                q.put_nowait(event_data)
            except queue.Full:
                # Queue is full, mark for removal
                logger.warning(f"Queue full for client {i}, removing...")
                dead_queues.append(i)

        # Remove dead queues in reverse order to maintain indices
        for i in reversed(dead_queues):
            workflow_event_queues.pop(i)

        logger.debug(f"Broadcast complete: {len(workflow_event_queues)} active clients")


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
        logger.debug(f"Audio converted successfully: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("FFmpeg is not installed or not in PATH")
        return False


def run_nvidia_transcription(filepath):
    """Executes the NVIDIA ASR script using gRPC and captures the transcription."""

    logger.info(f"Starting transcription for: {filepath}")
    logger.debug(f"File exists: {os.path.exists(filepath)}, Size: {os.path.getsize(filepath) if os.path.exists(filepath) else 'N/A'} bytes")

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

    logger.debug(f"Script path: {TRANSCRIPTION_SCRIPT_PATH}, Exists: {os.path.exists(TRANSCRIPTION_SCRIPT_PATH)}")

    try:
        logger.info("Executing transcription script...")
        # Execute the script with timeout
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)

        # Get all output
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        logger.debug(f"Script output: stdout={len(stdout)} chars, stderr={len(stderr)} chars")

        if stderr:
            logger.debug(f"STDERR: {stderr[:200]}")

        # The transcription text is typically the last line or contains "Transcription:"
        if "Transcription:" in stdout:
            # Extract the text after "Transcription: "
            for line in stdout.splitlines():
                if line.startswith('Transcription:'):
                    result_text = line.split(':', 1)[1].strip()
                    logger.info(f"Transcription completed: {len(result_text)} chars")
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
            logger.info(f"Transcription completed: {len(result_text)} chars from {len(lines)} lines")
            return result_text

        logger.warning("No transcription text found in output")
        return "ASR script executed, but no transcription text was found in the output."

    except subprocess.TimeoutExpired:
        err_msg = "Transcription script timed out (>60s)"
        logger.error(err_msg)
        return f"ASR Error: {err_msg}"

    except subprocess.CalledProcessError as e:
        err_msg = f"Script failed with exit code {e.returncode}"
        logger.error(f"{err_msg}: {e.stderr[:200]}")
        return f"ASR Error: {err_msg}"

    except FileNotFoundError as e:
        err_msg = f"Script file not found: {TRANSCRIPTION_SCRIPT_PATH}"
        logger.error(err_msg)
        return f"ASR Error: {err_msg}"

    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
        return f"ASR Error: {type(e).__name__}: {str(e)}"


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
        logger.info(f"Client {client_id} connected, total clients: {len(workflow_event_queues)}")

        try:
            # Send initial connection message
            logger.info(f"Client {client_id} connected to workflow stream")
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to workflow stream'})}\n\n"

            # Stream events from the queue
            while True:
                try:
                    # Get event from queue with timeout
                    event = client_queue.get(timeout=30)  # 30 second timeout for keep-alive
                    logger.debug(f"Sending {event.get('type')} event for {event.get('agent')} to client {client_id}")
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send keep-alive heartbeat
                    logger.debug(f"Sending heartbeat to client {client_id}")
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            # Clean up when client disconnects
            with workflow_event_lock:
                if client_queue in workflow_event_queues:
                    workflow_event_queues.remove(client_queue)
            logger.info(f"Client {client_id} disconnected, remaining clients: {len(workflow_event_queues)}")

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
        logger.info("Transcribe request received")

        if 'audioFile' not in request.files:
            logger.error(f"No audioFile in request. Available: {list(request.files.keys())}")
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audioFile']
        logger.info(f"Audio file received: {audio_file.filename} ({audio_file.content_type})")

        filename = secure_filename(audio_file.filename)
        uploaded_path = os.path.join(temp_dir, filename)

        # 1. Save the uploaded file
        logger.debug(f"Saving audio to: {uploaded_path}")
        audio_file.save(uploaded_path)

        if not os.path.exists(uploaded_path):
            raise RuntimeError(f"File failed to save: {uploaded_path}")

        file_size = os.path.getsize(uploaded_path)
        logger.info(f"File saved: {file_size} bytes")

        # 2. Convert to required format (mono, 16kHz) with fallback
        converted_path = uploaded_path
        converted_path_target = os.path.join(temp_dir, TEMP_WAV_FILE)

        # Try FFmpeg first
        logger.info("Converting audio to 16kHz mono WAV format")
        if convert_to_nvidia_format(uploaded_path, converted_path_target):
            converted_path = converted_path_target
            logger.debug(f"Conversion successful, output: {os.path.getsize(converted_path)} bytes")
        else:
            # FFmpeg failed, attempt transcription with original file
            logger.warning("FFmpeg conversion failed, attempting transcription with original file")
            # Continue with original file as last resort

        if not os.path.exists(converted_path):
            raise RuntimeError(f"Converted audio file not found: {converted_path}")

        # 3. Run NVIDIA ASR with converted audio
        logger.info("Starting NVIDIA ASR transcription")
        transcription_result = run_nvidia_transcription(converted_path)

        # 4. Return the result
        if transcription_result.startswith("ASR Error"):
            logger.error(f"Transcription error: {transcription_result}")
            return jsonify({"error": transcription_result}), 500

        logger.info(f"Transcription completed: {len(transcription_result)} chars")
        return jsonify({"transcription": transcription_result}), 200

    except Exception as e:
        logger.error(f"Transcribe endpoint error: {type(e).__name__}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

    finally:
        # 5. Clean up the temporary folder and all its contents
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")


@app.route('/orchestrate', methods=['POST'])
def orchestrate():
    """
    Run the meeting orchestrator workflow on a transcript.
    Returns 202 Accepted immediately, then streams results via SSE /stream-workflow.

    Expects JSON body:
    {
        "transcript": "meeting transcript text",
        "auto_execute": true/false (optional, defaults to true)
    }

    Returns immediately with 202 Accepted:
    {
        "status": "started",
        "message": "Workflow initiated. Check /stream-workflow for real-time updates."
    }

    Results are streamed via SSE with final event:
    {
        "type": "workflow_complete",
        "agent": "N/A",
        "results": {
            "planned_actions": [...],
            "execution_results": [...],
            "summary": "...",
            "calendar_events_count": N,
            "related_meetings_count": N
        }
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

        logger.info(f"Orchestrator workflow started (auto_execute={auto_execute}, transcript length={len(transcript)})")

        # Start the workflow in a background thread (non-blocking)
        def run_workflow_background():
            try:
                result = asyncio.run(run_orchestrator(transcript, auto_execute, event_callback=broadcast_workflow_event))

                logger.info(f"Workflow completed: {len(result['planned_actions'])} actions planned, {len(result['execution_results'])} results")

                # Broadcast final completion event via SSE
                completion_event = {
                    "type": "workflow_complete",
                    "agent": "N/A",
                    "results": result
                }
                broadcast_workflow_event(completion_event)
                logger.info("Workflow completion event broadcasted")

            except Exception as e:
                logger.error(f"Workflow error: {type(e).__name__}: {str(e)}", exc_info=True)

                # Broadcast error event via SSE
                error_event = {
                    "type": "workflow_error",
                    "agent": "N/A",
                    "error": str(e),
                    "details": traceback.format_exc()
                }
                broadcast_workflow_event(error_event)

        # Start background thread (daemon=True so it won't prevent app shutdown)
        workflow_thread = threading.Thread(target=run_workflow_background, daemon=True)
        workflow_thread.start()

        # Return 202 Accepted immediately (don't wait for workflow)
        return jsonify({
            "status": "started",
            "message": "Workflow initiated. Check /stream-workflow for real-time updates."
        }), 202

    except Exception as e:
        logger.error(f"Orchestrate endpoint error: {type(e).__name__}: {str(e)}", exc_info=True)
        return jsonify({
            "error": f"Orchestrator request failed: {str(e)}",
            "details": traceback.format_exc()
        }), 500


if __name__ == '__main__':
    logger.info("Starting Flask backend server on http://0.0.0.0:4000")
    logger.info("Prerequisites: FFmpeg must be installed, API_KEY environment variable must be set")
    app.run(host='0.0.0.0', port=4000, debug=False, use_reloader=False)