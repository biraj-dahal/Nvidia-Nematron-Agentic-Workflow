import { useEffect, useCallback, useRef, useState } from 'react';
import { WorkflowEvent } from '../types/workflow';

interface UseWorkflowStreamReturn {
  isConnected: boolean;
  lastEvent: WorkflowEvent | null;
  error: string | null;
  startStream: () => void;
  closeStream: () => void;
}

export const useWorkflowStream = (
  onEvent: (event: WorkflowEvent) => void,
): UseWorkflowStreamReturn => {
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WorkflowEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startStream = useCallback(() => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource('/stream-workflow');

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const data: WorkflowEvent = JSON.parse(event.data);
          setLastEvent(data);
          onEvent(data);
        } catch (parseError) {
          console.error('Error parsing SSE message:', parseError);
        }
      };

      eventSource.onerror = (err) => {
        console.error('SSE connection error:', err);
        setIsConnected(false);

        if (eventSource.readyState === EventSource.CLOSED) {
          setError('Workflow stream disconnected');
          eventSource.close();
        }
      };

      eventSourceRef.current = eventSource;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect to workflow stream';
      setError(errorMsg);
      setIsConnected(false);
    }
  }, [onEvent]);

  const closeStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      closeStream();
    };
  }, [closeStream]);

  return {
    isConnected,
    lastEvent,
    error,
    startStream,
    closeStream,
  };
};
