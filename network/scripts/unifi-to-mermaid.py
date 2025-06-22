#!/usr/bin/env python3
"""
UniFi Configuration to Mermaid Diagram Parser
Converts UniFi API JSON exports to Mermaid diagrams for GitHub documentation
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

class UniFiToMermaid:
    def __init__(self, config_dir: str = '.'):
        self.config_dir = Path(config_dir)
        self.networks = {}
        self.devices = {}
        self.port_profiles = {}
        self.firewall_rules = []
        self.firewall_groups = {}
        
    def load_configs(self):
        """Load all UniFi configuration files"""
        required_files = ['networks.json', 'devices.json']
        optional_files = ['port-profiles.json', 'firewall-rules.json', 'firewall-groups.json']
        
        try:
            # Load required files
            for filename in required_files:
                filepath = self.config_dir / filename
                if not filepath.exists():
                    print(f"❌ Required file not found: {filename}")
                    sys.exit(1)
            
            # Load networks (VLANs)
            with open(self.config_dir / 'networks.json') as f:
                data = json.load(f)
                self.networks = {net['_id']: net for net in data.get('data', [])}
                print(f"✅ Loaded {len(self.networks)} networks")
                
            # Load devices (switches, APs, etc.)
            with open(self.config_dir / 'devices.json') as f:
                data = json.load(f)
                self.devices = {dev['_id']: dev for dev in data.get('data', [])}
                print(f"✅ Loaded {len(self.devices)} devices")
                
            # Load optional files
            for filename in optional_files:
                filepath = self.config_dir / filename
                if filepath.exists():
                    try:
                        with open(filepath) as f:
                            data = json.load(f)
                            
                        if filename == 'port-profiles.json':
                            self.port_profiles = {prof['_id']: prof for prof in data.get('data', [])}
                            print(f"✅ Loaded {len(self.port_profiles)} port profiles")
                        elif filename == 'firewall-rules.json':
                            self.firewall_rules = data.get('data', [])
                            print(f"✅ Loaded {len(self.firewall_rules)} firewall rules")
                        elif filename == 'firewall-groups.json':
                            self.firewall_groups = {grp['_id']: grp for grp in data.get('data', [])}
                            print(f"✅ Loaded {len(self.firewall_groups)} firewall groups")
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Invalid JSON in {filename}: {e}")
                else:
                    print(f"⚠️  Optional file not found: {filename} (will use defaults)")
            
            print("✅ All available configuration files loaded successfully")
            
        except FileNotFoundError as e:
            print(f"❌ Required configuration file not found: {e}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def generate_physical_topology(self) -> str:
        """Generate physical network topology - actual cable/wireless connections"""
        mermaid = ["```mermaid", "graph TD"]
        
        # Add Internet connection
        mermaid.append('    Internet["🌐 Internet"]')
        
        # Find UDM/Gateway
        gateway = None
        print("🔍 Looking for gateway device...")
        for device in self.devices.values():
            device_type = device.get('type')
            device_name = device.get('name', 'Unknown')
            print(f"   Found device: {device_name} (type: {device_type})")
            
            if device_type in ['udm', 'usg', 'ugw']:
                gateway = device
                print(f"   ✅ Gateway found: {device_name}")
                break
                
        if gateway:
            gateway_name = gateway.get('name', 'UDM SE')
            gateway_model = gateway.get('model', 'UDM SE')
            gateway_id = "Gateway"
            mermaid.append(f'    {gateway_id}["{gateway_name}<br/>{gateway_model}"]')
            mermaid.append('    Internet --> Gateway')
        else:
            print("   ❌ No gateway device found!")
            gateway_id = "Gateway"
            mermaid.append('    Gateway["UDM SE<br/>Gateway"]')
            mermaid.append('    Internet --> Gateway')
        
        # Add physical devices and their connections
        access_points = []
        switches = []
        
        for device in self.devices.values():
            device_type = device.get('type')
            device_name = device.get('name', device.get('model', 'Unknown'))
            device_id = f"{device_type.upper()}_{device['_id'][:8]}"
            
            if device_type in ['usw', 'switch']:  # UniFi switches
                port_count = len(device.get('port_table', []))
                
                # Try to find uplink port to gateway
                uplink_port = None
                for port in device.get('port_table', []):
                    if port.get('up', False):
                        # Check if this port connects to gateway (simplified heuristic)
                        port_idx = port.get('port_idx')
                        if port_idx == 1:  # Often port 1 is uplink
                            uplink_port = port_idx
                            break
                
                mermaid.append(f'    {device_id}["{device_name}<br/>Switch ({port_count} ports)"]')
                
                # Connect switch to gateway with port info
                if uplink_port:
                    mermaid.append(f'    {gateway_id} ---|"Port {uplink_port}"| {device_id}')
                else:
                    mermaid.append(f'    {gateway_id} ---|"Ethernet"| {device_id}')
                switches.append((device_id, device))
                    
            elif device_type in ['uap', 'uap-ac', 'uap-hd', 'uap-pro']:  # UniFi Access Points
                # Check if it's wired or wireless uplink
                uplink = device.get('uplink', {})
                uplink_type = uplink.get('type', 'unknown')
                
                if uplink_type == 'wireless':
                    connection_type = "📶 Wireless Mesh"
                    line_style = "-.->|\"Mesh\"|"
                else:
                    connection_type = "🔌 Ethernet"
                    line_style = "---|\"Ethernet\"|"
                
                mermaid.append(f'    {device_id}["{device_name}<br/>Access Point<br/>{connection_type}"]')
                access_points.append((device_id, device, uplink_type, uplink))
        
        # Add physical connections for access points
        for ap_id, ap_device, uplink_type, uplink in access_points:
            if uplink_type == 'wireless':
                # Find the mesh parent by MAC
                uplink_mac = uplink.get('uplink_mac')
                if uplink_mac:
                    for parent_device in self.devices.values():
                        if parent_device.get('mac') == uplink_mac:
                            parent_type = parent_device.get('type', '')
                            if parent_type in ['udm', 'usg', 'ugw']:
                                parent_id = gateway_id
                            else:
                                parent_id = f"{parent_type.upper()}_{parent_device['_id'][:8]}"
                            mermaid.append(f'    {parent_id} -.->|"Mesh"| {ap_id}')
                            break
            else:
                # Wired AP - try to find actual port connection
                uplink_remote_port = uplink.get('uplink_remote_port')
                port_label = f"Port {uplink_remote_port}" if uplink_remote_port else "Ethernet"
                
                # Find which switch this AP is connected to
                uplink_mac = uplink.get('uplink_mac')
                connected_to_switch = False
                
                if uplink_mac:
                    for switch_device in self.devices.values():
                        if switch_device.get('mac') == uplink_mac and switch_device.get('type') in ['usw', 'switch']:
                            switch_id = f"USW_{switch_device['_id'][:8]}"
                            mermaid.append(f'    {switch_id} ---|"{port_label}"| {ap_id}')
                            connected_to_switch = True
                            break
                
                # If not connected to switch, assume connected to gateway
                if not connected_to_switch:
                    mermaid.append(f'    {gateway_id} ---|"{port_label}"| {ap_id}')
        
        mermaid.append("```")
        return '\n'.join(mermaid)

    def generate_logical_topology(self) -> str:
        """Generate logical network topology - VLANs and subnets"""
        mermaid = ["```mermaid", "graph TD"]
        
        # Find gateway for logical connections
        gateway = None
        for device in self.devices.values():
            if device.get('type') in ['udm', 'usg', 'ugw']:
                gateway = device
                break
        
        if gateway:
            gateway_name = gateway.get('name', 'UDM SE')
            mermaid.append(f'    Router["{gateway_name}<br/>Router/Firewall"]')
        else:
            mermaid.append('    Router["UDM SE<br/>Router/Firewall"]')
        
        # Add VLANs/Networks as logical segments
        vlan_nodes = []
        for net_id, network in self.networks.items():
            name = network.get('name', 'Unknown')
            vlan = network.get('vlan')
            subnet = network.get('ip_subnet', 'N/A')
            
            vlan_label = f"VLAN {vlan}" if vlan else "Default"
            node_id = f"VLAN{vlan if vlan else '1'}"
            
            mermaid.append(f'    {node_id}["{name}<br/>{vlan_label}<br/>{subnet}"]')
            mermaid.append(f'    Router --> {node_id}')
            vlan_nodes.append((node_id, vlan, name))
        
        # Add logical services/devices to VLANs
        # This could be enhanced with actual IP assignments if available
        example_services = {
            1: ["Samba AD", "Proxmox", "DNS"],
            20: ["SMB Server", "User Devices"],
            30: ["Keycloak", "Web Services"]
        }
        
        for node_id, vlan, name in vlan_nodes:
            if vlan in example_services:
                for service in example_services[vlan]:
                    service_id = f"SVC_{service.replace(' ', '')}"
                    mermaid.append(f'    {service_id}["{service}"]')
                    mermaid.append(f'    {node_id} --> {service_id}')
        
        # Add firewall rules as logical connections
        if self.firewall_rules:
            mermaid.append('    subgraph "Firewall Rules"')
            for i, rule in enumerate(self.firewall_rules[:3]):  # Show first 3 rules
                if rule.get('enabled', True):
                    rule_name = rule.get('name', f'Rule {i+1}')
                    action = rule.get('action', 'allow')
                    icon = "✅" if action == 'allow' else "❌"
                    mermaid.append(f'        FW{i}["{icon} {rule_name}"]')
            mermaid.append('    end')
        
        mermaid.append("```")
        return '\n'.join(mermaid)

    def generate_switch_details(self) -> str:
        """Generate detailed switch port configuration"""
        switches = [dev for dev in self.devices.values() if dev.get('type') in ['usw', 'switch']]
        
        if not switches:
            return "No switches found in configuration."
            
        mermaid_parts = []
        
        for switch in switches:
            switch_name = switch.get('name', switch.get('model', 'Switch'))
            switch_id = f"SW_{switch['_id'][:8]}"
            
            mermaid = ["```mermaid", f"graph TD"]
            mermaid.append(f'    subgraph {switch_id}["{switch_name}"]')
            
            # Get port overrides (configured ports)
            port_overrides = switch.get('port_overrides', [])
            port_table = switch.get('port_table', [])
            
            # Create a mapping of port configurations
            port_configs = {}
            for override in port_overrides:
                port_idx = override.get('port_idx')
                if port_idx:
                    port_configs[port_idx] = override
            
            # Generate port information
            active_ports = []
            for port in port_table:
                port_idx = port.get('port_idx')
                if not port_idx:
                    continue
                    
                port_config = port_configs.get(port_idx, {})
                port_name = port_config.get('name', f'Port {port_idx}')
                
                # Determine port type and VLAN
                port_type = "Access"
                vlan_info = "Default"
                
                # Check if port has profile configuration
                portconf_id = port_config.get('portconf_id')
                if portconf_id and portconf_id in self.port_profiles:
                    profile = self.port_profiles[portconf_id]
                    if profile.get('name'):
                        port_type = profile['name']
                    
                    # Check for native VLAN
                    native_vlan = profile.get('native_networkconf_id')
                    if native_vlan and native_vlan in self.networks:
                        network = self.networks[native_vlan]
                        vlan_num = network.get('vlan', 1)
                        vlan_info = f"VLAN {vlan_num}"
                
                # Check if port is up
                is_up = port.get('up', False)
                status_icon = "🟢" if is_up else "🔴"
                
                # PoE information
                poe_info = ""
                if port.get('port_poe', False):
                    poe_mode = port_config.get('poe_mode', 'auto')
                    poe_info = f"<br/>PoE: {poe_mode}"
                
                port_node_id = f"P{port_idx}"
                port_label = f"{status_icon} {port_name}<br/>{port_type}<br/>{vlan_info}{poe_info}"
                
                mermaid.append(f'        {port_node_id}["{port_label}"]')
                
                if is_up:
                    active_ports.append((port_idx, port_node_id, vlan_info))
            
            mermaid.append("    end")
            
            # Add connections to VLANs for active ports
            for port_idx, port_node_id, vlan_info in active_ports:
                if "VLAN" in vlan_info:
                    vlan_num = vlan_info.split()[1]
                    mermaid.append(f'    {switch_id}.{port_node_id} -.-> VLAN{vlan_num}_EXT["External {vlan_info}"]')
            
            mermaid.append("```")
            mermaid_parts.append(f"## {switch_name}\n\n" + '\n'.join(mermaid))
        
        return '\n\n'.join(mermaid_parts)

    def generate_firewall_matrix(self) -> str:
        """Generate firewall rules visualization"""
        if not self.firewall_rules:
            # Generate VLAN isolation matrix instead
            return self.generate_vlan_isolation_matrix()
            
        mermaid = ["```mermaid", "graph LR"]
        
        # Create source and destination subgraphs
        sources = set()
        destinations = set()
        
        for rule in self.firewall_rules:
            if not rule.get('enabled', True):
                continue
                
            src_id = rule.get('src_networkconf_id')
            dst_id = rule.get('dst_networkconf_id')
            
            if src_id and src_id in self.networks:
                sources.add(src_id)
            if dst_id and dst_id in self.networks:
                destinations.add(dst_id)
        
        # Add source networks
        if sources:
            mermaid.append("    subgraph Sources")
            for net_id in sources:
                network = self.networks[net_id]
                name = network.get('name', 'Unknown')
                vlan = network.get('vlan', 1)
                mermaid.append(f'        SRC_{net_id[:8]}["{name}<br/>VLAN {vlan}"]')
            mermaid.append("    end")
        
        # Add destination networks
        if destinations:
            mermaid.append("    subgraph Destinations")
            for net_id in destinations:
                network = self.networks[net_id]
                name = network.get('name', 'Unknown')
                vlan = network.get('vlan', 1)
                mermaid.append(f'        DST_{net_id[:8]}["{name}<br/>VLAN {vlan}"]')
            mermaid.append("    end")
        
        # Add firewall rules as connections
        for rule in self.firewall_rules:
            if not rule.get('enabled', True):
                continue
                
            src_id = rule.get('src_networkconf_id')
            dst_id = rule.get('dst_networkconf_id')
            action = rule.get('action', 'allow')
            protocol = rule.get('protocol', 'all')
            dst_port = rule.get('dst_port', '')
            
            if src_id and dst_id and src_id in self.networks and dst_id in self.networks:
                src_node = f"SRC_{src_id[:8]}"
                dst_node = f"DST_{dst_id[:8]}"
                
                # Create rule label
                rule_label = f"{protocol}"
                if dst_port:
                    rule_label += f":{dst_port}"
                
                # Different arrow styles for allow/deny
                if action == 'allow':
                    mermaid.append(f'    {src_node} -->|"{rule_label}"| {dst_node}')
                else:
                    mermaid.append(f'    {src_node} -.->|"❌ {rule_label}"| {dst_node}')
        
        mermaid.append("```")
        return '\n'.join(mermaid)

    def generate_vlan_isolation_matrix(self) -> str:
        """Generate VLAN isolation matrix when no explicit firewall rules exist"""
        if not self.networks:
            return "No network configuration found."
            
        output = []
        output.append("## Firewall Zone Configuration")
        output.append("")
        output.append("*UDM SE uses zone-based firewall. Zone details not accessible via API.*")
        output.append("")
        
        # Create VLAN and zone table
        vlans = []
        zones = {}
        
        for network in self.networks.values():
            name = network.get('name', 'Unknown')
            vlan = network.get('vlan')
            subnet = network.get('ip_subnet', 'N/A')
            zone_id = network.get('firewall_zone_id', 'No Zone')
            internet_access = network.get('internet_access_enabled', True)
            
            vlans.append((vlan, name, subnet, zone_id, internet_access))
            
            # Group networks by zone
            if zone_id != 'No Zone':
                if zone_id not in zones:
                    zones[zone_id] = []
                zones[zone_id].append(name)
        
        vlans.sort(key=lambda x: x[0] if x[0] is not None else 999)  # Sort by VLAN number
        
        # Create table header
        output.append("| VLAN | Network Name | Subnet | Internet Access | Firewall Zone |")
        output.append("|------|--------------|--------|-----------------|---------------|")
        
        for vlan, name, subnet, zone_id, internet_access in vlans:
            vlan_display = str(vlan) if vlan is not None else "WAN"
            internet_icon = "🌐 Yes" if internet_access else "🚫 No"
            zone_short = zone_id[:8] + "..." if len(zone_id) > 12 else zone_id
            output.append(f"| {vlan_display} | {name} | {subnet} | {internet_icon} | {zone_short} |")
        
        output.append("")
        
        # Show firewall zone groupings
        if zones:
            output.append("### Firewall Zone Groupings:")
            for zone_id, networks in zones.items():
                zone_short = zone_id[:12] + "..." if len(zone_id) > 16 else zone_id
                network_list = ", ".join(networks)
                output.append(f"- **Zone {zone_short}**: {network_list}")
            output.append("")
        
        output.append("### Typical UDM SE Zone-Based Firewall Behavior:")
        output.append("- **Same Zone**: Networks in same zone can communicate freely")
        output.append("- **Different Zones**: Communication blocked by default")
        output.append("- **WAN Zones**: Handle internet/external access")
        output.append("- **Custom Rules**: Can be created between zones in UniFi UI")
        output.append("")
        
        # Add cross-VLAN access requirements for your setup
        output.append("### Required Cross-Zone Access for Your Setup:")
        
        # Find which zones contain your key services
        mgmt_networks = [name for vlan, name, _, _, _ in vlans if 'management' in name.lower() or vlan == 1]
        secure_networks = [name for vlan, name, _, _, _ in vlans if 'secure' in name.lower() or vlan == 20]
        services_networks = [name for vlan, name, _, _, _ in vlans if 'service' in name.lower() or vlan == 30]
        
        if secure_networks and mgmt_networks:
            output.append(f"- **{secure_networks[0]} → {mgmt_networks[0]}**: Ports 53, 88, 389, 445, 464 (for AD authentication)")
        
        if services_networks and mgmt_networks:
            output.append(f"- **{services_networks[0]} → {mgmt_networks[0]}**: Ports 389, 636 (for Keycloak LDAP)")
        
        output.append("")
        output.append("*Configure these rules in UniFi Network → Settings → Policy Engine → Firewall*")
        
        return '\n'.join(output)

    def generate_port_mapping(self) -> str:
        """Generate detailed port mapping for cable management"""
        output = []
        
        # Process each device with ports (switches and gateways)
        for device in self.devices.values():
            device_type = device.get('type')
            if device_type not in ['usw', 'switch', 'udm', 'usg', 'ugw']:
                continue
                
            device_name = device.get('name', device.get('model', 'Unknown'))
            device_model = device.get('model', '')
            
            # Add device type indicator
            if device_type in ['udm', 'usg', 'ugw']:
                type_label = "Gateway/Router"
            else:
                type_label = "Switch"
                
            output.append(f"## {device_name} ({type_label})")
            if device_model:
                output.append(f"*Model: {device_model}*")
            output.append("")
            
            # Create port mapping table
            output.append("| Port | Status | Speed | Device Connected | Device Type | VLAN | Profile | PoE | Notes |")
            output.append("|------|--------|-------|------------------|-------------|------|---------|-----|-------|")
            
            port_table = device.get('port_table', [])
            port_overrides = device.get('port_overrides', [])
            
            # Create mapping of port overrides
            port_configs = {}
            for override in port_overrides:
                port_idx = override.get('port_idx')
                if port_idx:
                    port_configs[port_idx] = override
            
            # Process each port
            for port in sorted(port_table, key=lambda x: x.get('port_idx', 0)):
                port_idx = port.get('port_idx')
                if not port_idx:
                    continue
                    
                # Port status
                is_up = port.get('up', False)
                status = "🟢 Up" if is_up else "🔴 Down"
                
                # Port speed
                speed = port.get('speed', 0)
                speed_str = f"{speed}M" if speed else "N/A"
                
                # Connected device info
                connected_device = "Not Connected"
                device_connected_type = ""
                
                if is_up:
                    # Try to find what's connected by looking at other devices
                    current_device_mac = device.get('mac')
                    for other_device in self.devices.values():
                        uplink = other_device.get('uplink', {})
                        if (uplink.get('uplink_mac') == current_device_mac and 
                            uplink.get('uplink_remote_port') == port_idx):
                            connected_device = other_device.get('name', other_device.get('model', 'Unknown'))
                            other_type = other_device.get('type', '')
                            if other_type == 'uap':
                                device_connected_type = "Access Point"
                            elif other_type in ['usw', 'switch']:
                                device_connected_type = "Switch"
                            elif other_type in ['udm', 'usg']:
                                device_connected_type = "Gateway"
                            else:
                                device_connected_type = other_type.upper()
                            break
                    
                    # Special handling for gateway ports
                    if device_type in ['udm', 'usg', 'ugw'] and connected_device == "Not Connected":
                        if port_idx == 1:
                            connected_device = "Internet/WAN"
                            device_connected_type = "ISP Connection"
                        elif port.get('tx_bytes', 0) > 0 or port.get('rx_bytes', 0) > 0:
                            connected_device = "LAN Device"
                            device_connected_type = "Network"
                    
                    # For switches, check for uplink or unknown devices
                    elif device_type in ['usw', 'switch'] and connected_device == "Not Connected":
                        if port_idx == 1:
                            connected_device = "Gateway/Router"
                            device_connected_type = "Uplink"
                        elif port.get('tx_bytes', 0) > 0 or port.get('rx_bytes', 0) > 0:
                            connected_device = "Unknown Device"
                            device_connected_type = "Unknown"
                
                # VLAN and profile info
                port_config = port_configs.get(port_idx, {})
                port_name = port_config.get('name', f'Port {port_idx}')
                
                # Get profile information
                vlan_info = "Default"
                profile_name = "Default"
                portconf_id = port_config.get('portconf_id')
                
                if portconf_id and portconf_id in self.port_profiles:
                    profile = self.port_profiles[portconf_id]
                    profile_name = profile.get('name', 'Custom')
                    
                    # Get VLAN info
                    native_vlan_id = profile.get('native_networkconf_id')
                    if native_vlan_id and native_vlan_id in self.networks:
                        network = self.networks[native_vlan_id]
                        vlan_num = network.get('vlan', 1)
                        vlan_info = f"VLAN {vlan_num}"
                
                # PoE information
                poe_info = "No"
                if port.get('port_poe', False):
                    poe_mode = port_config.get('poe_mode', 'auto')
                    poe_power = port.get('poe_power', 0)
                    
                    # Handle poe_power being string or number
                    try:
                        poe_power_num = float(poe_power) if poe_power else 0
                        if poe_power_num > 0:
                            poe_info = f"Yes ({poe_power_num:.1f}W)"
                        else:
                            poe_info = f"Yes ({poe_mode})"
                    except (ValueError, TypeError):
                        poe_info = f"Yes ({poe_mode})"
                
                # Additional notes
                notes = []
                if port_config.get('name') and port_config['name'] != f'Port {port_idx}':
                    notes.append(f"Named: {port_config['name']}")
                if port.get('full_duplex', False):
                    notes.append("Full Duplex")
                
                notes_str = ", ".join(notes) if notes else ""
                
                # Add row to table
                output.append(f"| {port_idx} | {status} | {speed_str} | {connected_device} | {device_connected_type} | {vlan_info} | {profile_name} | {poe_info} | {notes_str} |")
            
            output.append("")
            
            # Add summary statistics
            total_ports = len(port_table)
            active_ports = sum(1 for p in port_table if p.get('up', False))
            poe_ports = sum(1 for p in port_table if p.get('port_poe', False))
            
            output.append(f"**Summary:** {active_ports}/{total_ports} ports active")
            if poe_ports > 0:
                # Calculate total PoE power with error handling
                total_poe_power = 0
                for p in port_table:
                    poe_power = p.get('poe_power', 0)
                    try:
                        total_poe_power += float(poe_power) if poe_power else 0
                    except (ValueError, TypeError):
                        pass  # Skip invalid power values
                
                output.append(f", {poe_ports} PoE ports ({total_poe_power:.1f}W total)")
            output.append("")
            output.append("---")
            output.append("")
        
        return '\n'.join(output) if output else "No switches or gateways found for port mapping."

    def generate_all_diagrams(self) -> Dict[str, str]:
        """Generate all Mermaid diagrams and return as dictionary"""
        return {
            'physical_topology': self.generate_physical_topology(),
            'logical_topology': self.generate_logical_topology(),
            'port_mapping': self.generate_port_mapping(),
            'switch_details': self.generate_switch_details(),
            'firewall_matrix': self.generate_firewall_matrix()
        }

def main():
    if len(sys.argv) > 1:
        config_dir = sys.argv[1]
    else:
        config_dir = '.'
    
    parser = UniFiToMermaid(config_dir)
    parser.load_configs()
    
    diagrams = parser.generate_all_diagrams()
    
    # Create output directory
    output_dir = Path('network-diagrams')
    output_dir.mkdir(exist_ok=True)
    
    # Write each diagram to a separate file
    for name, content in diagrams.items():
        output_file = output_dir / f'{name}.md'
        with open(output_file, 'w') as f:
            f.write(f"# {name.replace('_', ' ').title()}\n\n")
            f.write(content)
        print(f"📄 Generated: {output_file}")
    
    # Create combined documentation
    combined_file = output_dir / 'network-documentation.md'
    with open(combined_file, 'w') as f:
        f.write("# Network Documentation\n\n")
        f.write("*Auto-generated from UniFi Controller configuration*\n\n")
        
        f.write("## Physical Topology\n\n")
        f.write("Shows actual cable connections and wireless mesh links.\n\n")
        f.write(diagrams['physical_topology'])
        f.write("\n\n")
        
        f.write("## Logical Network\n\n") 
        f.write("Shows VLANs, subnets, and logical network segmentation.\n\n")
        f.write(diagrams['logical_topology'])
        f.write("\n\n")
        
        f.write("## Port Mapping\n\n")
        f.write("Detailed port-by-port documentation for cable management.\n\n")
        f.write(diagrams['port_mapping'])
        f.write("\n\n")
        
        f.write("## Switch Configuration\n\n")
        f.write(diagrams['switch_details'])
        f.write("\n\n")
        
        f.write("## Firewall Rules\n\n")
        f.write(diagrams['firewall_matrix'])
        f.write("\n\n")
        
        f.write("---\n")
        f.write("*Generated automatically from UniFi configuration*")
    
    print(f"📚 Combined documentation: {combined_file}")
    print("🎉 All network diagrams generated successfully!")

if __name__ == '__main__':
    main()