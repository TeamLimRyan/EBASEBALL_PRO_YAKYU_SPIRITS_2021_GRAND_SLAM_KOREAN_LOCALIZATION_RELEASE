"""Optional Control installer for Eden versions whose NSP installer crashes.

Run with Eden closed. Only the three hash-locked Control/CNMT entries are
changed. The original entries are backed up before any change.
"""
import argparse,hashlib,json,os,shutil
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def apply(control,nsp,registered,restore=False):
    registered=registered.resolve()
    if registered.name!='registered' or not registered.is_dir():raise ValueError('Choose Eden nand/user/Contents/registered')
    backup=registered.parent/'eb2_control_v09_backup';marker=backup/'backup.json'
    if restore:
        if not marker.exists():raise ValueError('Backup not found')
        stored=json.loads(marker.read_text('utf8'))
        if stored!=control['changes']:raise ValueError('Backup belongs to another patch')
        for c in stored:
            old=backup/c['old'];new=registered/c['new'];dest=registered/c['old']
            if digest(old)!=c['old_sha256']:raise ValueError('Backup hash mismatch')
            if dest.exists() and digest(dest)!=c['old_sha256']:raise ValueError('Original path now contains a different file')
            if new.exists() and digest(new)!=c['sha256']:raise ValueError('Patched path now contains a different file')
        for c in stored:
            shutil.copyfile(backup/c['old'],registered/c['old'])
            new=registered/c['new']
            if new.exists():new.unlink()
        print('Original Control restored; backup retained.');return
    if digest(nsp)!=control['target_sha256']:raise ValueError('Patched update NSP hash mismatch')
    backup.mkdir(exist_ok=True)
    if marker.exists() and json.loads(marker.read_text('utf8'))!=control['changes']:raise ValueError('Foreign backup directory')
    for c in control['changes']:
        old=registered/c['old'];saved=backup/c['old'];new=registered/c['new']
        if saved.exists():
            if digest(saved)!=c['old_sha256']:raise ValueError('Backup hash mismatch')
        else:
            if not old.exists() or digest(old)!=c['old_sha256']:raise ValueError('Expected original update NCA not installed')
            shutil.copyfile(old,saved)
        if new.exists() and digest(new)!=c['sha256']:raise ValueError('New NCA name conflict')
    marker.write_text(json.dumps(control['changes'],indent=2),encoding='utf8')
    with nsp.open('rb') as f:
        for c in control['changes']:
            f.seek(c['offset']);b=f.read(c['size'])
            if hashlib.sha256(b).hexdigest()!=c['sha256']:raise ValueError('NSP entry hash mismatch')
            dest=registered/c['new']
            if not dest.exists():
                tmp=dest.with_suffix(dest.suffix+'.eb2-tmp');tmp.write_bytes(b);tmp.replace(dest)
    # Retire only the old metadata entry after all new entries are verified.
    for c in control['changes']:
        if c['old'].endswith('.cnmt.nca'):
            old=registered/c['old']
            if old.exists():
                if digest(old)!=c['old_sha256']:raise ValueError('Original metadata changed during installation')
                old.unlink()
    print('Korean Control installed. Original Control and metadata backed up.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--patch-output',type=Path,required=True);p.add_argument('--registered',type=Path,required=True);p.add_argument('--restore',action='store_true');a=p.parse_args()
    m=json.loads(Path(__file__).with_name('manifest.json').read_text('utf8'));c=m['control'];apply(c,a.patch_output/c['target_name'],a.registered,a.restore)

if __name__=='__main__':main()
