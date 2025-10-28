import React from 'react';
import {
  Stack,
  Button,
  Box,
  Typography,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  Warning,
} from '@mui/icons-material';

interface ApprovalButtonsProps {
  onApprove: () => void;
  onCancel: () => void;
  disabled?: boolean;
}

/**
 * ApprovalButtons Component
 *
 * Shows "Approve & Execute" and "Cancel" buttons for manual approval workflow.
 * Only visible when auto_execute is false in the orchestrator settings.
 *
 * The approve button triggers execution of planned actions.
 * The cancel button aborts the workflow without executing actions.
 */
const ApprovalButtons: React.FC<ApprovalButtonsProps> = ({
  onApprove,
  onCancel,
  disabled = false,
}) => {
  return (
    <Box
      sx={{
        p: 3,
        backgroundColor: 'rgba(255, 255, 255, 0.03)',
        borderRadius: 2,
        border: '1px solid rgba(118, 185, 0, 0.3)',
      }}
    >
      {/* Warning/Info message */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          mb: 3,
          p: 2,
          backgroundColor: 'rgba(255, 193, 7, 0.1)',
          borderRadius: 1,
          border: '1px solid rgba(255, 193, 7, 0.3)',
        }}
      >
        <Warning sx={{ color: '#ffc107', fontSize: 28 }} />
        <Box>
          <Typography
            variant="body1"
            sx={{
              color: 'text.primary',
              fontWeight: 600,
              mb: 0.5,
            }}
          >
            Manual Approval Required
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Review the planned actions above. Click "Approve & Execute" to proceed with
            creating calendar events and sending email summaries, or "Cancel" to abort.
          </Typography>
        </Box>
      </Box>

      {/* Action buttons */}
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{
          justifyContent: 'center',
          alignItems: 'stretch',
        }}
      >
        {/* Approve Button */}
        <Button
          variant="contained"
          size="large"
          startIcon={<CheckCircle />}
          onClick={onApprove}
          disabled={disabled}
          sx={{
            flex: 1,
            minWidth: '200px',
            backgroundColor: '#76B900',
            color: 'white',
            fontWeight: 600,
            py: 1.5,
            transition: 'all 0.3s ease',
            '&:hover': {
              backgroundColor: '#5a9000',
              transform: 'translateY(-2px)',
              boxShadow: '0 6px 20px rgba(118, 185, 0, 0.4)',
            },
            '&:active': {
              transform: 'translateY(0)',
            },
            '&:disabled': {
              backgroundColor: 'rgba(118, 185, 0, 0.3)',
              color: 'rgba(255, 255, 255, 0.5)',
            },
          }}
        >
          Approve & Execute
        </Button>

        {/* Cancel Button */}
        <Button
          variant="outlined"
          size="large"
          startIcon={<Cancel />}
          onClick={onCancel}
          disabled={disabled}
          sx={{
            flex: 1,
            minWidth: '200px',
            borderColor: 'rgba(156, 163, 175, 0.5)',
            color: 'rgb(156, 163, 175)',
            fontWeight: 600,
            py: 1.5,
            transition: 'all 0.3s ease',
            '&:hover': {
              borderColor: 'rgb(156, 163, 175)',
              backgroundColor: 'rgba(156, 163, 175, 0.1)',
              transform: 'translateY(-2px)',
            },
            '&:active': {
              transform: 'translateY(0)',
            },
            '&:disabled': {
              borderColor: 'rgba(156, 163, 175, 0.2)',
              color: 'rgba(156, 163, 175, 0.3)',
            },
          }}
        >
          Cancel
        </Button>
      </Stack>

      {/* Disabled state message */}
      {disabled && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: 'block',
            textAlign: 'center',
            mt: 2,
            fontStyle: 'italic',
          }}
        >
          Please wait for the current operation to complete...
        </Typography>
      )}
    </Box>
  );
};

export default ApprovalButtons;
