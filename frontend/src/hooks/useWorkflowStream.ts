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
      console.log('🔌 [useWorkflowStream] Closing existing EventSource...');
      eventSourceRef.current.close();
    }

    try {
      console.log('🔌 [useWorkflowStream] Opening EventSource to /stream-workflow...');
      console.log('🔌 [useWorkflowStream] Current origin:', window.location.origin);

      // Use relative path so it routes through nginx proxy properly
      const backendUrl = '/stream-workflow';
      console.log('🔌 [useWorkflowStream] Connecting to backend via proxy:', backendUrl);
      const eventSource = new EventSource(backendUrl);

      // Flag to track if we've received first message (which indicates connection is working)
      let receivedFirstMessage = false;
      let messageCount = 0;

      eventSource.onopen = () => {
        console.log('✓ [useWorkflowStream] SSE onopen event fired');
        console.log('✓ [useWorkflowStream] EventSource readyState:', eventSource.readyState);
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        messageCount++;
        console.log(`🚨🚨🚨 [useWorkflowStream] MESSAGE HANDLER FIRED - Message #${messageCount}`);
        console.log(`📨 Data received:`, event.data.substring(0, 100));

        try {
          const data: WorkflowEvent = JSON.parse(event.data);
          console.log('✓ [useWorkflowStream] Parsed event:', data.type, 'Agent:', data.agent || 'N/A');

          // Mark connection as established on first message
          if (!receivedFirstMessage) {
            receivedFirstMessage = true;
            console.log('✓ [useWorkflowStream] First message received - connection is working!');
            setIsConnected(true);
            setError(null);
          }

          console.log('📨 [useWorkflowStream] Calling onEvent callback...');
          setLastEvent(data);
          onEvent(data);
          console.log('✓ [useWorkflowStream] onEvent callback executed');
        } catch (parseError) {
          console.error('❌ [useWorkflowStream] Error parsing SSE message:', parseError, 'Data:', event.data);
        }
      };

      eventSource.onerror = (err) => {
        console.error('❌ [useWorkflowStream] SSE connection error:', err);
        console.error('❌ [useWorkflowStream] EventSource readyState:', eventSource.readyState);
        console.error('❌ [useWorkflowStream] Total messages received before error:', messageCount);
        setIsConnected(false);

        if (eventSource.readyState === EventSource.CLOSED) {
          console.log('❌ [useWorkflowStream] Workflow stream disconnected');
          setError('Workflow stream disconnected');
          eventSource.close();
        }
      };

      eventSourceRef.current = eventSource;

      // Set connection to true immediately since we've successfully created the EventSource
      // The browser will establish the connection asynchronously
      console.log('✓ [useWorkflowStream] EventSource object created, readyState:', eventSource.readyState);
      console.log('✓ [useWorkflowStream] Setting isConnected to true');
      setIsConnected(true);
      setError(null);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect to workflow stream';
      console.error('❌ [useWorkflowStream] Failed to connect:', errorMsg);
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
