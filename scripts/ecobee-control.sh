#!/bin/bash
#
# Ecobee Thermostat Control via Home Assistant
#
# Usage:
#   ./ecobee-control.sh status                    # Get current status
#   ./ecobee-control.sh set-temp 72               # Set temperature to 72°F
#   ./ecobee-control.sh set-mode heat|cool|auto   # Set HVAC mode
#   ./ecobee-control.sh set-preset home|away|sleep # Set preset
#
# Setup:
#   export HA_URL="https://homeassistant.home"
#   export HA_TOKEN="your_long_lived_access_token"
#   export ECOBEE_ENTITY="climate.ecobee_thermostat"  # Find in HA Developer Tools
#

set -e

# Configuration
HA_URL="${HA_URL:-https://homeassistant.home}"
HA_TOKEN="${HA_TOKEN:-}"
ECOBEE_ENTITY="${ECOBEE_ENTITY:-climate.ecobee}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Ecobee Thermostat Control"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  status                  Get current thermostat status"
    echo "  set-temp <temp>         Set target temperature (°F)"
    echo "  set-range <low> <high>  Set temperature range for auto mode"
    echo "  set-mode <mode>         Set HVAC mode (heat, cool, heat_cool, off)"
    echo "  set-preset <preset>     Set preset (home, away, sleep)"
    echo "  turn-on                 Turn on HVAC"
    echo "  turn-off                Turn off HVAC"
    echo ""
    echo "Environment Variables:"
    echo "  HA_URL          Home Assistant URL (default: https://homeassistant.home)"
    echo "  HA_TOKEN        Long-lived access token (required)"
    echo "  ECOBEE_ENTITY   Climate entity ID (default: climate.ecobee)"
    exit 1
}

check_token() {
    if [ -z "$HA_TOKEN" ]; then
        echo -e "${RED}Error: HA_TOKEN environment variable not set${NC}"
        echo "Create a long-lived access token in Home Assistant:"
        echo "  Profile → Long-Lived Access Tokens → Create Token"
        exit 1
    fi
}

api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ "$method" == "GET" ]; then
        curl -s -X GET \
            -H "Authorization: Bearer $HA_TOKEN" \
            -H "Content-Type: application/json" \
            "${HA_URL}/api/${endpoint}"
    else
        curl -s -X POST \
            -H "Authorization: Bearer $HA_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${HA_URL}/api/${endpoint}"
    fi
}

get_status() {
    check_token
    
    local response=$(api_call GET "states/$ECOBEE_ENTITY")
    
    if echo "$response" | grep -q "error"; then
        echo -e "${RED}Error: Could not get thermostat status${NC}"
        echo "$response"
        exit 1
    fi
    
    echo -e "${GREEN}Ecobee Thermostat Status${NC}"
    echo "========================="
    
    local state=$(echo "$response" | jq -r '.state')
    local current_temp=$(echo "$response" | jq -r '.attributes.current_temperature')
    local target_temp=$(echo "$response" | jq -r '.attributes.temperature // "N/A"')
    local target_low=$(echo "$response" | jq -r '.attributes.target_temp_low // "N/A"')
    local target_high=$(echo "$response" | jq -r '.attributes.target_temp_high // "N/A"')
    local humidity=$(echo "$response" | jq -r '.attributes.current_humidity // "N/A"')
    local hvac_action=$(echo "$response" | jq -r '.attributes.hvac_action // "N/A"')
    local preset=$(echo "$response" | jq -r '.attributes.preset_mode // "N/A"')
    local fan=$(echo "$response" | jq -r '.attributes.fan_mode // "N/A"')
    
    echo "Mode:            $state"
    echo "Current Temp:    ${current_temp}°F"
    if [ "$target_temp" != "N/A" ] && [ "$target_temp" != "null" ]; then
        echo "Target Temp:     ${target_temp}°F"
    else
        echo "Target Range:    ${target_low}°F - ${target_high}°F"
    fi
    echo "Humidity:        ${humidity}%"
    echo "HVAC Action:     $hvac_action"
    echo "Preset:          $preset"
    echo "Fan Mode:        $fan"
}

set_temperature() {
    check_token
    local temp="$1"
    
    if [ -z "$temp" ]; then
        echo -e "${RED}Error: Temperature required${NC}"
        usage
    fi
    
    echo -e "${YELLOW}Setting temperature to ${temp}°F...${NC}"
    
    local response=$(api_call POST "services/climate/set_temperature" \
        "{\"entity_id\": \"$ECOBEE_ENTITY\", \"temperature\": $temp}")
    
    echo -e "${GREEN}Temperature set to ${temp}°F${NC}"
}

set_temperature_range() {
    check_token
    local low="$1"
    local high="$2"
    
    if [ -z "$low" ] || [ -z "$high" ]; then
        echo -e "${RED}Error: Low and high temperatures required${NC}"
        usage
    fi
    
    echo -e "${YELLOW}Setting temperature range to ${low}°F - ${high}°F...${NC}"
    
    local response=$(api_call POST "services/climate/set_temperature" \
        "{\"entity_id\": \"$ECOBEE_ENTITY\", \"target_temp_low\": $low, \"target_temp_high\": $high}")
    
    echo -e "${GREEN}Temperature range set to ${low}°F - ${high}°F${NC}"
}

set_hvac_mode() {
    check_token
    local mode="$1"
    
    if [ -z "$mode" ]; then
        echo -e "${RED}Error: Mode required (heat, cool, heat_cool, off)${NC}"
        usage
    fi
    
    echo -e "${YELLOW}Setting HVAC mode to ${mode}...${NC}"
    
    local response=$(api_call POST "services/climate/set_hvac_mode" \
        "{\"entity_id\": \"$ECOBEE_ENTITY\", \"hvac_mode\": \"$mode\"}")
    
    echo -e "${GREEN}HVAC mode set to ${mode}${NC}"
}

set_preset() {
    check_token
    local preset="$1"
    
    if [ -z "$preset" ]; then
        echo -e "${RED}Error: Preset required (home, away, sleep)${NC}"
        usage
    fi
    
    echo -e "${YELLOW}Setting preset to ${preset}...${NC}"
    
    local response=$(api_call POST "services/climate/set_preset_mode" \
        "{\"entity_id\": \"$ECOBEE_ENTITY\", \"preset_mode\": \"$preset\"}")
    
    echo -e "${GREEN}Preset set to ${preset}${NC}"
}

turn_on() {
    check_token
    echo -e "${YELLOW}Turning on HVAC...${NC}"
    
    local response=$(api_call POST "services/climate/turn_on" \
        "{\"entity_id\": \"$ECOBEE_ENTITY\"}")
    
    echo -e "${GREEN}HVAC turned on${NC}"
}

turn_off() {
    check_token
    echo -e "${YELLOW}Turning off HVAC...${NC}"
    
    local response=$(api_call POST "services/climate/turn_off" \
        "{\"entity_id\": \"$ECOBEE_ENTITY\"}")
    
    echo -e "${GREEN}HVAC turned off${NC}"
}

# Main
case "$1" in
    status)
        get_status
        ;;
    set-temp)
        set_temperature "$2"
        ;;
    set-range)
        set_temperature_range "$2" "$3"
        ;;
    set-mode)
        set_hvac_mode "$2"
        ;;
    set-preset)
        set_preset "$2"
        ;;
    turn-on)
        turn_on
        ;;
    turn-off)
        turn_off
        ;;
    *)
        usage
        ;;
esac
