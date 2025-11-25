# Session Data Compression Initiative

**Status:** 📋 Proposed (Not Yet Started)  
**Priority:** Medium  
**Created:** November 22, 2025

## Quick Summary

After achieving ~222 Hz sample rate (35x improvement from 25 Hz), we're now collecting 15,000+ readings per session. Transmission time has become a bottleneck. This initiative explores compression strategies to reduce transmission time by 80-95%.

## The Challenge

- **Current:** 15,134 readings = ~1.36 MB JSON
- **Problem:** Long transmission delays
- **Goal:** Reduce to <150 KB, ideally single MQTT message

## Proposed Solution

**Phase 1:** Binary encoding + delta compression (90-95% reduction)  
**Phase 2:** Additional lightweight compression if needed (optional)

## Key Documents

- **[PROPOSAL.md](./PROPOSAL.md)** - Full technical proposal with 3 options analyzed
  - Option 1: Binary + Delta (Recommended)
  - Option 2: MessagePack  
  - Option 3: gzip on JSON

## Current Status

- [x] Problem identified
- [x] Options researched and documented
- [ ] Measurements collected (transmission time, memory usage)
- [ ] Approach selected
- [ ] Implementation started

## Questions to Answer First

1. How long does current transmission actually take?
2. What's the real AWS IoT MQTT message size limit?
3. Is WiFi or data size the actual bottleneck?
4. How much PSRAM/heap available during transmission?

## Context

This became relevant after solving the sample rate bottleneck:
- **Before:** 25 Hz (PS_Duty misconfiguration + library delays)
- **After:** 222 Hz (Fixed PS_Duty, removed 10ms delays)
- **Next:** Optimize transmission pipeline

## Timeline

- **November 22, 2025:** Problem identified, proposal created
- **TBD:** Measurements and approach selection
- **TBD:** Implementation

---

**Related:**
- [Object Detection Initiative](../object-detection/) - Needs high sample rate data
- [Data Collection System](../data-collection/) - Overall pipeline documentation

