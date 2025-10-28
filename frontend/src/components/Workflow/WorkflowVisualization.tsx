import React, { useMemo } from 'react';
import { Box, Paper } from '@mui/material';
import { TimelineBar } from './TimelineBar';
import { AgentCard } from './AgentCard';
import { AgentCardState } from '../../types/workflow';
import { AGENT_NAMES } from '../../types/workflow';

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
  // Sort cards to match the order in AGENT_NAMES (timeline order)
  const sortedCards = useMemo(() => {
    const cardMap = new Map(agentCards.map(card => [card.agentName, card]));
    return AGENT_NAMES
      .map(agentName => cardMap.get(agentName))
      .filter((card) => card !== undefined) as AgentCardState[];
  }, [agentCards]);

  console.log('🎨 [WorkflowVisualization] Props received:', {
    isVisible,
    activeAgent,
    completedAgents,
    agentCardsCount: agentCards.length,
    sortedCardsCount: sortedCards.length,
    agentCards: sortedCards.map(c => ({ name: c.agentName, status: c.status })),
    progress,
  });

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
        {sortedCards.map((card) => (
          <AgentCard
            key={card.agentName}
            agentName={card.agentName}
            status={card.status}
            description={card.description}
            logs={card.logs}
          />
        ))}
      </Box>
    </Paper>
  );
};
