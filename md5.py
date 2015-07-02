#!/usr/bin/env python3

"""An implementation of MD5 that exposes internals and is directly built up
from mathematical primitives from the MD5 specification.

It achieves about 500KB/s, or 1/1000x of GNU md5sum.
Thus, this is not an implementation great for larges amounts of hashing.
Instead, the point is access to internals."""

__date__ = '2015-07-02'
__version__ = 0.8

import math
import binascii

# util
bin_to_words = lambda x: [x[4*i:4*(i+1)] for i in range(len(x)//4)]
words_to_bin = lambda x: b''.join(x)
word_to_int = lambda x: int.from_bytes(x, 'little')
int_to_word = lambda x: x.to_bytes(4, 'little')
bin_to_int = lambda x: list(map(word_to_int, bin_to_words(x)))
int_to_bin = lambda x: words_to_bin(map(int_to_word, x))
mod32bit = lambda x: x % 2**32
rotleft = lambda x,n: (x << n) | (x >> (32-n))

# initial state
IHV0_HEX = '0123456789abcdeffedcba9876543210'
IHV0 = bin_to_int(binascii.unhexlify(IHV0_HEX.encode()))

# parameters
BLOCK_SIZE = 64 # 512 bits (64 bytes)
ROUNDS = BLOCK_SIZE

# addition constants
AC = [int(2**32 * abs(math.sin(t+1))) for t in range(ROUNDS)]

# rotation constants
RC = [7,12,17,22] * 4 + [5,9,14,20] * 4 + [4,11,16,23] * 4 + [6,10,15,21] * 4

# non-linear functions
F = lambda x,y,z: (x & y) ^ (~x & z)
G = lambda x,y,z: (z & x) ^ (~z & y)
H = lambda x,y,z: x ^ y ^ z
I = lambda x,y,z: y ^ (x | ~z)
Fx = [F] * 16 + [G] * 16 + [H] * 16 + [I] * 16

# data selection
M1 = lambda t: t
M2 = lambda t: (1 + 5*t) % 16
M3 = lambda t: (5 + 3*t) % 16
M4 = lambda t: (7*t) % 16
Mx = [M1] * 16 + [M2] * 16 + [M3] * 16 + [M4] * 16
Wx = [mxi(i) for i,mxi in enumerate(Mx)]

# iterations and function composition
RoundQNext = lambda w,q,i: mod32bit(q[0] + rotleft(mod32bit(Fx[i](q[0],q[1],q[2]) + q[3] + AC[i] + w[Wx[i]]), RC[i]))
DoRounds = lambda w,q,i: DoRounds(w, [RoundQNext(w,q,i)] + q[:3], i+1) if (i < ROUNDS) else q
MD5CompressionInt = lambda ihvs, b: [mod32bit(ihvsi + qi) for ihvsi,qi in zip(ihvs, DoRounds(bin_to_int(b),ihvs,0))]
arrSh = lambda x: [x[1],x[2],x[3],x[0]]
arrUs = lambda x: [x[3],x[0],x[1],x[2]]
MD5Compression = lambda ihv, b: arrUs(MD5CompressionInt(arrSh(ihv),b))


class MD5:
    """Implementation of MD5
    
    Expected outputs:
    >>> MD5(b'').hexdigest()
    'd41d8cd98f00b204e9800998ecf8427e'
    >>> MD5(b'a').hexdigest()
    '0cc175b9c0f1b6a831c399e269772661'
    >>> MD5(b'abc').hexdigest()
    '900150983cd24fb0d6963f7d28e17f72'
    >>> MD5(b'message digest').hexdigest()
    'f96b697d7cb7938d525a2f31aaf161d0'
    >>> MD5(b'abcdefghijklmnopqrstuvwxyz').hexdigest()
    'c3fcd3d76192e4007dfb496cca67e13b'
    >>> MD5(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789').hexdigest()
    'd174ab98d277d9f5a5611c2c9f419d9f'
    >>> MD5(b'12345678901234567890123456789012345678901234567890123456789012345678901234567890').hexdigest()
    '57edf4a22be3c955ac49da2e2107b67a'
    """
    
    def __init__(self, data=None):
        self._ihv = IHV0
        self.bits = 0
        self.buf = b''
        if data:
            self.update(data)
    
    def update(self, data):
        self.bits += len(data) * 8
        self.buf += data
        while len(self.buf) >= BLOCK_SIZE:
           to_compress, self.buf = self.buf[:BLOCK_SIZE], self.buf[BLOCK_SIZE:]
           self._ihv = MD5Compression(self._ihv, to_compress)
    
    def digest(self):
        # total reseved bytes
        total_bytes = (self.bits // 8)
        
        # we deduct 1 extra byte for the 1 bit from the zero pading length
        zerolen = (56 - (total_bytes + 1)) % 64
        
        pad = bytes([0x80] + [0] * zerolen) + (total_bytes * 8).to_bytes(8, 'little')

        temp = MD5()
        temp._ihv = self._ihv 
        temp.update(self.buf + pad)
        digest_value = temp._ihv
        
        return int_to_bin(digest_value)
        
        
    def hexdigest(self):
        return binascii.hexlify(self.digest()).decode()
    
    def ihv(self):
        return int_to_bin(self._ihv)
    
    def hexihv(self):
        """Get the current IHV in hex
        
        >>> MD5().hexihv() == IHV0_HEX
        True
        >>> MD5(b'test').hexihv() == IHV0_HEX
        True
        >>> MD5(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?').hexihv()
        '9d39fa2529070110ab7f132e7a9cacf3'
        """
        return binascii.hexlify(self.ihv()).decode()

def md5(data=None):
    return MD5(data)


if __name__ == '__main__':
    # Testing
    
    # check the the standard MD5 suite expected outputs in the class docstring
    print('Doctests')
    import doctest
    doctest.testmod(verbose=True)
    print()
    
    print('Unittests')
    import unittest
    import hashlib
    
    class _TestMD5(unittest.TestCase):
        
        def test_against_reference_implementation(self):
            AMOUNT = 1024
            import random, string
            rand = random.Random()
            rand.seed(4)
            
            randstring = lambda n: ''.join(rand.choice(string.ascii_uppercase + string.digits) for _ in range(n)).encode()
            randbin = lambda n: bytes((random.getrandbits(8) for i in range(n)))
            
            for i in range(AMOUNT):
                rlen = rand.randrange(4, 15)
                randtype = rand.choice([randstring, randbin])
                to_hash = randtype(rlen)
                expected = hashlib.md5(to_hash).hexdigest()
                got = md5(to_hash).hexdigest()
                self.assertEqual(expected, got, 'hashes for {} do not match'.format(to_hash))
        
        def test_boundary_padding(self):
            for i in range(196):
                to_hash = b'a' * i
                expected = hashlib.md5(to_hash).hexdigest()
                got = md5(to_hash).hexdigest()
                self.assertEqual(expected, got, 'hashes for {} do not match'.format(to_hash.decode()))
                
        def test_hashing_resume(self):
            basestr = b'asdfjkl;' * 32
            expected = md5(basestr).hexdigest()
            for i in range(len(basestr)):
                a,b = basestr[:i], basestr[i:]
                hashobj = md5(a)
                discard = hashobj.digest()
                hashobj.update(b)
                got = hashobj.hexdigest()
                self.assertEqual(expected, got, 'hashes split on index {} do not match'.format(basestr, i))
        
    unittest.main(verbosity=2)
