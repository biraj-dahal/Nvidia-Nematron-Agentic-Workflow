import React from 'react';
import { Box, Paper } from '@mui/material';
import { TimelineBar } from './TimelineBar';
import { AgentCard } from './AgentCard';
import { AgentCardState } from '../../types/workflow';

interface WorkflowVisualizationProps {
  isVisible: boolean;
  activeAgent: string | null;
  completedAgents: string[];
  agentCards: AgentCardState[];
  progress: number;
}

export const WorkflowVisualization: React.FC<WorkflowVisualizationProps> = ({
  isVisible,
  activeAgent,
  completedAgents,
  agentCards,
  progress,
}) => {
  if (!isVisible) {
    return null;
  }

  return (
    <Paper
      sx={{
        marginY: 3,
        padding: 3,
        backgroundColor: '#0a0a0a',
        border: '2px solid #76B900',
        borderRadius: '10px',
        maxWidth: '1200px',
        marginLeft: 'auto',
        marginRight: 'auto',
      }}
    >
      {/* Timeline Bar at Top */}
      <TimelineBar activeAgent={activeAgent} completedAgents={completedAgents} progress={progress} />

      {/* Agent Cards */}
      <Box
        sx={{
          marginTop: 3,
          maxHeight: '600px',
          overflowY: 'auto',
          paddingRight: 1,
          '&::-webkit-scrollbar': {
            width: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#1a1a1a',
            borderRadius: '3px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#76B900',
            borderRadius: '3px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#92e000',
          },
        }}
      >
        {agentCards.map((card) => (
          <AgentCard
            key={card.agentName}
            agentName={card.agentName}
            status={card.status}
            description={card.description}
            expanded={card.expanded}
          />
        ))}
      </Box>
    </Paper>
  );
};
