"""
Database connection management for the Router Network Interface Monitor.
Provides a connection pool and context manager for database connections.
"""

import logging
import time
from contextlib import contextmanager
from typing import Optional

import mysql.connector
from mysql.connector import Error, pooling

from ..config import Config

logger = logging.getLogger(__name__)

# Global connection pool
connection_pool = None

def initialize_connection_pool(config: Config):
    """Initialize the database connection pool."""
    global connection_pool
    
    if connection_pool is not None:
        logger.debug("Connection pool already initialized")
        return
    
    try:
        logger.info(f"Initializing database connection pool with size {config.db_pool_size}-{config.db_pool_max_size}")
        
        # Create a pool name using the database credentials to ensure uniqueness
        pool_name = f"router_monitor_pool_{config.db_host}_{config.db_name}"
        
        pool_config = {
            "pool_name": pool_name,
            "pool_size": config.db_pool_size,
            "pool_reset_session": True,
            "host": config.db_host,
            "user": config.db_user,
            "password": config.db_password,
            "database": config.db_name,
            "use_pure": True,
            "connection_timeout": config.db_connection_timeout,
            "autocommit": False,
        }
        
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
        logger.info("Database connection pool initialized successfully")
        
    except Error as e:
        logger.error(f"Error initializing connection pool: {e}")
        raise

@contextmanager
def db_connection(config: Config):
    """Context manager for database connection from pool."""
    global connection_pool
    connection = None
    
    # Initialize pool if it doesn't exist
    if connection_pool is None:
        initialize_connection_pool(config)
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Get connection from pool
            connection = connection_pool.get_connection()
            logger.debug("Acquired connection from pool")
            yield connection
            break
        except Error as e:
            retry_count += 1
            logger.error(f"Error getting connection from pool (attempt {retry_count}/{max_retries}): {e}")
            if retry_count >= max_retries:
                raise
            # Brief pause before retrying
            time.sleep(0.5)
        finally:
            if connection:
                try:
                    # Return the connection to the pool
                    connection.close()
                    logger.debug("Returned connection to pool")
                except Error as e:
                    logger.warning(f"Error returning connection to pool: {e}")

def execute_with_retry(cursor, query, params=None, max_retries=3):
    """Execute a database query with retry logic."""
    retry_count = 0
    while retry_count < max_retries:
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return True
        except Error as e:
            retry_count += 1
            backoff = 0.5 * (2 ** retry_count)  # Exponential backoff
            logger.warning(f"Database query failed (attempt {retry_count}/{max_retries}): {e}")
            if retry_count >= max_retries:
                raise
            time.sleep(backoff)
    return False