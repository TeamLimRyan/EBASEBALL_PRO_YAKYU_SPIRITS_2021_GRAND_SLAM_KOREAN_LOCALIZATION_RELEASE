"""Read-only RDI/RDB primitives, rewritten for Spirits 2021.

Format/obfuscation reference: snake7594/Switch-Pawapuro2024-KR,
commit 6bede0f323f16da5a5bff67778407ae68d92e8d5, tools/rdblib.py.
Upstream permits use/modification/redistribution for noncommercial fan translation.
No upstream module is imported or executed. See README.md for provenance.
"""
from array import array
from functools import lru_cache
from pathlib import Path
import hashlib
import struct
import sys
import json
import os
import threading
import time
from datetime import datetime, timezone

VERSION = "1.1.0"
SECTOR = 512
MASK32 = 0xffffffff


def align(value, boundary):
    return (value + boundary - 1) // boundary * boundary


def name_seed(name):
    """Filename-derived obfuscation seed, unrelated to console key files."""
    chars = name.upper().replace("/", "\\").encode("ascii")
    shifts = (5, 6, 4, 5, 6, 5, 4, 5, 5, 6, 6, 5, 6, 4, 6, 4)
    base = len(chars) + sum(i * c for i, c in enumerate(reversed(chars), 1))
    result, shift = base, 0
    for i, c in enumerate(chars):
        result = (result + ((c - 48) << shift)) & MASK32
        shift = (shift + shifts[(base + i) & 15]) % 29
    return result


@lru_cache(maxsize=16384)
def initial_state(seed):
    state = [0] * 64
    for bit in range(32):
        for column in range(64):
            if column % 31 == 0:
                seed = ((seed * 5 + 0xb1aef645) & MASK32) >> 1
                bits = seed
            state[column] |= (bits & 1) << bit
            bits >>= 1
    return tuple(state)


class Cipher:
    def __init__(self, seed):
        self.state = list(initial_state(seed))
        self.position = 0

    def transform(self, data):
        if len(data) % 4:
            raise ValueError("cipher input must be word aligned")
        words = array("I")
        words.frombytes(data)
        if sys.byteorder != "little":
            words.byteswap()
        state, position = self.state, self.position
        for i in range(len(words)):
            j = position & 63
            state[j] ^= state[(j + 3) & 63]
            words[i] ^= state[(j + 1) & 63]
            position += 1
        self.position = position
        if sys.byteorder != "little":
            words.byteswap()
        return words.tobytes()


def crypt(data, seed):
    return Cipher(seed).transform(data)


def slot_seed(name):
    return name_seed("RES00.RDI") ^ name_seed(name)


