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
  Notes,
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
  const { workflow: workflowState, startWorkflow, handleWorkflowEvent, resetWorkflow } = useWorkflow();

  // Local state
  const [isTranscriptionExpanded, setIsTranscriptionExpanded] = useState(true);
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
  } = useMediaRecorder();

  // State for transcript
  const [transcript, setTranscript] = useState<string>('');

  const {
    isLoading: isTranscribing,
    error: orchestratorError,
    result: orchestratorResult,
    transcribeAudio,
    runOrchestrator,
    setResultFromSSE,
    setErrorFromSSE,
  } = useOrchestrator();

  // Callback for workflow stream events
  // NOTE: Don't include workflowState in dependency array - it would cause the callback
  // to be recreated every time state changes, which resets the EventSource connection
  const onWorkflowEvent = useCallback((event: any) => {
    console.log('📡 [App] Received SSE event:', event.type, event.agent || 'N/A');

    // Handle workflow completion event (from immediate response pattern)
    if (event.type === 'workflow_complete') {
      console.log('✅ [App] Workflow completed via SSE, setting results...');
      setResultFromSSE(event.results);
      setStatusMessage('Workflow completed successfully!');
      setShowResults(true);
      // Close stream after completion
      setTimeout(() => {
        stopStream();
      }, 1000);
      return;
    }

    // Handle workflow error event
    if (event.type === 'workflow_error') {
      console.log('❌ [App] Workflow error via SSE:', event.error);
      setErrorFromSSE(event.error);
      stopStream();
      return;
    }

    // Handle regular workflow events (stage_start, stage_complete, etc.)
    handleWorkflowEvent(event);
    console.log('📡 [App] handleWorkflowEvent called');
  }, [handleWorkflowEvent, setResultFromSSE, setErrorFromSSE, stopStream]);

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

  // Monitor workflow state changes (logging only on cards/agents change)
  useEffect(() => {
    if (workflowState.agentCards.length > 0 || workflowState.completedAgents.length > 0) {
      console.log('📊 [App] Workflow state changed:', {
        currentAgent: workflowState.currentAgent,
        agentCardsCount: workflowState.agentCards.length,
        completedAgentsCount: workflowState.completedAgents.length,
        agentCards: workflowState.agentCards.map(c => ({ name: c.agentName, status: c.status })),
        progress: Math.round(workflowState.progress),
      });
    }
  }, [workflowState.agentCards, workflowState.completedAgents, workflowState.currentAgent, workflowState.progress]);

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

      // Start workflow stream for real-time updates FIRST
      // This ensures the SSE connection is ready to receive events
      startStream();

      // Initialize workflow and show cards
      startWorkflow();
      setShowWorkflowViz(true);  // Show cards immediately
      setShowResults(false);

      // Start recording
      await startRecording();

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

      // Transcribe audio
      const transcriptionText = await transcribeAudio(audioData);

      if (!transcriptionText) {
        throw new Error('Transcription failed or returned empty text');
      }

      setTranscript(transcriptionText);
      setStatusMessage('Transcription complete. Analyzing meeting content...');

      // Show workflow visualization
      setShowWorkflowViz(true);

      // Run orchestrator with transcription - note: handleOrchestration is defined below
      // so we call it directly instead of including in dependencies
      await (async (transcriptionText: string) => {
        try {
          setStatusMessage('Running AI workflow...');
          setShowWorkflowViz(true);

          const result = await runOrchestrator(transcriptionText, autoExecute);

          // With the new 202 Accepted pattern:
          // - result will be null (workflow runs in background)
          // - Results will arrive via SSE event (workflow_complete)
          // - Don't need to do anything here, just wait for SSE

          if (result) {
            // Legacy 200 OK response (has results immediately)
            setStatusMessage('Workflow completed successfully!');
            setShowResults(true);

            // Stop stream after completion
            setTimeout(() => {
              stopStream();
            }, 1000);
          } else {
            // 202 Accepted response (workflow started, waiting for SSE)
            setStatusMessage('Workflow started. Processing in background...');
            // Results will be set when workflow_complete event arrives via SSE
          }

        } catch (err) {
          setError(`Orchestration failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
          setStatusMessage('');
          stopStream();
        }
      })(transcriptionText);

    } catch (err) {
      setError(`Transcription failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatusMessage('');
      stopStream();
    }
  }, [transcribeAudio, stopStream, runOrchestrator, autoExecute]);

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
    <Box
      sx={{
        minHeight: '100vh',
        backgroundImage: 'url(/nvidia-bg.webp)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundAttachment: 'fixed',
        backgroundColor: '#0a0a0a',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(10, 10, 10, 0.35)',
          zIndex: 0,
          pointerEvents: 'none',
        },
      }}
    >
      <CssBaseline />

      {/* App Bar */}
      <AppBar position="static" sx={{ backgroundColor: '#1a1a1a', position: 'relative', zIndex: 1 }}>
        <Toolbar>
          <Box
            component="img"
            src="/1.png"
            alt="NemoPM Logo"
            sx={{
              height: 60,
              width: 60,
              mr: 3,
              filter: 'drop-shadow(0 0 6px rgba(118, 185, 0, 0.6))',
            }}
          />
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 700 }}>
            NemoPM
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

      <Container maxWidth="xl" sx={{ py: 4, position: 'relative', zIndex: 1 }}>
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
          <Paper sx={{
            p: 3,
            mb: 3,
            backgroundColor: 'rgba(26, 26, 26, 0.4)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            border: '1px solid rgba(118, 185, 0, 0.2)',
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
            '&:hover': {
              backgroundColor: 'rgba(26, 26, 26, 0.6)',
              borderColor: 'rgba(118, 185, 0, 0.4)',
            },
          }}>
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
            backgroundColor: 'rgba(26, 26, 26, 0.4)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            border: '2px solid rgba(118, 185, 0, 0.3)',
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
            '&:hover': {
              backgroundColor: 'rgba(26, 26, 26, 0.6)',
              borderColor: 'rgba(118, 185, 0, 0.4)',
            },
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
        {transcript && (
          <Paper sx={{
            p: 3,
            mb: 4,
            backgroundColor: 'rgba(26, 26, 26, 0.4)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            border: '1px solid rgba(118, 185, 0, 0.2)',
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
            '&:hover': {
              backgroundColor: 'rgba(26, 26, 26, 0.6)',
              borderColor: 'rgba(118, 185, 0, 0.4)',
            },
          }}>
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 2,
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
              onClick={() => setIsTranscriptionExpanded(!isTranscriptionExpanded)}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Notes sx={{ fontSize: 24, color: '#76B900' }} />
                <Typography variant="h6" sx={{ color: '#76B900', fontWeight: 600 }}>
                  Transcription
                </Typography>
              </Box>
              <IconButton size="small">
                {isTranscriptionExpanded ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>
            <Collapse in={isTranscriptionExpanded}>
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
