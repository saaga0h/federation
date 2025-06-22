#!/bin/bash
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Login to UniFi OS
echo "Logging in to UDM SE..."
curl -k -X POST "$CONTROLLER/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"'"$USERNAME"'","password":"'"$PASSWORD"'"}' \
  --cookie-jar unifi-cookies -s

if [ $? -eq 0 ]; then
    echo "Login successful, extracting configuration..."
    
# Network configuration (VLANs) - keep as /rest/
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/networkconf" \
  --cookie unifi-cookies -s > networks.json

# Try to get firewall zone information
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/firewallzone" \
  --cookie unifi-cookies -s > firewall-zones.json

# Also try 'zone' endpoints
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/zone" \
  --cookie unifi-cookies -s > zones.json

# Check what we got
echo "=== Firewall Zones ==="
cat firewall-zones.json | jq '.data | length' 2>/dev/null || echo "No data or invalid JSON"
cat firewall-zones.json | head -10

echo "=== Zones ==="
cat zones.json | jq '.data | length' 2>/dev/null || echo "No data or invalid JSON"
cat zones.json | head -10

# Extract all the firewall zone IDs from your networks
echo "=== Firewall Zone IDs in your VLANs ==="
cat networks.json | jq -r '.data[] | select(has("firewall_zone_id")) | "\(.name) (VLAN \(.vlan)): \(.firewall_zone_id)"'

# Try to get rules based on zones
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/firewallrule" \
  --cookie unifi-cookies -s > firewall-rules-v2.json

# Maybe try with zone-based queries
# Get a sample zone ID first
ZONE_ID=$(cat networks.json | jq -r '.data[0].firewall_zone_id' 2>/dev/null)
if [ ! -z "$ZONE_ID" ] && [ "$ZONE_ID" != "null" ]; then
  echo "Testing with zone ID: $ZONE_ID"
  curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/firewallrule/$ZONE_ID" \
    --cookie unifi-cookies -s > zone-specific-rules.json
fi




# # Firewall rules - keep as /rest/
# curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/firewallrule" \
#   --cookie unifi-cookies -s > firewall-rules.json

# curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/firewallgroup" \
#   --cookie unifi-cookies -s > firewall-groups.json

# Port profiles - keep as /rest/
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/portconf" \
  --cookie unifi-cookies -s > port-profiles.json

# Devices - use /stat/ (this is working for you)
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/stat/device" \
  --cookie unifi-cookies -s > devices.json

# Additional device/stats endpoints
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/stat/device-basic" \
  --cookie unifi-cookies -s > devices-basic.json

# Port forwarding - try both
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/portforward" \
  --cookie unifi-cookies -s > port-forwards.json

# Wireless networks - keep as /rest/
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/wlanconf" \
  --cookie unifi-cookies -s > wireless-networks.json

# Site settings - keep as /rest/
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/setting" \
  --cookie unifi-cookies -s > site-settings.json

# User groups - keep as /rest/
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/rest/usergroup" \
  --cookie unifi-cookies -s > user-groups.json

# Gateway/UDM specific endpoints
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/stat/sysinfo" \
  --cookie unifi-cookies -s > gateway-sysinfo.json

# System information (includes UDM details)
curl -k -X GET "$CONTROLLER/api/system" \
  --cookie unifi-cookies -s > system-info.json

# UDM specific device info
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/stat/device" \
  --cookie unifi-cookies -s | jq '.data[] | select(.type == "udm" or .type == "usg" or .type == "ugw")' > gateway-device.json

# Health information (includes gateway)
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/stat/health" \
  --cookie unifi-cookies -s > health-stats.json

# Site information (may include gateway details)
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/stat/current-user" \
  --cookie unifi-cookies -s > current-user.json
  
# Add after the existing device endpoints
curl -k -X GET "$CONTROLLER/proxy/network/api/s/default/stat/sta" \
  --cookie unifi-cookies -s > connected-clients.json

    echo "Configuration extracted successfully!"
else
    echo "Login failed"
fi

# Cleanup
rm -f unifi-cookies
