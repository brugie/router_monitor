import logging


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return a logger for the application."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("monitor.log"),
            logging.StreamHandler()
        ],
    )
    
    logger = logging.getLogger("router_monitor")
    logger.setLevel(log_level)
    
    if verbose:
        logger.debug("Verbose logging enabled")
    
    return logger