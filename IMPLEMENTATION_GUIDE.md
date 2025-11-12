# Motion Play Data Collection System - Implementation Guide

**Status:** In Progress  
**Current Phase:** Phase 0 - Setup & Preparation  
**Date Started:** November 12, 2025

---

## 📁 Repository Structure

```
motion-play/
├── firmware/              # ESP32-S3 code (PlatformIO)
│   ├── src/               # Source code
│   ├── include/           # Header files
│   ├── lib/               # Libraries
│   └── data/              # (To be created) Certificates and config files
├── lambda/                # AWS Lambda functions
│   ├── processData/       # (To be created) Process sensor data
│   ├── processStatus/     # (To be created) Update device status
│   ├── sendCommand/       # (To be created) Send commands to device
│   ├── getSessions/       # (To be created) Retrieve sessions
│   ├── getSessionData/    # (To be created) Get session details
│   ├── updateSession/     # (To be created) Update session metadata
│   └── deleteSession/     # (To be created) Delete sessions
├── frontend/              # React web application
│   └── motion-play-ui/    # (To be created) Vite + React + TypeScript
├── infrastructure/        # (Optional) AWS CDK or CloudFormation
├── hardware/              # PCB designs and schematics
└── docs/                  # Documentation
    └── data collection/   # Requirements, design, and implementation plan
```

---

## 🚀 Implementation Phases

### ✅ Phase 0: Setup & Preparation (Current)
**Duration:** Week 1 (4-6 hours)  
**Goal:** Establish development environment and project structure

#### Task Checklist:

- [ ] **Task 0.1: AWS Account Setup** (1 hour)
  - [ ] Run `aws configure` with your AWS credentials
  - [ ] Choose AWS region (recommended: `us-west-2`)
  - [ ] Test: `aws sts get-caller-identity`
  - [ ] Set up billing alert in AWS Console ($20/month threshold)

- [x] **Task 0.2: Project Repository Setup** (30 minutes)
  - [x] Created `lambda/`, `frontend/`, `infrastructure/` directories
  - [ ] Create `.gitignore` files
  - [ ] Initial commit with documentation

- [ ] **Task 0.3: ESP32 Development Environment** (1.5 hours)
  - [ ] Verify PlatformIO is working
  - [ ] Update `platformio.ini` with required libraries
  - [ ] Test compile and upload to device
  - [ ] Verify serial monitor works

- [ ] **Task 0.4: Frontend Development Environment** (1 hour)
  - [ ] Install Node.js 18+ (if not installed)
  - [ ] Create React project with Vite: `npm create vite@latest`
  - [ ] Install dependencies (axios, recharts, tailwindcss)
  - [ ] Test dev server

- [ ] **Task 0.5: AWS IoT Core Initial Setup** (1.5 hours)
  - [ ] Create IoT Thing: `motionplay-device-001`
  - [ ] Generate and download device certificates
  - [ ] Create IoT Policy (see technical design doc)
  - [ ] Attach policy to certificate
  - [ ] Attach certificate to Thing
  - [ ] Save IoT endpoint URL

- [ ] **Task 0.6: DynamoDB Tables Creation** (45 minutes)
  - [ ] Create `MotionPlaySessions` table
  - [ ] Create `MotionPlaySensorData` table
  - [ ] Create `MotionPlayDevices` table
  - [ ] Configure GSI on Sessions table
  - [ ] Document table ARNs

---

### 📋 Phase 1: Basic Connectivity
**Duration:** Weeks 2-3 (8-12 hours)  
**Goal:** Establish bidirectional communication between ESP32 and AWS IoT Core

*(Details in implementation plan)*

---

### 📋 Phase 2: Data Pipeline
**Duration:** Weeks 3-4 (10-14 hours)  
**Goal:** Implement complete data collection and storage flow

*(Details in implementation plan)*

---

### 📋 Phase 3: Web Interface
**Duration:** Weeks 5-6 (12-16 hours)  
**Goal:** Create functional web interface for device control and data viewing

*(Details in implementation plan)*

---

### 📋 Phase 4: Integration & Polish
**Duration:** Weeks 7-8 (8-12 hours)  
**Goal:** Complete integration, testing, and polish for Phase 1 release

*(Details in implementation plan)*

---

## 📖 Key Documents

- **Requirements:** `docs/data collection/tech_reqs.md`
- **Technical Design:** `docs/data collection/technical_design_doc.md`
- **Implementation Plan:** `docs/data collection/implementation_plan.md`

---

## 🎯 Next Steps

1. **Configure AWS CLI:**
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Enter region: us-west-2
   # Enter output format: json
   ```

2. **Set up billing alert:**
   - Go to AWS Console → Billing → Budgets
   - Create budget with $20/month threshold

3. **Verify ESP32 environment:**
   ```bash
   cd firmware
   pio run
   ```

4. **Create frontend project:**
   ```bash
   cd frontend
   npm create vite@latest motion-play-ui -- --template react-ts
   ```

---

## 💡 Tips

- Work through tasks sequentially within each phase
- Test each component before moving to the next
- Document any deviations from the plan
- Track time spent on each task for future estimation
- Commit to git after completing each task

---

## 🐛 Troubleshooting

**AWS CLI not working:**
- Ensure credentials are in `~/.aws/credentials`
- Check region is set in `~/.aws/config`

**PlatformIO issues:**
- Update PlatformIO: `pio upgrade`
- Clean build: `pio run --target clean`

**ESP32 upload issues:**
- Check USB cable and port
- Hold BOOT button while uploading
- Try different baud rate

---

## 📊 Progress Tracking

| Phase | Status | Hours Spent | Notes |
|-------|--------|-------------|-------|
| Phase 0 | In Progress | - | Started Nov 12, 2025 |
| Phase 1 | Not Started | - | - |
| Phase 2 | Not Started | - | - |
| Phase 3 | Not Started | - | - |
| Phase 4 | Not Started | - | - |

---

**Last Updated:** November 12, 2025

