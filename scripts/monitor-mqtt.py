#!/usr/bin/env python3
"""
Monitor MQTT messages from MotionPlay device
Usage: python3 monitor-mqtt.py
"""

import json
import time
from datetime import datetime
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder
import boto3

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Statistics
stats = {
    'total_messages': 0,
    'total_readings': 0,
    'sessions': {},
    'start_time': time.time()
}

def on_message_received(topic, payload, **kwargs):
    """Callback when message is received"""
    stats['total_messages'] += 1
    
    try:
        data = json.loads(payload)
        session_id = data.get('session_id', 'unknown')
        batch_offset = data.get('batch_offset', '?')
        readings_count = len(data.get('readings', []))
        payload_size = len(payload)
        
        # Track session stats
        if session_id not in stats['sessions']:
            stats['sessions'][session_id] = {
                'batches': 0,
                'readings': 0,
                'start_time': time.time()
            }
        
        stats['sessions'][session_id]['batches'] += 1
        stats['sessions'][session_id]['readings'] += readings_count
        stats['total_readings'] += readings_count
        
        # Print message info
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"{Colors.OKCYAN}[{timestamp}]{Colors.ENDC} "
              f"Session: {Colors.BOLD}{session_id}{Colors.ENDC} | "
              f"Batch: {batch_offset} | "
              f"Readings: {Colors.OKGREEN}{readings_count}{Colors.ENDC} | "
              f"Size: {payload_size:,} bytes")
        
        # Print running totals
        session_total = stats['sessions'][session_id]['readings']
        print(f"  📊 Session total: {session_total} readings "
              f"({stats['sessions'][session_id]['batches']} batches)")
        print(f"  📈 Grand total: {stats['total_readings']} readings "
              f"({stats['total_messages']} messages)")
        print()
        
    except json.JSONDecodeError:
        print(f"{Colors.FAIL}❌ Failed to parse message{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error processing message: {e}{Colors.ENDC}")

def main():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("═" * 60)
    print("  🔍 MotionPlay MQTT Monitor")
    print("═" * 60)
    print(f"{Colors.ENDC}\n")
    
    # Get IoT endpoint
    iot_client = boto3.client('iot', region_name='us-west-2')
    endpoint = iot_client.describe_endpoint(endpointType='iot:Data-ATS')
    endpoint_address = endpoint['endpointAddress']
    
    topic = "motionplay/+/data"
    
    print(f"{Colors.OKBLUE}Endpoint:{Colors.ENDC} {endpoint_address}")
    print(f"{Colors.OKBLUE}Topic:{Colors.ENDC} {topic}")
    print(f"\n{Colors.WARNING}⏳ Waiting for messages...{Colors.ENDC}")
    print(f"{Colors.WARNING}   Start a session on your device to see data{Colors.ENDC}\n")
    print("─" * 60)
    print()
    
    # Create MQTT connection
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
    
    # Build connection using AWS IoT credentials
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=endpoint_address,
        cert_filepath="/path/to/cert.pem",  # You'll need to provide these
        pri_key_filepath="/path/to/private.key",
        client_bootstrap=client_bootstrap,
        ca_filepath="/path/to/AmazonRootCA1.pem",
        client_id="mqtt-monitor-" + str(int(time.time())),
        clean_session=False,
        keep_alive_secs=30
    )
    
    print(f"{Colors.OKGREEN}✓ Connecting to IoT Core...{Colors.ENDC}")
    connect_future = mqtt_connection.connect()
    connect_future.result()
    print(f"{Colors.OKGREEN}✓ Connected!{Colors.ENDC}\n")
    
    # Subscribe to topic
    print(f"{Colors.OKGREEN}✓ Subscribing to {topic}...{Colors.ENDC}")
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=topic,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received
    )
    subscribe_future.result()
    print(f"{Colors.OKGREEN}✓ Subscribed!{Colors.ENDC}\n")
    print("═" * 60)
    print()
    
    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⏹ Stopping monitor...{Colors.ENDC}\n")
        
        # Print final statistics
        print("═" * 60)
        print(f"{Colors.HEADER}{Colors.BOLD}  📊 Final Statistics{Colors.ENDC}")
        print("═" * 60)
        print(f"Total messages received: {stats['total_messages']}")
        print(f"Total readings received: {stats['total_readings']}")
        print(f"Runtime: {time.time() - stats['start_time']:.1f}s")
        print()
        
        if stats['sessions']:
            print(f"{Colors.BOLD}Sessions:{Colors.ENDC}")
            for session_id, session_stats in stats['sessions'].items():
                print(f"  • {session_id}:")
                print(f"      Batches: {session_stats['batches']}")
                print(f"      Readings: {session_stats['readings']}")
                duration = time.time() - session_stats['start_time']
                print(f"      Duration: {duration:.1f}s")
        
        # Disconnect
        disconnect_future = mqtt_connection.disconnect()
        disconnect_future.result()
        print(f"\n{Colors.OKGREEN}✓ Disconnected{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error: {e}{Colors.ENDC}")

