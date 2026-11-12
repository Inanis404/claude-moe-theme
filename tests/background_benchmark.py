"""Compare two background scripts in fresh, isolated Chromium processes."""
import argparse
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def measure(playwright, script):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 960})
    page.set_content('''<style>body{margin:0}main{position:relative;height:960px;display:grid;grid-template-columns:1fr 1fr}.epitaxy-chat-panel{position:relative;min-height:0}section{height:100%}</style><main></main>''')
    page.evaluate('''() => {for(let index=0;index<4;index++){
      const panel=document.createElement('div');panel.className='epitaxy-chat-panel';
      panel.innerHTML='<section data-chat-transcript>Synthetic session</section>';
      document.querySelector('main').append(panel);
    }}''')
    page.add_script_tag(path=str(script))
    page.evaluate('args=>installClaudeChatBackground(...args)', [
        'data:image/jpeg;base64,' + base64.b64encode((ROOT / 'runtime/chat-background.jpg').read_bytes()).decode(),
        base64.b64encode((ROOT / 'runtime/chat-background.mp4').read_bytes()).decode(), False])
    page.wait_for_function("[...document.querySelectorAll('video')].length>0 && [...document.querySelectorAll('video')].every(video=>video.currentTime>0)")
    page.wait_for_timeout(1000)
    session = browser.new_browser_cdp_session()

    def snapshot():
        processes = session.send('SystemInfo.getProcessInfo')['processInfo']
        return {process['id']: process for process in processes}

    before = snapshot()
    frames_before = page.evaluate("[...document.querySelectorAll('video')].reduce((total,video)=>total+video.getVideoPlaybackQuality().totalVideoFrames,0)")
    page.wait_for_timeout(5000)
    after = snapshot()
    delta = {}
    for process_id, process in after.items():
        if process_id in before and process['type'] in ('browser', 'renderer', 'GPU') and process['cpuTime'] >= before[process_id]['cpuTime']:
            delta[process['type']] = delta.get(process['type'], 0) + process['cpuTime'] - before[process_id]['cpuTime']
    result = {'players': page.locator('video').count(), 'sampleSeconds': 5, 'cpuSecondsByProcessType': delta,
              'presentedFrames': page.evaluate("[...document.querySelectorAll('video')].reduce((total,video)=>total+video.getVideoPlaybackQuality().totalVideoFrames,0)") - frames_before}
    browser.close()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=ROOT / 'runtime/chat-background.js')
    args = parser.parse_args()
    with sync_playwright() as playwright:
        results = [{'baseline': measure(playwright, args.baseline), 'candidate': measure(playwright, args.candidate)} for trial in range(2)]
    output = ROOT / '.local/multi-panel/benchmark.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'trials': results, 'note': 'Headless Chromium CPU time only. GPU process CPU time is not GPU utilization; hardware GPU load and native Electron remain unmeasured.'}, indent=2))
    print(output.read_text())
