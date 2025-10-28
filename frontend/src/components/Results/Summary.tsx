import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Divider,
} from '@mui/material';
import {
  Email,
  CheckCircle,
} from '@mui/icons-material';

interface SummaryProps {
  summary: string;
  showEmailSent?: boolean;
}

/**
 * Summary Component
 *
 * Displays the AI-generated meeting summary with formatted text.
 * Shows a confirmation message that the email summary was sent.
 */
const Summary: React.FC<SummaryProps> = ({ summary, showEmailSent = true }) => {
  // Return null if no summary
  if (!summary) {
    return null;
  }

  /**
   * Formats the summary text with proper line breaks and structure
   */
  const formatSummary = (text: string): string[] => {
    // Split by newlines and filter out empty lines
    return text
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);
  };

  const formattedLines = formatSummary(summary);

  return (
    <Paper
      sx={{
        p: 4,
        backgroundColor: 'rgba(20, 20, 20, 0.8)',
        border: '1px solid rgba(118, 185, 0, 0.3)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative gradient overlay */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'linear-gradient(90deg, #76B900 0%, #5a9000 100%)',
        }}
      />

      <Typography
        variant="h5"
        gutterBottom
        sx={{
          color: '#76B900',
          fontWeight: 700,
          mb: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        📋 Meeting Summary
      </Typography>

      {/* Summary Content */}
      <Box
        sx={{
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          borderRadius: 2,
          p: 3,
          mb: 3,
        }}
      >
        {formattedLines.map((line, index) => {
          // Check if line is a header (starts with ## or #)
          const isHeader = line.startsWith('##') || line.startsWith('#');
          // Check if line is a bullet point
          const isBullet = line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ');

          if (isHeader) {
            return (
              <Typography
                key={index}
                variant="h6"
                sx={{
                  color: '#76B900',
                  fontWeight: 600,
                  mt: index > 0 ? 2 : 0,
                  mb: 1,
                }}
              >
                {line.replace(/^#+\s*/, '')}
              </Typography>
            );
          }

          if (isBullet) {
            return (
              <Typography
                key={index}
                variant="body1"
                sx={{
                  color: 'white',
                  lineHeight: 1.8,
                  pl: 2,
                  mb: 0.5,
                  '&::before': {
                    content: '"•"',
                    color: '#76B900',
                    fontWeight: 'bold',
                    display: 'inline-block',
                    width: '1em',
                    marginLeft: '-1em',
                  },
                }}
              >
                {line.replace(/^[-*•]\s*/, '')}
              </Typography>
            );
          }

          return (
            <Typography
              key={index}
              variant="body1"
              sx={{
                color: 'white',
                lineHeight: 1.8,
                mb: 1.5,
                whiteSpace: 'pre-wrap',
              }}
            >
              {line}
            </Typography>
          );
        })}
      </Box>

      {/* Email Sent Confirmation */}
      {showEmailSent && (
        <>
          <Divider
            sx={{
              borderColor: 'rgba(118, 185, 0, 0.2)',
              mb: 2,
            }}
          />
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1,
              p: 2,
              backgroundColor: 'rgba(118, 185, 0, 0.1)',
              borderRadius: 2,
              border: '1px solid rgba(118, 185, 0, 0.3)',
            }}
          >
            <Email sx={{ color: '#76B900', fontSize: 24 }} />
            <Typography
              variant="body1"
              sx={{
                color: '#76B900',
                fontWeight: 600,
              }}
            >
              📧 Email summary sent to all attendees
            </Typography>
            <CheckCircle sx={{ color: '#76B900', fontSize: 20 }} />
          </Box>
        </>
      )}
    </Paper>
  );
};

export default Summary;
