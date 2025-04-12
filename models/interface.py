from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class Interface:
    """Interface model representing a network interface on a router."""
    if_index: str
    if_type: str
    router_id: Optional[int] = None
    if_name: Optional[str] = None
    if_descr: Optional[str] = None
    if_mtu: Optional[int] = None
    if_speed: Optional[int] = None
    if_phys_address: Optional[str] = None
    if_high_speed: Optional[int] = None
    if_alias: Optional[str] = None
    ip_addresses: Optional[str] = None
    interface_id: Optional[int] = None
    last_update: Optional[datetime] = None
    if_admin_status: Optional[int] = None
    if_oper_status: Optional[int] = None
    if_in_octets: Optional[int] = None
    if_out_octets: Optional[int] = None
    if_hc_in_octets: Optional[int] = None
    if_hc_out_octets: Optional[int] = None

    @classmethod
    def from_snmp_data(cls, if_index: str, data: Dict[str, Any]) -> 'Interface':
        """Create an Interface instance from SNMP data."""
        return cls(
            if_index=if_index,
            if_type=data.get('ifType', ''),
            if_name=data.get('ifName'),
            if_descr=data.get('ifDescr'),
            if_mtu=data.get('ifMTU'),
            if_speed=data.get('ifSpeed'),
            if_phys_address=data.get('ifPhysAddress'),
            if_high_speed=data.get('ifHighSpeed'),
            if_alias=data.get('ifAlias'),
            ip_addresses=data.get('ipAddresses'),
            if_admin_status=data.get('ifAdminStatus'),
            if_oper_status=data.get('ifOperStatus'),
            if_in_octets=data.get('ifInOctets'),
            if_out_octets=data.get('ifOutOctets'),
            if_hc_in_octets=data.get('ifHCInOctets'),
            if_hc_out_octets=data.get('ifHCOutOctets')
        )

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            'router_id': self.router_id,
            'ifIndex': self.if_index,
            'ifName': self.if_name,
            'ifDescr': self.if_descr,
            'ifType': self.if_type,
            'ifMTU': self.if_mtu,
            'ifSpeed': self.if_speed,
            'ifPhysAddress': self.if_phys_address,
            'ifHighSpeed': self.if_high_speed,
            'ifAlias': self.if_alias,
            'ipAddresses': self.ip_addresses
        }

    def to_stats_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for statistics database operations."""
        return {
            'interface_id': self.interface_id,
            'ifAdminStatus': self.if_admin_status,
            'ifOperStatus': self.if_oper_status,
            'ifInOctets': self.if_in_octets,
            'ifOutOctets': self.if_out_octets,
            'ifHCInOctets': self.if_hc_in_octets,
            'ifHCOutOctets': self.if_hc_out_octets
        }


@dataclass
class InterfaceBatch:
    """Container for interface statistics batch operations."""
    interfaces: List[Interface]
    router_id: int
    
    def get_stats_batch_values(self, timestamp: str) -> List[tuple]:
        """Get values for batch statistics insertion."""
        values = []
        for interface in self.interfaces:
            if not interface.interface_id:
                continue
                
            values.append((
                interface.interface_id,
                timestamp,
                int(interface.if_admin_status or 0),
                int(interface.if_oper_status or 0),
                int(interface.if_in_octets or 0),
                int(interface.if_out_octets or 0),
                int(interface.if_hc_in_octets or 0),
                int(interface.if_hc_out_octets or 0)
            ))
        return values