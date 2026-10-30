'use strict';
const {WebContentsView,webContents}=require('electron');
const path=require('node:path');

// A temporary child view covers the actual client area, never a separately positioned window.
module.exports=function attachStartupCover(win,{assets,sound=false,maxMs=28000,onClose=()=>{},onError=()=>{}}){
 const host=win.contentView;
 const originalAdd=host.addChildView,ownAdd=Object.getOwnPropertyDescriptor(host,'addChildView');
 const view=new WebContentsView({webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true,backgroundThrottling:false,autoplayPolicy:'no-user-gesture-required'}});
 const wc=view.webContents,keys=new Set();let closed=false,timer,playing=false,finishing=false,attached=false;
 const priorFocus=webContents.getFocusedWebContents();
 view.setBackgroundColor('#00000000');
 const fit=()=>{if(!closed&&!win.isDestroyed()){const [width,height]=win.getContentSize();view.setBounds({x:0,y:0,width:Math.max(1,width),height:Math.max(1,height)});}};
 const focus=()=>{if(!closed&&playing&&win.isFocused()&&!wc.isDestroyed())wc.focus();};
 const resize=()=>{fit();setImmediate(fit);};
 const key=(event,input)=>{if(input.type==='keyDown'&&['Escape','Enter',' '].includes(input.key)){event.preventDefault();close('skip');}};
 const trackKeys=contents=>{if(contents&&!keys.has(contents)){keys.add(contents);contents.on('before-input-event',key);}};
 const wrapped=function(child){
  const result=originalAdd.apply(this,arguments);
  if(!closed&&child!==view){trackKeys(child.webContents);if(attached)originalAdd.call(host,view);fit();}
  return result;
 };
 function close(reason='done'){
  if(closed)return;closed=true;clearTimeout(timer);
  win.off('resize',resize);win.off('show',focus);win.off('focus',focus);win.off('closed',parentClosed);
  for(const item of keys)if(!item.isDestroyed())item.off('before-input-event',key);
  if(host.addChildView===wrapped){if(ownAdd)Object.defineProperty(host,'addChildView',ownAdd);else delete host.addChildView;}
  try{if(!win.isDestroyed())host.removeChildView(view);}catch{}
  if(!wc.isDestroyed()){
   // Remove the picture immediately, but allow the audio envelope to reach zero before teardown.
   const retire=()=>{if(!wc.isDestroyed())wc.close();};
   const fallback=setTimeout(retire,400);fallback.unref();
   wc.executeJavaScript('window.__claudeStopSound?.(0.12)').catch(()=>{}).finally(()=>{clearTimeout(fallback);retire();});
  }
  if(!win.isDestroyed()&&win.isFocused()&&priorFocus&&!priorFocus.isDestroyed())priorFocus.focus();
  onClose(reason);
 }
 const parentClosed=()=>close('window-closed');
 try{
  host.addChildView=wrapped;
  fit(); // Keep the loading surface offscreen until the first portrait frame is ready.
  trackKeys(win.webContents);trackKeys(wc);
  for(const child of host.children)trackKeys(child.webContents);
  win.on('resize',resize);win.on('show',focus);win.on('focus',focus);win.once('closed',parentClosed);
  wc.setWindowOpenHandler(()=>({action:'deny'}));
  wc.setAudioMuted(!sound);
  wc.on('will-navigate',event=>event.preventDefault());
  wc.on('page-title-updated',(_event,title)=>{
   if(title.startsWith('CLAUDE_SPLASH_READY')&&!attached&&!closed){
    attached=true;originalAdd.call(host,view);fit();
    wc.executeJavaScript('window.__claudeBeginPlayback?.()').catch(()=>{onError();close('start-failed');});
   }
   else if(title.startsWith('CLAUDE_SPLASH_DONE')&&!finishing){
    finishing=true;
    wc.executeJavaScript("window.__claudeStopSound?.(0.7);document.documentElement.style.transition='opacity 700ms';document.documentElement.style.opacity='0'").catch(()=>{});
    const fade=setTimeout(()=>close('done'),720);fade.unref();
   }
   else if(title.startsWith('CLAUDE_SPLASH_PLAYING')){playing=true;focus();}
  });
  wc.once('render-process-gone',()=>{onError();close('renderer-failed');});
  timer=setTimeout(()=>close('timeout'),maxMs);timer.unref();
  wc.loadFile(path.join(assets,'splash','splash.html'),{query:{launcher:'',embedded:'',...(sound?{}:{mute:''})}}).catch(()=>{onError();close('load-failed');});
 }catch(error){close('attach-failed');throw error;}
 return {view,close,get closed(){return closed;}};
};
