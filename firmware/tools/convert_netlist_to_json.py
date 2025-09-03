#!/usr/bin/env python3
"""
KiCad Netlist Export Plugin - XML to JSON Converter
Converts KiCad's XML netlist format into a JSON graph structure.
"""

import sys
import os
import json
from collections import defaultdict
from datetime import datetime

def log_message(message, log_file=None):
    """Write a timestamped message to log file and stderr."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    # Always print to stderr for debugging
    print(log_entry, file=sys.stderr)
    
    # Also write to log file if provided
    if log_file:
        try:
            with open(log_file, "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Could not write to log file: {e}", file=sys.stderr)


def main():
    """Main entry point for the plugin."""
    # Determine log file path early
    log_file = None
    if len(sys.argv) >= 2:
        base_path = os.path.splitext(sys.argv[1])[0]
        log_file = base_path + "_export.log"
        
        # Clear previous log
        try:
            with open(log_file, "w") as f:
                f.write("=== KiCad Netlist to JSON Export Log ===\n")
        except:
            pass
    
    log_message("Script started", log_file)
    log_message(f"Python version: {sys.version}", log_file)
    log_message(f"Command line args: {sys.argv}", log_file)
    log_message(f"Current working directory: {os.getcwd()}", log_file)
    log_message(f"Script location: {os.path.abspath(__file__)}", log_file)
    
    # Check arguments
    if len(sys.argv) < 2:
        log_message("Error: Not enough arguments", log_file)
        log_message("Usage: convert_netlist_to_json.py <input_xml> [output_json]", log_file)
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Determine output file
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
        # KiCad might pass %O without extension, so add .json if needed
        if not output_file.endswith('.json'):
            output_file = output_file + '.json'
    else:
        base_name = os.path.splitext(input_file)[0]
        output_file = base_name + '.json'
    
    log_message(f"Input file: {input_file}", log_file)
    log_message(f"Output file: {output_file}", log_file)
    
    # Check input file exists
    if not os.path.exists(input_file):
        log_message(f"Error: Input file '{input_file}' not found.", log_file)
        sys.exit(1)
    else:
        log_message(f"Input file exists, size: {os.path.getsize(input_file)} bytes", log_file)
    
    # Setup import paths
    log_message("Setting up import paths...", log_file)
    
    # Try multiple possible locations for kicad_netlist_reader
    possible_paths = [
        "/Applications/KiCad/KiCad.app/Contents/SharedSupport/plugins/",
        os.path.dirname(os.path.abspath(__file__)),  # Same directory as this script
        os.path.dirname(input_file),  # Same directory as input file
    ]
    
    for path in possible_paths:
        if path and path not in sys.path:
            sys.path.insert(0, path)
            log_message(f"Added to sys.path: {path}", log_file)
    
    log_message(f"Full sys.path: {sys.path}", log_file)
    
    # Try to import kicad_netlist_reader
    log_message("Attempting to import kicad_netlist_reader...", log_file)
    
    try:
        import kicad_netlist_reader
        log_message("Successfully imported kicad_netlist_reader", log_file)
        log_message(f"Module location: {kicad_netlist_reader.__file__ if hasattr(kicad_netlist_reader, '__file__') else 'unknown'}", log_file)
    except ImportError as e:
        log_message(f"ImportError: {e}", log_file)
        
        # Try to find the file manually
        for path in possible_paths:
            reader_file = os.path.join(path, "kicad_netlist_reader.py")
            if os.path.exists(reader_file):
                log_message(f"Found kicad_netlist_reader.py at: {reader_file}", log_file)
            else:
                log_message(f"Not found at: {reader_file}", log_file)
        
        sys.exit(1)
    except Exception as e:
        log_message(f"Unexpected error during import: {type(e).__name__}: {e}", log_file)
        sys.exit(1)
    
    # Load the netlist
    log_message("Loading netlist...", log_file)
    try:
        netlist = kicad_netlist_reader.netlist(input_file)
        log_message("Successfully created netlist object", log_file)
    except Exception as e:
        log_message(f"Error creating netlist object: {type(e).__name__}: {e}", log_file)
        sys.exit(1)
    
    # Build the JSON structure
    log_message("Building JSON structure...", log_file)
    
    try:
        # Build component map
        components_map = {}
        
        # Get components - try different methods
        components = None
        if hasattr(netlist, 'getComponents'):
            components = netlist.getComponents()
            log_message(f"Got components using getComponents()", log_file)
        elif hasattr(netlist, 'components'):
            components = netlist.components
            log_message(f"Got components using .components", log_file)
        else:
            log_message("Error: Could not find components in netlist", log_file)
            sys.exit(1)
        
        component_count = 0
        for component in components:
            component_count += 1
            ref = component.getRef()
            
            # Extract component data
            component_data = {
                "refDes": ref,
                "partName": "",
                "value": "",
                "footprint": "",
                "customFields": {},
                "pins": []
            }
            
            # Try to get various attributes
            if hasattr(component, 'getPartName'):
                component_data["partName"] = component.getPartName() or ""
            
            if hasattr(component, 'getValue'):
                component_data["value"] = component.getValue() or ""
            
            if hasattr(component, 'getFootprint'):
                component_data["footprint"] = component.getFootprint() or ""
            
            components_map[ref] = component_data
        
        log_message(f"Processed {component_count} components", log_file)
        
        # Build nets and connections
        nets_map = {}  # Change from defaultdict to regular dict since we're storing objects now
        
        # Get nets - the kicad_netlist_reader typically uses getNets()
        nets = netlist.getNets()
        log_message(f"Got {len(nets)} nets using getNets()", log_file)
        
        net_count = 0
        node_count = 0
        for net in nets:
            net_count += 1
            
            # Debug first net
            if net_count == 1:
                log_message(f"First net object type: {type(net)}", log_file)
                all_attrs = dir(net)
                log_message(f"First net dir (first 30): {all_attrs[:30]}", log_file)
                # Look for interesting attributes
                for attr in ['name', 'code', 'children', 'attributes', 'element']:
                    if hasattr(net, attr):
                        value = getattr(net, attr)
                        log_message(f"net.{attr} = {value} (type: {type(value).__name__})", log_file)
            
            # Get net name and class from the attributes dictionary
            net_name = ""
            net_code = ""
            net_class = "Default"  # Default value
            if hasattr(net, 'attributes') and isinstance(net.attributes, dict):
                net_name = net.attributes.get('name', '')
                net_code = net.attributes.get('code', '')
                net_class = net.attributes.get('class', 'Default')
            
            if not net_name:
                net_name = f"Net-{net_code}" if net_code else f"Net_{net_count}"
            
            # Get the nodes - check what's available
            nodes = []
            if hasattr(net, 'children'):
                nodes = net.children
            elif hasattr(net, 'nodes'):
                nodes = net.nodes
            
            if not nodes:
                log_message(f"No nodes found for net {net_name}", log_file)
                continue
            
            if net_count <= 2:  # Log first couple nets
                log_message(f"Processing net '{net_name}' (code: {net_code}) with {len(nodes)} nodes", log_file)
            
            for node in nodes:
                node_count += 1
                
                # Debug first node - check what's in the attributes
                if node_count == 1:
                    log_message(f"First node type: {type(node)}", log_file)
                    node_attrs = dir(node)
                    log_message(f"First node dir (first 30): {node_attrs[:30]}", log_file)
                    # Check for specific attributes
                    for attr in ['name', 'ref', 'pin', 'pinfunction', 'attributes', 'element', 'children']:
                        if hasattr(node, attr):
                            value = getattr(node, attr)
                            log_message(f"node.{attr} = {value} (type: {type(value).__name__})", log_file)
                
                # Get node properties from attributes dictionary
                ref = ""
                pin = ""
                pinfunction = ""
                pintype = ""
                
                # Debug: Check if attributes exist and what's in them for every node
                if hasattr(node, 'attributes'):
                    if node_count <= 5:
                        log_message(f"Node {node_count} attributes dict: {node.attributes}", log_file)
                    
                    if isinstance(node.attributes, dict):
                        ref = node.attributes.get('ref', '')
                        pin = node.attributes.get('pin', '')
                        pinfunction = node.attributes.get('pinfunction', '')
                        pintype = node.attributes.get('pintype', '')
                
                # Log what we extracted
                if node_count <= 5:
                    log_message(f"Node {node_count} extracted: ref={ref}, pin={pin}, pinfunction={pinfunction}, pintype={pintype}, net={net_name}", log_file)
                
                # Add pin to component
                if ref and ref in components_map:
                    components_map[ref]["pins"].append({
                        "pinName": pinfunction,
                        "pinNumber": pin,
                        "pinType": pintype,
                        "net": net_name
                    })
                elif ref:
                    if node_count <= 5:
                        log_message(f"Warning: Component {ref} not found in components_map", log_file)
                
                # Add connection to net - store the net class here
                if ref:
                    if net_name not in nets_map:
                        nets_map[net_name] = {"class": net_class, "connections": []}
                    nets_map[net_name]["connections"].append({
                        "refDes": ref,
                        "pin": pinfunction if pinfunction else pin
                    })
        
        log_message(f"Processed {net_count} nets with {node_count} total nodes", log_file)
        
        # Get circuit title/name
        circuit_name = "Circuit"
        if hasattr(netlist, 'getTitle'):
            circuit_name = netlist.getTitle() or "Circuit"
        elif hasattr(netlist, 'getSource'):
            circuit_name = os.path.basename(netlist.getSource())
        
        # Build final structure
        circuit_data = {
            "circuitName": circuit_name,
            "components": list(components_map.values()),
            "nets": [
                {"netName": name, "connections": connections} 
                for name, connections in nets_map.items()
            ]
        }
        
        log_message(f"Built JSON structure with {len(components_map)} components and {len(nets_map)} nets", log_file)
        
    except Exception as e:
        log_message(f"Error building JSON structure: {type(e).__name__}: {e}", log_file)
        import traceback
        log_message(f"Traceback: {traceback.format_exc()}", log_file)
        sys.exit(1)
    
    # Write output
    log_message(f"Writing output to: {output_file}", log_file)
    try:
        with open(output_file, 'w') as f:
            json.dump(circuit_data, f, indent=2)
        log_message(f"Successfully wrote {os.path.getsize(output_file)} bytes to {output_file}", log_file)
        
        # Verify the file was created
        if os.path.exists(output_file):
            log_message(f"Output file verified to exist", log_file)
        else:
            log_message(f"Warning: Output file not found after writing!", log_file)
            
    except Exception as e:
        log_message(f"Error writing output file: {type(e).__name__}: {e}", log_file)
        sys.exit(1)
    
    log_message("Script completed successfully", log_file)
    sys.exit(0)


if __name__ == "__main__":
    main()