from dataclasses import dataclass, field

@dataclass
class LoggerColors:
    """
    Class reprenting the ANSI escape color codes for the terminal
    """

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

