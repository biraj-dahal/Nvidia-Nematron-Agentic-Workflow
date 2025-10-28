import os
import subprocess
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import shutil # Used for file cleanup

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app) 
UPLOAD_FOLDER = 'uploads'
TEMP_WAV_FILE = 'recording_16k_mono.wav'
# Full path to the NVIDIA script (adjust if your structure is different)
TRANSCRIPTION_SCRIPT_PATH = os.path.join(
    'python-clients', 'scripts', 'asr', 'transcribe_file.py'
)
# NVIDIA NIM details
NIM_SERVER = "grpc.nvcf.nvidia.com:443"
NIM_FUNCTION_ID = "71203149-d3b7-4460-8231-1be2543a1fca"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Ensure API Key is set
NVIDIA_API_KEY = os.environ.get("API_KEY")
if not NVIDIA_API_KEY:
    raise EnvironmentError("The API_KEY environment variable is not set. Please set it as per NVIDIA instructions.")


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

def run_nvidia_transcription(filepath):
    """Executes the NVIDIA ASR script and captures the transcription."""
    
    # Construct the command to execute the NVIDIA script
    command = [
        'python3', TRANSCRIPTION_SCRIPT_PATH,
        '--server', NIM_SERVER,
        '--use-ssl',
        
        # CORRECTED METADATA ARGUMENTS: Pass key and value as separate elements
        '--metadata', 'function-id', NIM_FUNCTION_ID, # 3 separate elements
        '--metadata', 'authorization', f'Bearer {NVIDIA_API_KEY}', # 3 separate elements
        
        '--input-file', filepath
    ]
    
    try:
     # Execute the script
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        
        # --- ORIGINAL (STRICT) PARSING ---
        # output_lines = result.stdout.strip().split('\n')
        # transcription_line = [line for line in output_lines if line.startswith('Transcription:')]
        # if transcription_line:
        #     # Extract the text after "Transcription: "
        #     return transcription_line[0].split(':', 1)[1].strip()
        # return "ASR script executed, but transcription text was not found in the output."
        
        # --- FIXED (EASY) PARSING ---
        # Get all non-error output, strip whitespace, and return the whole thing.
        # The transcription text is typically the last line.
        output = result.stdout.strip()
        
        # If the output is too long, just return the last line (most likely the transcription)
        if len(output.splitlines()) > 1:
            return output.splitlines()[-1].strip()
        
        return output if output else "ASR script executed, but no text output was received."
    
    except subprocess.CalledProcessError as e:
        print(f"NVIDIA Script Error: {e.stderr}")
        return f"ASR Error: Failed to run NVIDIA transcription script. {e.stderr}"
    except Exception as e:
        print(f"Unexpected ASR Error: {e}")
        return f"ASR Error: An unexpected error occurred. {e}"


@app.route('/transcribe', methods=['POST'])
def transcribe():
    # Temporary files are stored in the 'uploads' folder
    temp_dir = os.path.join(UPLOAD_FOLDER, os.urandom(8).hex())
    os.makedirs(temp_dir)
    
    uploaded_path = None
    converted_path = None
    
    try:
        if 'audioFile' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audioFile']
        filename = secure_filename(audio_file.filename)
        uploaded_path = os.path.join(temp_dir, filename)
        
        # 1. Save the uploaded file
        audio_file.save(uploaded_path)
        
        # 2. Convert to required format
        converted_path = os.path.join(temp_dir, TEMP_WAV_FILE)
        if not convert_to_nvidia_format(uploaded_path, converted_path):
            return jsonify({"error": "Failed to convert audio file using ffmpeg."}), 500
        
        # 3. Run NVIDIA ASR
        transcription_result = run_nvidia_transcription(converted_path)
        
        # 4. Return the result
        return jsonify({"transcription": transcription_result}), 200

    except Exception as e:
        print(f"Server-side error: {e}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        # 5. Clean up the temporary folder and all its contents
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    print(f"Starting ASR Backend Server on http://localhost:3000. Ensure ffmpeg is installed and API_KEY is set.")
    app.run(port=3000, debug=True)