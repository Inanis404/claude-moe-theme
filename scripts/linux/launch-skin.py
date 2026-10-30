#!/usr/bin/env python3
import fcntl,json,os,pathlib,sys
from native_quit import main_instances,request_quit

def main():
    base=pathlib.Path.home()/'.local/share/claude-atelier'
    target=(pathlib.Path(json.loads((base/'current.json').read_text())['release'])/'claude-desktop').resolve(strict=True)
    if target.parent.parent!=(base/'releases').resolve():raise RuntimeError('Unexpected runtime path')
    if os.getuid()==0:raise RuntimeError('Use your normal Linux user')
    args=sys.argv[1:]
    if any(not (a.startswith('claude://') or (pathlib.Path(a).is_file() and pathlib.Path(a).suffix in ['.mcpb','.skill'])) for a in args):raise RuntimeError('Unsupported launch argument')
    with (base/'launch.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 0
        for instance in main_instances(base):
            if instance.executable==target:continue
            if not request_quit(instance):
                print('QUIT_PENDING: 请完成旧 Claude 的退出确认，再打开皮肤版。',file=sys.stderr)
                return 14
        if any(i.executable!=target for i in main_instances(base)):
            print('QUIT_PENDING: 旧客户端仍在退出，请稍后重试。',file=sys.stderr)
            return 14
        os.chdir(pathlib.Path.home())
        # WSLg reserves the Wayland input-method connection. GTK/XWayland supports our Fcitx module.
        os.execv(str(target),[str(target),'--ozone-platform=x11',*args])

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print('Atelier startup: '+str(e),file=sys.stderr);sys.exit(1)
