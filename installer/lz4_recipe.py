"""Exact LZ4 block reconstruction with source-bound restored literal data."""
import struct

def unpack(packed,record=False):
    out=bytearray();skeleton=bytearray(packed) if record else None;trace=[];at=0
    def extra(n):
        nonlocal at
        if n==15:
            while True:
                x=packed[at];at+=1;n+=x
                if x!=255:break
        return n
    while at<len(packed):
        token=packed[at];at+=1;n=extra(token>>4)
        if record:trace.append((at,len(out),n));skeleton[at:at+n]=bytes(n)
        out.extend(packed[at:at+n]);at+=n
        if at==len(packed):break
        distance=int.from_bytes(packed[at:at+2],'little');at+=2;assert 0<distance<=len(out)
        n=extra(token&15)+4;pattern=out[-distance:];out.extend((pattern*((n+distance-1)//distance))[:n])
    if record:
        recipe=b'LZR1'+struct.pack('<II',len(skeleton),len(trace))+skeleton+b''.join(struct.pack('<III',*v) for v in trace)
        assert restore(recipe,out)==packed
        return bytes(out),recipe
    return bytes(out)

def restore(recipe,raw):
    assert recipe[:4]==b'LZR1';n,count=struct.unpack_from('<II',recipe,4);assert len(recipe)==12+n+count*12
    result=bytearray(recipe[12:12+n])
    for p,r,size in struct.iter_unpack('<III',recipe[12+n:]):result[p:p+size]=raw[r:r+size]
    return bytes(result)

def segments(nso):
    assert nso[:4]==b'NSO0';flags=struct.unpack_from('<I',nso,12)[0];rows=[]
    for i in range(3):
        off,mem,size=struct.unpack_from('<III',nso,16+i*16);compressed=bool(flags&(1<<i));packed_size=struct.unpack_from('<I',nso,96+i*4)[0] if compressed else size
        packed=nso[off:off+packed_size];raw=unpack(packed) if compressed else packed;assert len(raw)==size
        rows.append(dict(offset=off,size=size,packed_size=packed_size,compressed=compressed,raw=raw,packed=packed))
    return rows
