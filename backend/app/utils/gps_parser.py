"""
RoadPulse AI - Geolocation & SRT Telemetry Utilities
Parses drone/dashcam SRT GPS subtitles, computes geodesic distances, and calculates PCI.
"""

import re
import math
from typing import List, Dict, Any, Optional


def parse_srt_gps(content: str) -> List[Dict[str, Any]]:
    """
    Parses video SRT subtitle tracks to extract timestamped GPS coordinates.
    Supports DJI, Viofo, GoPro, and standard dashcam metadata formats.
    """
    points = []
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 3:
            continue

        # Line 2 is time range: 00:00:01,000 --> 00:00:02,000
        time_match = re.search(r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})', lines[1])
        if not time_match:
            continue

        ts = time_match.group(1).replace(',', '.')
        parts = ts.split(':')
        time_sec = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

        # Search subsequent lines for lat, lon, speed, altitude
        text = " ".join(lines[2:])
        lat, lon, speed, alt = None, None, None, None

        # Format 1: [latitude: 12.9716] [longitude: 77.5946]
        m = re.search(r'latitude[:\s]+([-+]?\d+\.\d+)', text, re.IGNORECASE)
        if m:
            lat = float(m.group(1))
        m = re.search(r'longitude[:\s]+([-+]?\d+\.\d+)', text, re.IGNORECASE)
        if m:
            lon = float(m.group(1))

        # Format 2: lat: 12.9716, lon: 77.5946
        if lat is None:
            m = re.search(r'lat[:\s]+([-+]?\d+\.\d+)', text, re.IGNORECASE)
            if m:
                lat = float(m.group(1))
        if lon is None:
            m = re.search(r'lon[g]?[:\s]+([-+]?\d+\.\d+)', text, re.IGNORECASE)
            if m:
                lon = float(m.group(1))

        # Format 3: Raw comma or space separated coords (e.g. 12.9716, 77.5946)
        if lat is None or lon is None:
            m = re.search(r'([-+]?\d{1,2}\.\d{4,8})\s*,\s*([-+]?\d{1,3}\.\d{4,8})', text)
            if m:
                lat = float(m.group(1))
                lon = float(m.group(2))

        # Speed match
        m = re.search(r'speed[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        if m:
            speed = float(m.group(1))

        if lat is not None and lon is not None:
            # Validate sensible earthly bounds
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                points.append({
                    "time": time_sec,
                    "latitude": lat,
                    "longitude": lon,
                    "speed": speed,
                })

    return points


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS points in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def calculate_pci_score(total_defects: int, road_length_km: float, high_severity_count: int) -> float:
    """
    Computes standard Pavement Condition Index (PCI) on a 0-100 scale (ASTM D6433).
    100 = Perfect condition, 0 = Failed / impassable.
    """
    if road_length_km <= 0.05:
        road_length_km = 0.5  # Default segment normalization

    defects_per_km = total_defects / road_length_km

    # Deduct value based on distress density and high-severity hazard count
    deduct = (defects_per_km * 4.5) + (high_severity_count * 8.0)
    pci = max(0.0, min(100.0, 100.0 - deduct))
    return round(pci, 1)


def pci_to_condition_label(pci: float) -> str:
    """Converts numeric PCI to standard road condition classification."""
    if pci >= 85:
        return "Good"
    elif pci >= 65:
        return "Average"
    elif pci >= 40:
        return "Poor"
    return "Critical"
