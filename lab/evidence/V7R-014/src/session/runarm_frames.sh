# runarm_frames.sh <TEST> <ARM> — session helper from V7R-012/-013 (run from the repo root): V8 at 20 us/div, then 3 SINGLE captures at 10 us/div, address trigger 0x6B write. Set L (log path) for the session.
SCOPE=192.168.50.2; q(){ (printf '%s\n' "$1"; sleep "${2:-1}") | nc -G 3 "$SCOPE" 5555; }
T=$1; A=$2; L=${L:?set L=lab/log/<date>_sNN.yaml}
q ':TRIGger:MODE IIC'; q ':TRIGger:IIC:SCL CHANnel2'; q ':TRIGger:IIC:SDA CHANnel1'; q ':TRIGger:IIC:WHEN ADDR'; q ':TRIGger:IIC:AWIDth 7'; q ':TRIGger:IIC:ADDRess 107'; q ':TRIGger:IIC:DIRection WRITe'
echo "trig $(q ':TRIGger:MODE?') $(q ':TRIGger:IIC:ADDRess?') $(q ':TRIGger:IIC:DIRection?') $(q ':SYSTem:ERRor?')"
q ':TIMebase:MAIN:SCALe 2e-5'; q ':TRIGger:SWEep SING'; sleep 2; echo "V8 status $(q ':TRIGger:STATus?')"
python3 tools/lab/capture.py --test $T --arm val_V8_$A --items VPP --session $L 2>&1 | grep -E "png|NOTE|rror"
q ':TIMebase:MAIN:SCALe 1e-5'; echo "tb $(q ':TIMebase:MAIN:SCALe?')"
for i in 1 2 3; do q ':TRIGger:SWEep SING'; sleep 2; echo "status $(q ':TRIGger:STATus?')"; python3 tools/lab/capture.py --test $T --arm $A --items VPP --session $L 2>&1 | grep -E "csv|NOTE|rror"; done
