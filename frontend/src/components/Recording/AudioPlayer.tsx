import React from 'react';
import { Box, Typography } from '@mui/material';

interface AudioPlayerProps {
  audioUrl?: string;
  isVisible: boolean;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, isVisible }) => {
  if (!isVisible || !audioUrl) {
    return null;
  }

  return (
    <Box sx={{ marginY: 3, textAlign: 'center' }}>
      <Typography variant="body1" sx={{ marginBottom: 2, color: 'text.secondary' }}>
        🔊 Playback your recording:
      </Typography>
      <audio
        controls
        src={audioUrl}
        style={{
          width: '100%',
          maxWidth: '500px',
        }}
      />
    </Box>
  );
};
