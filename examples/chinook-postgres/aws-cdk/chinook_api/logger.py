import logging
import os

# Configuring the logging module with basic settings, including format and log level,
# where the log level is obtained from the environment variable LOGGING_LEVEL
# with a default of DEBUG, and force=True to ensure the configuration is applied immediately.
logging.basicConfig(
    format="%(name)s:%(lineno)s - %(levelname)s - %(message)s",
    level=os.getenv("LOGGING_LEVEL", "DEBUG").upper(),
    force=True,
)


def logger(name=None):
    """
    Function to create a logger with a specified name or default name.

    Parameters:
        name (str): Name of the logger. If not provided, the root logger is returned.

    Returns:
        logging.Logger: Logger object with the specified name or the root logger.

    """
    # Retrieving the logging level from the environment variable LOGGING_LEVEL
    # with a default of DEBUG, and converting it to uppercase
    loggingLevel = os.getenv("LOGGING_LEVEL", "DEBUG").upper()

    # Setting the logging level for the root logger to the obtained logging level
    logging.getLogger().setLevel(loggingLevel)

    # Returning a logger object with the specified name or the root logger
    return logging.getLogger(name)

INFO = logging.INFO
DEBUG = logging.DEBUG
