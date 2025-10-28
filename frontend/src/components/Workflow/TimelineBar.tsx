import React, { useMemo } from 'react';
import { Box, Paper } from '@mui/material';
import { AGENT_NAMES } from '../../types/workflow';

interface TimelineBarProps {
  activeAgent: string | null;
  completedAgents: string[];
  progress: number;
}

export const TimelineBar: React.FC<TimelineBarProps> = ({ activeAgent, completedAgents, progress }) => {
  const getAgentStatus = (agentName: string): 'pending' | 'active' | 'completed' => {
    if (activeAgent === agentName) return 'active';
    if (completedAgents.includes(agentName)) return 'completed';
    return 'pending';
  };

  const shortNames = useMemo(() => {
    const mapping: Record<string, string> = {
      'Transcript Analyzer': 'Analyze',
      'Research & Entity Extraction': 'Research',
      'Calendar Context Fetch': 'Calendar',
      'Related Meetings Finder': 'Meetings',
      'Action Planner': 'Plan',
      'Decision Analyzer': 'Decide',
      'Risk Assessor': 'Risk',
      'Action Executor': 'Execute',
      'Summary Generator': 'Summary',
    };
    return mapping;
  }, []);

  return (
    <Paper
      sx={{
        marginY: 3,
        padding: 2,
        backgroundColor: '#1a1a1a',
        border: '2px solid #76B900',
        borderRadius: '8px',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
        {AGENT_NAMES.map((agentName) => {
          const status = getAgentStatus(agentName);
          const isActive = status === 'active';
          const isCompleted = status === 'completed';

          return (
            <Box
              key={agentName}
              sx={{
                flex: 1,
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              {/* Dot */}
              <Box
                sx={{
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  backgroundColor: isActive ? '#76B900' : isCompleted ? '#76B900' : '#444',
                  border: isActive ? '2px solid #92e000' : `2px solid ${isCompleted ? '#76B900' : '#666'}`,
                  marginBottom: 1,
                  boxShadow: isActive ? '0 0 15px rgba(118, 185, 0, 0.8)' : 'none',
                  animation: isActive ? 'pulse 1.5s infinite' : 'none',
                  '@keyframes pulse': {
                    '0%, 100%': {
                      boxShadow: '0 0 15px rgba(118, 185, 0, 0.8)',
                    },
                    '50%': {
                      boxShadow: '0 0 25px rgba(118, 185, 0, 1)',
                    },
                  },
                }}
              />
              {/* Label */}
              <Box
                sx={{
                  fontSize: '0.75rem',
                  color: isActive ? '#76B900' : isCompleted ? '#76B900' : '#ccc',
                  fontWeight: isActive ? 'bold' : 500,
                }}
              >
                {shortNames[agentName] || agentName}
              </Box>
            </Box>
          );
        })}
      </Box>

      {/* Progress Bar */}
      <Box
        sx={{
          height: 2,
          backgroundColor: '#333',
          marginTop: 2,
          borderRadius: 1,
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            height: '100%',
            backgroundColor: '#76B900',
            width: `${progress}%`,
            transition: 'width 0.3s ease',
          }}
        />
      </Box>
    </Paper>
  );
};
