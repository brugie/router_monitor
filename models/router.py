from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Router:
    """Router model representing a network device."""
    ip_address: str
    sys_name: Optional[str] = None
    sys_descr: Optional[str] = None
    sys_uptime: Optional[int] = None
    sys_location: Optional[str] = None
    sys_contact: Optional[str] = None
    sys_object_id: Optional[str] = None
    router_id: Optional[int] = None
    last_update: Optional[datetime] = None

    @classmethod
    def from_snmp_data(cls, ip_address: str, data: Dict[str, Any]) -> 'Router':
        """Create a Router instance from SNMP data."""
        return cls(
            ip_address=ip_address,
            sys_name=data.get('sysName'),
            sys_descr=data.get('sysDescr'),
            sys_uptime=data.get('sysUpTime'),
            sys_location=data.get('sysLocation'),
            sys_contact=data.get('sysContact'),
            sys_object_id=data.get('sysObjectID')
        )

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            'ip_address': self.ip_address,
            'sysName': self.sys_name,
            'sysDescr': self.sys_descr,
            'sysUpTime': self.sys_uptime,
            'sysLocation': self.sys_location,
            'sysContact': self.sys_contact,
            'sysObjectID': self.sys_object_id
        }