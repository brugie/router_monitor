"""
Data Access Object for router operations.
Handles database operations related to routers.
"""

import logging
from typing import Dict, Any, Optional, List

from mysql.connector import Error

from ..config import Config
from .connection import db_connection, execute_with_retry

logger = logging.getLogger(__name__)

async def save_router(router_ip: str, router_info: Dict[str, Any], config: Config) -> Optional[int]:
    """
    Save or update router information in the database.
    
    Args:
        router_ip: IP address of the router
        router_info: Router information dictionary
        config: Application configuration
        
    Returns:
        Optional[int]: Router ID if successful, None otherwise
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor()
            
            # Check if router exists
            execute_with_retry(
                cursor,
                "SELECT router_id FROM routers WHERE ip_address = %s",
                (router_ip,)
            )
            result = cursor.fetchone()
            
            if result:
                # Update existing router
                router_id = result[0]
                execute_with_retry(
                    cursor,
                    """
                    UPDATE routers 
                    SET sysName = %s, sysDescr = %s, sysUpTime = %s, 
                        sysLocation = %s, sysContact = %s, sysObjectID = %s 
                    WHERE router_id = %s
                    """,
                    (
                        router_info.get('sysName'),
                        router_info.get('sysDescr'),
                        router_info.get('sysUpTime'),
                        router_info.get('sysLocation'),
                        router_info.get('sysContact'),
                        router_info.get('sysObjectID'),
                        router_id
                    )
                )
                logger.info(f"Updated router information for {router_ip} (ID: {router_id})")
            else:
                # Insert new router
                execute_with_retry(
                    cursor,
                    """
                    INSERT INTO routers 
                    (ip_address, sysName, sysDescr, sysUpTime, sysLocation, sysContact, sysObjectID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        router_ip,
                        router_info.get('sysName'),
                        router_info.get('sysDescr'),
                        router_info.get('sysUpTime'),
                        router_info.get('sysLocation'),
                        router_info.get('sysContact'),
                        router_info.get('sysObjectID')
                    )
                )
                router_id = cursor.lastrowid
                logger.info(f"Inserted new router {router_ip} with ID {router_id}")
            
            connection.commit()
            return router_id
            
    except Error as e:
        logger.error(f"Database error saving router: {e}")
        return None

def save_failed_routers(failed_routers: List[str], filename: str):
    """Save failed router IP addresses to a file."""
    try:
        with open(filename, 'w') as file:
            for router_ip in failed_routers:
                file.write(f"{router_ip}\n")
        logger.info(f"Saved {len(failed_routers)} failed routers to {filename}")
    except Exception as e:
        logger.error(f"Error saving failed routers to {filename}: {e}")