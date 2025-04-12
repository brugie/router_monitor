"""
Interface Data Access Object (DAO) Module

This module provides database operations for network interfaces and their statistics.
It handles CRUD operations for interfaces and batch operations for interface statistics.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, time
import mysql.connector
from mysql.connector import Error

from .connection import db_connection, execute_with_retry

logger = logging.getLogger(__name__)


async def get_interface_by_id(interface_id: int, config) -> Optional[Dict[str, Any]]:
    """
    Retrieve interface details by interface ID.
    
    Args:
        interface_id: The unique ID of the interface
        config: Application configuration
        
    Returns:
        Optional[Dict[str, Any]]: Interface information or None if not found
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor(dictionary=True)
            execute_with_retry(
                cursor,
                """
                SELECT * FROM interfaces WHERE interface_id = %s
                """,
                (interface_id,)
            )
            result = cursor.fetchone()
            return result
    except Error as e:
        logger.error(f"Database error retrieving interface {interface_id}: {e}")
        return None


async def get_interfaces_by_router_id(router_id: int, config) -> List[Dict[str, Any]]:
    """
    Retrieve all interfaces for a specific router.
    
    Args:
        router_id: The ID of the router
        config: Application configuration
        
    Returns:
        List[Dict[str, Any]]: List of interface dictionaries
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor(dictionary=True)
            execute_with_retry(
                cursor,
                """
                SELECT * FROM interfaces WHERE router_id = %s
                ORDER BY ifIndex
                """,
                (router_id,)
            )
            return cursor.fetchall()
    except Error as e:
        logger.error(f"Database error retrieving interfaces for router {router_id}: {e}")
        return []


async def get_interface_id_map(router_id: int, config) -> Dict[str, int]:
    """
    Get mapping between interface indices and their database IDs for a router.
    
    Args:
        router_id: The ID of the router
        config: Application configuration
        
    Returns:
        Dict[str, int]: Dictionary mapping ifIndex to interface_id
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor()
            execute_with_retry(
                cursor,
                "SELECT interface_id, ifIndex FROM interfaces WHERE router_id = %s",
                (router_id,)
            )
            
            interface_map = {}
            for row in cursor.fetchall():
                interface_map[row[1]] = row[0]  # Map ifIndex to interface_id
                
            return interface_map
    except Error as e:
        logger.error(f"Database error getting interface ID map for router {router_id}: {e}")
        return {}


async def save_or_update_interfaces(router_id: int, interfaces: Dict[str, Dict[str, Any]], config) -> bool:
    """
    Save or update interfaces for a router in the database.
    
    Args:
        router_id: The ID of the router these interfaces belong to
        interfaces: Dictionary of interfaces keyed by ifIndex
        config: Application configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor()
            
            # Process interfaces
            for if_index, interface in interfaces.items():
                # Check if interface exists
                execute_with_retry(
                    cursor,
                    "SELECT interface_id FROM interfaces WHERE router_id = %s AND ifIndex = %s",
                    (router_id, if_index)
                )
                if_result = cursor.fetchone()
                
                if if_result:
                    # Update existing interface
                    interface_id = if_result[0]
                    execute_with_retry(
                        cursor,
                        """
                        UPDATE interfaces 
                        SET ifName = %s, ifDescr = %s, ifType = %s, ifMTU = %s,
                            ifSpeed = %s, ifPhysAddress = %s, ifHighSpeed = %s,
                            ifAlias = %s, ipAddresses = %s
                        WHERE interface_id = %s
                        """,
                        (
                            interface.get('ifName'),
                            interface.get('ifDescr'),
                            interface.get('ifType'),
                            interface.get('ifMTU'),
                            interface.get('ifSpeed'),
                            interface.get('ifPhysAddress'),
                            interface.get('ifHighSpeed'),
                            interface.get('ifAlias'),
                            interface.get('ipAddresses'),
                            interface_id
                        )
                    )
                    logger.debug(f"Updated interface {if_index} for router {router_id}")
                else:
                    # Insert new interface
                    execute_with_retry(
                        cursor,
                        """
                        INSERT INTO interfaces
                        (router_id, ifIndex, ifName, ifDescr, ifType, ifMTU,
                         ifSpeed, ifPhysAddress, ifHighSpeed, ifAlias, ipAddresses)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            router_id,
                            if_index,
                            interface.get('ifName'),
                            interface.get('ifDescr'),
                            interface.get('ifType'),
                            interface.get('ifMTU'),
                            interface.get('ifSpeed'),
                            interface.get('ifPhysAddress'),
                            interface.get('ifHighSpeed'),
                            interface.get('ifAlias'),
                            interface.get('ipAddresses')
                        )
                    )
                    logger.debug(f"Inserted new interface {if_index} for router {router_id}")
            
            connection.commit()
            logger.info(f"Saved {len(interfaces)} interfaces for router {router_id}")
            return True
            
    except Error as e:
        logger.error(f"Database error saving interfaces for router {router_id}: {e}")
        return False


async def save_interface_stats_batch(interfaces_data: List[Dict[str, Any]], router_id: int, config) -> bool:
    """
    Save interface statistics in batch mode for better performance.
    
    Args:
        interfaces_data: List of interface data dictionaries
        router_id: The ID of the router these interfaces belong to
        config: Application configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # First, get all interface IDs for this router
            interface_map = await get_interface_id_map(router_id, config)
            
            if not interface_map:
                logger.error(f"No interfaces found in database for router_id {router_id}")
                return False
            
            # Prepare batch insert for interface stats
            stats_values = []
            for interface in interfaces_data:
                if_index = interface.get('ifIndex')
                if if_index not in interface_map:
                    logger.warning(f"Interface with index {if_index} not found in database for router_id {router_id}")
                    continue
                
                interface_id = interface_map[if_index]
                
                # Collect stats data - convert values to ensure they're numeric
                stats_values.append((
                    interface_id,
                    current_time,
                    int(interface.get('ifAdminStatus', 0) or 0),
                    int(interface.get('ifOperStatus', 0) or 0),
                    int(interface.get('ifInOctets', 0) or 0),
                    int(interface.get('ifOutOctets', 0) or 0),
                    int(interface.get('ifHCInOctets', 0) or 0),
                    int(interface.get('ifHCOutOctets', 0) or 0)
                ))
            
            # Insert stats in batch if we have any
            if stats_values:
                # Use executemany with retry for batch inserts
                max_retries = 3
                retry_count = 0
                success = False
                
                while retry_count < max_retries and not success:
                    try:
                        cursor.executemany(
                            """
                            INSERT INTO interface_stats 
                            (interface_id, timestamp, ifAdminStatus, ifOperStatus, 
                             ifInOctets, ifOutOctets, ifHCInOctets, ifHCOutOctets)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            stats_values
                        )
                        connection.commit()
                        success = True
                    except Error as e:
                        retry_count += 1
                        logger.error(f"Database error in batch insert (attempt {retry_count}/{max_retries}): {e}")
                        if retry_count >= max_retries:
                            raise
                        time.sleep(0.5 * (2 ** retry_count))  # Exponential backoff
                
                logger.info(f"Saved {len(stats_values)} interface statistics records")
                return success
            else:
                logger.warning(f"No valid interface statistics to save for router_id {router_id}")
                return False
                
    except Error as e:
        logger.error(f"Database error saving interface statistics: {e}")
        return False


async def get_interface_stats(interface_id: int, start_time: datetime, end_time: datetime, config) -> List[Dict[str, Any]]:
    """
    Retrieve interface statistics for a specific time range.
    
    Args:
        interface_id: The ID of the interface
        start_time: Beginning of time range
        end_time: End of time range
        config: Application configuration
        
    Returns:
        List[Dict[str, Any]]: Interface statistics records
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor(dictionary=True)
            execute_with_retry(
                cursor,
                """
                SELECT * FROM interface_stats 
                WHERE interface_id = %s AND timestamp BETWEEN %s AND %s
                ORDER BY timestamp
                """,
                (interface_id, start_time, end_time)
            )
            return cursor.fetchall()
    except Error as e:
        logger.error(f"Database error retrieving stats for interface {interface_id}: {e}")
        return []


async def delete_old_interface_stats(days_to_keep: int, config) -> bool:
    """
    Delete interface statistics older than a specified number of days.
    
    Args:
        days_to_keep: Keep statistics newer than this many days
        config: Application configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with db_connection(config) as connection:
            cursor = connection.cursor()
            execute_with_retry(
                cursor,
                """
                DELETE FROM interface_stats 
                WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
                """,
                (days_to_keep,)
            )
            deleted_count = cursor.rowcount
            connection.commit()
            logger.info(f"Deleted {deleted_count} old interface statistics records")
            return True
    except Error as e:
        logger.error(f"Database error deleting old statistics: {e}")
        return False


async def calculate_interface_utilization(interface_id: int, start_time: datetime, end_time: datetime, config) -> List[Dict[str, Any]]:
    """
    Calculate interface utilization over time.
    
    Args:
        interface_id: The ID of the interface
        start_time: Beginning of time range
        end_time: End of time range
        config: Application configuration
        
    Returns:
        List[Dict[str, Any]]: Interface utilization records with timestamp, in_utilization, out_utilization
    """
    try:
        # First get interface details to get the speed
        interface = await get_interface_by_id(interface_id, config)
        if not interface:
            logger.error(f"Interface {interface_id} not found")
            return []
        
        # Use ifHighSpeed if available, otherwise ifSpeed
        interface_speed = interface.get('ifHighSpeed', 0)
        if not interface_speed or interface_speed == 0:
            interface_speed = interface.get('ifSpeed', 0)
        
        if interface_speed == 0:
            logger.warning(f"Interface {interface_id} has zero speed, can't calculate utilization")
            return []
        
        # Get all statistics for this interface in the time range
        stats = await get_interface_stats(interface_id, start_time, end_time, config)
        if len(stats) < 2:
            logger.warning(f"Not enough data points to calculate utilization for interface {interface_id}")
            return []
        
        # Calculate utilization between each pair of consecutive samples
        utilization = []
        for i in range(1, len(stats)):
            prev = stats[i-1]
            curr = stats[i]
            
            # Calculate time difference in seconds
            time_diff = (curr['timestamp'] - prev['timestamp']).total_seconds()
            if time_diff <= 0:
                continue
            
            # Calculate byte differences, prefer HC counters
            in_bytes = curr['ifHCInOctets'] - prev['ifHCInOctets'] if curr['ifHCInOctets'] and prev['ifHCInOctets'] else curr['ifInOctets'] - prev['ifInOctets']
            out_bytes = curr['ifHCOutOctets'] - prev['ifHCOutOctets'] if curr['ifHCOutOctets'] and prev['ifHCOutOctets'] else curr['ifOutOctets'] - prev['ifOutOctets']
            
            # Handle counter resets
            if in_bytes < 0:
                in_bytes = curr['ifHCInOctets'] if curr['ifHCInOctets'] else curr['ifInOctets']
            if out_bytes < 0:
                out_bytes = curr['ifHCOutOctets'] if curr['ifHCOutOctets'] else curr['ifOutOctets']
            
            # Calculate bits per second
            in_bps = (in_bytes * 8) / time_diff
            out_bps = (out_bytes * 8) / time_diff
            
            # Calculate utilization as percentage of interface speed
            # interface_speed is in Mbps, convert to bps
            speed_bps = interface_speed * 1000000
            in_utilization = (in_bps / speed_bps) * 100 if speed_bps > 0 else 0
            out_utilization = (out_bps / speed_bps) * 100 if speed_bps > 0 else 0
            
            utilization.append({
                'timestamp': curr['timestamp'],
                'in_bps': in_bps,
                'out_bps': out_bps,
                'in_utilization': in_utilization,
                'out_utilization': out_utilization
            })
        
        return utilization
    except Exception as e:
        logger.error(f"Error calculating interface utilization: {e}")
        return []