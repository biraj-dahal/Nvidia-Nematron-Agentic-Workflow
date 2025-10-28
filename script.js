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

        // Display transcription in the transcription box
        const transcriptionBox = document.getElementById('transcriptionBox');
        const transcriptionTextEl = document.getElementById('transcriptionText');
        transcriptionBox.classList.remove('hidden');
        transcriptionTextEl.textContent = transcriptionText;

        statusMessage.textContent = 'Transcription complete! Running meeting analysis...';

        // Automatically call orchestrator
        callOrchestrator(transcriptionText);

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

// ============================================
// ORCHESTRATOR INTEGRATION
// ============================================

let currentTranscript = '';  // Store transcript for re-processing

async function callOrchestrator(transcript) {
    currentTranscript = transcript;
    const autoExecute = document.getElementById('autoExecuteToggle').checked;

    try {
        statusMessage.textContent = 'Analyzing meeting and planning actions...';

        const response = await fetch('http://localhost:3000/orchestrate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                transcript: transcript,
                auto_execute: autoExecute
            })
        });

        if (!response.ok) {
            throw new Error(`Orchestrator error: ${response.statusText}`);
        }

        const result = await response.json();

        // Display results
        displayOrchestratorResults(result, autoExecute);

    } catch (error) {
        statusMessage.textContent = `Orchestrator failed: ${error.message}`;
        console.error('Orchestrator Error:', error);
    }
}

function displayOrchestratorResults(result, autoExecute) {
    const resultsContainer = document.getElementById('orchestratorResults');
    resultsContainer.classList.remove('hidden');

    // Display planned actions
    displayPlannedActions(result.planned_actions);

    // Show/hide approval section based on auto_execute
    const approvalSection = document.getElementById('approvalSection');
    if (!autoExecute) {
        approvalSection.classList.remove('hidden');
        statusMessage.textContent = 'Review planned actions and approve to execute.';
    } else {
        approvalSection.classList.add('hidden');
    }

    // Display execution results (only if auto_execute was true)
    if (autoExecute && result.execution_results && result.execution_results.length > 0) {
        displayExecutionResults(result.execution_results);
    }

    // Display summary
    if (result.summary) {
        displaySummary(result.summary);
    }

    statusMessage.textContent = autoExecute
        ? 'Meeting analysis complete! ✓'
        : 'Meeting analyzed. Review actions above.';
}

function displayPlannedActions(actions) {
    const actionsGrid = document.getElementById('plannedActions');
    actionsGrid.innerHTML = '';  // Clear previous

    if (!actions || actions.length === 0) {
        actionsGrid.innerHTML = '<p class="no-actions">No actions planned for this meeting.</p>';
        return;
    }

    actions.forEach((action, index) => {
        const card = document.createElement('div');
        card.className = 'action-card';

        // Determine badge color and icon
        const badge = getActionBadge(action.action_type);

        // Format attendees
        const attendeesText = action.attendees && action.attendees.length > 0
            ? `<p><strong>Attendees:</strong> ${action.attendees.join(', ')}</p>`
            : '';

        card.innerHTML = `
            <div class="action-badge ${badge.class}">${badge.icon} ${badge.label}</div>
            <h4>${action.event_title || 'Action ' + (index + 1)}</h4>
            ${action.event_date ? `<p><strong>Date:</strong> ${action.event_date}</p>` : ''}
            ${action.duration_minutes ? `<p><strong>Duration:</strong> ${action.duration_minutes} minutes</p>` : ''}
            ${attendeesText}
            ${action.notes ? `<p><strong>Notes:</strong> ${action.notes}</p>` : ''}
            <p class="reasoning"><em>${action.reasoning}</em></p>
        `;

        actionsGrid.appendChild(card);
    });
}

function getActionBadge(actionType) {
    const badges = {
        'create_event': { icon: '📅', label: 'Create Event', class: 'badge-create' },
        'add_notes': { icon: '🗒️', label: 'Add Notes', class: 'badge-notes' },
        'find_available_slot': { icon: '🔍', label: 'Find Slot', class: 'badge-find' },
        'update_event': { icon: '✏️', label: 'Update Event', class: 'badge-update' }
    };
    return badges[actionType] || { icon: '📋', label: actionType, class: 'badge-default' };
}

function displayExecutionResults(results) {
    const executionSection = document.getElementById('executionSection');
    const resultsList = document.getElementById('executionResults');

    executionSection.classList.remove('hidden');
    resultsList.innerHTML = '';

    results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'result-item';

        // Check if result indicates success or error
        const isError = result.toLowerCase().includes('error') || result.toLowerCase().includes('failed');
        const icon = isError ? '❌' : '✅';
        const className = isError ? 'result-error' : 'result-success';

        item.className += ` ${className}`;
        item.innerHTML = `<span class="result-icon">${icon}</span> ${result}`;

        resultsList.appendChild(item);
    });
}

function displaySummary(summary) {
    const summarySection = document.getElementById('summarySection');
    const summaryContent = document.getElementById('summaryContent');

    summarySection.classList.remove('hidden');
    summaryContent.textContent = summary;
}

// Approval button handlers
document.getElementById('approveButton').addEventListener('click', async () => {
    const button = document.getElementById('approveButton');
    button.disabled = true;
    button.textContent = 'Executing...';

    statusMessage.textContent = 'Executing actions...';

    try {
        const response = await fetch('http://localhost:3000/orchestrate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                transcript: currentTranscript,
                auto_execute: true  // Force execution
            })
        });

        if (!response.ok) {
            throw new Error(`Execution error: ${response.statusText}`);
        }

        const result = await response.json();

        // Update display with execution results
        displayExecutionResults(result.execution_results);
        if (result.summary) {
            displaySummary(result.summary);
        }

        // Hide approval section
        document.getElementById('approvalSection').classList.add('hidden');

        statusMessage.textContent = 'Actions executed successfully! ✓';

    } catch (error) {
        statusMessage.textContent = `Execution failed: ${error.message}`;
        console.error('Execution Error:', error);
        button.disabled = false;
        button.textContent = '✓ Approve & Execute';
    }
});

document.getElementById('rejectButton').addEventListener('click', () => {
    document.getElementById('approvalSection').classList.add('hidden');
    statusMessage.textContent = 'Actions cancelled by user.';
});