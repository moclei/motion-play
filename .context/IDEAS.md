# Feature Ideas & Backlog

Ideas for future development. Not prioritized, just captured.

---

## Detection & Algorithms

### Direction Detection
- Implement reliable direction detection (A→B vs B→A sensor sequence)
- Sample rate now ~360 Hz (was 24 Hz) ✅ - sufficient for detection
- Peak detection algorithm for identifying passing objects
- Derivative-based direction classification
- Confidence scoring system

### Object Detection Optimization
- ✅ Sample rate improved from 24 Hz to ~360 Hz (achieved!)
- Further I2C clock speed increase (400kHz → 1MHz) for even higher rates
- Disable ambient light reading for additional speedup when not needed
- Integration time trade-offs (1T vs 2T vs 4T)
- Calibration: proximity vs distance curves

### ML/AI Pipeline
- Export labeled session data for training
- SageMaker integration for model training
- TensorFlow Lite on ESP32 for on-device inference
- Pattern recognition for different objects/speeds

---

## Hardware & Firmware

### Sensor Improvements
- Interrupt-based detection (vs polling)
- Multi-pulse IR for extended range
- Sensor calibration routine
- Dynamic threshold adjustment based on ambient conditions

### Power Management
- Battery operation support
- WiFi sleep mode when idle
- Display dimming/sleep
- Custom power PCB to replace DWEII module

### Future Hardware
- Migrate from T-Display-S3 to custom ESP32-S3 board
- Integrate ESP32-S3 directly into main PCB
- Add second sensor ring for more detection points
- Bluetooth mesh for multi-device coordination

---

## Frontend & Cloud

### Session Management
- Session comparison view (side-by-side analysis)
- Batch labeling for multiple sessions
- Session templates/presets
- Auto-cleanup of old sessions (TTL)

### Real-time Features
- WebSocket for live sensor data visualization
- Live detection event stream
- Real-time multi-device coordination view

### Data Analysis
- Statistical analysis tools in frontend
- Anomaly detection for sensor readings
- Session quality scoring
- Export to common ML formats (TFRecord, etc.)

### Session Compression
- Compress sensor data before cloud storage
- Delta encoding for consecutive readings
- S3 for large sessions (>400KB)
- Estimated 10-50x compression possible

---

## Multi-Device

### Bluetooth Mesh
- Device-to-device communication
- Coordinated detection across multiple hoops
- Latency synchronization
- Group management

### Multi-Device Cloud
- Device groups in DynamoDB
- Coordinated session recording
- Cross-device event correlation
- Training/game presets per group

---

## Game Modes

### Training Programs
- Reaction time training
- Accuracy training (target zones)
- Speed progression
- Custom workout builder

### Game Implementations
- Simple pass-through counting
- Timed challenges
- Pattern matching (specific sequence)
- Competitive multi-player modes

---

## Infrastructure

### Security
- Cognito user authentication
- Per-user device permissions
- Rate limiting
- Audit logging

### Monitoring
- CloudWatch dashboards
- Device health alerts
- Usage analytics
- Cost monitoring

### Deployment
- Infrastructure as Code (CDK)
- CI/CD pipeline
- OTA firmware updates via AWS IoT Jobs
- Staged rollouts

---

*Last Updated: December 5, 2025*

