import React, { createContext, useContext, useState, useCallback } from 'react';
import { WorkflowState, AgentCardState, WorkflowEvent, AGENT_NAMES } from '../types/workflow';

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
      agentCards: AGENT_NAMES.map((name) => ({
        agentName: name,
        status: 'pending',
        description: '',
        expanded: false,
      })),
    }));
  }, []);

  const stopWorkflow = useCallback(() => {
    setWorkflow((prev) => ({
      ...prev,
      isRunning: false,
    }));
  }, []);

  const handleWorkflowEvent = useCallback((event: WorkflowEvent) => {
    const { type, agent, description, status } = event;
    console.log('🔄 [State Update]', type, agent || 'N/A');

    if (type === 'stage_start' && agent) {
      setWorkflow((prev) => ({
        ...prev,
        currentAgent: agent,
        agentCards: prev.agentCards.map((card) =>
          card.agentName === agent
            ? { ...card, status: 'active', description: description || 'Processing...', expanded: true }
            : card,
        ),
      }));
    } else if (type === 'stage_complete' && agent) {
      setWorkflow((prev) => {
        const completedCount = prev.completedAgents.length + 1;
        const newProgress = (completedCount / AGENT_NAMES.length) * 100;

        return {
          ...prev,
          currentAgent: null,
          completedAgents: [...prev.completedAgents, agent],
          progress: newProgress,
          agentCards: prev.agentCards.map((card) =>
            card.agentName === agent
              ? { ...card, status: 'completed', expanded: false }
              : card,
          ),
        };
      });
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
