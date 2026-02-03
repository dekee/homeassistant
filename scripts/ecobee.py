#!/usr/bin/env python3
"""
Ecobee Thermostat Control via Home Assistant REST API

Usage:
    python ecobee.py status
    python ecobee.py set-temp 72
    python ecobee.py set-mode heat
    python ecobee.py set-preset away

Environment Variables:
    HA_URL          Home Assistant URL (default: https://homeassistant.home)
    HA_TOKEN        Long-lived access token (required)
    ECOBEE_ENTITY   Climate entity ID (default: climate.ecobee)
"""

import os
import sys
import json
import urllib.request
import urllib.error
import ssl

# Configuration
HA_URL = os.environ.get("HA_URL", "https://homeassistant.home")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
ECOBEE_ENTITY = os.environ.get("ECOBEE_ENTITY", "climate.ecobee")

# Disable SSL verification for self-signed certs (homelab)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def api_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make an API request to Home Assistant."""
    url = f"{HA_URL}/api/{endpoint}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.reason}")
        sys.exit(1)


def get_status():
    """Get current thermostat status."""
    state = api_request("GET", f"states/{ECOBEE_ENTITY}")
    
    attrs = state.get("attributes", {})
    
    print("Ecobee Thermostat Status")
    print("=" * 30)
    print(f"Mode:           {state.get('state')}")
    print(f"Current Temp:   {attrs.get('current_temperature')}°F")
    
    if attrs.get("temperature"):
        print(f"Target Temp:    {attrs.get('temperature')}°F")
    else:
        print(f"Target Range:   {attrs.get('target_temp_low')}°F - {attrs.get('target_temp_high')}°F")
    
    print(f"Humidity:       {attrs.get('current_humidity')}%")
    print(f"HVAC Action:    {attrs.get('hvac_action')}")
    print(f"Preset:         {attrs.get('preset_mode')}")
    print(f"Fan Mode:       {attrs.get('fan_mode')}")
    
    return state


def set_temperature(temp: float):
    """Set target temperature."""
    api_request("POST", "services/climate/set_temperature", {
        "entity_id": ECOBEE_ENTITY,
        "temperature": temp
    })
    print(f"Temperature set to {temp}°F")


def set_temperature_range(low: float, high: float):
    """Set temperature range for auto mode."""
    api_request("POST", "services/climate/set_temperature", {
        "entity_id": ECOBEE_ENTITY,
        "target_temp_low": low,
        "target_temp_high": high
    })
    print(f"Temperature range set to {low}°F - {high}°F")


def set_hvac_mode(mode: str):
    """Set HVAC mode (heat, cool, heat_cool, off)."""
    api_request("POST", "services/climate/set_hvac_mode", {
        "entity_id": ECOBEE_ENTITY,
        "hvac_mode": mode
    })
    print(f"HVAC mode set to {mode}")


def set_preset(preset: str):
    """Set preset mode (home, away, sleep)."""
    api_request("POST", "services/climate/set_preset_mode", {
        "entity_id": ECOBEE_ENTITY,
        "preset_mode": preset
    })
    print(f"Preset set to {preset}")


def turn_on():
    """Turn on HVAC."""
    api_request("POST", "services/climate/turn_on", {
        "entity_id": ECOBEE_ENTITY
    })
    print("HVAC turned on")


def turn_off():
    """Turn off HVAC."""
    api_request("POST", "services/climate/turn_off", {
        "entity_id": ECOBEE_ENTITY
    })
    print("HVAC turned off")


def main():
    if not HA_TOKEN:
        print("Error: HA_TOKEN environment variable not set")
        print("Create a long-lived access token in Home Assistant:")
        print("  Profile → Long-Lived Access Tokens → Create Token")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        get_status()
    elif command == "set-temp":
        set_temperature(float(sys.argv[2]))
    elif command == "set-range":
        set_temperature_range(float(sys.argv[2]), float(sys.argv[3]))
    elif command == "set-mode":
        set_hvac_mode(sys.argv[2])
    elif command == "set-preset":
        set_preset(sys.argv[2])
    elif command == "turn-on":
        turn_on()
    elif command == "turn-off":
        turn_off()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
