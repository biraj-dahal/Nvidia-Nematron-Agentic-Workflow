import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

interface TranscriptionDisplayProps {
  transcription: string;
  isVisible: boolean;
}

export const TranscriptionDisplay: React.FC<TranscriptionDisplayProps> = ({ transcription, isVisible }) => {
  if (!isVisible || !transcription) {
    return null;
  }

  return (
    <Paper
      sx={{
        marginY: 3,
        padding: 2,
        backgroundColor: '#1a1a1a',
        border: '2px solid #76B900',
        borderRadius: '8px',
        maxHeight: '300px',
        overflowY: 'auto',
      }}
    >
      <Typography variant="subtitle2" sx={{ marginBottom: 1, color: '#76B900' }}>
        📝 Transcription
      </Typography>
      <Typography variant="body2" sx={{ lineHeight: 1.6, color: '#FFFFFF', whiteSpace: 'pre-wrap' }}>
        {transcription}
      </Typography>
    </Paper>
  );
};
