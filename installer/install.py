"""eBASEBALL 2021 Korean v0.9: offline, resumable, source-bound installer."""
import argparse,hashlib,json,os,platform,shutil,struct,subprocess,sys,zlib,time
from pathlib import Path,PurePosixPath
import deflate_recipe,jpeg_recipe,lz4_recipe
from rdb_primitives import slot_seed
from fast_rdb import crypt

PACKAGE=Path(__file__).resolve().parent
BLOCK=8*1024*1024

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(BLOCK),b''):h.update(b)
    return h.hexdigest()

def safe(root,relative):
    p=PurePosixPath(relative)
    if p.is_absolute() or not relative or '..' in p.parts or '\\' in relative or ':' in relative:raise ValueError('Unsafe package path')
    out=root.joinpath(*p.parts)
    if not out.resolve().is_relative_to(root.resolve()):raise ValueError('Path escapes destination')
    for q in [out,*out.parents]:
        if q==root.parent:break
        if q.is_symlink() or getattr(q,'is_junction',lambda:False)():raise ValueError('Link in output path')
    return out

def write_json(p,value):
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    for attempt in range(30):
        try:tmp.replace(p);break
        except PermissionError:
            if attempt==29:raise
            time.sleep(.1)

def verify(p,row):
    if not p.is_file() or p.stat().st_size!=row['size'] or digest(p)!=row['sha256']:raise ValueError('File size or SHA-256 mismatch: '+row.get('path',p.name))

class Installer:
    def __init__(self,args):
        self.args=args;self.manifest_bytes=(PACKAGE/'manifest.json').read_bytes();self.m=json.loads(self.manifest_bytes);self.id=hashlib.sha256(self.manifest_bytes).hexdigest()
        self.source=args.source.resolve();self.output=args.output.resolve();self.update=args.update_nsp.resolve()
        if self.output==self.source or self.output.is_relative_to(self.source) or self.source.is_relative_to(self.output):raise ValueError('Source and output directories overlap')
        self.stage=self.output.with_name('.'+self.output.name+'.eb2-v09-stage');self.marker=dict(package=self.id,layout=args.layout)
        if self.stage.is_symlink() or getattr(self.stage,'is_junction',lambda:False)():raise ValueError('Stage cannot be a link')
        self.done=0;self.total=len(self.m['loose'])+sum(len(a['jobs']) for a in self.m['archives'])+1
        self.xdelta=safe(PACKAGE,self.m['backend']['path']);self.state={}
    def report(self,event):
        row=dict(version='0.9',event=event,done=self.done,total=self.total,python=platform.python_version(),package=self.id)
        write_json(self.output.with_name('.'+self.output.name+'.diagnostic.json'),row)
        print(f'[{self.done}/{self.total}] {event}',flush=True)
    def preflight(self):
        print('Checking original files and package hashes...',flush=True)
        verify(self.xdelta,self.m['backend'])
        for row in self.m['package_files']:verify(safe(PACKAGE,row['path']),row)
        for row in self.m['sources']:verify(safe(self.source,row['path']),row)
        verify(self.update,self.m['control']['source'])
    def dest(self,title,relative):
        prefix=f'{title}/KoreanPatch' if self.args.layout=='eden' else f'atmosphere/contents/{title}'
        return safe(self.stage,prefix+'/'+relative)
    def delta(self,source,record,output):
        patch=safe(PACKAGE,record['path']);output.parent.mkdir(parents=True,exist_ok=True)
        result=subprocess.run([str(self.xdelta),'-f','-d','-s',str(source),str(patch),str(output)],capture_output=True)
        if result.returncode:raise ValueError('xdelta restoration failed: '+record['path'])
    def raw_delta(self,raw,row):
        if hashlib.sha256(raw).hexdigest()!=row['source_raw_sha256']:raise ValueError('Decoded source hash mismatch')
        a=self.work/'source.raw';b=self.work/'target.raw';a.write_bytes(raw);self.delta(a,row['delta'],b);result=b.read_bytes()
        if len(result)!=row['raw_size'] or hashlib.sha256(result).hexdigest()!=row['target_raw_sha256']:raise ValueError('Restored data hash mismatch')
        return result
    def loose(self,row):
        title,relative=row['target'].split('/',1);dest=self.dest(title,relative)
        if dest.exists() and dest.stat().st_size==row['target_size'] and digest(dest)==row['target_sha256']:return dest
        source=safe(self.source,row['source']);a=source.read_bytes();kind=row['kind']
        if kind=='direct':b=self.raw_delta(a,row)
        elif kind=='jpeg':b=jpeg_recipe.restore(safe(PACKAGE,row['recipe']['path']).read_bytes(),self.raw_delta(jpeg_recipe.create(a)[0],row))
        elif kind=='nso':
            b=bytearray(row['target_size']);prefix=bytes.fromhex(row['prefix_hex']);b[:len(prefix)]=prefix
            for s,t in zip(lz4_recipe.segments(a),row['segments']):
                raw=self.raw_delta(s['raw'],t);recipe=zlib.decompress(safe(PACKAGE,t['recipe']['path']).read_bytes());packed=lz4_recipe.restore(recipe,raw) if t['compressed'] else raw
                if len(packed)!=t['packed_size']:raise ValueError('NSO packed size mismatch')
                b[t['offset']:t['offset']+len(packed)]=packed
        else:raise ValueError('Unknown file kind')
        if len(b)!=row['target_size'] or hashlib.sha256(b).hexdigest()!=row['target_sha256']:raise ValueError('Restored file mismatch')
        dest.parent.mkdir(parents=True,exist_ok=True);tmp=dest.with_name(dest.name+'.tmp');tmp.write_bytes(b);tmp.replace(dest);return dest
    def archive(self,row):
        title='0100F88012E34000';dest=self.dest(title,'romfs/cdvdroot/'+row['name']);source=safe(self.source,row['source'])
        key='archive:'+row['name']
        if self.state.get(key)=='DONE' and dest.exists() and dest.stat().st_size==row['target_size'] and digest(dest)==row['target_sha256']:
            self.done+=len(row['jobs']);return dest
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not self.state.get(key):
            shutil.copyfile(source,dest)
            with dest.open('r+b') as f:f.truncate(row['target_size'])
            self.state[key]='RUNNING';self.checkpoint()
        with dest.open('r+b') as out:
            for job in row['jobs']:
                jkey='slot:'+job['id'];ready=False
                if self.state.get(jkey)=='DONE':
                    out.seek(job['offset']);ready=hashlib.sha256(out.read(job['size'])).hexdigest()==job['slot_sha256']
                if not ready:
                    e=job['source_entry'];sp=safe(self.source,'effective/romfs/cdvdroot/'+e['rdb'])
                    with sp.open('rb') as sf:
                        sf.seek(e['offset']);header=crypt(sf.read(32),slot_seed(e['source_name']));n=struct.unpack_from('<I',header,24)[0];sf.seek(e['offset']);body=crypt(sf.read(32+(n+3)//4*4),slot_seed(e['source_name']))[32:32+n]
                    raw=zlib.decompress(body) if e['compression']=='zlib' else body
                    result=self.raw_delta(raw,job);recipe=zlib.decompress(safe(PACKAGE,job['recipe']['path']).read_bytes());packed=deflate_recipe.restore(recipe,result) if recipe[:4] in [b'DFR1',b'DFR2'] else result
                    blob=crypt(bytes.fromhex(job['header_hex'])+packed+bytes.fromhex(job['padding_hex']),slot_seed(e['source_name']))
                    if len(blob)!=job['size'] or hashlib.sha256(blob).hexdigest()!=job['slot_sha256']:raise ValueError('Restored archive slot mismatch')
                    out.seek(job['offset']);out.write(blob);out.flush();self.state[jkey]='DONE';self.checkpoint()
                self.done+=1;self.report(job['id'])
        if digest(dest)!=row['target_sha256']:raise ValueError('Final archive SHA-256 mismatch')
        self.state[key]='DONE';self.checkpoint();return dest
    def checkpoint(self):write_json(self.stage/'journal.json',self.state)
    def link_second(self,first,relative):
        second=self.dest('0100F88012E34001',relative);second.parent.mkdir(parents=True,exist_ok=True)
        if second.exists():
            if digest(first)!=digest(second):raise ValueError('Second program output differs')
            return
        try:os.link(first,second)
        except OSError:shutil.copyfile(first,second)
    def run(self):
        self.preflight();self.output.parent.mkdir(parents=True,exist_ok=True)
        if self.output.exists():
            marker=self.output/'package-id.json'
            if not marker.exists() or json.loads(marker.read_text())!=self.marker:raise ValueError('Existing output belongs to another package')
            self.verify_final(self.output);print('Existing completed output verified.');return
        if self.stage.exists():
            marker=self.stage/'package-id.json'
            if not marker.exists() or json.loads(marker.read_text())!=self.marker:raise ValueError('Foreign staging directory')
        else:
            if shutil.disk_usage(self.output.parent).free<self.m['required_space']:raise ValueError('Insufficient output disk space')
            self.stage.mkdir();write_json(self.stage/'package-id.json',self.marker)
        self.work=self.stage/'work';self.work.mkdir(exist_ok=True);journal=self.stage/'journal.json';self.state=json.loads(journal.read_text()) if journal.exists() else {}
        for row in self.m['loose']:
            dest=self.loose(row)
            if row['target'].startswith('0100F88012E34000/romfs/'):self.link_second(dest,row['target'].split('/',1)[1])
            self.done+=1;self.report(row['target'])
        for row in self.m['archives']:
            dest=self.archive(row);self.link_second(dest,'romfs/cdvdroot/'+row['name'])
        c=self.m['control'];dest=safe(self.stage,c['target_name'])
        if not dest.exists() or digest(dest)!=c['target_sha256']:self.delta(self.update,c['delta'],dest)
        if digest(dest)!=c['target_sha256']:raise ValueError('Control update hash mismatch')
        self.done+=1;self.report('VERIFYING_OUTPUT');self.verify_final(self.stage)
        # Remove only the three installer-owned scratch files in the owned stage.
        for name in ['source.raw','target.raw']:
            p=self.work/name
            if p.exists():p.unlink()
        self.work.rmdir();self.stage.rename(self.output);self.report('COMPLETE')
    def verify_final(self,root):
        for row in self.m['targets']:
            title,rel=row['path'].split('/',1);prefix=f'{title}/KoreanPatch' if self.args.layout=='eden' else f'atmosphere/contents/{title}'
            verify(safe(root,prefix+'/'+rel),row)
        c=self.m['control'];verify(safe(root,c['target_name']),dict(size=c['target_size'],sha256=c['target_sha256']))

def main():
    p=argparse.ArgumentParser(description='eBASEBALL 2021 Korean patch v0.9')
    p.add_argument('--source',type=Path,required=True,help='Original merged extraction root: effective/ and program1/')
    p.add_argument('--update-nsp',type=Path,required=True,help='Original Japanese v786432 update NSP')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--layout',choices=['eden','atmosphere'],default='eden');args=p.parse_args()
    try:Installer(args).run()
    except Exception as e:print(f'INSTALL FAILED: {e}',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
