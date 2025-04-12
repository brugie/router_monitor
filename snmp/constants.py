#!/usr/bin/env python3
"""
Constants for SNMP OIDs and other SNMP-related settings.
"""

# OID Constants for SNMP queries
OID_CONSTANTS = {
    # System information
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    "sysLocation": "1.3.6.1.2.1.1.6.0",
    "sysContact": "1.3.6.1.2.1.1.4.0",
    "sysObjectID": "1.3.6.1.2.1.1.2.0",
    
    # IP address information
    "ipAddress": "1.3.6.1.2.1.4.20.1.1",
    "ipAdEntIfIndex": "1.3.6.1.2.1.4.20.1.2",
    
    # Interface information
    "ifIndex": "1.3.6.1.2.1.2.2.1.1",
    "ifDescr": "1.3.6.1.2.1.2.2.1.2",
    "ifName": "1.3.6.1.2.1.31.1.1.1.1",
    "ifType": "1.3.6.1.2.1.2.2.1.3",
    "ifMTU": "1.3.6.1.2.1.2.2.1.4",
    "ifSpeed": "1.3.6.1.2.1.2.2.1.5",
    "ifPhysAddress": "1.3.6.1.2.1.2.2.1.6",
    "ifAdminStatus": "1.3.6.1.2.1.2.2.1.7",
    "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",
    
    # Traffic counters
    "ifInOctets": "1.3.6.1.2.1.2.2.1.10",
    "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",
    "ifHCInOctets": "1.3.6.1.2.1.31.1.1.1.6",
    "ifHCOutOctets": "1.3.6.1.2.1.31.1.1.1.10",
    
    # High-speed interfaces
    "ifHighSpeed": "1.3.6.1.2.1.31.1.1.1.15",
    "ifAlias": "1.3.6.1.2.1.31.1.1.1.18",
}

# Default SNMP settings
DEFAULT_SNMP_PORT = 161
DEFAULT_SNMP_COMMUNITY = "public"
DEFAULT_SNMP_TIMEOUT = 2
DEFAULT_SNMP_RETRIES = 2

# Admin and operational status codes
INTERFACE_STATUS = {
    # Admin status values
    "ifAdminStatus": {
        1: "up",
        2: "down",
        3: "testing"
    },
    # Operational status values
    "ifOperStatus": {
        1: "up",
        2: "down",
        3: "testing",
        4: "unknown",
        5: "dormant",
        6: "notPresent",
        7: "lowerLayerDown"
    }
}