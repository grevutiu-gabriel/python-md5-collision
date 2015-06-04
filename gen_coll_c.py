#!/usr/bin/env python3

from coll import Collider, md5pad, filter_disallow_binstrings
import os, sys

# First compile the C code into a binary
temp = 'out_c_demo_temp'

os.system('gcc c_demo.c -o {}'.format(temp))

with open(temp, 'rb') as tempfile:
    compdata = bytearray(tempfile.read())
    
    
first = None
second = None

# Find strings in binary:
# We find where in the first one we can put a collision pair (aligned to 64 bytes).
# The second string gets a copy of the first from the pair,
# and it is put at the same offset into the first string.
for i in range(0, len(compdata), 64):
    s = compdata[i:i+128]
    if s != b'%' * 128:
        continue
        
    for q in range(i,i+(64*3+2)):
        if compdata[q] == ord('+') or compdata[q] == ord('-'):
            startchars = q-(64*3)
            if not first:
                first = i
                offset = i - startchars
            else:
                second = startchars + offset
                
            compdata[q] = 0
            break
        

if not (first and second):
    raise Exception('error: did not find marker strings')

# Splice in the collision blocks according to the obtained offsets
collider = Collider(blockfilter=filter_disallow_binstrings([b'\0']))
collider.bincat(compdata[:first])
collider.safe_diverge()
c1, c2 = collider.get_last_coll()
collider.bincat(compdata[first+128:second] + c1 + compdata[second+128:])

# Write out good and evil binaries
cols = collider.get_collisions()

GOOD = 'out_c_good'
EVIL = 'out_c_evil'

with open(GOOD,  'wb') as good:
    good.write(next(cols))
    
with open(EVIL, 'wb') as evil:
    evil.write(next(cols))

os.system('chmod +x {} {}'.format(GOOD, EVIL))
os.remove(temp)
