import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { Notes } from '@mui/icons-material';

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
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Notes sx={{ fontSize: 20, color: '#76B900' }} />
        <Typography variant="subtitle2" sx={{ color: '#76B900' }}>
          Transcription
        </Typography>
      </Box>
      <Typography variant="body2" sx={{ lineHeight: 1.6, color: '#FFFFFF', whiteSpace: 'pre-wrap' }}>
        {transcription}
      </Typography>
    </Paper>
  );
};
