"""Isolated Chromium regression and synthetic visual evidence; no Desktop attachment."""
import base64
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.local' / 'multi-panel'


def run(script):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 960})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content('''<!doctype html><html><head><style>
        *{box-sizing:border-box}body{margin:0;font:18px sans-serif;background:#faf8f4}
        aside{position:absolute;width:180px;height:100vh;padding:20px;background:#eee9e0}
        header{height:40px;margin-left:180px;padding:10px}
        main{margin-left:180px;height:920px;display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
        .epitaxy-root{min-height:0;display:flex;flex-direction:column}
        .epitaxy-chat-panel{position:relative;flex:1;min-height:0;display:flex;flex-direction:column;border-radius:12px;overflow:hidden}
        [data-epitaxy-transcript-region]{padding:24px;flex:1}
        [contenteditable]{padding:20px;margin:15px;background:#fffdf8;border-radius:12px}
        </style></head><body><aside>Synthetic sidebar</aside><header>Native toolbar</header><main></main></body></html>''')
        page.evaluate('''() => {
          window.addPanel = () => {
            const root=document.createElement('div');root.className='epitaxy-root';
            root.innerHTML='<div class="epitaxy-chat-panel"><div data-epitaxy-transcript-region><h2>Synthetic session</h2><p class="stream">Assistant message</p></div><div data-chat-input-container><div contenteditable="true" role="textbox">Unsent draft</div></div></div>';
            document.querySelector('main').append(root);
          };addPanel();
        }''')
        page.add_script_tag(path=str(script))
        poster = 'data:image/jpeg;base64,' + base64.b64encode((ROOT / 'runtime/chat-background.jpg').read_bytes()).decode()
        video = base64.b64encode((ROOT / 'runtime/chat-background.mp4').read_bytes()).decode()
        page.evaluate('args => installClaudeChatBackground(...args)', [poster, video, False])

        def check(count):
            page.wait_for_function('count => window.__claudeFixedBackground.stats().players === count', arg=count)
            page.wait_for_function('''() => [...document.querySelectorAll('video')].every(video=>video.videoWidth===1920 && video.currentTime>0 && !video.paused && !video.error)''')
            stats = page.evaluate('window.__claudeFixedBackground.stats()')
            assert all(panel['layer']['maxEdgeError'] < 1 for panel in stats['panels']), stats
            assert page.evaluate("new Set([...document.querySelectorAll('video')].map(video=>video.src)).size") == 1
            assert page.evaluate('''() => [...document.querySelectorAll('[contenteditable]')].every(input=>{
              const rect=input.getBoundingClientRect();return document.elementFromPoint(rect.x+10,rect.y+10)===input;
            })''')
            assert page.evaluate("!document.querySelector('header').hasAttribute('data-claude-background') && !document.querySelector('aside').hasAttribute('data-claude-background')")
            return stats

        check(1)
        page.screenshot(path=str(OUTPUT / 'single.png'))
        page.evaluate('addPanel()')
        check(2)
        page.screenshot(path=str(OUTPUT / 'dual.png'))
        page.evaluate('addPanel()')
        check(3)
        page.screenshot(path=str(OUTPUT / 'triple.png'))
        page.evaluate('addPanel()')
        check(4)
        page.evaluate('''() => {window.savedVideos=[...document.querySelectorAll('video')];window.scans=window.__claudeFixedBackground.stats().scans;
          for(let index=0;index<80;index++)document.querySelector('.stream').textContent='Streaming token '+index;
        }''')
        page.wait_for_timeout(400)
        assert page.evaluate('window.__claudeFixedBackground.stats().scans===window.scans')
        assert page.evaluate('window.savedVideos.every(video=>video.isConnected)')
        page.evaluate("document.querySelector('main').style.gridTemplateColumns='2fr 1fr'")
        check(4)
        page.evaluate("document.querySelector('main').lastElementChild.remove()")
        check(3)
        assert page.evaluate('window.savedVideos[3].getAttribute("src")===null && window.savedVideos[3].paused')
        page.evaluate("document.querySelector('main').firstElementChild.style.display='none'")
        page.wait_for_function('window.savedVideos[0].paused')
        page.evaluate("document.querySelector('main').firstElementChild.style.display='flex'")
        check(3)
        page.evaluate("document.documentElement.classList.add('dark')")
        page.wait_for_function("[...document.querySelectorAll('[data-claude-video-layer]')].every(layer=>layer.lastChild.style.background==='rgba(28, 25, 23, 0.74)')")
        page.evaluate('window.__claudeFixedBackground.setSuspended(true)')
        assert page.evaluate("[...document.querySelectorAll('video')].every(video=>video.paused)")
        page.evaluate('window.__claudeFixedBackground.setSuspended(false)')
        check(3)
        before = page.evaluate("document.querySelector('video').getVideoPlaybackQuality().totalVideoFrames")
        page.wait_for_timeout(600)
        after = page.evaluate("document.querySelector('video').getVideoPlaybackQuality().totalVideoFrames")
        assert after > before
        page.evaluate("document.querySelector('video').currentTime=document.querySelector('video').duration-0.1")
        page.wait_for_function("document.querySelector('video').currentTime<1")
        page.goto('about:blank')
        page.set_content((ROOT / 'runtime/selftest.html').read_text(encoding='utf-8'))
        page.add_script_tag(path=str(script))
        page.evaluate('args => installClaudeChatBackground(...args)', [poster, video, False])
        check(1)
        page.screenshot(path=str(OUTPUT / 'original-single.png'))
        assert not errors, errors
        (OUTPUT / 'report.json').write_text(json.dumps({'passed': True, 'cases': ['single', 'dual', 'triple', 'four', 'stream stability', 'shared source', 'resize', 'remove cleanup', 'hide/show', 'dark mask', 'suspend/resume', 'decoded frame advancement'], 'decodedFrames': [before, after], 'productionAttached': False}, indent=2))
        browser.close()
    print('Multi-panel regression passed; evidence: ' + str(OUTPUT))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script', type=Path, default=ROOT / 'runtime/chat-background.js')
    run(parser.parse_args().script)
