#!/usr/bin/env python3
"""
SNMP client for executing snmpget and snmpwalk commands.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List

from .parsers import parse_snmp_value, parse_snmp_walk_response

# Configure logging
logger = logging.getLogger(__name__)


async def check_snmp_tools_installed() -> bool:
    """
    Check if net-snmp tools are installed.
    
    Returns:
        bool: True if snmpget is installed, False otherwise
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "snmpget", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return proc.returncode == 0
    except FileNotFoundError:
        logger.error("SNMP tools (net-snmp) not found. Please install net-snmp package.")
        return False


async def snmp_get(target: str, oid: str, community: str, port: int, timeout: int, retries: int) -> Optional[Any]:
    """
    Perform SNMP GET operation for a single OID using snmpget command.
    
    Args:
        target: Target IP address
        oid: OID to query
        community: SNMP community string
        port: SNMP port
        timeout: Timeout in seconds
        retries: Number of retries
    
    Returns:
        Optional[Any]: Parsed value or None if error occurred
    """
    cmd = [
        "snmpget", "-v2c", 
        "-c", community,
        "-r", str(retries),
        "-t", str(timeout),
        f"{target}:{port}", 
        oid
    ]
    
    try:
        # Run the snmpget command asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error = stderr.decode().strip()
            logger.warning(f"SNMP error for {target} OID {oid}: {error}")
            return None
        
        output = stdout.decode().strip()
        if "No Such Object" in output or "No Such Instance" in output:
            logger.warning(f"OID {oid} not found on {target}")
            return None
        
        # Extract the actual value using a regex to handle all cases
        import re
        match = re.search(r'=\s*(.+)$', output)
        if match:
            value_str = match.group(1).strip()
            return parse_snmp_value(value_str)
        
        logger.warning(f"Could not parse SNMP response: {output}")
        return output  # Return raw output if parsing failed
        
    except Exception as e:
        logger.warning(f"Error executing snmpget for {target} OID {oid}: {e}")
        return None


async def snmp_walk(target: str, oid: str, community: str, port: int, timeout: int, retries: int) -> Dict[str, Any]:
    """
    Perform SNMP WALK operation using snmpwalk command.
    
    Args:
        target: Target IP address
        oid: Base OID to walk
        community: SNMP community string
        port: SNMP port
        timeout: Timeout in seconds
        retries: Number of retries
    
    Returns:
        Dict[str, Any]: Dictionary with OID indices as keys and parsed values
    """
    cmd = [
        "snmpwalk", "-v2c",
        "-c", community,
        "-r", str(retries),
        "-t", str(timeout),
        f"{target}:{port}",
        oid
    ]
    
    try:
        # Run the snmpwalk command asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error = stderr.decode().strip()
            logger.warning(f"SNMP walk error for {target} OID {oid}: {error}")
            return {}
        
        output = stdout.decode().strip()
        return parse_snmp_walk_response(output)
        
    except Exception as e:
        logger.warning(f"Error executing snmpwalk for {target} OID {oid}: {e}")
        return {}


async def get_device_info(router_ip: str, community: str, port: int, timeout: int, retries: int, 
                         request_interval: float) -> Dict[str, Any]:
    """
    Get device (router) information based on system OIDs.
    
    Args:
        router_ip: IP address of the router
        community: SNMP community string
        port: SNMP port
        timeout: Timeout in seconds
        retries: Number of retries
        request_interval: Interval between requests to the same router
        
    Returns:
        Dict[str, Any]: Dictionary with router information
    """
    from .constants import OID_CONSTANTS
    
    device_info = {"ip_address": router_ip}
    for name, oid in OID_CONSTANTS.items():
        if name.startswith("sys"):  # Only get system info, not interface info
            value = await snmp_get(router_ip, oid, community, port, timeout, retries)
            device_info[name] = value if value is not None else "Error retrieving value"
            # Rate limiting
            await asyncio.sleep(request_interval)
    return device_info


async def get_ip_to_interface_mapping(router_ip: str, community: str, port: int, timeout: int, retries: int,
                                    request_interval: float) -> Dict[str, List[str]]:
    """
    Get mapping between IP addresses and interface indices.
    
    Args:
        router_ip: IP address of the router
        community: SNMP community string
        port: SNMP port
        timeout: Timeout in seconds
        retries: Number of retries
        request_interval: Interval between requests to the same router
        
    Returns:
        Dict[str, List[str]]: Dictionary with interface indices as keys and lists of IP addresses as values
    """
    from .constants import OID_CONSTANTS
    
    mapping = {}
    ip_addresses = await snmp_walk(router_ip, OID_CONSTANTS["ipAddress"], community, port, timeout, retries)
    await asyncio.sleep(request_interval)  # Rate limiting
    
    ip_to_if_indices = await snmp_walk(router_ip, OID_CONSTANTS["ipAdEntIfIndex"], community, port, timeout, retries)
    await asyncio.sleep(request_interval)  # Rate limiting

    for idx in ip_addresses:
        if idx in ip_to_if_indices:
            if_idx = str(ip_to_if_indices[idx])
            mapping.setdefault(if_idx, []).append(str(ip_addresses[idx]))
    
    return mapping


async def get_monitored_interfaces(router_ip: str, community: str, port: int, timeout: int, retries: int,
                                 request_interval: float) -> Dict[str, Dict[str, Any]]:
    """
    Get interfaces to monitor based on the specified interface types.
    
    Args:
        router_ip: IP address of the router
        community: SNMP community string
        port: SNMP port
        timeout: Timeout in seconds
        retries: Number of retries
        request_interval: Interval between requests to the same router
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary with interface indices as keys and interface data as values
    """
    from .constants import OID_CONSTANTS
    from ..models.interface import INTERFACE_TYPES_TO_MONITOR
    
    if_types = await snmp_walk(router_ip, OID_CONSTANTS["ifType"], community, port, timeout, retries)
    await asyncio.sleep(request_interval)  # Rate limiting
    
    if not if_types:
        logger.warning(f"No interface types found for router {router_ip}")
        return {}
    
    monitored_indices = []
    for index, if_type in if_types.items():
        try:
            if_type_int = int(if_type)
            if if_type_int in INTERFACE_TYPES_TO_MONITOR:
                monitored_indices.append(index)
                logger.debug(f"Found interface type {if_type_int} ({INTERFACE_TYPES_TO_MONITOR[if_type_int]}) on index {index}")
        except (ValueError, TypeError):
            logger.warning(f"Invalid interface type value for index {index}: {if_type}")

    if not monitored_indices:
        logger.info(f"No monitored interface types found for router {router_ip}")
        return {}
    
    logger.info(f"Found {len(monitored_indices)} monitored interfaces for router {router_ip}")
    
    interfaces = {
        index: {
            "ifIndex": index, 
            "ifType": f"{if_types[index]} ({INTERFACE_TYPES_TO_MONITOR.get(int(if_types[index]), 'Unknown')})"
        } for index in monitored_indices
    }
    
    # Get other interface attributes
    for name, oid in OID_CONSTANTS.items():
        if name in ["ifIndex", "ifType"] or name.startswith("sys"):
            continue
            
        values = await snmp_walk(router_ip, oid, community, port, timeout, retries)
        await asyncio.sleep(request_interval)  # Rate limiting
        
        for index in monitored_indices:
            if index in values:
                interfaces[index][name] = values[index]
            else:
                interfaces[index][name] = None
    
    # Add IP addresses to interfaces
    ip_if_mapping = await get_ip_to_interface_mapping(router_ip, community, port, timeout, retries, request_interval)
    for index in interfaces:
        interfaces[index]["ipAddresses"] = ", ".join(ip_if_mapping.get(index, []))
    
    return interfaces