import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  Paper,
} from '@mui/material';
import {
  CalendarToday,
  AccessTime,
  People,
  Description,
  Psychology,
} from '@mui/icons-material';
import { MeetingAction } from '../../types/workflow';

interface ActionCardsProps {
  actions: MeetingAction[];
}

/**
 * ActionCards Component
 *
 * Displays a grid of planned meeting actions with detailed information.
 * Each card shows the action type, event details, attendees, and AI reasoning.
 */
const ActionCards: React.FC<ActionCardsProps> = ({ actions }) => {
  // Show message if no actions are planned
  if (!actions || actions.length === 0) {
    return (
      <Paper
        sx={{
          p: 4,
          textAlign: 'center',
          backgroundColor: 'rgba(118, 185, 0, 0.1)',
          border: '1px solid rgba(118, 185, 0, 0.3)',
        }}
      >
        <Typography variant="h6" color="text.secondary">
          No actions planned
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          The AI hasn't identified any actions to take based on the meeting transcript.
        </Typography>
      </Paper>
    );
  }

  /**
   * Get color for action type chip based on the action type
   */
  const getActionTypeColor = (actionType: string): 'primary' | 'secondary' | 'success' | 'warning' => {
    switch (actionType?.toUpperCase()) {
      case 'CREATE_EVENT':
        return 'success';
      case 'ADD_NOTES':
        return 'primary';
      case 'FIND_SLOT':
        return 'warning';
      case 'UPDATE_EVENT':
        return 'secondary';
      default:
        return 'primary';
    }
  };

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' },
        gap: 3,
      }}
    >
      {actions.map((action, index) => (
        <Box key={index}>
          <Card
            sx={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              backgroundColor: 'rgba(26, 26, 26, 0.4)',
              backdropFilter: 'blur(10px)',
              WebkitBackdropFilter: 'blur(10px)',
              border: '1px solid rgba(118, 185, 0, 0.3)',
              boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                backgroundColor: 'rgba(26, 26, 26, 0.6)',
                boxShadow: '0 12px 40px rgba(118, 185, 0, 0.3)',
                border: '1px solid rgba(118, 185, 0, 0.6)',
              },
            }}
          >
            <CardContent sx={{ flexGrow: 1 }}>
              {/* Action Type Chip */}
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Chip
                  label={action.action_type || 'UNKNOWN'}
                  color={getActionTypeColor(action.action_type)}
                  size="small"
                  sx={{ fontWeight: 'bold' }}
                />
                <Typography variant="caption" color="text.secondary">
                  Action #{index + 1}
                </Typography>
              </Box>

              {/* Event Title */}
              {action.event_title && (
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{
                    color: '#76B900',
                    fontWeight: 600,
                    mb: 2,
                    wordBreak: 'break-word',
                  }}
                >
                  {action.event_title}
                </Typography>
              )}

              {/* Calendar Event ID (for existing events) */}
              {action.calendar_event_id && (
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                  <CalendarToday sx={{ fontSize: 18, mr: 1, color: '#76B900' }} />
                  <Typography variant="body2" color="text.secondary">
                    Event ID: {action.calendar_event_id.substring(0, 12)}...
                  </Typography>
                </Box>
              )}

              {/* Event Date */}
              {action.event_date && (
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                  <CalendarToday sx={{ fontSize: 18, mr: 1, color: '#76B900' }} />
                  <Typography variant="body2">
                    {new Date(action.event_date).toLocaleDateString('en-US', {
                      weekday: 'short',
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </Typography>
                </Box>
              )}

              {/* Duration */}
              {action.duration_minutes && (
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                  <AccessTime sx={{ fontSize: 18, mr: 1, color: '#76B900' }} />
                  <Typography variant="body2">
                    {action.duration_minutes} minutes
                  </Typography>
                </Box>
              )}

              {/* Attendees */}
              {action.attendees && action.attendees.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <People sx={{ fontSize: 18, mr: 1, color: '#76B900' }} />
                    <Typography variant="body2" fontWeight={600}>
                      Attendees:
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {action.attendees.map((attendee, idx) => (
                      <Chip
                        key={idx}
                        label={attendee}
                        size="small"
                        variant="outlined"
                        sx={{
                          borderColor: 'rgba(118, 185, 0, 0.5)',
                          color: 'text.primary',
                        }}
                      />
                    ))}
                  </Box>
                </Box>
              )}

              {/* Notes/Description */}
              {action.notes && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Description sx={{ fontSize: 18, mr: 1, color: '#76B900' }} />
                    <Typography variant="body2" fontWeight={600}>
                      Notes:
                    </Typography>
                  </Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      pl: 3.5,
                      fontStyle: 'italic',
                      wordBreak: 'break-word',
                    }}
                  >
                    {action.notes}
                  </Typography>
                </Box>
              )}

              {/* AI Reasoning */}
              {action.reasoning && (
                <Box
                  sx={{
                    mt: 2,
                    pt: 2,
                    borderTop: '1px solid rgba(118, 185, 0, 0.2)',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Psychology sx={{ fontSize: 18, mr: 1, color: '#76B900' }} />
                    <Typography variant="body2" fontWeight={600}>
                      AI Reasoning:
                    </Typography>
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      pl: 3.5,
                      display: 'block',
                      lineHeight: 1.5,
                      wordBreak: 'break-word',
                    }}
                  >
                    {action.reasoning}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Box>
      ))}
    </Box>
  );
};

export default ActionCards;
