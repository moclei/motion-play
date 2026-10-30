# cardraw.py <text> — append a raw-observation bullet before "### Measured values" in the V7R-016 card
import sys
p='lab/cards/V7R-016-u3-sda-low-replicated-setups.md'; s=open(p).read(); a="### Measured values (from log"
s=s.replace(a, sys.argv[1].rstrip()+"\n\n"+a, 1); s=s.replace("\n\n\n"+a, "\n\n"+a); open(p,'w').write(s)
