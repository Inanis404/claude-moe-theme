"""Ask the exact Linux client to quit through its normal Ctrl+Q accelerator."""
import dataclasses,os,pathlib,re,subprocess,time

@dataclasses.dataclass(frozen=True)
class Instance:
    pid:int
    executable:pathlib.Path
    started:str

def inspect(pid):
    proc=pathlib.Path('/proc')/str(pid)
    try:
        if proc.stat().st_uid!=os.getuid():return None
        stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
        if stat[0]=='Z':return None
        return Instance(int(pid),(proc/'exe').resolve(strict=True),stat[19])
    except (OSError,ValueError,IndexError):return None

def main_instances(base):
    found=[]
    official=pathlib.Path('/usr/lib/claude-desktop/claude-desktop').resolve()
    releases=(base/'releases').resolve()
    for proc in pathlib.Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        instance=inspect(int(proc.name))
        if not instance:continue
        exe=instance.executable
        known_copy=exe.name=='claude-desktop' and exe.parent.parent==releases and (exe.parent/'atelier-release.json').is_file()
        if exe!=official and not known_copy:continue
        try:
            args=(proc/'cmdline').read_bytes().split(b'\0')[1:]
            if any(a.startswith(b'--type=') for a in args):continue
        except OSError:continue
        found.append(instance)
    return found

def run(*args):
    return subprocess.run(['xdotool',*map(str,args)],capture_output=True,text=True,timeout=3)

def window_for(instance):
    result=run('search','--onlyvisible','--pid',instance.pid)
    candidates=[]
    for wid in result.stdout.split():
        if not wid.isdigit():continue
        if run('getwindowpid',wid).stdout.strip()!=str(instance.pid):continue
        geometry=dict(re.findall(r'^(WIDTH|HEIGHT)=(\d+)$',run('getwindowgeometry','--shell',wid).stdout,re.M))
        width,height=int(geometry.get('WIDTH',0)),int(geometry.get('HEIGHT',0))
        if width>=240 and height>=160:candidates.append((width*height,wid))
    return max(candidates)[1] if candidates else None

def request_quit(instance,timeout=20,restore=True):
    if inspect(instance.pid)!=instance:return True
    # Reopening this exact executable asks its existing single-instance handler to unhide it.
    if restore:
        subprocess.Popen([str(instance.executable)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    deadline=time.monotonic()+timeout
    window_deadline=min(deadline,time.monotonic()+4)
    window=None
    while time.monotonic()<window_deadline:
        if inspect(instance.pid)!=instance:return True
        window=window_for(instance)
        if window:break
        time.sleep(.2)
    if not window or inspect(instance.pid)!=instance:return inspect(instance.pid)!=instance
    # Targeted X events do not type into another application or require a global key injection.
    if run('key','--window',window,'ctrl+q').returncode!=0:return inspect(instance.pid)!=instance
    while time.monotonic()<deadline:
        if inspect(instance.pid)!=instance:return True
        time.sleep(.2)
    return False  # Keep confirmations/tasks alive; never escalate to a termination signal.
