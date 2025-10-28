import React, { createContext, useContext, useState, useCallback } from 'react';
import { WorkflowState, WorkflowEvent, AGENT_NAMES } from '../types/workflow';

interface WorkflowContextType {
  workflow: WorkflowState;
  startWorkflow: () => void;
  stopWorkflow: () => void;
  handleWorkflowEvent: (event: WorkflowEvent) => void;
  resetWorkflow: () => void;
}

const initialWorkflowState: WorkflowState = {
  isRunning: false,
  currentAgent: null,
  completedAgents: [],
  agentCards: [],
  progress: 0,
};

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [workflow, setWorkflow] = useState<WorkflowState>(initialWorkflowState);

  const startWorkflow = useCallback(() => {
    setWorkflow((prev) => ({
      ...prev,
      isRunning: true,
      agentCards: [], // Start with empty cards - add them as agents start
    }));
  }, []);

  const stopWorkflow = useCallback(() => {
    setWorkflow((prev) => ({
      ...prev,
      isRunning: false,
    }));
  }, []);

  const handleWorkflowEvent = useCallback((event: WorkflowEvent) => {
    const { type, agent, description, logs: eventLogs } = event;
    console.log('🔄 [WorkflowContext] ========== EVENT RECEIVED ==========');
    console.log(`🔄 [WorkflowContext] Type: ${type} | Agent: ${agent || 'N/A'}`);
    console.log(`🔄 [WorkflowContext] Description: ${description || 'N/A'}`);
    if (eventLogs && eventLogs.length > 0) {
      console.log(`🔄 [WorkflowContext] Logs included: ${eventLogs.length} entries`);
    }

    // Handle log updates for any event (append logs to existing card)
    if (eventLogs && eventLogs.length > 0 && agent) {
      setWorkflow((prev) => {
        const updated: WorkflowState = {
          ...prev,
          agentCards: prev.agentCards.map((card) =>
            card.agentName === agent
              ? { ...card, logs: [...card.logs, ...eventLogs] }
              : card,
          ),
        };
        return updated;
      });
    }

    if (type === 'stage_start' && agent) {
      console.log(`🔄 [WorkflowContext] ✅ STAGE_START: Creating card for "${agent}"`);
      setWorkflow((prev) => {
        const cardExists = prev.agentCards.some(c => c.agentName === agent);
        console.log(`🔄 [WorkflowContext] Current cards: ${prev.agentCards.length} | Card exists: ${cardExists}`);

        // If card doesn't exist, create it; otherwise update existing card
        const updatedCards = cardExists
          ? prev.agentCards.map((card) =>
              card.agentName === agent
                ? {
                    ...card,
                    status: 'active' as const,
                    description: description || 'Processing...',
                    expanded: true,
                    logs: description ? [...card.logs] : card.logs, // Keep existing logs
                  }
                : card,
            )
          : [
              ...prev.agentCards,
              {
                agentName: agent,
                status: 'active' as const,
                description: description || 'Processing...',
                expanded: true,
                logs: [], // Initialize empty logs for new card
              },
            ];

        const updated: WorkflowState = {
          ...prev,
          currentAgent: agent,
          agentCards: updatedCards,
        };

        console.log(`🔄 [WorkflowContext] ✨ STATE UPDATED - Cards: ${updated.agentCards.length}, Active: "${updated.currentAgent}"`);
        console.log(`🔄 [WorkflowContext] Card details:`, updated.agentCards.map(c => ({ name: c.agentName, status: c.status, logs: c.logs.length })));

        return updated;
      });
    } else if (type === 'stage_complete' && agent) {
      console.log(`🔄 [WorkflowContext] ✅ STAGE_COMPLETE: Marking "${agent}" as completed`);
      setWorkflow((prev) => {
        const completedCount = prev.completedAgents.length + 1;
        const newProgress = (completedCount / AGENT_NAMES.length) * 100;

        const updated: WorkflowState = {
          ...prev,
          currentAgent: null,
          completedAgents: [...prev.completedAgents, agent],
          progress: newProgress,
          agentCards: prev.agentCards.map((card) =>
            card.agentName === agent
              ? {
                  ...card,
                  status: 'completed' as const,
                  expanded: true, // Keep expanded so user can view logs - don't auto-collapse!
                  // Keep logs from completion event if provided
                  logs: eventLogs && eventLogs.length > 0 ? [...card.logs, ...eventLogs] : card.logs,
                }
              : card,
          ),
        };

        console.log(`🔄 [WorkflowContext] ✨ STATE UPDATED - Completed: ${updated.completedAgents.length}/${AGENT_NAMES.length}, Progress: ${Math.round(newProgress)}%`);
        console.log(`🔄 [WorkflowContext] Completed agents:`, updated.completedAgents);

        return updated;
      });
    } else {
      console.log(`🔄 [WorkflowContext] ℹ️ Event type not handled: ${type}`);
    }
  }, []);

  const resetWorkflow = useCallback(() => {
    setWorkflow(initialWorkflowState);
  }, []);

  const value: WorkflowContextType = {
    workflow,
    startWorkflow,
    stopWorkflow,
    handleWorkflowEvent,
    resetWorkflow,
  };

  return <WorkflowContext.Provider value={value}>{children}</WorkflowContext.Provider>;
};

export const useWorkflow = (): WorkflowContextType => {
  const context = useContext(WorkflowContext);
  if (!context) {
    throw new Error('useWorkflow must be used within WorkflowProvider');
  }
  return context;
};
