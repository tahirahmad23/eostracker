
import pytest
from database.models import Device
from datetime import date

@pytest.fixture
def seed_devices(db):
    devices = [
        Device(vendor="Cisco", model="Catalyst 9300", device_type="Switch", eos_date=date(2030, 1, 1), slug="cisco-9300"),
        Device(vendor="Cisco", model="ASR 1000", device_type="Router", eos_date=date(2028, 5, 15), slug="cisco-asr-1000"),
        Device(vendor="Juniper", model="MX480", device_type="Router", eos_date=date(2029, 10, 1), slug="juniper-mx480"),
        Device(vendor="Arista", model="7050X", device_type="Switch", eos_date=date(2027, 3, 20), slug="arista-7050x"),
    ]
    for d in devices:
        db.add(d)
    db.commit()
    return devices

def test_search_devices_all(client, seed_devices):
    response = client.get("/api/devices/search")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 4
    assert len(data["data"]["devices"]) == 4

def test_search_devices_query(client, seed_devices):
    response = client.get("/api/devices/search?q=cisco")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 2
    assert all(d["vendor"] == "Cisco" for d in data["data"]["devices"])

def test_search_devices_vendor_filter(client, seed_devices):
    response = client.get("/api/devices/search?vendor=Juniper")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["devices"][0]["model"] == "MX480"

def test_search_devices_pagination(client, seed_devices):
    response = client.get("/api/devices/search?page_size=2&page=1")
    data = response.json()
    assert len(data["data"]["devices"]) == 2
    assert data["data"]["page"] == 1
    assert data["data"]["pages"] == 2
    
    response2 = client.get("/api/devices/search?page_size=2&page=2")
    data2 = response2.json()
    assert len(data2["data"]["devices"]) == 2
    assert data2["data"]["devices"] != data["data"]["devices"]

def test_get_device_detail(client, seed_devices, db):
    # Get ID of first seeded device
    device = db.query(Device).filter_by(slug="cisco-9300").first()
    
    response = client.get(f"/api/devices/{device.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["model"] == "Catalyst 9300"
    
def test_get_device_not_found(client):
    response = client.get("/api/devices/99999")
    assert response.status_code == 404
