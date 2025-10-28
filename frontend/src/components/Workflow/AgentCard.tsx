import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, Collapse, Chip } from '@mui/material';
import { ExpandMore } from '@mui/icons-material';

interface AgentCardProps {
  agentName: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  description: string;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}

export const AgentCard: React.FC<AgentCardProps> = ({
  agentName,
  status,
  description,
  expanded: externalExpanded = false,
  onToggle,
}) => {
  const [localExpanded, setLocalExpanded] = useState(externalExpanded);
  const isExpanded = externalExpanded !== undefined ? externalExpanded : localExpanded;

  // Sync external expanded prop with local state for real-time updates
  useEffect(() => {
    setLocalExpanded(externalExpanded);
  }, [externalExpanded]);

  const handleToggle = () => {
    const newState = !isExpanded;
    setLocalExpanded(newState);
    onToggle?.(newState);
  };

  const statusColor = {
    pending: '#666',
    active: '#76B900',
    completed: '#4CAF50',
    error: '#F44336',
  };

  const statusBgColor = {
    pending: 'rgba(100, 100, 100, 0.1)',
    active: 'rgba(118, 185, 0, 0.2)',
    completed: 'rgba(76, 175, 80, 0.2)',
    error: 'rgba(244, 67, 54, 0.2)',
  };

  return (
    <Card
      sx={{
        backgroundColor: '#1a1a1a',
        border: isExpanded ? '2px solid #76B900' : '1px solid #444',
        borderRadius: '8px',
        marginBottom: 2,
        transition: 'all 0.3s ease',
        boxShadow: status === 'active' ? '0 0 15px rgba(118, 185, 0, 0.3)' : 'none',
        '&:hover': {
          borderColor: '#76B900',
        },
      }}
    >
      {/* Header - Always Visible */}
      <Box
        onClick={handleToggle}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 2,
          backgroundColor: '#2a2a2a',
          cursor: 'pointer',
          userSelect: 'none',
          transition: 'background-color 0.3s ease',
          '&:hover': {
            backgroundColor: '#333',
          },
        }}
      >
        {/* Left: Dot + Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
          {/* Status Dot */}
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: statusColor[status],
              animation: status === 'active' ? 'pulse 1.5s infinite' : 'none',
              '@keyframes pulse': {
                '0%, 100%': {
                  boxShadow: `0 0 8px ${statusColor[status]}`,
                },
                '50%': {
                  boxShadow: `0 0 12px ${statusColor[status]}`,
                },
              },
            }}
          />

          {/* Title + Description */}
          <Box>
            <Typography variant="h6" sx={{ margin: 0, fontSize: '1.1em', fontWeight: 'bold' }}>
              {agentName}
            </Typography>
            <Typography variant="caption" sx={{ color: '#aaa', marginTop: 0.5 }}>
              {description}
            </Typography>
          </Box>
        </Box>

        {/* Middle: Status Badge */}
        <Chip
          label={status.toUpperCase()}
          size="small"
          sx={{
            backgroundColor: statusBgColor[status],
            color: statusColor[status],
            border: `1px solid ${statusColor[status]}`,
            fontWeight: 'bold',
            marginRight: 2,
          }}
        />

        {/* Right: Toggle Arrow */}
        <ExpandMore
          sx={{
            transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.3s ease',
            color: isExpanded ? '#76B900' : '#888',
          }}
        />
      </Box>

      {/* Body - Collapsible */}
      <Collapse in={isExpanded} timeout="auto" unmountOnExit>
        <CardContent sx={{ backgroundColor: '#252525', padding: 2 }}>
          <Typography variant="caption" sx={{ color: '#76B900', fontWeight: 'bold', fontSize: '0.8em', display: 'block', marginBottom: 1, textTransform: 'uppercase' }}>
            Status Details
          </Typography>
          <Box
            sx={{
              backgroundColor: '#2a2a2a',
              padding: 1.5,
              borderRadius: '4px',
              borderLeft: '3px solid #76B900',
              color: '#ccc',
              fontSize: '0.95em',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {description || 'No details available'}
          </Box>
        </CardContent>
      </Collapse>
    </Card>
  );
};
