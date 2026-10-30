'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {WebContentsView}=require('electron');
const attach=require('./startup-cover.cjs');
module.exports=async({app,BrowserWindow,assets,testRoot})=>{
 const checks=[];
 const wait=async(fn,ms=20000)=>{const until=Date.now()+ms;while(Date.now()<until){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out waiting for media');};
 try{
  const win=new BrowserWindow({width:1220,height:820,show:false,webPreferences:{sandbox:true,contextIsolation:true,nodeIntegration:false}});
  await win.loadFile(path.join(assets,'selftest.html'));win.show();
  await wait(()=>win.webContents.executeJavaScript('document.querySelector("[data-claude-background-video]")?.currentTime>0.1'));
  const aligned=()=>win.webContents.executeJavaScript(`(()=>{const host=document.querySelector('[data-claude-video-host]'),layer=document.querySelector('[data-claude-video-layer]');if(!host||!layer)return false;const a=host.getBoundingClientRect(),b=layer.getBoundingClientRect();return ['left','top','right','bottom'].every(k=>Math.abs(a[k]-b[k])<1);})()`);
  assert(await aligned(),'background edges must match the transformed chat container without double offsets');
  await win.webContents.executeJavaScript("document.body.style.gridTemplateColumns='72px 1fr'");await wait(aligned);
  await win.webContents.executeJavaScript("document.querySelector('main').style.transform='none';document.querySelector('main').style.contain='none'");await wait(aligned);
  await win.webContents.executeJavaScript("document.body.style.gridTemplateColumns='';document.querySelector('main').style.transform='';document.querySelector('main').style.contain=''");await wait(aligned);
  checks.push('background edges stay aligned with transformed or ordinary chat containers and a collapsed sidebar');
  const background=await win.webContents.executeJavaScript(`(()=>{
    const v=document.querySelector('[data-claude-background-video]'),layer=v.parentElement;
    const draft=document.querySelector('[contenteditable]'),r=draft.getBoundingClientRect();
    return {width:v.videoWidth,height:v.videoHeight,loop:v.loop,muted:v.muted,paused:v.paused,
      fixed:getComputedStyle(layer).position,pointer:getComputedStyle(layer).pointerEvents,
      aside:document.querySelector('aside').hasAttribute('data-claude-background'),
      draft:draft.textContent,inputHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===draft,
      userBubble:getComputedStyle(document.querySelector('section')).backgroundColor,
      players:document.querySelectorAll('[data-claude-background-video]').length,
      titlebarClean:!document.querySelector('header [data-claude-video-layer]')&&!document.querySelector('header').hasAttribute('data-claude-background'),
      belowTitlebar:layer.getBoundingClientRect().top>=document.querySelector('header').getBoundingClientRect().bottom};
  })()`);
  assert.equal(background.width,1920);assert.equal(background.height,1080);assert(background.loop&&background.muted&&!background.paused);
  assert.equal(background.players,1);assert(background.titlebarClean);assert(background.belowTitlebar);
  assert.equal(background.fixed,'absolute');assert.equal(background.pointer,'none');assert(!background.aside);assert(background.inputHit);
  assert.equal(background.draft,'Unsent synthetic draft');
  assert.equal(background.userBubble,'rgb(238, 233, 224)');
  await win.webContents.executeJavaScript(`window.__bgLooped=false;{const v=document.querySelector('[data-claude-background-video]');v.addEventListener('timeupdate',()=>{if(v.currentTime<1)window.__bgLooped=true;});v.currentTime=v.duration-.2;}`);
  await wait(()=>win.webContents.executeJavaScript('window.__bgLooped'));
  await win.webContents.executeJavaScriptInIsolatedWorld(24602,[{code:'window.__claudeFixedBackground.setSuspended(true)'}]);
  assert(await win.webContents.executeJavaScript('document.querySelector("[data-claude-background-video]").paused'));
  await win.webContents.executeJavaScriptInIsolatedWorld(24602,[{code:'window.__claudeFixedBackground.setSuspended(false)'}]);
  await wait(()=>win.webContents.executeJavaScript('!document.querySelector("[data-claude-background-video]").paused'));
  await new Promise(r=>setTimeout(r,350));
  const scans=await win.webContents.executeJavaScriptInIsolatedWorld(24602,[{code:'window.__claudeFixedBackground.stats().scans'}]);
  await win.webContents.executeJavaScript(`{const n=document.querySelectorAll('section')[1];for(let i=0;i<40;i++)n.textContent='Token '+i;n.textContent='Synthetic assistant message';}`);
  await new Promise(r=>setTimeout(r,350));
  assert.equal(await win.webContents.executeJavaScriptInIsolatedWorld(24602,[{code:'window.__claudeFixedBackground.stats().scans'}]),scans);
  checks.push('one 1080p background player stays below the title bar, loops muted, pauses on request, and ignores streamed text updates');
  const nativeSnapshot=`(()=>{const clone=document.body.cloneNode(true);clone.querySelectorAll('[data-claude-video-layer]').forEach(n=>n.remove());clone.querySelectorAll('*').forEach(n=>{for(const a of [...n.attributes])if(a.name.startsWith('data-claude-'))n.removeAttribute(a.name);});return clone.innerHTML;})()`;
  const original=await win.webContents.executeJavaScript(nativeSnapshot);
  const cover=attach(win,{assets,sound:true});const wc=cover.view.webContents;wc.setAudioMuted(true);
  assert(!win.contentView.children.includes(cover.view));
  await wait(()=>wc.getTitle().startsWith('CLAUDE_SPLASH_PLAYING'));
  assert.equal(win.contentView.children.at(-1),cover.view);
  const extra=new WebContentsView({webPreferences:{sandbox:true,contextIsolation:true,nodeIntegration:false}});
  win.contentView.addChildView(extra);assert.equal(win.contentView.children.at(-1),cover.view);
  win.setSize(1320,880);await new Promise(r=>setTimeout(r,200));
  assert(await aligned(),'background must stay aligned after window resize');
  const [width,height]=win.getContentSize();assert.deepEqual(cover.view.getBounds(),{x:0,y:0,width,height});
  const media=await wc.executeJavaScript(`({motion:document.documentElement.dataset.portraitMotion,lineOpacity:getComputedStyle(document.querySelector('#line')).opacity,videoTime:document.querySelector('#awake').currentTime})`);
  assert.equal(media.motion,'optimized-video');assert(Number(media.lineOpacity)>.5);assert.equal(media.videoTime,0);
  const first=await wc.capturePage(),bitmap=first.toBitmap();let visible=0;
  for(let i=0;i<bitmap.length;i+=4)if(Math.max(bitmap[i],bitmap[i+1],bitmap[i+2])>90)visible++;
  assert(visible/(bitmap.length/4)>.02);fs.writeFileSync(path.join(testRoot,'first-frame.png'),first.toPNG());
  checks.push('the original line art is visible first, the new video waits for the reveal, and the cover follows window resize');
  await wc.executeJavaScript(`window.__awakeEnded=false;document.querySelector('#awake').addEventListener('ended',()=>window.__awakeEnded=true);`);
  await wait(()=>wc.executeJavaScript('document.querySelector("#awake").currentTime>1'));
  const playback=await wc.executeJavaScript(`(()=>{const v=document.querySelector('#awake');return {width:v.videoWidth,height:v.videoHeight,loop:v.loop,paused:v.paused,src:v.currentSrc,opacity:getComputedStyle(v).opacity,camera:getComputedStyle(document.querySelector('#cam')).transform};})()`);
  assert.equal(playback.width,1920);assert.equal(playback.height,1080);assert(!playback.loop&&!playback.paused);assert(playback.src.endsWith('/awake-playback.mp4'));assert.equal(playback.opacity,'1');assert.equal(playback.camera,'none');
  fs.writeFileSync(path.join(testRoot,'splash.png'),(await wc.capturePage()).toPNG());
  await wait(()=>wc.executeJavaScript('window.__awakeEnded'));
  checks.push('the optimized awake clip plays through to its ended event once, with a fixed camera');
  await wait(()=>cover.closed);await wait(()=>wc.isDestroyed());
  assert.equal(await win.webContents.executeJavaScript(nativeSnapshot),original);
  assert.equal(await win.webContents.executeJavaScript("Boolean(document.querySelector('[data-amber-avatar],#amber-native-skin-settings,[data-amber-role]'))"),false);
  assert(!Object.hasOwn(win.contentView,'addChildView'));
  fs.writeFileSync(path.join(testRoot,'chat-background.png'),(await win.webContents.capturePage()).toPNG());
  checks.push('the cover releases automatically and leaves the looping background and native chat controls intact');
  const clicked=attach(win,{assets});await wait(()=>clicked.view.webContents.getTitle().startsWith('CLAUDE_SPLASH_PLAYING'));
  await clicked.view.webContents.executeJavaScript("document.body.dispatchEvent(new MouseEvent('click',{bubbles:true}))");await wait(()=>clicked.closed);
  const escaped=attach(win,{assets});await wait(()=>escaped.view.webContents.getTitle().startsWith('CLAUDE_SPLASH_PLAYING'));
  escaped.view.webContents.sendInputEvent({type:'keyDown',keyCode:'Escape'});await wait(()=>escaped.closed);
  const timed=attach(win,{assets,maxMs:100});await wait(()=>timed.closed);
  assert(!Object.hasOwn(win.contentView,'addChildView'));checks.push('click, Escape and timeout release the animation');
  const report={passed:true,checks,testRoot};fs.writeFileSync(path.join(testRoot,'report.json'),JSON.stringify(report,null,2));
  console.log('CLAUDE_SPLASH_TEST '+JSON.stringify(report));app.exit(0);
 }catch(error){console.error('CLAUDE_SPLASH_TEST '+JSON.stringify({passed:false,error:String(error),checks,testRoot}));app.exit(1);}
};
