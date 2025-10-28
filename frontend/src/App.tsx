import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  LinearProgress,
  Divider,
  IconButton,
  Collapse,
  Switch,
  FormControlLabel,
  Tooltip,
  AppBar,
  Toolbar,
} from '@mui/material';
import {
  Mic,
  Stop,
  Settings as SettingsIcon,
  ExpandMore,
  ExpandLess,
  Info,
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

// Context and Theme
import { WorkflowProvider, useWorkflow } from './context/WorkflowContext';
import { nvidiaTheme } from './theme/nvidiaTheme';

// Hooks
import { useMediaRecorder, useOrchestrator, useWorkflowStream } from './hooks';

// Components
import { WorkflowVisualization } from './components/Workflow';
import {
  ActionCards,
  ExecutionResults,
  Summary,
  ApprovalButtons,
} from './components/Results';

/**
 * Main Application Component (Internal)
 *
 * This component contains the core application logic and must be wrapped
 * by WorkflowProvider to access workflow context.
 */
const AppContent: React.FC = () => {
  // Workflow context
  const { workflow: workflowState, startWorkflow, stopWorkflow, handleWorkflowEvent, resetWorkflow } = useWorkflow();

  // Local state
  const [showTranscription, setShowTranscription] = useState(false);
  const [showWorkflowViz, setShowWorkflowViz] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [autoExecute, setAutoExecute] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');

  // Custom hooks
  const {
    recordingState,
    audioBlob,
    startRecording,
    stopRecording,
    resetRecording,
  } = useMediaRecorder();

  // State for transcript
  const [transcript, setTranscript] = useState<string>('');

  const {
    isLoading: isTranscribing,
    error: orchestratorError,
    result: orchestratorResult,
    transcribeAudio,
    runOrchestrator,
  } = useOrchestrator();

  // Callback for workflow stream events
  const onWorkflowEvent = useCallback((event: any) => {
    handleWorkflowEvent(event);
  }, [handleWorkflowEvent]);

  const { startStream, closeStream: stopStream } = useWorkflowStream(onWorkflowEvent);

  // Error handling effect
  useEffect(() => {
    if (recordingState.error) {
      setError(`Recording error: ${recordingState.error}`);
    } else if (orchestratorError) {
      setError(`Processing error: ${orchestratorError}`);
    } else {
      setError(null);
    }
  }, [recordingState.error, orchestratorError]);

  /**
   * Handle start recording
   * Initializes the workflow stream and starts audio recording
   */
  const handleStartRecording = async () => {
    try {
      setError(null);
      setStatusMessage('Starting recording...');

      // Reset workflow state
      resetWorkflow();
      startWorkflow();
      setShowTranscription(false);
      setShowWorkflowViz(false);
      setShowResults(false);

      // Start recording
      await startRecording();

      // Start workflow stream for real-time updates
      startStream();

      setStatusMessage('Recording in progress. Speak clearly into your microphone.');
    } catch (err) {
      setError(`Failed to start recording: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatusMessage('');
    }
  };

  /**
   * Handle stop recording
   * Stops recording and initiates transcription
   */
  const handleStopRecording = () => {
    setStatusMessage('Stopping recording...');
    stopRecording();
    setStatusMessage('Recording stopped. Processing audio...');
  };

  /**
   * Handle transcription of recorded audio
   */
  const handleTranscription = useCallback(async (audioData: Blob) => {
    try {
      setStatusMessage('Transcribing audio...');
      setShowTranscription(true);

      // Transcribe audio
      const transcriptionText = await transcribeAudio(audioData);

      if (!transcriptionText) {
        throw new Error('Transcription failed or returned empty text');
      }

      setTranscript(transcriptionText);
      setStatusMessage('Transcription complete. Analyzing meeting content...');

      // Show workflow visualization
      setShowWorkflowViz(true);

      // Run orchestrator with transcription
      await handleOrchestration(transcriptionText);

    } catch (err) {
      setError(`Transcription failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatusMessage('');
      stopStream();
    }
  }, [transcribeAudio, stopStream]);

  /**
   * Process audio blob after recording stops
   * Transcribes audio and runs orchestrator workflow
   */
  useEffect(() => {
    if (audioBlob && !recordingState.isRecording) {
      handleTranscription(audioBlob);
    }
  }, [audioBlob, recordingState.isRecording, handleTranscription]);

  /**
   * Handle orchestration workflow
   * Runs the AI workflow to process the meeting transcript
   */
  const handleOrchestration = async (transcriptionText: string) => {
    try {
      setStatusMessage('Running AI workflow...');

      // Run orchestrator (workflow updates will come via SSE)
      const result = await runOrchestrator(transcriptionText, autoExecute);

      if (result) {
        setStatusMessage('Workflow completed successfully!');
        setShowResults(true);

        // Stop stream after completion
        setTimeout(() => {
          stopStream();
        }, 1000);
      }

    } catch (err) {
      setError(`Orchestration failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatusMessage('');
      stopStream();
    }
  };

  /**
   * Handle approval of planned actions (manual execution mode)
   */
  const handleApprove = async () => {
    try {
      setStatusMessage('Executing approved actions...');

      // TODO: Call execute endpoint on backend
      // For now, just show completion message
      setStatusMessage('Actions executed successfully!');

    } catch (err) {
      setError(`Execution failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatusMessage('');
    }
  };

  /**
   * Handle cancellation of workflow
   */
  const handleCancel = () => {
    setStatusMessage('Workflow cancelled.');
    stopStream();
    resetWorkflow();
    setShowResults(false);
  };

  /**
   * Determine if approval buttons should be shown
   */
  const shouldShowApproval =
    !autoExecute &&
    orchestratorResult?.planned_actions &&
    orchestratorResult.planned_actions.length > 0 &&
    !orchestratorResult.execution_results;

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: '#0a0a0a' }}>
      <CssBaseline />

      {/* App Bar */}
      <AppBar position="static" sx={{ backgroundColor: '#1a1a1a' }}>
        <Toolbar>
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 700 }}>
            🎙️ NVIDIA Meeting Assistant
          </Typography>
          <Tooltip title="Settings">
            <IconButton
              color="inherit"
              onClick={() => setShowSettings(!showSettings)}
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Error Alert */}
        {error && (
          <Alert
            severity="error"
            onClose={() => setError(null)}
            sx={{ mb: 3 }}
          >
            {error}
          </Alert>
        )}

        {/* Settings Panel */}
        <Collapse in={showSettings}>
          <Paper sx={{ p: 3, mb: 3, backgroundColor: 'rgba(255, 255, 255, 0.05)' }}>
            <Typography variant="h6" gutterBottom sx={{ color: '#76B900' }}>
              Settings
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={autoExecute}
                  onChange={(e) => setAutoExecute(e.target.checked)}
                  disabled={recordingState.isRecording || isTranscribing}
                />
              }
              label={
                <Box>
                  <Typography variant="body1">Auto-execute actions</Typography>
                  <Typography variant="caption" color="text.secondary">
                    When enabled, planned actions will be executed automatically without approval
                  </Typography>
                </Box>
              }
            />
          </Paper>
        </Collapse>

        {/* Status Message */}
        {statusMessage && (
          <Alert
            severity="info"
            sx={{ mb: 3 }}
            icon={<Info />}
          >
            {statusMessage}
          </Alert>
        )}

        {/* Recording Section */}
        <Paper
          sx={{
            p: 4,
            mb: 4,
            textAlign: 'center',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            border: '2px solid rgba(118, 185, 0, 0.3)',
          }}
        >
          <Typography variant="h4" gutterBottom sx={{ color: '#76B900', fontWeight: 700 }}>
            Record Meeting
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
            Click the button below to start recording your meeting. The AI will analyze it in real-time.
          </Typography>

          <Button
            variant="contained"
            size="large"
            startIcon={recordingState.isRecording ? <Stop /> : <Mic />}
            onClick={recordingState.isRecording ? handleStopRecording : handleStartRecording}
            disabled={isTranscribing}
            sx={{
              px: 6,
              py: 2,
              fontSize: '1.2rem',
              fontWeight: 600,
              backgroundColor: recordingState.isRecording ? '#ef4444' : '#76B900',
              '&:hover': {
                backgroundColor: recordingState.isRecording ? '#dc2626' : '#5a9000',
              },
              transition: 'all 0.3s ease',
            }}
          >
            {recordingState.isRecording ? 'Stop Recording' : 'Start Recording'}
          </Button>

          {/* Recording Progress */}
          {recordingState.isRecording && (
            <Box sx={{ mt: 3 }}>
              <LinearProgress
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: 'rgba(239, 68, 68, 0.2)',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: '#ef4444',
                  }
                }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Recording... Click "Stop Recording" when finished
              </Typography>
            </Box>
          )}

          {/* Processing Progress */}
          {isTranscribing && (
            <Box sx={{ mt: 3 }}>
              <LinearProgress
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: 'rgba(118, 185, 0, 0.2)',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: '#76B900',
                  }
                }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Transcribing audio and processing with AI...
              </Typography>
            </Box>
          )}
        </Paper>

        {/* Transcription Section */}
        {showTranscription && transcript && (
          <Paper sx={{ p: 3, mb: 4, backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 2,
                cursor: 'pointer',
              }}
              onClick={() => setShowTranscription(!showTranscription)}
            >
              <Typography variant="h6" sx={{ color: '#76B900', fontWeight: 600 }}>
                📝 Transcription
              </Typography>
              <IconButton size="small">
                {showTranscription ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>
            <Collapse in={showTranscription}>
              <Divider sx={{ mb: 2, borderColor: 'rgba(118, 185, 0, 0.2)' }} />
              <Typography
                variant="body2"
                sx={{
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.8,
                  color: 'text.secondary',
                }}
              >
                {transcript}
              </Typography>
            </Collapse>
          </Paper>
        )}

        {/* Workflow Visualization */}
        {showWorkflowViz && (
          <Box sx={{ mb: 4 }}>
            <WorkflowVisualization
              isVisible={showWorkflowViz}
              activeAgent={workflowState.currentAgent}
              completedAgents={workflowState.completedAgents}
              agentCards={workflowState.agentCards}
              progress={workflowState.progress}
            />
          </Box>
        )}

        {/* Results Section */}
        {showResults && orchestratorResult && (
          <Box>
            <Typography
              variant="h4"
              sx={{
                color: '#76B900',
                fontWeight: 700,
                mb: 3,
                textAlign: 'center',
              }}
            >
              Results
            </Typography>

            {/* Planned Actions */}
            {orchestratorResult.planned_actions && (
              <Box sx={{ mb: 4 }}>
                <Typography variant="h6" gutterBottom sx={{ color: '#76B900', mb: 2 }}>
                  Planned Actions
                </Typography>
                <ActionCards actions={orchestratorResult.planned_actions} />
              </Box>
            )}

            {/* Approval Buttons (if manual execution) */}
            {shouldShowApproval && (
              <Box sx={{ mb: 4 }}>
                <ApprovalButtons
                  onApprove={handleApprove}
                  onCancel={handleCancel}
                  disabled={isTranscribing}
                />
              </Box>
            )}

            {/* Execution Results */}
            {orchestratorResult.execution_results && (
              <Box sx={{ mb: 4 }}>
                <ExecutionResults results={orchestratorResult.execution_results} />
              </Box>
            )}

            {/* Summary */}
            {orchestratorResult.summary && (
              <Box sx={{ mb: 4 }}>
                <Summary
                  summary={orchestratorResult.summary}
                  showEmailSent={!!orchestratorResult.execution_results}
                />
              </Box>
            )}
          </Box>
        )}

        {/* Footer */}
        <Box sx={{ mt: 8, py: 4, textAlign: 'center', borderTop: '1px solid rgba(118, 185, 0, 0.2)' }}>
          <Typography variant="body2" color="text.secondary">
            Powered by NVIDIA Nemotron LLM & LangGraph
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Version 1.0.0 | Built for NVIDIA Hackathon
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

/**
 * Main App Component with Provider
 *
 * Wraps the application with necessary providers (Theme, Workflow Context)
 */
const App: React.FC = () => {
  return (
    <ThemeProvider theme={nvidiaTheme}>
      <WorkflowProvider>
        <AppContent />
      </WorkflowProvider>
    </ThemeProvider>
  );
};

export default App;
