# arm.sh <ARM> "<marker text>" — marker into the v7 log, wait for >= 3 [scope] t-lines after it, V8 + 2 captures, frames, controls (V7R-016 session helper)
cd /Users/marcocleirigh/Workspace/motion-play; SP=$(dirname "$0"); A=$1; LOG=lab/captures/V7R-016/2026-10-27_V7R-016_v7_01.txt
echo "=== $A ($2) $(date +%H:%M:%S)" >> $LOG
after() { awk -v a="=== $A " 'index($0,a)==1{n=NR} {L[NR]=$0} END{for(i=n+1;i<=NR;i++) print L[i]}' $LOG; }
for i in $(seq 1 45); do [ "$(after | grep -c '\[scope\] t=')" -ge 3 ] && break; sleep 2; done
echo "boot check ($(date +%H:%M:%S)): $(after | grep -m1 -E '\[scope\] (t=|sketch=)' | cut -c1-70)"
L=lab/log/2026-10-27_s03.yaml bash $SP/runarm_frames.sh V7R-016 $A 2>&1 | grep -E "wrote|rror|NOTE"
python3 $SP/arm_frames_V7R-016.py $A | tee $SP/${A}_summary.txt
python3 $SP/controls.py $A | tee $SP/${A}_controls.txt
