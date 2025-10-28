import React, { useMemo } from 'react';
import { Box, Card, CardContent, Typography, Chip, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import { ExpandMore } from '@mui/icons-material';
import { LogEntry } from '../../types/workflow';

interface AgentCardProps {
  agentName: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  description: string;
  logs?: LogEntry[];
}

export const AgentCard: React.FC<AgentCardProps> = ({
  agentName,
  status,
  description,
  logs = [],
}) => {
  console.log(`🃏 [AgentCard] ${agentName} - Rendering with status: ${status}, logs: ${logs.length}`);

  // Group logs by type
  const groupedLogs = useMemo(() => {
    const grouped: Record<string, LogEntry[]> = {
      thinking: [],
      input: [],
      processing: [],
      api_call: [],
      output: [],
      timing: [],
      error: [],
    };
    logs.forEach(log => {
      grouped[log.type].push(log);
    });
    return grouped;
  }, [logs]);

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
        border: '2px solid #76B900',
        borderRadius: '8px',
        marginBottom: 2,
        transition: 'all 0.3s ease',
        boxShadow: status === 'active' ? '0 0 15px rgba(118, 185, 0, 0.3)' : 'none',
      }}
    >
      {/* Header - Always Visible */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 2,
          backgroundColor: '#2a2a2a',
          userSelect: 'none',
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

        {/* Status Badge */}
        <Chip
          label={status.toUpperCase()}
          size="small"
          sx={{
            backgroundColor: statusBgColor[status],
            color: statusColor[status],
            border: `1px solid ${statusColor[status]}`,
            fontWeight: 'bold',
          }}
        />
      </Box>

      {/* Body - Always Visible */}
        <CardContent sx={{ backgroundColor: '#252525', padding: 2 }}>
          {/* Execution Logs Section */}
          {logs.length > 0 && (
            <Box>
              <Typography variant="caption" sx={{ color: '#76B900', fontWeight: 'bold', fontSize: '0.8em', display: 'block', marginBottom: 1, textTransform: 'uppercase' }}>
                Execution Logs ({logs.length})
              </Typography>

              {/* Input Logs */}
              {groupedLogs.input.length > 0 && (
                <Accordion defaultExpanded={false} sx={{ backgroundColor: '#2a2a2a', marginBottom: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMore />} sx={{ color: '#76B900' }}>
                    📥 Input ({groupedLogs.input.length})
                  </AccordionSummary>
                  <AccordionDetails sx={{ backgroundColor: '#1a1a1a', padding: 1.5 }}>
                    {groupedLogs.input.map((log, idx) => (
                      <Box key={idx} sx={{ marginBottom: 1, color: '#ccc', fontSize: '0.85em', fontFamily: 'monospace' }}>
                        <Typography variant="caption" sx={{ color: '#aaa' }}>
                          {log.timestamp}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: '#ccc', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {log.message}
                        </Typography>
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}

              {/* Processing Logs */}
              {groupedLogs.processing.length > 0 && (
                <Accordion defaultExpanded={true} sx={{ backgroundColor: '#2a2a2a', marginBottom: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMore />} sx={{ color: '#76B900' }}>
                    ⚙️ Processing ({groupedLogs.processing.length})
                  </AccordionSummary>
                  <AccordionDetails sx={{ backgroundColor: '#1a1a1a', padding: 1.5 }}>
                    {groupedLogs.processing.map((log, idx) => (
                      <Box key={idx} sx={{ marginBottom: 1, color: '#ccc', fontSize: '0.85em', fontFamily: 'monospace' }}>
                        <Typography variant="caption" sx={{ color: '#aaa' }}>
                          {log.timestamp}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: '#ccc', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {log.message}
                        </Typography>
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}

              {/* Thinking Logs */}
              {groupedLogs.thinking.length > 0 && (
                <Accordion defaultExpanded={true} sx={{ backgroundColor: '#2a2a2a', marginBottom: 1, border: '1px solid #4a7c59' }}>
                  <AccordionSummary expandIcon={<ExpandMore />} sx={{ color: '#7cb342' }}>
                    💭 AI Reasoning ({groupedLogs.thinking.length})
                  </AccordionSummary>
                  <AccordionDetails sx={{ backgroundColor: '#1a1a1a', padding: 1.5 }}>
                    {groupedLogs.thinking.map((log, idx) => (
                      <Box key={idx} sx={{ marginBottom: 1, color: '#b8e6b8', fontSize: '0.85em', fontFamily: 'monospace', backgroundColor: '#1e2a1e', padding: 1.5, borderRadius: '4px', borderLeft: '3px solid #7cb342' }}>
                        <Typography variant="caption" sx={{ color: '#7cb342', fontWeight: 'bold' }}>
                          {log.timestamp} - Model Thinking
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: '#b8e6b8', whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginTop: 0.5, fontStyle: 'italic' }}>
                          {log.message}
                        </Typography>
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}

              {/* API Call Logs */}
              {groupedLogs.api_call.length > 0 && (
                <Accordion defaultExpanded={true} sx={{ backgroundColor: '#2a2a2a', marginBottom: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMore />} sx={{ color: '#76B900' }}>
                    🤖 API Calls ({groupedLogs.api_call.length})
                  </AccordionSummary>
                  <AccordionDetails sx={{ backgroundColor: '#1a1a1a', padding: 1.5 }}>
                    {groupedLogs.api_call.map((log, idx) => (
                      <Box key={idx} sx={{ marginBottom: 1.5, color: '#ccc', fontSize: '0.85em', fontFamily: 'monospace', borderBottom: '1px solid #333', paddingBottom: 1 }}>
                        <Typography variant="caption" sx={{ color: '#aaa' }}>
                          {log.timestamp}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: '#ccc', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {log.message}
                        </Typography>
                        {log.metadata && (
                          <Box sx={{ marginTop: 0.5, color: '#999', fontSize: '0.8em' }}>
                            {log.metadata.model && <Typography variant="caption" sx={{ display: 'block' }}>Model: {log.metadata.model}</Typography>}
                            {log.metadata.tokens && <Typography variant="caption" sx={{ display: 'block' }}>Tokens: {log.metadata.tokens}</Typography>}
                            {log.metadata.latency_ms && <Typography variant="caption" sx={{ display: 'block' }}>Latency: {log.metadata.latency_ms}ms</Typography>}
                          </Box>
                        )}
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}

              {/* Output Logs */}
              {groupedLogs.output.length > 0 && (
                <Accordion defaultExpanded={false} sx={{ backgroundColor: '#2a2a2a', marginBottom: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMore />} sx={{ color: '#76B900' }}>
                    📤 Output ({groupedLogs.output.length})
                  </AccordionSummary>
                  <AccordionDetails sx={{ backgroundColor: '#1a1a1a', padding: 1.5 }}>
                    {groupedLogs.output.map((log, idx) => (
                      <Box key={idx} sx={{ marginBottom: 1, color: '#ccc', fontSize: '0.85em', fontFamily: 'monospace' }}>
                        <Typography variant="caption" sx={{ color: '#aaa' }}>
                          {log.timestamp}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: '#ccc', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {log.message}
                        </Typography>
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}

              {/* Timing Logs */}
              {groupedLogs.timing.length > 0 && (
                <Accordion defaultExpanded={false} sx={{ backgroundColor: '#2a2a2a', marginBottom: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMore />} sx={{ color: '#76B900' }}>
                    ⏱️ Timing ({groupedLogs.timing.length})
                  </AccordionSummary>
                  <AccordionDetails sx={{ backgroundColor: '#1a1a1a', padding: 1.5 }}>
                    {groupedLogs.timing.map((log, idx) => (
                      <Box key={idx} sx={{ marginBottom: 1, color: '#ccc', fontSize: '0.85em', fontFamily: 'monospace' }}>
                        <Typography variant="caption" sx={{ color: '#aaa' }}>
                          {log.timestamp}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: '#ccc', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {log.message}
                        </Typography>
                        {log.metadata?.duration_ms && (
                          <Typography variant="caption" sx={{ display: 'block', color: '#999', marginTop: 0.5 }}>
                            Duration: {log.metadata.duration_ms}ms
                          </Typography>
                        )}
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}

              {/* Error Logs */}
              {groupedLogs.error.length > 0 && (
                <Accordion defaultExpanded={true} sx={{ backgroundColor: '#2a2a2a', marginBottom: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMore />} sx={{ color: '#F44336' }}>
                    ⚠️ Errors ({groupedLogs.error.length})
                  </AccordionSummary>
                  <AccordionDetails sx={{ backgroundColor: '#1a1a1a', padding: 1.5 }}>
                    {groupedLogs.error.map((log, idx) => (
                      <Box key={idx} sx={{ marginBottom: 1, color: '#ff6b6b', fontSize: '0.85em', fontFamily: 'monospace' }}>
                        <Typography variant="caption" sx={{ color: '#aaa' }}>
                          {log.timestamp}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: '#ff6b6b', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {log.message}
                        </Typography>
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}
            </Box>
          )}
        </CardContent>
    </Card>
  );
};
