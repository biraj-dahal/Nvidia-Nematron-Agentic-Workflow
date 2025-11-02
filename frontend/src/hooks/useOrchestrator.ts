import { useState, useCallback } from 'react';
import axios from 'axios';
import { OrchestratorResponse, OrchestrateRequest, TranscriptionResult } from '../types/workflow';

interface UseOrchestratorReturn {
  isLoading: boolean;
  error: string | null;
  result: OrchestratorResponse | null;
  transcribeAudio: (audioBlob: Blob) => Promise<string>;
  runOrchestrator: (transcript: string, autoExecute: boolean) => Promise<OrchestratorResponse | null>;
  setResultFromSSE: (result: OrchestratorResponse) => void;
  setErrorFromSSE: (error: string) => void;
  reset: () => void;
}

export const useOrchestrator = (): UseOrchestratorReturn => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OrchestratorResponse | null>(null);

  const transcribeAudio = useCallback(async (audioBlob: Blob): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('audioFile', audioBlob, 'recording.webm');

      const response = await axios.post<TranscriptionResult>('/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      return response.data.transcription;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Transcription failed';
      setError(`Transcription Error: ${errorMsg}`);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const runOrchestrator = useCallback(
    async (transcript: string, autoExecute: boolean): Promise<OrchestratorResponse | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const payload: OrchestrateRequest = {
          transcript,
          auto_execute: autoExecute,
        };

        // POST /orchestrate returns 202 Accepted immediately
        // Workflow runs in background and results are streamed via SSE
        const response = await axios.post<{ status: string; message: string } | OrchestratorResponse>(
          '/orchestrate',
          payload,
          { timeout: 30000 } // 30 second timeout (won't hit Cloudflare's 100s limit)
        );

        // Handle both 200 OK (legacy) and 202 Accepted (new immediate response)
        if (response.status === 202 || response.status === 200) {
          // For 202: workflow started, results will come via SSE
          // For 200: results are in response (backward compatibility)
          if (response.status === 200 && 'planned_actions' in response.data) {
            // Legacy response - has results immediately
            setResult(response.data as OrchestratorResponse);
            setIsLoading(false);
            return response.data as OrchestratorResponse;
          } else {
            // 202 Accepted - keep loading until SSE sends workflow_complete
            // setIsLoading stays true, will be updated when SSE receives workflow_complete
            console.log('✓ Workflow initiated (202 Accepted), waiting for results via SSE...');
            return null;
          }
        }
      } catch (err) {
        let errorMsg = 'Orchestration failed';
        let isTimeout = false;

        if (axios.isAxiosError(err)) {
          if (err.code === 'ECONNABORTED') {
            errorMsg = 'Request timeout (100s) - but workflow may still be running';
            isTimeout = true;
          } else if (err.response?.status === 524) {
            errorMsg = 'Cloudflare timeout (100s) - but workflow may still be running';
            isTimeout = true;
          } else {
            errorMsg = err.response?.data?.error || err.message;
          }
        } else if (err instanceof Error) {
          errorMsg = err.message;
        }

        // For timeout errors, show warning but keep loading
        // SSE may still deliver results
        if (isTimeout) {
          setError(`⚠️ ${errorMsg}`);
          // Keep isLoading=true to wait for SSE completion
          return null;
        } else {
          setError(`Orchestrator Error: ${errorMsg}`);
          setIsLoading(false);
          return null;
        }
      }
    },
    [],
  );

  // Add method to set result from SSE completion event
  const setResultFromSSE = useCallback((orchestratorResult: OrchestratorResponse) => {
    setResult(orchestratorResult);
    setIsLoading(false);
  }, []);

  // Add method to handle SSE workflow errors
  const setErrorFromSSE = useCallback((errorMessage: string) => {
    setError(`Workflow Error: ${errorMessage}`);
    setIsLoading(false);
  }, []);

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setResult(null);
  }, []);

  return {
    isLoading,
    error,
    result,
    transcribeAudio,
    runOrchestrator,
    setResultFromSSE,
    setErrorFromSSE,
    reset,
  };
};
