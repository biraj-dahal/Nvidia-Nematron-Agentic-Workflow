import { useState, useCallback } from 'react';
import axios from 'axios';
import { OrchestratorResponse, OrchestrateRequest, TranscriptionResult } from '../types/workflow';

interface UseOrchestratorReturn {
  isLoading: boolean;
  error: string | null;
  result: OrchestratorResponse | null;
  transcribeAudio: (audioBlob: Blob) => Promise<string>;
  runOrchestrator: (transcript: string, autoExecute: boolean) => Promise<OrchestratorResponse | null>;
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

        const response = await axios.post<OrchestratorResponse>('/orchestrate', payload);

        setResult(response.data);
        return response.data;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Orchestration failed';
        setError(`Orchestrator Error: ${errorMsg}`);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

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
    reset,
  };
};
