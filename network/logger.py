import logging
from dataclasses import dataclass, field


@dataclass
class LoggerColors:
    
    # Styles
    RESET: str = field(default='\033[0m')
    BOLD: str = field(default='\033[1m')
    ITALIC: str = field(default='\033[3m')
    UNDERLINE: str = field(default='\033[4m')
    STRIKETHROUGH: str = field(default='\033[9m')

    # Colors
    RED: str = field(default='\033[31m')
    GREEN: str = field(default='\033[32m')
    YELLOW: str = field(default='\033[33m')
    BLUE: str = field(default='\033[34m')
    MAGENTA: str = field(default='\033[35m')
    CYAN: str = field(default='\033[36m')


# A custom log formatter that uses different formats for each log level
class CustomFormatter(logging.Formatter):

    # Initializes the formatter with a dictionary of formats
    def __init__(self, formats: dict):

        super().__init__()
        self.formats = formats
        # Separate formatter for messages without header
        self.plain_formatter = logging.Formatter('%(message)s')

    # Overrides the default format method.
    def format(self, extra: dict) -> str:

        # Check if the 'no_header' flag was passed in the 'extra' dictionary
        if hasattr(extra, 'no_header') and extra.no_header:
            return self.plain_formatter.format(extra)

        # If no flag, use the original logic to apply the level-specific header
        log_fmt = self.formats.get(extra.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(extra)

# Configure the custom logger
def setup_logger():

    logger = logging.getLogger('networking')
    
    # Custom format headers
    log_headers = {
        logging.DEBUG:   f"{LoggerColors.BOLD} *** [DEBUG   ]:{LoggerColors.RESET} %(msg)s",
        logging.INFO:    f"{LoggerColors.BOLD}{LoggerColors.BLUE} *** [INFO    ]:{LoggerColors.RESET} %(msg)s",
        logging.WARNING: f"{LoggerColors.BOLD}{LoggerColors.YELLOW} *** [WARNING ]:{LoggerColors.RESET} %(msg)s",
        logging.ERROR:   f"{LoggerColors.BOLD}{LoggerColors.RED} *** [ERROR   ]:{LoggerColors.RESET} %(msg)s",
        logging.CRITICAL:f"{LoggerColors.BOLD}{LoggerColors.MAGENTA} *** [CRITICAL]:{LoggerColors.RESET} %(msg)s",
    }

    # Set log level
    logger.setLevel(logging.INFO)

    # Create handler with custsom formatter
    handler = logging.StreamHandler()
    handler.terminator = ''
    custom_formatter = CustomFormatter(formats=log_headers)
    handler.setFormatter(custom_formatter)

    # Add custom handler
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger
