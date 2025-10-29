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
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

  // Custom components for markdown rendering with NVIDIA theme
  const markdownComponents = {
    h1: ({ node, ...props }: any) => (
      <Typography
        variant="h4"
        sx={{
          color: '#76B900',
          fontWeight: 700,
          mt: 3,
          mb: 2,
        }}
        {...props}
      />
    ),
    h2: ({ node, ...props }: any) => (
      <Typography
        variant="h5"
        sx={{
          color: '#76B900',
          fontWeight: 600,
          mt: 2.5,
          mb: 1.5,
        }}
        {...props}
      />
    ),
    h3: ({ node, ...props }: any) => (
      <Typography
        variant="h6"
        sx={{
          color: '#76B900',
          fontWeight: 600,
          mt: 2,
          mb: 1,
        }}
        {...props}
      />
    ),
    p: ({ node, ...props }: any) => (
      <Typography
        variant="body1"
        sx={{
          color: 'white',
          lineHeight: 1.8,
          mb: 1.5,
        }}
        {...props}
      />
    ),
    ul: ({ node, ...props }: any) => (
      <Box component="ul" sx={{ pl: 3, mb: 1.5, color: 'white' }} {...props} />
    ),
    ol: ({ node, ...props }: any) => (
      <Box component="ol" sx={{ pl: 3, mb: 1.5, color: 'white' }} {...props} />
    ),
    li: ({ node, ...props }: any) => (
      <Typography
        component="li"
        variant="body1"
        sx={{
          color: 'white',
          lineHeight: 1.8,
          mb: 0.5,
          '&::marker': {
            color: '#76B900',
          },
        }}
        {...props}
      />
    ),
    strong: ({ node, ...props }: any) => (
      <strong style={{ color: '#fff', fontWeight: 600 }} {...props} />
    ),
    em: ({ node, ...props }: any) => (
      <em style={{ color: '#ccc', fontStyle: 'italic' }} {...props} />
    ),
    code: ({ node, ...props }: any) => (
      <code
        style={{
          backgroundColor: 'rgba(118, 185, 0, 0.15)',
          color: '#76B900',
          padding: '2px 6px',
          borderRadius: '3px',
          fontFamily: 'monospace',
        }}
        {...props}
      />
    ),
    pre: ({ node, ...props }: any) => (
      <Box
        component="pre"
        sx={{
          backgroundColor: 'rgba(0, 0, 0, 0.3)',
          padding: 2,
          borderRadius: 1,
          overflowX: 'auto',
          mb: 2,
          border: '1px solid rgba(118, 185, 0, 0.2)',
        }}
        {...props}
      />
    ),
    table: ({ node, ...props }: any) => (
      <Box
        component="table"
        sx={{
          width: '100%',
          borderCollapse: 'collapse',
          mb: 2,
          border: '1px solid rgba(118, 185, 0, 0.2)',
        }}
        {...props}
      />
    ),
    thead: ({ node, ...props }: any) => (
      <Box
        component="thead"
        sx={{ backgroundColor: 'rgba(118, 185, 0, 0.1)' }}
        {...props}
      />
    ),
    th: ({ node, ...props }: any) => (
      <Box
        component="th"
        sx={{
          padding: 1.5,
          border: '1px solid rgba(118, 185, 0, 0.2)',
          color: '#76B900',
          fontWeight: 600,
          textAlign: 'left',
        }}
        {...props}
      />
    ),
    td: ({ node, ...props }: any) => (
      <Box
        component="td"
        sx={{
          padding: 1.5,
          border: '1px solid rgba(118, 185, 0, 0.2)',
          color: 'white',
        }}
        {...props}
      />
    ),
    blockquote: ({ node, ...props }: any) => (
      <Box
        sx={{
          borderLeft: '4px solid #76B900',
          paddingLeft: 2,
          marginLeft: 0,
          color: '#aaa',
          fontStyle: 'italic',
          mb: 2,
        }}
        {...props}
      />
    ),
    a: ({ node, ...props }: any) => (
      <Typography
        component="a"
        sx={{
          color: '#76B900',
          textDecoration: 'underline',
          '&:hover': { opacity: 0.8 },
        }}
        {...props}
      />
    ),
  };

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

      {/* Summary Content - Rendered Markdown */}
      <Box
        sx={{
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          borderRadius: 2,
          p: 3,
          mb: 3,
        }}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={markdownComponents}
        >
          {summary}
        </ReactMarkdown>
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
