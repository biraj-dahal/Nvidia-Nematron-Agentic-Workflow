"""
Custom logging configuration with color-coded output and aligned formatting.
Provides human-readable colored logs for terminal output while keeping plain text for file logs.
"""

import logging
import sys
from colorama import Fore, Back, Style, init

# Initialize colorama for cross-platform color support
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color-coded log levels and aligned columns."""

    # Color mapping for log levels
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    # Level names with fixed width (right-aligned)
    LEVEL_NAMES = {
        logging.DEBUG: "DEBUG   ",
        logging.INFO: "INFO    ",
        logging.WARNING: "WARNING ",
        logging.ERROR: "ERROR   ",
        logging.CRITICAL: "CRITICAL",
    }

    def format(self, record):
        """Format log record with colors and aligned columns."""
        # Get color and level name
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        level_name = self.LEVEL_NAMES.get(record.levelno, record.levelname.ljust(8))

        # Create timestamp (no color, just plain white)
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        # Format: [TIMESTAMP] [COLORED_LEVEL] [MODULE] Message
        formatted_message = (
            f"{timestamp} "
            f"[{color}{level_name}{Style.RESET_ALL}] "
            f"{Fore.LIGHTBLACK_EX}{record.name:20s}{Style.RESET_ALL} "
            f"- {record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            formatted_message += f"\n{record.exc_text}"

        return formatted_message


class PlainFormatter(logging.Formatter):
    """Plain text formatter for file output (no colors)."""

    def format(self, record):
        """Format log record without colors."""
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level_name = record.levelname.ljust(8)

        formatted_message = (
            f"{timestamp} [{level_name}] {record.name:20s} - {record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            formatted_message += f"\n{record.exc_text}"

        return formatted_message


def configure_logging(name: str = None, log_level: int = logging.INFO):
    """
    Configure logging with colored console output and plain text file output.

    Args:
        name: Logger name (typically __name__)
        log_level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # CRITICAL: Prevent propagation to root logger (Gunicorn)
    # This stops duplicate logs from appearing with different formatters
    logger.propagate = False

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    return logger


def log_section_header(logger, message: str):
    """
    Log a formatted section header to separate major operations.

    Args:
        logger: Logger instance
        message: Header message
    """
    separator = "=" * 70
    logger.info(separator)
    logger.info(f"  {message}")
    logger.info(separator)


def log_section_footer(logger):
    """Log a formatted section footer separator."""
    separator = "=" * 70
    logger.info(separator)
