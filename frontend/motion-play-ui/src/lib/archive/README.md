# Direction Detection Algorithm Archive

This folder contains archived versions of the direction detection algorithm.

## Version History

### v1: Rise Timing Based (`directionDetector_v1_rise_timing.ts`)
- **Archived**: 2024-12-06
- **Approach**: Used derivative-based rise detection to find when each side's signal started rising. The side that started rising first determined direction.
- **Issues**:
  - Rise start detection was sensitive to noise at the beginning of signals
  - Rise times were often very close together, making direction unclear
  - Didn't match how humans visually perceive "which wave came first"

### v2: Wave Envelope / Center of Mass (current)
- **Location**: `../directionDetector.ts`
- **Approach**: 
  1. Find the complete "wave envelope" for each side (where signal crosses 20% of peak height)
  2. Calculate center of mass (weighted average timestamp) within the wave
  3. Compare centers of mass - earlier one determines direction
- **Benefits**:
  - More robust - captures the "whole wave" timing
  - Less sensitive to noise at signal edges
  - Matches human visual perception of wave ordering

## Porting to Firmware

When updating the detection algorithm, remember to also update:
- `firmware/src/components/detection/DirectionDetector.cpp`
- `firmware/src/components/detection/DirectionDetector.h`

The TypeScript implementation serves as the reference that can be easily tested
in the browser before porting changes to C++.

