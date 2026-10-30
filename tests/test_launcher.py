import importlib.util,pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts/linux'))
import native_quit

root=pathlib.Path(__file__).resolve().parents[1]/'scripts/linux'
spec=importlib.util.spec_from_file_location('launch_skin',root/'launch-skin.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
base=pathlib.Path.home()/'.local/share/claude-atelier'
target=base/'releases/test-runtime/claude-desktop'
old=native_quit.Instance(999999,pathlib.Path('/usr/lib/claude-desktop/claude-desktop'),'test-old')
current=native_quit.Instance(999998,target,'test-current')

class Switched(Exception):pass
class SwitchTest(unittest.TestCase):
    def run_launcher(self,instances,quit_result=True):
        with patch.object(launcher.pathlib.Path,'read_text',return_value=__import__('json').dumps({'release':str(target.parent)})),patch.object(launcher.pathlib.Path,'resolve',lambda p,strict=False:p),patch.object(launcher.pathlib.Path,'open',return_value=__import__('tempfile').TemporaryFile(mode='a+')),patch.object(sys,'argv',['launch-skin.py']),patch.object(launcher,'main_instances',side_effect=instances),patch.object(launcher,'request_quit',return_value=quit_result) as quit_call,patch.object(launcher.os,'execv',side_effect=Switched) as launch:
            try:result=launcher.main()
            except Switched:result='launched'
            return result,quit_call.call_count,launch.call_count
    def test_old_closes_then_skin_opens(self):self.assertEqual(self.run_launcher([[old],[]]),('launched',1,1))
    def test_confirmation_is_preserved(self):self.assertEqual(self.run_launcher([[old]],False),(14,1,0))
    def test_existing_skin_is_only_restored(self):self.assertEqual(self.run_launcher([[current],[current]]),('launched',0,1))
    def test_new_old_instance_blocks_handoff(self):self.assertEqual(self.run_launcher([[old],[old]]),(14,1,0))
    def test_no_instance_starts_skin(self):self.assertEqual(self.run_launcher([[],[]]),('launched',0,1))
    def test_reused_pid_is_not_sent_keys(self):
        with patch.object(native_quit,'inspect',return_value=None),patch.object(native_quit,'run') as keys:
            self.assertTrue(native_quit.request_quit(old));keys.assert_not_called()
    def test_timeout_does_not_terminate_app(self):
        with patch.object(native_quit,'inspect',return_value=old),patch.object(native_quit,'window_for',return_value='123'),patch.object(native_quit,'run') as keys:
            keys.return_value.returncode=0
            self.assertFalse(native_quit.request_quit(old,timeout=.05,restore=False))
            self.assertEqual(keys.call_args.args,('key','--window','123','ctrl+q'))

if __name__=='__main__':unittest.main()
