#!/usr/bin/env python3
"""
Circadian Lighting - Gradually transition lights from cool to warm throughout the day.

Usage:
    python circadian.py run          # Run continuous circadian lighting
    python circadian.py update       # Single update based on current time (for cron/k8s)
    python circadian.py test         # Test: full day cycle in 1 minute
    python circadian.py set-temp 4000  # Set specific color temp (Kelvin)
    python circadian.py status       # Show current settings

Environment Variables:
    HA_URL      Home Assistant URL (default: https://homeassistant.home)
    HA_TOKEN    Long-lived access token (required)
"""

import os
import sys
import json
import time
import math
import urllib.request
import urllib.error
import ssl
from datetime import datetime

# Configuration
HA_URL = os.environ.get("HA_URL", "https://homeassistant.home")
HA_TOKEN = os.environ.get("HA_TOKEN", "")

# Circadian settings
WAKE_TIME = 6      # 6 AM - start transitioning to cool
PEAK_COOL = 12     # 12 PM - coolest (most blue/white)
SUNSET_START = 17  # 5 PM - start transitioning to warm
SLEEP_TIME = 22    # 10 PM - warmest (most orange/red)

# Color temperature range (Kelvin)
COOL_TEMP = 6500   # Bright daylight (bluish white)
WARM_TEMP = 2000   # Candlelight (orange/red)

# SSL context for self-signed certs
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
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.reason}")
        return {}
    except Exception as e:
        print(f"Error: {e}")
        return {}


def calculate_color_temp(hour: float) -> int:
    """
    Calculate color temperature based on time of day.
    
    Schedule:
    - 6 AM: Start warming up from warm to cool
    - 12 PM: Peak cool (6500K)
    - 5 PM: Start cooling down from cool to warm  
    - 10 PM: Full warm (2000K)
    - 10 PM - 6 AM: Stay warm
    """
    
    if hour < WAKE_TIME:
        # Before wake: stay warm
        return WARM_TEMP
    
    elif hour < PEAK_COOL:
        # Morning: transition from warm to cool
        progress = (hour - WAKE_TIME) / (PEAK_COOL - WAKE_TIME)
        # Use sine curve for smooth transition
        progress = math.sin(progress * math.pi / 2)
        return int(WARM_TEMP + (COOL_TEMP - WARM_TEMP) * progress)
    
    elif hour < SUNSET_START:
        # Midday: stay cool
        return COOL_TEMP
    
    elif hour < SLEEP_TIME:
        # Evening: transition from cool to warm
        progress = (hour - SUNSET_START) / (SLEEP_TIME - SUNSET_START)
        # Use sine curve for smooth transition
        progress = math.sin(progress * math.pi / 2)
        return int(COOL_TEMP - (COOL_TEMP - WARM_TEMP) * progress)
    
    else:
        # Night: stay warm
        return WARM_TEMP


def get_color_temp_lights() -> list:
    """Get all lights that support color temperature."""
    states = api_request("GET", "states")
    if not states:
        return []
    
    lights = []
    for state in states:
        entity_id = state.get("entity_id", "")
        if not entity_id.startswith("light."):
            continue
        
        attrs = state.get("attributes", {})
        supported_modes = attrs.get("supported_color_modes", [])
        
        # Only include lights that support color_temp
        if "color_temp" in supported_modes:
            # Skip groups to avoid duplicate commands
            if not attrs.get("is_hue_group", False):
                lights.append(entity_id)
    
    return lights


def set_color_temperature(kelvin: int, lights: list = None):
    """Set color temperature for all compatible lights."""
    if lights is None:
        lights = get_color_temp_lights()
    
    if not lights:
        print("No color temperature compatible lights found")
        return
    
    # Home Assistant uses mireds (micro reciprocal degrees)
    # mireds = 1,000,000 / kelvin
    mireds = int(1000000 / kelvin)
    
    # Clamp to typical Hue range (153-500 mireds)
    mireds = max(153, min(500, mireds))
    
    api_request("POST", "services/light/turn_on", {
        "entity_id": lights,
        "color_temp": mireds
    })
    
    return len(lights)


def run_circadian(test_mode: bool = False):
    """Run continuous circadian lighting updates."""
    
    print("Circadian Lighting")
    print("=" * 40)
    
    if test_mode:
        print("TEST MODE: Full day cycle in 60 seconds")
        print("-" * 40)
    else:
        print("Running continuous circadian lighting")
        print("Press Ctrl+C to stop")
        print("-" * 40)
    
    # Get compatible lights once
    lights = get_color_temp_lights()
    print(f"Found {len(lights)} color-temp compatible lights")
    print()
    
    if test_mode:
        # Test mode: simulate 24 hours in 60 seconds
        # Each second = 24 minutes of simulated time
        start_time = time.time()
        duration = 60  # seconds
        
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            # Map 0-60 seconds to 0-24 hours
            simulated_hour = (elapsed / duration) * 24
            
            color_temp = calculate_color_temp(simulated_hour)
            count = set_color_temperature(color_temp, lights)
            
            # Format simulated time
            sim_hour = int(simulated_hour)
            sim_min = int((simulated_hour % 1) * 60)
            
            print(f"Time: {sim_hour:02d}:{sim_min:02d} | Temp: {color_temp}K | Lights: {count}")
            
            time.sleep(2)  # Update every 2 seconds (= 48 min simulated)
        
        print()
        print("Test complete!")
    
    else:
        # Normal mode: update based on actual time
        while True:
            now = datetime.now()
            hour = now.hour + now.minute / 60
            
            color_temp = calculate_color_temp(hour)
            count = set_color_temperature(color_temp, lights)
            
            print(f"[{now.strftime('%H:%M')}] Color temp: {color_temp}K ({count} lights)")
            
            # Update every 5 minutes
            time.sleep(300)


def show_status():
    """Show current circadian status."""
    now = datetime.now()
    hour = now.hour + now.minute / 60
    color_temp = calculate_color_temp(hour)
    
    lights = get_color_temp_lights()
    
    print("Circadian Lighting Status")
    print("=" * 40)
    print(f"Current time:     {now.strftime('%H:%M')}")
    print(f"Calculated temp:  {color_temp}K")
    print(f"Compatible lights: {len(lights)}")
    print()
    print("Schedule:")
    print(f"  {WAKE_TIME:02d}:00 - {PEAK_COOL:02d}:00  Warm → Cool ({WARM_TEMP}K → {COOL_TEMP}K)")
    print(f"  {PEAK_COOL:02d}:00 - {SUNSET_START:02d}:00  Stay Cool ({COOL_TEMP}K)")
    print(f"  {SUNSET_START:02d}:00 - {SLEEP_TIME:02d}:00  Cool → Warm ({COOL_TEMP}K → {WARM_TEMP}K)")
    print(f"  {SLEEP_TIME:02d}:00 - {WAKE_TIME:02d}:00  Stay Warm ({WARM_TEMP}K)")


def main():
    if not HA_TOKEN:
        print("Error: HA_TOKEN environment variable not set")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "run":
        run_circadian(test_mode=False)
    elif command == "update":
        # Single update for cron/kubernetes
        now = datetime.now()
        hour = now.hour + now.minute / 60
        color_temp = calculate_color_temp(hour)
        lights = get_color_temp_lights()
        count = set_color_temperature(color_temp, lights)
        print(f"[{now.strftime('%H:%M')}] Set {count} lights to {color_temp}K")
    elif command == "test":
        run_circadian(test_mode=True)
    elif command == "set-temp":
        if len(sys.argv) < 3:
            print("Usage: circadian.py set-temp <kelvin>")
            sys.exit(1)
        kelvin = int(sys.argv[2])
        count = set_color_temperature(kelvin)
        print(f"Set {count} lights to {kelvin}K")
    elif command == "status":
        show_status()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
