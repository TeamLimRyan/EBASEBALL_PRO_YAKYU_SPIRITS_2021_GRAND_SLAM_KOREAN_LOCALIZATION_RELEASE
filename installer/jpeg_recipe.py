"""Lossless baseline JPEG coefficient transport; no pixel re-encoding.

Quantized coefficients are patched against the owner's original coefficients.
Headers and Huffman tables reconstruct the exact previously verified JPEG.
"""
import array,json,math,struct,sys

def huffman(counts,values):
    dec={};enc={};code=0;at=0
    for n,count in enumerate(counts,1):
        for _ in range(count):
            value=values[at];at+=1;dec[n,code]=value;enc[value]=(code,n);code+=1
        code<<=1
    return dec,enc

class Reader:
    def __init__(self,raw):self.raw=raw;self.at=0;self.buf=0;self.bits=0
    def read(self,n):
        while self.bits<n:
            v=self.raw[self.at];self.at+=1
            if v==255:assert self.raw[self.at]==0;self.at+=1
            self.buf=(self.buf<<8)|v;self.bits+=8
        self.bits-=n;v=(self.buf>>self.bits)&((1<<n)-1);self.buf&=(1<<self.bits)-1;return v
    def symbol(self,table):
        v=0
        for n in range(1,17):
            v=(v<<1)|self.read(1)
            if (n,v) in table:return table[n,v]
        raise ValueError('Bad JPEG Huffman code')
    def restart(self,index):
        self.bits=0;self.buf=0;assert self.raw[self.at:self.at+2]==bytes([255,208+index%8]);self.at+=2

class Writer:
    def __init__(self):self.raw=bytearray();self.buf=0;self.bits=0
    def put(self,value,n):
        self.buf=(self.buf<<n)|value;self.bits+=n
        while self.bits>=8:
            self.bits-=8;v=(self.buf>>self.bits)&255;self.raw.append(v)
            if v==255:self.raw.append(0)
        self.buf&=(1<<self.bits)-1
    def align(self):
        if self.bits:self.put((1<<(8-self.bits))-1,8-self.bits)
    def restart(self,index):self.align();self.raw.extend([255,208+index%8])

def extend(v,n):return v if not n or v>=(1<<(n-1)) else v-((1<<n)-1)
def amplitude(v):
    n=abs(v).bit_length();return n,v if v>=0 else v+(1<<n)-1

def parse_header(jpg):
    assert jpg[:2]==b'\xff\xd8';at=2;tables={};components={};restart=0
    while True:
        assert jpg[at]==255;marker=jpg[at+1];n=int.from_bytes(jpg[at+2:at+4],'big');body=jpg[at+4:at+2+n];at+=2+n
        if marker==0xc0:
            assert body[0]==8
            height,width,count=struct.unpack_from('>HHB',body,1)
            for i in range(count):
                cid,hv,tq=body[6+i*3:9+i*3];components[cid]=dict(h=hv>>4,v=hv&15,quant=tq)
        elif marker==0xc4:
            p=0
            while p<len(body):
                ident=body[p];counts=list(body[p+1:p+17]);count=sum(counts);values=list(body[p+17:p+17+count]);p+=17+count
                tables[ident]=huffman(counts,values)
        elif marker==0xdd:restart=int.from_bytes(body,'big')
        elif marker==0xda:
            count=body[0];order=[]
            for i in range(count):
                cid,sel=body[1+i*2:3+i*2];order.append((cid,sel>>4,16+(sel&15)))
            assert body[-3:]==b'\0\x3f\0' and len(order)==len(components)
            break
        elif marker in [0xc1,0xc2,0xc3]:raise ValueError('Only baseline JPEG supported')
    h=max(c['h'] for c in components.values());v=max(c['v'] for c in components.values())
    return dict(header=jpg[:at],tables=tables,components=components,order=order,restart=restart,mcus=math.ceil(width/(8*h))*math.ceil(height/(8*v))),jpg[at:]

def create(jpg):
    model,entropy=parse_header(jpg);r=Reader(entropy);coeff=array.array('h');previous={cid:0 for cid in model['components']}
    for mcu in range(model['mcus']):
        if mcu and model['restart'] and mcu%model['restart']==0:r.restart(mcu//model['restart']-1);previous=dict.fromkeys(previous,0)
        for cid,dc,ac in model['order']:
            c=model['components'][cid]
            for block in range(c['h']*c['v']):
                n=r.symbol(model['tables'][dc][0]);value=previous[cid]+extend(r.read(n),n);previous[cid]=value;row=[value]+[0]*63;k=1
                while k<64:
                    token=r.symbol(model['tables'][ac][0]);run=token>>4;n=token&15
                    if not n:
                        if run==0:break
                        assert run==15;k+=16
                    else:
                        k+=run;assert k<64;row[k]=extend(r.read(n),n);k+=1
                coeff.extend(row)
    assert entropy[r.at:]==b'\xff\xd9'
    if sys.byteorder!='little':coeff.byteswap()
    raw=coeff.tobytes();recipe=model['header']
    assert restore(recipe,raw)==jpg,'Noncanonical JPEG entropy stream'
    return raw,recipe

def restore(header,raw):
    model,_=parse_header(header);coeff=array.array('h');coeff.frombytes(raw)
    if sys.byteorder!='little':coeff.byteswap()
    w=Writer();previous={cid:0 for cid in model['components']};at=0
    for mcu in range(model['mcus']):
        if mcu and model['restart'] and mcu%model['restart']==0:w.restart(mcu//model['restart']-1);previous=dict.fromkeys(previous,0)
        for cid,dc,ac in model['order']:
            c=model['components'][cid];dt=model['tables'][dc][1];act=model['tables'][ac][1]
            for block in range(c['h']*c['v']):
                row=coeff[at:at+64];at+=64;diff=row[0]-previous[cid];previous[cid]=row[0]
                n,v=amplitude(diff);w.put(*dt[n]);w.put(v,n);zeros=0
                for value in row[1:]:
                    if not value:zeros+=1;continue
                    while zeros>=16:w.put(*act[240]);zeros-=16
                    n,v=amplitude(value);w.put(*act[(zeros<<4)|n]);w.put(v,n);zeros=0
                if zeros:w.put(*act[0])
    assert at==len(coeff);w.align();return header+bytes(w.raw)+b'\xff\xd9'

if __name__=='__main__':
    from pathlib import Path
    for name in sys.argv[1:]:
        p=Path(name);raw,recipe=create(p.read_bytes());print(p.name,len(raw),len(recipe),'EXACT PASS')
