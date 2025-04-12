#!/usr/bin/env python3
"""
Parsers for SNMP response values.
"""

import re
from typing import Union, Dict, Any


def parse_snmp_value(value_str: str) -> Union[str, int, float]:
    """
    Parse SNMP value string into appropriate Python type.
    
    Args:
        value_str: SNMP response value as string
        
    Returns:
        Union[str, int, float]: Parsed value in appropriate Python type
    """
    # Empty string handling
    if not value_str or value_str == "STRING:":
        return ""
        
    # String value (quoted)
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
        
    # INTEGER
    int_match = re.search(r'INTEGER:\s*(\d+)', value_str)
    if int_match:
        return int(int_match.group(1))
        
    # Counter32, Counter64, Gauge32
    counter_match = re.search(r'(Counter32|Counter64|Gauge32):\s*(\d+)', value_str)
    if counter_match:
        return int(counter_match.group(2))
        
    # Timeticks
    timeticks_match = re.search(r'Timeticks:\s*\((\d+)\)', value_str)
    if timeticks_match:
        return int(timeticks_match.group(1))
        
    # Hex-STRING for MAC addresses
    hex_match = re.search(r'Hex-STRING:\s*([0-9A-Fa-f\s]+)', value_str)
    if hex_match:
        # Convert space-separated hex values to MAC format
        hex_values = hex_match.group(1).strip().split()
        if len(hex_values) == 6:  # MAC address
            return ":".join(hex_values)
        return hex_match.group(1).strip()
        
    # IpAddress
    ip_match = re.search(r'IpAddress:\s*(\d+\.\d+\.\d+\.\d+)', value_str)
    if ip_match:
        return ip_match.group(1)
        
    # Try direct conversion to int or float
    try:
        return int(value_str)
    except ValueError:
        try:
            return float(value_str)
        except ValueError:
            # Return as string if all else fails
            return value_str


def parse_snmp_walk_response(output: str) -> Dict[str, Any]:
    """
    Parse the output of an SNMP walk command into a dictionary.
    
    Args:
        output: Output string from snmpwalk command
        
    Returns:
        Dict[str, Any]: Dictionary with OID indices as keys and parsed values
    """
    result = {}
    
    # Process each line of output
    for line in output.split('\n'):
        if not line.strip():
            continue
            
        # Parse the OID and value
        parts = line.split('=', 1)
        if len(parts) != 2:
            continue
            
        full_oid = parts[0].strip()
        value_part = parts[1].strip()
        
        # Extract the index from the OID
        oid_parts = full_oid.split('.')
        if len(oid_parts) > 0:
            index = oid_parts[-1]
        else:
            continue
        
        # Parse the value using the helper function
        result[index] = parse_snmp_value(value_part)
    
    return result