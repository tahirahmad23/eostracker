"""
Database seed data for EOS Tracker.

Populates the database with ~100 network devices from major vendors
with realistic EOS dates ranging from past to 3+ years in the future.
"""

from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from database.models import Device
from database.connection import get_db, SessionLocal


def generate_slug(vendor: str, model: str) -> str:
    """
    Generate SEO-friendly slug from vendor and model.
    
    Args:
        vendor: Device vendor name
        model: Device model name
    
    Returns:
        URL-safe slug
    
    Example:
        generate_slug("Cisco", "Catalyst 3850") -> "cisco-catalyst-3850"
    """
    combined = f"{vendor} {model}"
    slug = combined.lower()
    slug = slug.replace(" ", "-")
    slug = slug.replace("/", "-")
    slug = slug.replace("(", "")
    slug = slug.replace(")", "")
    return slug


def get_seed_devices() -> List[Dict[str, Any]]:
    """
    Get list of seed device data.
    
    Returns:
        List of device dictionaries with all required fields
    """
    today = date.today()
    
    devices = [
        # Cisco Routers - Mix of past, current, and future EOS dates
        {"vendor": "Cisco", "model": "ASR 1001-X", "device_type": "Router", 
         "eos_date": today - timedelta(days=730), "eol_date": today - timedelta(days=365),
         "description": "High-performance aggregation services router"},
        {"vendor": "Cisco", "model": "ASR 9000", "device_type": "Router",
         "eos_date": today + timedelta(days=90), "eol_date": today + timedelta(days=365),
         "description": "Core routing platform for service providers"},
        {"vendor": "Cisco", "model": "ISR 4451", "device_type": "Router",
         "eos_date": today + timedelta(days=180), "eol_date": today + timedelta(days=545),
         "description": "Integrated services router for enterprise branches"},
        {"vendor": "Cisco", "model": "ISR 4331", "device_type": "Router",
         "eos_date": today + timedelta(days=365), "eol_date": today + timedelta(days=730),
         "description": "Branch office router with cloud integration"},
        {"vendor": "Cisco", "model": "ISR 2901", "device_type": "Router",
         "eos_date": today - timedelta(days=365), "eol_date": today - timedelta(days=180),
         "description": "Legacy integrated services router"},
        {"vendor": "Cisco", "model": "ASR 1002-HX", "device_type": "Router",
         "eos_date": today + timedelta(days=730), "eol_date": today + timedelta(days=1095),
         "description": "High-throughput aggregation router"},
        {"vendor": "Cisco", "model": "ISR 4321", "device_type": "Router",
         "eos_date": today + timedelta(days=270), "eol_date": today + timedelta(days=635),
         "description": "Compact branch router with security features"},
        
        # Cisco Switches
        {"vendor": "Cisco", "model": "Catalyst 3850", "device_type": "Switch",
         "eos_date": today - timedelta(days=180), "eol_date": today - timedelta(days=90),
         "description": "Stackable enterprise switch with 40G uplinks"},
        {"vendor": "Cisco", "model": "Catalyst 9300", "device_type": "Switch",
         "eos_date": today + timedelta(days=1095), "eol_date": today + timedelta(days=1460),
         "description": "Next-gen campus switch with SD-Access"},
        {"vendor": "Cisco", "model": "Catalyst 9500", "device_type": "Switch",
         "eos_date": today + timedelta(days=1200), "eol_date": today + timedelta(days=1565),
         "description": "High-density core switch for enterprise"},
        {"vendor": "Cisco", "model": "Nexus 9300", "device_type": "Switch",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "Data center top-of-rack switch"},
        {"vendor": "Cisco", "model": "Nexus 7700", "device_type": "Switch",
         "eos_date": today + timedelta(days=450), "eol_date": today + timedelta(days=815),
         "description": "Modular data center core switch"},
        {"vendor": "Cisco", "model": "Catalyst 2960X", "device_type": "Switch",
         "eos_date": today - timedelta(days=90), "eol_date": today + timedelta(days=180),
         "description": "Compact access switch for small deployments"},
        {"vendor": "Cisco", "model": "Catalyst 3650", "device_type": "Switch",
         "eos_date": today - timedelta(days=450), "eol_date": today - timedelta(days=270),
         "description": "Stackable access switch (legacy)"},
        {"vendor": "Cisco", "model": "Nexus 9200", "device_type": "Switch",
         "eos_date": today + timedelta(days=1000), "eol_date": today + timedelta(days=1365),
         "description": "Compact data center switch"},
        
        # Juniper Routers
        {"vendor": "Juniper", "model": "MX204", "device_type": "Router",
         "eos_date": today + timedelta(days=800), "eol_date": today + timedelta(days=1165),
         "description": "Compact universal routing platform"},
        {"vendor": "Juniper", "model": "MX480", "device_type": "Router",
         "eos_date": today + timedelta(days=365), "eol_date": today + timedelta(days=730),
         "description": "High-performance core router"},
        {"vendor": "Juniper", "model": "MX960", "device_type": "Router",
         "eos_date": today + timedelta(days=180), "eol_date": today + timedelta(days=545),
         "description": "Large-scale service provider router"},
        {"vendor": "Juniper", "model": "ACX5448", "device_type": "Router",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "Metro access router"},
        {"vendor": "Juniper", "model": "PTX10003", "device_type": "Router",
         "eos_date": today + timedelta(days=1100), "eol_date": today + timedelta(days=1465),
         "description": "Packet transport router for metro/edge"},
        {"vendor": "Juniper", "model": "MX104", "device_type": "Router",
         "eos_date": today - timedelta(days=200), "eol_date": today - timedelta(days=30),
         "description": "Compact edge router (legacy)"},
        
        # Juniper Switches
        {"vendor": "Juniper", "model": "EX4300", "device_type": "Switch",
         "eos_date": today - timedelta(days=100), "eol_date": today + timedelta(days=90),
         "description": "Campus access switch"},
        {"vendor": "Juniper", "model": "EX4650", "device_type": "Switch",
         "eos_date": today + timedelta(days=700), "eol_date": today + timedelta(days=1065),
         "description": "High-density campus switch"},
        {"vendor": "Juniper", "model": "QFX5120", "device_type": "Switch",
         "eos_date": today + timedelta(days=850), "eol_date": today + timedelta(days=1215),
         "description": "Data center leaf switch"},
        {"vendor": "Juniper", "model": "QFX10002", "device_type": "Switch",
         "eos_date": today + timedelta(days=600), "eol_date": today + timedelta(days=965),
         "description": "High-performance spine switch"},
        {"vendor": "Juniper", "model": "EX9200", "device_type": "Switch",
         "eos_date": today + timedelta(days=270), "eol_date": today + timedelta(days=635),
         "description": "Modular core switch for enterprise"},
        
        # Arista Switches
        {"vendor": "Arista", "model": "7050X3", "device_type": "Switch",
         "eos_date": today + timedelta(days=1000), "eol_date": today + timedelta(days=1365),
         "description": "Fixed configuration data center switch"},
        {"vendor": "Arista", "model": "7280R3", "device_type": "Switch",
         "eos_date": today + timedelta(days=1200), "eol_date": today + timedelta(days=1565),
         "description": "Universal leaf/spine switch"},
        {"vendor": "Arista", "model": "7500R3", "device_type": "Switch",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "Modular data center switch"},
        {"vendor": "Arista", "model": "7060X4", "device_type": "Switch",
         "eos_date": today + timedelta(days=1100), "eol_date": today + timedelta(days=1465),
         "description": "Deep buffer switch for AI/ML workloads"},
        {"vendor": "Arista", "model": "7300X3", "device_type": "Switch",
         "eos_date": today + timedelta(days=950), "eol_date": today + timedelta(days=1315),
         "description": "Compact core/aggregation switch"},
        {"vendor": "Arista", "model": "7050SX3", "device_type": "Switch",
         "eos_date": today + timedelta(days=450), "eol_date": today + timedelta(days=815),
         "description": "Low-latency leaf switch"},
        {"vendor": "Arista", "model": "7280R2", "device_type": "Switch",
         "eos_date": today - timedelta(days=60), "eol_date": today + timedelta(days=240),
         "description": "Previous generation spine switch"},
        
        # Palo Alto Firewalls
        {"vendor": "Palo Alto", "model": "PA-5220", "device_type": "Firewall",
         "eos_date": today + timedelta(days=730), "eol_date": today + timedelta(days=1095),
         "description": "Next-gen firewall for enterprise"},
        {"vendor": "Palo Alto", "model": "PA-3220", "device_type": "Firewall",
         "eos_date": today + timedelta(days=800), "eol_date": today + timedelta(days=1165),
         "description": "Mid-range next-gen firewall"},
        {"vendor": "Palo Alto", "model": "PA-220", "device_type": "Firewall",
         "eos_date": today + timedelta(days=365), "eol_date": today + timedelta(days=730),
         "description": "Branch office firewall"},
        {"vendor": "Palo Alto", "model": "PA-850", "device_type": "Firewall",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "Compact enterprise firewall"},
        {"vendor": "Palo Alto", "model": "PA-5250", "device_type": "Firewall",
         "eos_date": today + timedelta(days=1000), "eol_date": today + timedelta(days=1365),
         "description": "High-throughput data center firewall"},
        {"vendor": "Palo Alto", "model": "PA-3020", "device_type": "Firewall",
         "eos_date": today - timedelta(days=365), "eol_date": today - timedelta(days=180),
         "description": "Legacy mid-range firewall"},
        {"vendor": "Palo Alto", "model": "PA-820", "device_type": "Firewall",
         "eos_date": today + timedelta(days=270), "eol_date": today + timedelta(days=635),
         "description": "Branch firewall with SD-WAN"},
        
        # Fortinet Firewalls
        {"vendor": "Fortinet", "model": "FortiGate 100F", "device_type": "Firewall",
         "eos_date": today + timedelta(days=1095), "eol_date": today + timedelta(days=1460),
         "description": "Entry-level enterprise firewall"},
        {"vendor": "Fortinet", "model": "FortiGate 200F", "device_type": "Firewall",
         "eos_date": today + timedelta(days=1000), "eol_date": today + timedelta(days=1365),
         "description": "Mid-range enterprise firewall"},
        {"vendor": "Fortinet", "model": "FortiGate 600F", "device_type": "Firewall",
         "eos_date": today + timedelta(days=1200), "eol_date": today + timedelta(days=1565),
         "description": "High-performance enterprise firewall"},
        {"vendor": "Fortinet", "model": "FortiGate 1500D", "device_type": "Firewall",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "Data center firewall platform"},
        {"vendor": "Fortinet", "model": "FortiGate 60F", "device_type": "Firewall",
         "eos_date": today + timedelta(days=730), "eol_date": today + timedelta(days=1095),
         "description": "Small office firewall"},
        {"vendor": "Fortinet", "model": "FortiGate 80E", "device_type": "Firewall",
         "eos_date": today - timedelta(days=180), "eol_date": today + timedelta(days=90),
         "description": "Legacy branch firewall"},
        {"vendor": "Fortinet", "model": "FortiGate 300E", "device_type": "Firewall",
         "eos_date": today - timedelta(days=90), "eol_date": today + timedelta(days=180),
         "description": "Previous generation mid-range firewall"},
        
        # Cisco Firewalls
        {"vendor": "Cisco", "model": "Firepower 2130", "device_type": "Firewall",
         "eos_date": today + timedelta(days=450), "eol_date": today + timedelta(days=815),
         "description": "Next-gen threat defense firewall"},
        {"vendor": "Cisco", "model": "Firepower 4145", "device_type": "Firewall",
         "eos_date": today + timedelta(days=800), "eol_date": today + timedelta(days=1165),
         "description": "High-throughput threat defense"},
        {"vendor": "Cisco", "model": "ASA 5525-X", "device_type": "Firewall",
         "eos_date": today - timedelta(days=450), "eol_date": today - timedelta(days=270),
         "description": "Legacy adaptive security appliance"},
        {"vendor": "Cisco", "model": "Firepower 1140", "device_type": "Firewall",
         "eos_date": today + timedelta(days=650), "eol_date": today + timedelta(days=1015),
         "description": "Branch firewall with threat intelligence"},
        
        # F5 Load Balancers
        {"vendor": "F5", "model": "BIG-IP 2000s", "device_type": "Load Balancer",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "Application delivery controller"},
        {"vendor": "F5", "model": "BIG-IP 4200v", "device_type": "Load Balancer",
         "eos_date": today + timedelta(days=1100), "eol_date": today + timedelta(days=1465),
         "description": "Virtual application delivery controller"},
        {"vendor": "F5", "model": "BIG-IP 5250v", "device_type": "Load Balancer",
         "eos_date": today + timedelta(days=1000), "eol_date": today + timedelta(days=1365),
         "description": "High-performance virtual ADC"},
        {"vendor": "F5", "model": "BIG-IP 8900", "device_type": "Load Balancer",
         "eos_date": today + timedelta(days=600), "eol_date": today + timedelta(days=965),
         "description": "Enterprise application delivery platform"},
        {"vendor": "F5", "model": "BIG-IP 3900", "device_type": "Load Balancer",
         "eos_date": today - timedelta(days=200), "eol_date": today - timedelta(days=30),
         "description": "Legacy load balancer"},
        
        # Additional Cisco Devices
        {"vendor": "Cisco", "model": "Catalyst 9200", "device_type": "Switch",
         "eos_date": today + timedelta(days=1050), "eol_date": today + timedelta(days=1415),
         "description": "Compact campus access switch"},
        {"vendor": "Cisco", "model": "Catalyst 9400", "device_type": "Switch",
         "eos_date": today + timedelta(days=1150), "eol_date": today + timedelta(days=1515),
         "description": "Modular campus core switch"},
        {"vendor": "Cisco", "model": "Nexus 9500", "device_type": "Switch",
         "eos_date": today + timedelta(days=750), "eol_date": today + timedelta(days=1115),
         "description": "Modular spine switch for data center"},
        {"vendor": "Cisco", "model": "ISR 1100", "device_type": "Router",
         "eos_date": today + timedelta(days=1300), "eol_date": today + timedelta(days=1665),
         "description": "Industrial IoT router"},
        
        # HPE/Aruba Switches
        {"vendor": "HPE Aruba", "model": "6300M", "device_type": "Switch",
         "eos_date": today + timedelta(days=1050), "eol_date": today + timedelta(days=1415),
         "description": "Modular campus core switch"},
        {"vendor": "HPE Aruba", "model": "6200F", "device_type": "Switch",
         "eos_date": today + timedelta(days=950), "eol_date": today + timedelta(days=1315),
         "description": "Fixed configuration access switch"},
        {"vendor": "HPE Aruba", "model": "8325", "device_type": "Switch",
         "eos_date": today + timedelta(days=1100), "eol_date": today + timedelta(days=1465),
         "description": "Data center leaf/spine switch"},
        {"vendor": "HPE Aruba", "model": "2930F", "device_type": "Switch",
         "eos_date": today + timedelta(days=180), "eol_date": today + timedelta(days=545),
         "description": "Legacy access switch"},
        
        # Dell Networking
        {"vendor": "Dell", "model": "S5248F-ON", "device_type": "Switch",
         "eos_date": today + timedelta(days=800), "eol_date": today + timedelta(days=1165),
         "description": "Open networking leaf switch"},
        {"vendor": "Dell", "model": "S5232F-ON", "device_type": "Switch",
         "eos_date": today + timedelta(days=850), "eol_date": today + timedelta(days=1215),
         "description": "100G data center switch"},
        {"vendor": "Dell", "model": "N3248TE-ON", "device_type": "Switch",
         "eos_date": today + timedelta(days=650), "eol_date": today + timedelta(days=1015),
         "description": "Campus access switch"},
        
        # Extreme Networks
        {"vendor": "Extreme", "model": "VSP 4900", "device_type": "Switch",
         "eos_date": today + timedelta(days=450), "eol_date": today + timedelta(days=815),
         "description": "Virtual services platform"},
        {"vendor": "Extreme", "model": "VSP 7400", "device_type": "Switch",
         "eos_date": today + timedelta(days=550), "eol_date": today + timedelta(days=915),
         "description": "Modular campus core switch"},
        {"vendor": "Extreme", "model": "X465", "device_type": "Switch",
         "eos_date": today + timedelta(days=700), "eol_date": today + timedelta(days=1065),
         "description": "Stackable access switch"},
        
        # Huawei (for international deployments)
        {"vendor": "Huawei", "model": "CloudEngine 6800", "device_type": "Switch",
         "eos_date": today + timedelta(days=600), "eol_date": today + timedelta(days=965),
         "description": "Data center switch"},
        {"vendor": "Huawei", "model": "NetEngine 8000", "device_type": "Router",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "Carrier-grade edge router"},
        
        # Additional specialty devices
        {"vendor": "Check Point", "model": "5200", "device_type": "Firewall",
         "eos_date": today + timedelta(days=700), "eol_date": today + timedelta(days=1065),
         "description": "Enterprise security gateway"},
        {"vendor": "Check Point", "model": "15600", "device_type": "Firewall",
         "eos_date": today + timedelta(days=900), "eol_date": today + timedelta(days=1265),
         "description": "High-performance security gateway"},
        {"vendor": "Citrix", "model": "ADC VPX 3000", "device_type": "Load Balancer",
         "eos_date": today + timedelta(days=800), "eol_date": today + timedelta(days=1165),
         "description": "Virtual application delivery controller"},
        {"vendor": "A10 Networks", "model": "Thunder 4435", "device_type": "Load Balancer",
         "eos_date": today + timedelta(days=650), "eol_date": today + timedelta(days=1015),
         "description": "Application delivery controller"},
    ]
    
    # Generate slugs for all devices
    for device in devices:
        device["slug"] = generate_slug(device["vendor"], device["model"])
    
    return devices


def seed_devices(db: Session = None) -> Dict[str, Any]:
    """
    Seed database with initial device data.
    
    Args:
        db: Database session (optional, creates new if not provided)
    
    Returns:
        Result dictionary with count of devices created
    
    Example:
        result = seed_devices()
        if result["success"]:
            print(f"Created {result['data']} devices")
    """
    try:
        # Create session if not provided
        if db is None:
            db = SessionLocal()
            close_session = True
        else:
            close_session = False
        
        # Check if devices already exist
        existing_count = db.query(Device).count()
        if existing_count > 0:
            if close_session:
                db.close()
            return {
                "success": False,
                "error": f"Database already contains {existing_count} devices. Clear database first."
            }
        
        # Get seed data
        devices_data = get_seed_devices()
        
        # Create device objects
        devices = []
        for data in devices_data:
            device = Device(**data)
            devices.append(device)
        
        # Bulk insert
        db.bulk_save_objects(devices)
        db.commit()
        
        count = len(devices)
        
        if close_session:
            db.close()
        
        return {
            "success": True,
            "data": count
        }
    
    except Exception as e:
        if db:
            db.rollback()
            if close_session:
                db.close()
        return {
            "success": False,
            "error": f"Failed to seed devices: {str(e)}"
        }


if __name__ == "__main__":
    """Run seed script directly."""
    print("Starting database seed...")
    result = seed_devices()
    
    if result["success"]:
        print(f"✓ Successfully created {result['data']} devices")
    else:
        print(f"✗ Error: {result['error']}")
