import logging

class CustomFormatter(logging.Formatter):
    """
    A custom log formatter that uses different formats for each log level
    """

    def __init__(self, formats: dict):
        """
        Initializes the formatter with a dictionary of formats

        Attributes:
            formats (dict): a dictionary mapping log levels (e.g., logging.INFO) to format strings
        """
        super().__init__()
        self.formats = formats
        # Separate formatter for messages without header
        self.plain_formatter = logging.Formatter('%(message)s')

    def format(self, extra: dict):
        """
        Overrides the default format method.

        Checks for a 'no_header' flag in the log record's 'extra' data.
        If 'no_header' is True, it formats the message without a header.
        Otherwise, it uses the level-specific format.

        Attributes:
            extra: optional attributes to customize formatting
        """
        # Check if the 'no_header' flag was passed in the 'extra' dictionary
        if hasattr(extra, 'no_header') and extra.no_header:
            return self.plain_formatter.format(extra)

        # If no flag, use the original logic to apply the level-specific header
        log_fmt = self.formats.get(extra.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(extra)

