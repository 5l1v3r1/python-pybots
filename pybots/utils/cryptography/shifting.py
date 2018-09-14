#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Classes and functions related to shifting algorithms.

The following classes and functions allow to build shifting-based generators.

"""

__author__ = "Alexandre D'Hondt"
__version__ = "1.0"
__copyright__ = "AGPLv3 (http://www.gnu.org/licenses/agpl.html)"
__all__ = ["LFSR", "Geffe"]


import copy
import numpy as np
import struct
from binascii import hexlify, unhexlify
from tinyscript.helpers import *


class Geffe(object):
    taps = [
        (3, 4, 6, 7, 8, 9, 11, 32),
        (1, 2, 3, 4, 6, 8, 9, 13, 14, 32),
        (1, 2, 3, 7, 12, 14, 15, 32),
    ]
    
    def __init__(self, key=None, seeds=(0, 0, 0)):
        seeds = Geffe.format_param(key, seeds)
        self._lfsrs = [LFSR(s, t, 32) for s, t in zip(seeds, Geffe.taps)]
    
    def get(self, length=None, output_format="str"):
        assert output_format in ["str", "hex", "bin"], "Bad output format"
        stream = []
        for bits in zip(self._lfsrs[0].get(length, "bin"),
                        self._lfsrs[1].get(length, "bin"),
                        self._lfsrs[2].get(length, "bin")):
            stream.append(Geffe.F(*bits))
        if output_format == "str":
            return bin2txt(stream)
        elif output_format == "hex":
            return hexlify(bin2txt(stream))
        else:
            return stream
    
    @staticmethod
    def F(x1, x2, x3):
        return (x1 & x2) ^ (int(not x1) & x3)
    
    @staticmethod
    def format_param(key, seeds):
        if key is not None:
            l, err = len(key), "Bad key format ({})"
            if is_str(key):
                if l == 12:
                    seeds = struct.unpack("iii", key)
                elif l == 96 and is_bin(key):
                    seeds = tuple([bin2int(key[i:i+32]) for i in \
                                   range(0, 96, 32)])
            elif is_lst(key):
                if l == 3 and all(is_str(s) for s in key):
                    seeds = tuple(map(lambda s: struct.unpack("i", s), key))
                elif l == 96 and is_bin(key):
                    bits = ''.join(list(map(str, key)))
                    seeds = map(lambda x: int("0b" + x, 2), \
                                [bits[i:i+32] for i in range(0, 96, 32)])
        assert len(seeds) == 3 and all(is_int(i) and i.bit_length() <= 32 \
                                       for i in seeds), "Invalid seeds"
        return seeds


class LFSR(object):
    """
    Linear Feedback Shift Register (LFSR) class.
    
    This can be defined by its parameters (seed, taps, nbits) or can be
     determined from a target using the Berlekamp-Massey algorithm.

    :param seed:   integer, list of bits or string for initializing the LFSR
    :param taps:   tuple or list of indices of the polynomial
    :param nbits:  LFSR register length of bits
    :param target: input string or list of bits to be matched while determining
                    LFSR's parameters
    """
    def __init__(self, seed=0, taps=None, nbits=None, target=None):
        assert all(x is not None for x in [seed, taps, nbits]) or target, \
               "Either (seed, taps, nbits) or target must be set"
        self.target = target
        if target is not None and (taps is None or nbits is None):
            self.target = LFSR.format_target(target)
            self.__berlekamp_massey_algorithm()
        else:
            self.seed, self.taps, self.n = LFSR.format_param(seed, taps, nbits)
        # test if parameters are correct if a target was provided
        if self.target is not None:
            self.test()
        
    def __berlekamp_massey_algorithm(self):
        # inspired from:
        #  https://gist.github.com/StuartGordonReid/a514ed478d42eca49568
        bitstream = list(map(int, [b for b in self.target]))
        n = len(bitstream)
        b, c = np.zeros(n), np.zeros(n)
        b[0], c[0] = 1, 1
        l, m, i = 0, -1, 0
        while i < n:
            v = bitstream[(i - l):i]
            v = v[::-1]
            cc = c[1:l + 1]
            d = (bitstream[i] + np.dot(v, cc)) % 2
            if d == 1:
                _ = copy.copy(c)
                p = np.zeros(n)
                for j in range(0, l):
                    if b[j] == 1:
                        p[j + i - m] = 1
                c = (c + p) % 2
                if l <= 0.5 * i:
                    l = i + 1 - l
                    m = i
                    b = _
            i += 1
        c = [i for i, x in enumerate(c.tolist()) if x == 1.0]
        c.remove(0)
        self.seed, self.taps, self.n = LFSR.format_param(self.target[:l], c, l)
    
    def get(self, length=None, output_format="str"):
        assert output_format in ["str", "hex", "bin"], "Bad output format"
        length = length or (1 if self.target is None else len(self.target))
        stream = [b for b in self.seed]
        assert len(stream) == self.n
        for _ in xrange(length):
            bit = 0
            for tap in self.taps:
                bit ^= stream[-tap]
            stream.append(bit)
        stream = stream[:length]
        if output_format == "str":
            return bin2txt(stream)
        elif output_format == "hex":
            return hexlify(bin2txt(stream))
        else:
            return stream
    
    def test(self, target=None):
        target = target or self.target
        assert self.target is not None, "Target not defined"
        target = LFSR.format_target(target)
        assert target == self.get(len(target), output_format="bin"), \
               "Target and generated bits do not match"
    
    @staticmethod
    def format_param(seed, taps, nbits):
        """ Ensure that:
            - seed is formatted as a list of bits
            - taps is a list of integers <= nbits
            - nbits is an integer """
        if isinstance(seed, int):
            seed = int2bin(seed, nbits)
        elif is_str(seed) and not is_bin(seed):
            if is_hex(seed):
                seed = unhexlify(seed)
            seed = txt2bin(seed)
        seed = [int(b) for b in seed]
        assert is_bin(seed), "Bad input format for seed"
        assert is_int(nbits), "Bad input format for number of bits"
        assert is_lst(taps) and all(is_int(i) and i <= nbits for i in taps), \
               "Bad input format for taps"
        return seed, taps, nbits
    
    @staticmethod
    def format_target(target):
        """ Ensure that target is formatted as a list of bits """
        if is_str(target) and not is_bin(target):
            if is_hex(target):
                target = unhexlify(target)
            target = [int(b) for b in txt2bin(target)]
        assert is_bin(target), "Bad input format for target"
        return target