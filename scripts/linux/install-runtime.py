#!/usr/bin/env python3
"""Create a local, versioned copy; never modify the installed Claude package."""
import argparse, hashlib, json, os, pathlib, shutil, struct, sys, time

ROOT=pathlib.Path(__file__).resolve().parents[2]
STAGE=ROOT/'runtime'
SCRIPTS=ROOT/'scripts/linux'
COMPAT=json.loads((ROOT/'config/compatibility.json').read_text())
SOURCE=pathlib.Path(COMPAT['officialDirectory'])
HOME=pathlib.Path.home()
BASE=HOME/'.local/share/claude-atelier'
EXPECTED=COMPAT['coreVersion']
ADDED=['claude-bootstrap.cjs','startup-cover.cjs','splash-self-test.cjs','chat-background.cjs']

def sha(data): return hashlib.sha256(data).hexdigest()
def hashfile(p):
    with open(p,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def read_asar(p):
    raw=p.read_bytes();size=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[16:16+size]),raw,8+struct.unpack_from('<I',raw,4)[0]
def walk(node,prefix=''):
    for name,item in node.get('files',{}).items():
        key=prefix+name
        if 'files' in item: yield from walk(item,key+'/')
        else: yield key,item
def content(item,raw,base):
    start=base+int(item['offset']);return raw[start:start+item['size']]
def integrity(data):
    size=4194304
    return {'algorithm':'SHA256','hash':sha(data),'blockSize':size,'blocks':[sha(data[i:i+size]) for i in range(0,len(data),size)] or [sha(b'')]}
def repack(source,destination):
    tree,raw,base=read_asar(source)
    original={name:content(item,raw,base) for name,item in walk(tree) if 'offset' in item and not item.get('unpacked')}
    package=json.loads(original['package.json'])
    assert package['version']==EXPECTED and package['main']=='.vite/build/index.pre.js'
    package['main']='claude-bootstrap.cjs'
    package['claudeLocalCustomization']={'mode':'splash-and-background','version':'1.4.1','originalMain':'.vite/build/index.pre.js'}
    changes={'package.json':json.dumps(package,ensure_ascii=False,separators=(',',':')).encode()}
    changes.update({name:(STAGE/name).read_bytes() for name in ADDED})
    for name,data in changes.items():
        tree['files'][name]={'size':len(data),'offset':'0','integrity':integrity(data)}
    payload=bytearray()
    for name,item in walk(tree):
        if item.get('unpacked') or 'link' in item: continue
        data=changes.get(name,original.get(name))
        if data is None: raise ValueError('Missing file: '+name)
        item['offset']=str(len(payload));item['size']=len(data);payload.extend(data)
    header=json.dumps(tree,ensure_ascii=False,separators=(',',':')).encode()
    pickled=struct.pack('<I',len(header))+header
    pickled+=b'\0'*((-len(pickled))%4)
    pickled=struct.pack('<I',len(pickled))+pickled
    destination.write_bytes(struct.pack('<II',4,len(pickled))+pickled+payload)
    # Validate every original packed file; only package.json may differ.
    check,updated,newbase=read_asar(destination)
    verified=0
    for name,item in walk(check):
        if name in original and name!='package.json':
            assert content(item,updated,newbase)==original[name],name
            verified+=1
    for name in changes: assert content(check['files'][name],updated,newbase)==changes[name]
    return verified

def install(base=None, register_desktop=True):
    global BASE
    if base is not None: BASE=pathlib.Path(base).expanduser().resolve()
    if os.getuid()==0: raise RuntimeError('Install as the normal Linux user.')
    tree,raw,base=read_asar(SOURCE/'resources/app.asar')
    p=json.loads(content(tree['files']['package.json'],raw,base))
    if p['version']!=EXPECTED: raise RuntimeError('This skin build supports Claude '+EXPECTED+'; installed '+p['version'])
    asset_names=['selftest.html','chat-background.js','chat-background.jpg','chat-background.mp4']
    digest=hashlib.sha256()
    for folder,names in [(STAGE,ADDED+asset_names),(SCRIPTS,['launch-skin.py','native_quit.py','run.sh','session-env.sh'])]:
        for name in names:
            digest.update(name.encode());digest.update((folder/name).read_bytes())
    for file in sorted((STAGE/'splash').rglob('*')):
        if file.is_file(): digest.update(str(file.relative_to(STAGE)).encode());digest.update(file.read_bytes())
    payload_hash=digest.hexdigest()
    release=BASE/'releases'/(EXPECTED+'-splash-'+payload_hash[:12])
    if not (release/'atelier-release.json').is_file():
        if release.exists(): raise RuntimeError('An incomplete release exists; leaving it for inspection: '+str(release))
        release.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(SOURCE,release,symlinks=True,ignore=shutil.ignore_patterns('chrome-sandbox'))
        # Reuse the official root-owned setuid helper without changing its permissions.
        (release/'chrome-sandbox').symlink_to(SOURCE/'chrome-sandbox')
        verified=repack(SOURCE/'resources/app.asar',release/'resources/app.asar')
        assets=release/'resources/atelier';assets.mkdir()
        for name in asset_names: shutil.copy2(STAGE/name,assets/name)
        shutil.copytree(STAGE/'splash',assets/'splash')
        assert hashfile(SOURCE/'claude-desktop')==hashfile(release/'claude-desktop')
        info={'skinVersion':'1.0.0','coreVersion':EXPECTED,'payloadHash':payload_hash,'coreBinaryUnchanged':True,'verifiedOriginalPackedFiles':verified,'asarSha256':hashfile(release/'resources/app.asar')}
        (release/'atelier-release.json').write_text(json.dumps(info,indent=2))
    else:
        info=json.loads((release/'atelier-release.json').read_text())
        if info.get('payloadHash')!=payload_hash or hashfile(release/'resources/app.asar')!=info['asarSha256']: raise RuntimeError('Release verification failed.')
    tools=BASE/'bin';tools.mkdir(parents=True,exist_ok=True)
    for name in ['launch-skin.py','native_quit.py','run.sh','session-env.sh']:
        shutil.copy2(SCRIPTS/name,tools/name);(tools/name).chmod(0o755)
    (BASE/'current.json.tmp').write_text(json.dumps({'release':str(release),'coreVersion':EXPECTED,'skinVersion':'1.0.0'}))
    (BASE/'current.json.tmp').replace(BASE/'current.json')
    if register_desktop: register_desktop_entry(release,tools)
    return {'ok':True,'release':str(release),**info}

def register_desktop_entry(release,tools):
    appdir=HOME/'.local/share/applications';appdir.mkdir(parents=True,exist_ok=True)
    desktop=appdir/'com.anthropic.Claude.desktop'
    if desktop.exists() and 'X-Claude-Atelier=true' not in desktop.read_text():
        backup=desktop.with_name(desktop.name+'.before-atelier')
        if backup.exists(): raise RuntimeError('Existing desktop override needs review before replacement.')
        shutil.copy2(desktop,backup)
    desktop.write_text('[Desktop Entry]\nName=Claude\nComment=Claude with startup animation\nType=Application\nExec="'+str(tools/'run.sh')+'" %U\nIcon='+str(release/'resources/atelier/splash/assets/icon.png')+'\nTerminal=false\nStartupWMClass=com.anthropic.Claude\nMimeType=x-scheme-handler/claude;application/vnd.anthropic.mcpb;application/vnd.anthropic.skill;\nCategories=Utility;Development;\nX-Claude-Atelier=true\n')
    import subprocess
    subprocess.run(['update-desktop-database',str(appdir)],check=True,capture_output=True)
    subprocess.run(['gio','mime','x-scheme-handler/claude','com.anthropic.Claude.desktop'],check=True,capture_output=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=pathlib.Path,help='Separate runtime directory, useful for isolated tests')
    parser.add_argument('--no-desktop',action='store_true',help='Do not register the desktop or URL handler')
    args=parser.parse_args()
    try: print(json.dumps(install(args.base,not args.no_desktop),ensure_ascii=False))
    except Exception as e: print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False));sys.exit(1)
