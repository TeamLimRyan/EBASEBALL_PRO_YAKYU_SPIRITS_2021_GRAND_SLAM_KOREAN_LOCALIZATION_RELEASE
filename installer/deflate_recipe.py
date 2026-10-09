"""Preserve a zlib stream's exact coding decisions without shipping literals.

The recipe contains Huffman tables, matches and literal locations. Literal
values come exclusively from the separately restored, source-bound raw data.
No compression search is performed by restore(). Python standard library only.
"""
import array
import json
import struct
import sys
import zlib
import ctypes
from pathlib import Path

_native=None
def native_path():
    compact=Path(__file__).with_name('native_bits_v4.dll')
    if compact.exists():return compact
    latest=Path(__file__).with_name('native_bits_v3.dll')
    if latest.exists():return latest
    newer=Path(__file__).with_name('native_bits_v2.dll')
    return newer if newer.exists() else Path(__file__).with_name('native_bits.dll')
def patch_trace(buf,raw,trace,lengths,clear=False,delta=False):
    global _native
    table=codes(lengths)
    dll=native_path()
    if dll.exists():
        if _native is None:
            _native=ctypes.CDLL(str(dll)).patch_literals
            _native.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_int]
            _native.restype=ctypes.c_int
        raw=bytes(raw);trace=bytes(trace);ct=(ctypes.c_uint16*512)(*[v for pair in table[:256] for v in pair]);out=(ctypes.c_ubyte*len(buf)).from_buffer(buf)
        if _native(out,len(buf),ctypes.c_char_p(raw),len(raw),ctypes.c_char_p(trace),len(trace)//8,ct,int(clear)|(2 if delta else 0)):raise ValueError('Invalid literal trace')
    else:
        previous_p=previous_r=0
        for p,r in struct.iter_unpack('<II',trace):
            if delta:p+=previous_p;r+=previous_r;previous_p,previous_r=p,r
            v,n=table[raw[r]];assert n;write_bits(buf,p,n,0 if clear else v)

LBASE=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
LEXTRA=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0]
DEXTRA=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]

class Bits:
    def __init__(self,data): self.data=data+b'\0'*8; self.pos=16
    def peek(self,n):
        p=self.pos//8
        return (int.from_bytes(self.data[p:p+4],'little')>>(self.pos%8))&((1<<n)-1)
    def read(self,n): v=self.peek(n);self.pos+=n;return v

def codes(lengths):
    counts=[0]*16
    for n in lengths:
        if n: counts[n]+=1
    nxt=[0]*16;v=0
    for n in range(1,16): v=(v+counts[n-1])<<1;nxt[n]=v
    out=[]
    for n in lengths:
        if n:
            v=nxt[n];nxt[n]+=1
            out.append((int(format(v,f'0{n}b')[::-1],2),n))
        else: out.append((0,0))
    return out

def decoder(lengths):
    table=[None]*32768
    for symbol,(v,n) in enumerate(codes(lengths)):
        if n:
            for j in range(v,32768,1<<n): table[j]=(symbol,n)
    return table

def symbol(reader,table):
    pair=table[reader.peek(15)]
    if pair is None: raise ValueError('Invalid Huffman code')
    v,n=pair;reader.pos+=n;return v

def write_bits(buf,pos,n,value):
    at=pos//8;shift=pos%8;size=(shift+n+7)//8
    old=int.from_bytes(buf[at:at+size],'little')
    mask=((1<<n)-1)<<shift
    buf[at:at+size]=((old&~mask)|(value<<shift)).to_bytes(size,'little')

def serialize(skeleton,blocks):
    meta=[];traces=bytearray()
    for row in blocks:
        if 'trace' in row:
            t=row.pop('trace');row['trace_offset']=len(traces);row['trace_size']=len(t);traces.extend(t)
        meta.append(row)
    m=json.dumps(meta,separators=(',',':')).encode()
    return b'DFR1'+struct.pack('<III',len(skeleton),len(m),len(traces))+skeleton+m+traces

def native_create(packed,raw):
    dll=ctypes.CDLL(str(native_path()))
    if not hasattr(dll,'deflate_trace'):return None
    blocks=[];failures=[];skeleton=bytearray(len(packed));out=(ctypes.c_ubyte*len(packed)).from_buffer(skeleton)
    callback_type=ctypes.CFUNCTYPE(None,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t)
    @callback_type
    def callback(kind,p,r,n,lengths,nl,trace,count):
        try:
            if kind==0:blocks.append(dict(stored=[p,r,n]))
            else:blocks.append(dict(lengths=list(ctypes.string_at(lengths,nl)),trace=ctypes.string_at(trace,count*8)))
        except Exception as exc:failures.append(exc)
    fn=dll.deflate_trace;fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,callback_type];fn.restype=ctypes.c_int
    status=fn(ctypes.c_char_p(packed),len(packed),ctypes.c_char_p(raw),len(raw),out,callback)
    if status or failures:raise ValueError(f'Native DEFLATE parser failed: {status}')
    return serialize(skeleton,blocks)

def create(packed,native=True):
    assert len(packed)>6 and (packed[0]*256+packed[1])%31==0 and not packed[1]&32
    raw=zlib.decompress(packed)
    if native and native_path().exists():
        recipe=native_create(packed,raw)
        if recipe is not None:
            assert restore(recipe,raw)==packed
            return raw,recipe
    b=Bits(packed);skeleton=bytearray(packed)
    blocks=[];outpos=0
    while True:
        final=b.read(1);kind=b.read(2)
        if kind==0:
            b.pos=(b.pos+7)//8*8;n=b.read(16);assert b.read(16)==n^65535
            at=b.pos//8;assert packed[at:at+n]==raw[outpos:outpos+n]
            blocks.append(dict(stored=[at,outpos,n]));skeleton[at:at+n]=bytes(n)
            outpos+=n;b.pos+=n*8
        else:
            if kind==1: lit=[8]*144+[9]*112+[7]*24+[8]*8;dist=[5]*32
            elif kind==2:
                nl=b.read(5)+257;nd=b.read(5)+1;nc=b.read(4)+4
                order=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
                cl=[0]*19
                for j in range(nc):cl[order[j]]=b.read(3)
                table=decoder(cl);all_lengths=[]
                while len(all_lengths)<nl+nd:
                    c=symbol(b,table)
                    if c<16:all_lengths.append(c)
                    elif c==16:all_lengths.extend([all_lengths[-1]]*(b.read(2)+3))
                    elif c==17:all_lengths.extend([0]*(b.read(3)+3))
                    else:all_lengths.extend([0]*(b.read(7)+11))
                assert len(all_lengths)==nl+nd
                lit=all_lengths[:nl];dist=all_lengths[nl:]
            else:raise ValueError('Reserved DEFLATE block')
            lt=decoder(lit);dt=decoder(dist);trace=array.array('I')
            while True:
                start=b.pos;c=symbol(b,lt)
                if c<256:
                    assert raw[outpos]==c
                    trace.extend([start,outpos]);outpos+=1
                elif c==256:break
                else:
                    assert 257<=c<=285
                    outpos+=LBASE[c-257]+b.read(LEXTRA[c-257])
                    d=symbol(b,dt);assert d<30;b.read(DEXTRA[d])
            if sys.byteorder!='little':trace.byteswap()
            patch_trace(skeleton,raw,trace.tobytes(),lit,True)
            blocks.append(dict(lengths=lit,trace=trace.tobytes()))
        if final:break
    assert outpos==len(raw)
    recipe=serialize(skeleton,blocks)
    assert restore(recipe,raw)==packed
    return raw,recipe

def restore(recipe,raw):
    assert recipe[:4] in [b'DFR1',b'DFR2']
    ns,nm,nt=struct.unpack_from('<III',recipe,4);assert len(recipe)==16+ns+nm+nt
    buf=bytearray(recipe[16:16+ns]);meta=json.loads(recipe[16+ns:16+ns+nm]);traces=memoryview(recipe)[16+ns+nm:]
    for row in meta:
        if 'stored' in row:
            p,r,n=row['stored'];buf[p:p+n]=raw[r:r+n]
        else:
            at=row['trace_offset'];end=at+row['trace_size']
            patch_trace(buf,raw,traces[at:end],row['lengths'],delta=recipe[:4]==b'DFR2')
    assert zlib.adler32(raw)&0xffffffff==int.from_bytes(buf[-4:],'big')
    return bytes(buf)

if __name__=='__main__':
    import os
    for data in [b'',bytes(range(256))*33,b'hello Korean localization '*5000,os.urandom(131072)]:
        for level in [0,1,6,9]:
            packed=zlib.compress(data,level);raw,recipe=create(packed)
            assert raw==data and restore(recipe,raw)==packed
            assert create(packed,native=False)==(raw,recipe)
    print('DEFLATE exact reconstruction: 16/16 PASS')
