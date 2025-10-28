import { createTheme, ThemeOptions } from '@mui/material/styles';

const NVIDIA_GREEN = '#76B900';
const NVIDIA_GREEN_LIGHT = '#92e000';
const DARK_BG = '#000000';
const CARD_BG = '#1a1a1a';
const BORDER_COLOR = '#444444';

const themeOptions: ThemeOptions = {
  palette: {
    mode: 'dark',
    primary: {
      main: NVIDIA_GREEN,
      light: NVIDIA_GREEN_LIGHT,
      dark: '#5a8a00',
      contrastText: DARK_BG,
    },
    secondary: {
      main: '#2196F3',
      light: '#64B5F6',
      dark: '#1565C0',
    },
    background: {
      default: DARK_BG,
      paper: CARD_BG,
    },
    error: {
      main: '#F44336',
      light: '#EF5350',
      dark: '#C62828',
    },
    success: {
      main: '#4CAF50',
      light: '#81C784',
      dark: '#2E7D32',
    },
    warning: {
      main: '#FF9800',
      light: '#FFB74D',
      dark: '#E65100',
    },
    info: {
      main: '#2196F3',
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#CCCCCC',
    },
    divider: BORDER_COLOR,
  },
  typography: {
    fontFamily: "'Roboto', 'Arial', sans-serif",
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
      letterSpacing: '0.15rem',
      color: NVIDIA_GREEN,
      textShadow: `0 0 15px rgba(118, 185, 0, 0.5)`,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      color: NVIDIA_GREEN,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
      color: NVIDIA_GREEN,
    },
    body1: {
      fontSize: '1rem',
      color: '#FFFFFF',
    },
    body2: {
      fontSize: '0.875rem',
      color: '#CCCCCC',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'uppercase',
          fontWeight: 600,
          borderRadius: '5px',
          transition: 'all 0.3s ease',
          '&:hover': {
            boxShadow: `0 0 20px ${NVIDIA_GREEN}`,
          },
        },
        contained: {
          '&:active': {
            transform: 'translateY(1px)',
          },
        },
      },
      defaultProps: {
        disableElevation: false,
      },
    },
    MuiButtonBase: {
      defaultProps: {
        disableRipple: false,
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: CARD_BG,
          border: `1px solid ${BORDER_COLOR}`,
          borderRadius: '8px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: NVIDIA_GREEN,
            boxShadow: `0 6px 12px rgba(118, 185, 0, 0.2)`,
            transform: 'translateY(-2px)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: CARD_BG,
          backgroundImage: 'none',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: CARD_BG,
          borderBottom: `2px solid ${NVIDIA_GREEN}`,
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.3)',
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: {
          '& input': {
            color: '#FFFFFF',
            '&::placeholder': {
              color: '#888888',
              opacity: 1,
            },
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          '& fieldset': {
            borderColor: BORDER_COLOR,
          },
          '&:hover fieldset': {
            borderColor: NVIDIA_GREEN,
          },
          '&.Mui-focused fieldset': {
            borderColor: NVIDIA_GREEN,
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          '&.Mui-checked': {
            color: NVIDIA_GREEN,
          },
        },
      },
    },
  },
};

export const nvidiaTheme = createTheme(themeOptions);
