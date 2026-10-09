/* Source-bound DEFLATE literal restoration. Copyright 2026 TeamLimRyan.
 * MIT licensed; distributed with source. No compression or key handling. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API
#endif
API int patch_literals(uint8_t *out, size_t out_size, const uint8_t *raw,
                       size_t raw_size, const uint32_t *trace, size_t count,
                       const uint16_t *codes, int clear) {
    uint32_t previous_bit=0,previous_raw=0;
    for(size_t i=0;i<count;i++) {
        uint32_t bit=trace[i*2], r=trace[i*2+1];
        if(clear&2){bit+=previous_bit;r+=previous_raw;previous_bit=bit;previous_raw=r;}
        if(r>=raw_size)return 1;
        unsigned n=codes[raw[r]*2+1];
        if(n==0||n>15||(uint64_t)bit+n>(uint64_t)out_size*8)return 2;
        unsigned value=(clear&1)?0:codes[raw[r]*2];
        size_t p=bit/8;unsigned shift=bit%8;
        unsigned mask=((1u<<n)-1u)<<shift;value<<=shift;
        unsigned bytes=(shift+n+7)/8;
        for(unsigned j=0;j<bytes;j++) {
            out[p+j]=(uint8_t)((out[p+j]&~(mask>>(j*8)))|(value>>(j*8)));
        }
    }
    return 0;
}
API int rdb_transform(uint32_t *words,size_t count,uint32_t *state) {
    for(size_t i=0;i<count;i++) {
        unsigned j=(unsigned)(i&63);state[j]^=state[(j+3)&63];words[i]^=state[(j+1)&63];
    }return 0;
}

typedef struct {const uint8_t *data;size_t size,bit;int error;} Bits;
static unsigned read_bits(Bits *b,unsigned n) {
    if(b->bit+n>b->size*8){b->error=1;return 0;}
    size_t at=b->bit/8;unsigned shift=b->bit%8;uint32_t v=0;
    for(unsigned i=0;i<3&&at+i<b->size;i++)v|=(uint32_t)b->data[at+i]<<(i*8);
    b->bit+=n;return (v>>shift)&((1u<<n)-1u);
}
static int make_table(const uint8_t *lengths,unsigned count,uint32_t *table) {
    unsigned counts[16]={0},next[16]={0},code=0;memset(table,0,32768*sizeof(uint32_t));
    for(unsigned i=0;i<count;i++){if(lengths[i]>15)return 1;if(lengths[i])counts[lengths[i]]++;}
    for(unsigned n=1;n<=15;n++){code=(code+counts[n-1])<<1;next[n]=code;}
    for(unsigned i=0;i<count;i++) {
        unsigned n=lengths[i];if(!n)continue;unsigned value=next[n]++,reverse=0;
        for(unsigned j=0;j<n;j++){reverse=(reverse<<1)|(value&1);value>>=1;}
        for(unsigned p=reverse;p<32768;p+=1u<<n)table[p]=(i<<5)|n;
    }return 0;
}
static unsigned read_symbol(Bits *b,const uint32_t *table,unsigned *length) {
    size_t before=b->bit;unsigned remaining=(unsigned)((b->size*8-before)<15?(b->size*8-before):15);
    unsigned code=read_bits(b,remaining);b->bit=before;uint32_t entry=table[code];*length=entry&31;
    if(!*length){b->error=1;return 0;}b->bit+=*length;return entry>>5;
}
typedef void (*TraceCallback)(unsigned,unsigned,unsigned,unsigned,const uint8_t*,unsigned,const uint32_t*,size_t);
API int deflate_trace(const uint8_t *packed,size_t packed_size,const uint8_t *raw,size_t raw_size,uint8_t *skeleton,TraceCallback callback) {
    static const unsigned order[19]={16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15};
    static const unsigned lb[29]={3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258};
    static const unsigned le[29]={0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0};
    static const unsigned de[30]={0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13};
    Bits b={packed,packed_size,16,0};size_t out=0,capacity=65536,count=0;int result=0;
    uint32_t *lt=malloc(32768*4),*dt=malloc(32768*4),*trace=malloc(capacity*8);
    if(!lt||!dt||!trace){result=9;goto end;}
    memcpy(skeleton,packed,packed_size);
    for(;;) {
        unsigned final=read_bits(&b,1),kind=read_bits(&b,2),nl=0,nd=0;uint8_t lengths[320]={0};count=0;
        if(kind==0) {
            b.bit=(b.bit+7)/8*8;unsigned n=read_bits(&b,16),inv=read_bits(&b,16);size_t at=b.bit/8;
            if((n^65535)!=inv||at+n>packed_size||out+n>raw_size||memcmp(packed+at,raw+out,n)){result=1;goto end;}
            memset(skeleton+at,0,n);callback(0,(unsigned)at,(unsigned)out,n,NULL,0,NULL,0);b.bit+=n*8;out+=n;
        } else {
            if(kind==1) {
                nl=288;nd=32;for(unsigned i=0;i<144;i++)lengths[i]=8;for(unsigned i=144;i<256;i++)lengths[i]=9;for(unsigned i=256;i<280;i++)lengths[i]=7;for(unsigned i=280;i<288;i++)lengths[i]=8;for(unsigned i=288;i<320;i++)lengths[i]=5;
            } else if(kind==2) {
                nl=read_bits(&b,5)+257;nd=read_bits(&b,5)+1;unsigned nc=read_bits(&b,4)+4;uint8_t cl[19]={0};
                for(unsigned i=0;i<nc;i++)cl[order[i]]=(uint8_t)read_bits(&b,3);
                if(make_table(cl,19,lt)){result=2;goto end;}
                unsigned at=0;
                while(at<nl+nd&&!b.error) {
                    unsigned bits,s=read_symbol(&b,lt,&bits),n=1,value=s;
                    if(s==16){if(!at){result=3;goto end;}n=read_bits(&b,2)+3;value=lengths[at-1];}
                    else if(s==17){n=read_bits(&b,3)+3;value=0;}
                    else if(s==18){n=read_bits(&b,7)+11;value=0;}
                    if(at+n>nl+nd){result=4;goto end;}memset(lengths+at,value,n);at+=n;
                }
            } else {result=5;goto end;}
            if(make_table(lengths,nl,lt)||make_table(lengths+nl,nd,dt)){result=6;goto end;}
            while(!b.error) {
                size_t start=b.bit;unsigned bits,s=read_symbol(&b,lt,&bits);
                if(s<256) {
                    if(out>=raw_size||raw[out]!=s||start>UINT32_MAX){result=7;goto end;}
                    if(count==capacity){capacity*=2;uint32_t *more=realloc(trace,capacity*8);if(!more){result=9;goto end;}trace=more;}
                    trace[count*2]=(uint32_t)start;trace[count*2+1]=(uint32_t)out;count++;out++;
                    size_t p=start/8;unsigned shift=start%8,mask=((1u<<bits)-1u)<<shift;
                    for(unsigned j=0;j<(shift+bits+7)/8;j++)skeleton[p+j]&=(uint8_t)~(mask>>(8*j));
                } else if(s==256)break;
                else {
                    if(s>285){result=8;goto end;}out+=lb[s-257]+read_bits(&b,le[s-257]);unsigned d=read_symbol(&b,dt,&bits);if(d>=30){result=8;goto end;}read_bits(&b,de[d]);
                }
            }
            callback(1,0,0,0,lengths,nl,trace,count);
        }
        if(b.error||out>raw_size){result=10;goto end;}if(final)break;
    }
    if(out!=raw_size)result=11;
end:free(lt);free(dt);free(trace);return result;
}
