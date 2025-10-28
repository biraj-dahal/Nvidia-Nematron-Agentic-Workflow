import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { useWorkflow } from '../../context/WorkflowContext';

/**
 * WorkflowStatusLog Component
 *
 * Displays workflow progress as a simple text-based status log.
 * Shows all 9 stages with their current status (pending/active/completed).
 */
export const WorkflowStatusLog: React.FC = () => {
  const { workflow } = useWorkflow();
  const { agentCards, progress } = workflow;

  // Symbol map for status
  const getStatusSymbol = (status: string): string => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'active':
        return '⏳';
      case 'error':
        return '✗';
      default:
        return '⬜';
    }
  };

  // Color map for status
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return '#76B900'; // NVIDIA Green
      case 'active':
        return '#FFA500'; // Orange
      case 'error':
        return '#ef4444'; // Red
      default:
        return '#888888'; // Gray
    }
  };

  // Status text
  const getStatusText = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'done';
      case 'active':
        return 'running...';
      case 'error':
        return 'error';
      default:
        return 'pending';
    }
  };

  return (
    <Paper
      sx={{
        p: 3,
        mb: 4,
        backgroundColor: 'rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(118, 185, 0, 0.3)',
        fontFamily: 'monospace',
      }}
    >
      {/* Header */}
      <Typography
        variant="h6"
        sx={{
          color: '#76B900',
          mb: 2,
          fontWeight: 700,
          fontFamily: 'monospace',
        }}
      >
        Workflow Progress
      </Typography>

      {/* Progress Bar */}
      <Box sx={{ mb: 3 }}>
        <Box
          sx={{
            width: '100%',
            height: 6,
            backgroundColor: 'rgba(118, 185, 0, 0.1)',
            borderRadius: 3,
            overflow: 'hidden',
            mb: 1,
          }}
        >
          <Box
            sx={{
              height: '100%',
              width: `${progress}%`,
              backgroundColor: '#76B900',
              transition: 'width 0.3s ease',
            }}
          />
        </Box>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontFamily: 'monospace' }}
        >
          {Math.round(progress)}% complete
        </Typography>
      </Box>

      {/* Status Log */}
      <Box sx={{ fontFamily: 'monospace', fontSize: '0.85rem', lineHeight: 1.8 }}>
        {agentCards.length === 0 ? (
          <Typography color="text.secondary">No workflow in progress</Typography>
        ) : (
          agentCards.map((card) => (
            <Box
              key={card.agentName}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                mb: 1,
                color: getStatusColor(card.status),
                transition: 'color 0.3s ease',
              }}
            >
              {/* Status Symbol */}
              <span style={{ fontSize: '1.2em', minWidth: '1.5em' }}>
                {getStatusSymbol(card.status)}
              </span>

              {/* Agent Name */}
              <span>{card.agentName}</span>

              {/* Status Text */}
              <span style={{ fontSize: '0.8em', opacity: 0.7 }}>
                ({getStatusText(card.status)})
              </span>
            </Box>
          ))
        )}
      </Box>

      {/* Footer */}
      {agentCards.length > 0 && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            mt: 2,
            display: 'block',
            fontFamily: 'monospace',
            fontSize: '0.75rem',
          }}
        >
          {agentCards.filter((c) => c.status === 'completed').length} of{' '}
          {agentCards.length} stages completed
        </Typography>
      )}
    </Paper>
  );
};
