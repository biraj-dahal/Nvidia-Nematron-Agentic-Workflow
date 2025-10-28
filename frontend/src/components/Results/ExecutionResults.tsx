import React from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  CheckCircle,
  Error as ErrorIcon,
  Info,
} from '@mui/icons-material';
import { ExecutionResult } from '../../types/workflow';

interface ExecutionResultsProps {
  results: ExecutionResult[] | string[];
}

/**
 * ExecutionResults Component
 *
 * Displays a list of execution results from the orchestrator.
 * Each result shows with a status indicator (success/error) and message.
 * Supports both string messages and structured ExecutionResult objects.
 */
const ExecutionResults: React.FC<ExecutionResultsProps> = ({ results }) => {
  // Return null if no results
  if (!results || results.length === 0) {
    return null;
  }

  /**
   * Determines if a result represents a successful execution
   */
  const isSuccessResult = (result: ExecutionResult | string): boolean => {
    if (typeof result === 'string') {
      // Check for success indicators in string
      const lowerResult = result.toLowerCase();
      return (
        lowerResult.includes('success') ||
        lowerResult.includes('created') ||
        lowerResult.includes('added') ||
        lowerResult.includes('updated') ||
        lowerResult.includes('found') ||
        !lowerResult.includes('error') &&
        !lowerResult.includes('failed') &&
        !lowerResult.includes('not found')
      );
    }
    // For structured results, check status or success field
    return result.status === 'success' || result.success === true;
  };

  /**
   * Determines if a result represents an error
   */
  const isErrorResult = (result: ExecutionResult | string): boolean => {
    if (typeof result === 'string') {
      const lowerResult = result.toLowerCase();
      return (
        lowerResult.includes('error') ||
        lowerResult.includes('failed') ||
        lowerResult.includes('not found')
      );
    }
    return result.status === 'error' || result.success === false;
  };

  /**
   * Gets the display message from a result
   */
  const getResultMessage = (result: ExecutionResult | string): string => {
    if (typeof result === 'string') {
      return result;
    }
    return result.message || JSON.stringify(result);
  };

  /**
   * Gets the appropriate icon for a result
   */
  const getResultIcon = (result: ExecutionResult | string) => {
    if (isErrorResult(result)) {
      return <ErrorIcon sx={{ color: '#ef4444' }} />;
    }
    if (isSuccessResult(result)) {
      return <CheckCircle sx={{ color: '#76B900' }} />;
    }
    return <Info sx={{ color: '#3b82f6' }} />;
  };

  /**
   * Gets the appropriate styling for a result item
   */
  const getResultStyles = (result: ExecutionResult | string) => {
    if (isErrorResult(result)) {
      return {
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
      };
    }
    if (isSuccessResult(result)) {
      return {
        backgroundColor: 'rgba(118, 185, 0, 0.1)',
        border: '1px solid rgba(118, 185, 0, 0.3)',
      };
    }
    return {
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      border: '1px solid rgba(59, 130, 246, 0.3)',
    };
  };

  return (
    <Paper
      sx={{
        p: 3,
        backgroundColor: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid rgba(118, 185, 0, 0.2)',
      }}
    >
      <Typography
        variant="h6"
        gutterBottom
        sx={{
          color: '#76B900',
          fontWeight: 600,
          mb: 2,
          display: 'flex',
          alignItems: 'center',
        }}
      >
        Execution Results
      </Typography>

      <List sx={{ p: 0 }}>
        {results.map((result, index) => (
          <React.Fragment key={index}>
            <ListItem
              className="result-item"
              sx={{
                ...getResultStyles(result),
                borderRadius: 1,
                mb: 1.5,
                transition: 'all 0.2s ease',
                '&:hover': {
                  transform: 'translateX(4px)',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>
                {getResultIcon(result)}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Typography
                    variant="body2"
                    sx={{
                      wordBreak: 'break-word',
                      lineHeight: 1.6,
                    }}
                  >
                    {getResultMessage(result)}
                  </Typography>
                }
                secondary={
                  typeof result !== 'string' && result.details ? (
                    <Typography
                      variant="caption"
                      sx={{
                        display: 'block',
                        mt: 0.5,
                        color: 'text.secondary',
                        fontStyle: 'italic',
                      }}
                    >
                      {result.details}
                    </Typography>
                  ) : null
                }
              />
            </ListItem>
            {index < results.length - 1 && (
              <Divider
                sx={{
                  my: 0.5,
                  borderColor: 'rgba(118, 185, 0, 0.1)',
                }}
              />
            )}
          </React.Fragment>
        ))}
      </List>

      {/* Summary counts */}
      <Box
        sx={{
          mt: 2,
          pt: 2,
          borderTop: '1px solid rgba(118, 185, 0, 0.2)',
          display: 'flex',
          justifyContent: 'space-around',
          flexWrap: 'wrap',
          gap: 2,
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="h4" sx={{ color: '#76B900', fontWeight: 'bold' }}>
            {results.filter(isSuccessResult).length}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Successful
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="h4" sx={{ color: '#ef4444', fontWeight: 'bold' }}>
            {results.filter(isErrorResult).length}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Failed
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="h4" sx={{ color: '#3b82f6', fontWeight: 'bold' }}>
            {results.length}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Total
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default ExecutionResults;
