import { useState, useRef, useCallback } from 'react';
import { RecordingState } from '../types/workflow';

interface UseMediaRecorderReturn {
  recordingState: RecordingState;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  resetRecording: () => void;
}

export const useMediaRecorder = (): UseMediaRecorderReturn => {
  const [recordingState, setRecordingState] = useState<RecordingState>({
    isRecording: false,
    error: undefined,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      // Reset previous recording
      audioChunksRef.current = [];
      setRecordingState({ isRecording: true, error: undefined });

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;

      // Create media recorder
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      // Handle data available
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Start recording
      mediaRecorder.start();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start recording';
      setRecordingState({
        isRecording: false,
        error: `Error: ${errorMessage}. Make sure you allow microphone access.`,
      });
    }
  }, []);

  const stopRecording = useCallback(async (): Promise<void> => {
    return new Promise((resolve) => {
      const mediaRecorder = mediaRecorderRef.current;

      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        resolve();
        return;
      }

      mediaRecorder.onstop = () => {
        // Create blob from chunks
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);

        // Stop all tracks
        if (audioStreamRef.current) {
          audioStreamRef.current.getTracks().forEach((track) => track.stop());
        }

        // Update state
        setRecordingState({
          isRecording: false,
          audioUrl,
          mimeType,
          duration: audioBlob.size,
        });

        resolve();
      };

      mediaRecorder.stop();
    });
  }, []);

  const resetRecording = useCallback(() => {
    audioChunksRef.current = [];
    setRecordingState({ isRecording: false });
    if (recordingState.audioUrl) {
      URL.revokeObjectURL(recordingState.audioUrl);
    }
  }, [recordingState.audioUrl]);

  return {
    recordingState,
    startRecording,
    stopRecording,
    resetRecording,
  };
};
