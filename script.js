const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const statusMessage = document.getElementById('statusMessage');
const audioPlayback = document.getElementById('audioPlayback');

let mediaRecorder;
let audioChunks = [];
let audioStream;

// --- Functions to toggle buttons and status (No Change Needed Here) ---
function startRecordingUI() {
    startButton.classList.add('hidden');
    stopButton.classList.remove('hidden');
    statusMessage.textContent = 'Recording... (Click End Recording to stop)';
}

function stopRecordingUI(audioUrl) {
    startButton.classList.remove('hidden');
    stopButton.classList.add('hidden');
    statusMessage.textContent = 'Recording finished!';
    
    // Add audio playback element
    audioPlayback.innerHTML = `
        <p>Playback your recording:</p>
        <audio controls src="${audioUrl}"></audio>
    `;
}

function errorRecordingUI(error) {
    startButton.classList.remove('hidden');
    stopButton.classList.add('hidden');
    statusMessage.textContent = `Error: ${error.message}. Make sure you allow microphone access.`;
    console.error('Recording Error:', error);
}

// --- Recording Logic (FIX APPLIED HERE) ---

// 1. START RECORDING
startButton.addEventListener('click', async () => {
    // Clear previous recording and status
    audioChunks = [];
    audioPlayback.innerHTML = '';
    statusMessage.textContent = 'Requesting microphone access...';

    try {
        // Request microphone access
        audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Get the default MIME type supported by the browser for recording
        // If not specified, the browser will usually pick a good, supported format.
        // We ensure a default format like 'audio/webm' in the Blob creation if necessary.
        mediaRecorder = new MediaRecorder(audioStream);

        // Event handler for when data is available
        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        // Event handler for when recording stops
        mediaRecorder.onstop = () => {
         statusMessage.textContent = 'Processing recording for transcription...';
    
    const mimeType = mediaRecorder.mimeType || 'audio/webm';
    const audioBlob = new Blob(audioChunks, { type: mimeType });
    const audioUrl = URL.createObjectURL(audioBlob); 

    audioStream.getTracks().forEach(track => track.stop());

    // --- MAIN CHANGE: Call the transcription function ---
    transcribeAudio(audioBlob, audioUrl);
        };
async function transcribeAudio(audioBlob, audioUrl) {
    const formData = new FormData();
    // The server will save this file and rename/convert it later if needed
    formData.append('audioFile', audioBlob, 'recording.webm'); 

    try {
        // Send the audio file to your Flask backend
        const response = await fetch('http://localhost:3000/transcribe', { 
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();

        // Display results
        stopRecordingUI(audioUrl); 
        const transcriptionText = data.transcription || "Transcription failed or returned no text.";
        
        // Use innerHTML to allow for bold tag
        statusMessage.innerHTML += `<br><br><strong>NVIDIA ASR Result:</strong> ${transcriptionText}`;
        
    } catch (error) {
        errorRecordingUI(new Error("Failed to reach transcription service. Is the backend running on port 3000?"));
        console.error('Transcription Upload Error:', error);
    }
}
        // Start the recording
        mediaRecorder.start();
        startRecordingUI();

    } catch (error) {
        errorRecordingUI(error);
    }
});

// 2. STOP RECORDING
stopButton.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        statusMessage.textContent = 'Processing recording...';
    }
});