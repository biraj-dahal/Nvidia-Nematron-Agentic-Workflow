import React from 'react';
import { Button, Stack } from '@mui/material';
import { Mic, Stop } from '@mui/icons-material';

interface RecordingControlsProps {
  isRecording: boolean;
  onStart: () => void;
  onStop: () => void;
  disabled?: boolean;
}

export const RecordingControls: React.FC<RecordingControlsProps> = ({
  isRecording,
  onStart,
  onStop,
  disabled = false,
}) => {
  return (
    <Stack direction="row" spacing={2} justifyContent="center" sx={{ marginBottom: 3 }}>
      {!isRecording ? (
        <Button
          variant="contained"
          color="primary"
          size="large"
          startIcon={<Mic />}
          onClick={onStart}
          disabled={disabled}
          sx={{
            px: 4,
            py: 1.5,
          }}
        >
          Start Recording
        </Button>
      ) : (
        <Button
          variant="contained"
          color="error"
          size="large"
          startIcon={<Stop />}
          onClick={onStop}
          disabled={disabled}
          sx={{
            px: 4,
            py: 1.5,
          }}
        >
          End Recording
        </Button>
      )}
    </Stack>
  );
};
