import React from 'react';
import ReactDOM from 'react-dom/client';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import './index.css';
import App from './App';
import { nvidiaTheme } from './theme/nvidiaTheme';
import { WorkflowProvider } from './context/WorkflowContext';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <ThemeProvider theme={nvidiaTheme}>
      <CssBaseline />
      <WorkflowProvider>
        <App />
      </WorkflowProvider>
    </ThemeProvider>
  </React.StrictMode>
);

reportWebVitals();
