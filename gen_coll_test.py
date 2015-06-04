#!/usr/bin/env python3

from coll import Collider, md5pad, filter_disallow_binstrings

# Generate a 213-way collision as a test
c = Collider(pad=b' ', blockfilter=filter_disallow_binstrings([b'\0']))
# begin the output files with hello world text
c.strcat('Hello world.')

# Diverge 8 times. That means 2^8 possibilities
for i in range(8):
    print('Stage {} of 8'.format(i+1))
    # we fork into 2 different possibilities of collision blocks (128 byte garbage each) here
    c.diverge()
    # place some text in the middle of each divergence
    c.strcat('More text: {}\n'.format(i))

c.strcat('\nFinal.')

# Select the first 213 collisions to output to file
for i,data in enumerate(c.get_collisions(count=213)):
    with open('out_test_%03d.txt' % i, 'wb') as f:
        f.write(data)
        
print('Done')