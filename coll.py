import os
import zipfile
import urllib.request
import io
import sys
from md5 import MD5
import itertools
import binascii

FASTCOLL_LOC = 'https://www.win.tue.nl/hashclash/fastcoll_v1.0.0.5-1_source.zip'
FASTCOLL_PLACE = 'fastcoll'

# grab fastcoll, we need boost library dev (header file) packages installed to compile it
# sudo apt-get install libboost-all-dev
if not os.path.exists(FASTCOLL_PLACE):
    print('Grabbing fastcoll')
    resp = urllib.request.urlopen(FASTCOLL_LOC)
    data = resp.read()
    mf = io.BytesIO(data)
    with zipfile.ZipFile(mf) as zf:
        os.mkdir(FASTCOLL_PLACE)
        zf.extractall(FASTCOLL_PLACE)
    
    print('Compiling fastcoll')
    back = os.getcwd()
    os.chdir(FASTCOLL_PLACE)
    with open('Makefile', 'w') as mkf:
        mkf.write("""fastcoll:\n\tg++ -O3 *.cpp -lboost_filesystem -lboost_program_options -lboost_system -o fastcoll\n""")
    r = os.system('make')
    os.chdir(back)
    if r == 0:
        print('done preparing fastcoll')
    else:
        raise Exception('could not compile fastcoll')

### utilities for payload construction
    
def md5pad(b, ch=b'\0'):
    return md5lpad(len(b), ch)

def md5lpad(l, ch=b'\0'):
    c = l % 64
    if c == 0:
        c = 64
    padl = 64 - c
    return ch*padl

### block filter utilities

def filter_disallow_binstrings(strs):
    def out_filter(b):
        badsubst = strs
        return all((e not in b) for e in badsubst)
    return out_filter
    
### generating a collision
    
def collide(ihv):
    '''Returns a tuple pair of binary block alternatives that still result in same MD5 from the IHV.'''
    # a.k.a it generates a chosen prefix collision
    # This is very hackish, but what else can be done when the fastcoll license is so restrictive?
    back = os.getcwd()
    os.chdir(FASTCOLL_PLACE)
    
    ivhex = binascii.hexlify(ihv).decode()
    
    f0, f1 = 'out-{}-0'.format(ivhex), 'out-{}-1'.format(ivhex)
    
    # developer toggle of whether to display output
    plus = '  > /dev/null 2>&1'
    os.system('./fastcoll --ihv {} -o {} {}{}'.format(ivhex, f0, f1, plus))
    
    with open(f0, 'rb') as f0d:
        b0 = f0d.read()
    
    with open(f1, 'rb') as f1d:
        b1 = f1d.read()
    
    try:
        os.remove(f0)
        os.remove(f1)
    except:
        pass
    
    os.chdir(back)
    return b0, b1

### very helpful stateful Collider class

class Collider:
    '''Helper class to generate files with multiple chosen prefix collisions efficiently'''
    
    def __init__(self, data=b'', pad=b'\0', blockfilter=lambda x: True):
        '''Generate a new collider with starting data, default padding, and default collison block filters'''
        self.alldata = [b'']
        self.div = []
        self.dlen = 0
        
        self.pad = pad
        self.blockfilter = blockfilter
        self.digester = MD5()
        
        if type(data)==str:
            self.strcat(data)
        else:
            self.bincat(data)
    
    def bincat(self, data):
        '''Add binary data to the working binary state'''
        self.dlen += len(data)
        self.digester.update(data)
        self.alldata[-1] += data
        
    def strcat(self, s):
        '''Add string data to the working binary state'''
        self.bincat(s.encode())
    
    def padnow(self, pad=None):
        '''Pad the current working data on the end to a multiple of md5 block size (64 bytes)'''
        if not pad:
            pad = self.pad
        ndata = md5lpad(self.dlen, pad)
        self.bincat(ndata)
        
    def diverge(self, pad=None, blockfilter=None):
        '''Place a choice of 2 different sets of 128 bytes that still keep the running md5
        hash (via chosen prefix). Beforehand, the current data will be padded if necessary'''
        if not pad:
            pad = self.pad
        if not blockfilter:
            blockfilter = self.blockfilter
        
        self.padnow(pad)
        
        self.alldata.append(b'')
        
        # run until the blockfilter passes
        while True:
            b0, b1 = collide(self.digester.ihv())
            if blockfilter(b0) and blockfilter(b1):
                break
        
        self.dlen += len(b0)
        self.digester.update(b0)
        self.div.append((b0, b1))
        
    def assert_aligned(self):
        '''Perform an assertion that the total consumed data is aligned to the md5 block size (64 bytes)'''
        assert(self.dlen % 64 == 0)
        
    def safe_diverge(self, pad=None, blockfilter=None):
        '''Only diverge if we don't need to pad. Otherwise we fair with an assertion error.'''
        self.assert_aligned()
        self.diverge(pad, blockfilter)
        
    def get_collisions(self, count=None, lsb_last=True):
        '''Generator that returns colliding data in succession'''
        if not count:
            count = 2 ** len(self.div)
        
        for i,bincode in enumerate(itertools.product(range(2), repeat=len(self.div))):
            if i >= count:
                break
            if not lsb_last:
                bincode = tuple(reversed(bincode))
            
            blocks = map(lambda i: self.div[i][bincode[i]], range(len(bincode)))
            zip_data = itertools.zip_longest(self.alldata, blocks, fillvalue=b'')
            out = b''.join(b''.join(e) for e in zip_data)
            yield out
            
    def get_last_coll(self):
        '''Get both blocks from the last found collision'''
        return self.div[-1]