"""
Configuration management for the Router Network Interface Monitor.
Handles loading configuration from files and environment variables.
"""

import os
import sys
import configparser
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration settings for the router monitor."""
    community: str
    port: int
    timeout: int
    retries: int
    db_host: str
    db_user: str
    db_password: str
    db_name: str
    max_concurrent_routers: int
    partition_interval_days: int
    failed_routers_file: str
    db_pool_size: int
    db_pool_max_size: int
    db_connection_timeout: int
    request_interval: float = 0.1

def load_config() -> Config:
    """Load configuration from config.ini file."""
    config_parser = configparser.ConfigParser()
    
    # Set default values
    default_config = {
        'snmp': {
            'community': 'public',
            'port': '161',
            'timeout': '2',
            'retries': '2',
            'request_interval': '0.1'
        },
        'database': {
            'host': 'localhost',
            'user': 'router_monitor',
            'password': 'password',
            'name': 'router_monitor',
            'pool_size': '5',
            'pool_max_size': '10',
            'connection_timeout': '10'
        },
        'monitor': {
            'max_concurrent_routers': '10',
            'partition_interval_days': '30',
            'failed_routers_file': 'failed_routers.txt'
        }
    }
    
    # Load default values
    config_parser.read_dict(default_config)
    
    # Try to read from config file
    if os.path.exists('config.ini'):
        config_parser.read('config.ini')
    else:
        logger.warning("Config file 'config.ini' not found, using default values")
        # Create default config file
        with open('config.ini', 'w') as config_file:
            config_parser.write(config_file)
        logger.info("Created default config file 'config.ini'")
    
    # Extract values from config
    try:
        config = Config(
            community=config_parser.get('snmp', 'community'),
            port=config_parser.getint('snmp', 'port'),
            timeout=config_parser.getint('snmp', 'timeout'),
            retries=config_parser.getint('snmp', 'retries'),
            db_host=config_parser.get('database', 'host'),
            db_user=config_parser.get('database', 'user'),
            db_password=config_parser.get('database', 'password'),
            db_name=config_parser.get('database', 'name'),
            max_concurrent_routers=config_parser.getint('monitor', 'max_concurrent_routers'),
            partition_interval_days=config_parser.getint('monitor', 'partition_interval_days'),
            failed_routers_file=config_parser.get('monitor', 'failed_routers_file'),
            db_pool_size=config_parser.getint('database', 'pool_size'),
            db_pool_max_size=config_parser.getint('database', 'pool_max_size'),
            db_connection_timeout=config_parser.getint('database', 'connection_timeout'),
            request_interval=config_parser.getfloat('snmp', 'request_interval')
        )
        
        return config
    except (configparser.Error, ValueError) as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)