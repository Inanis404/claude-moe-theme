'use strict';
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
module.exports=function attachChatBackground(app,assets,{selfTest=false}={}){
 const {BrowserWindow}=require('electron');let suspended=false;const tracked=new Set(),reports={};
 const script=fs.readFileSync(path.join(assets,'chat-background.js'),'utf8');
 const image='data:image/jpeg;base64,'+fs.readFileSync(path.join(assets,'chat-background.jpg')).toString('base64');
 const video=fs.readFileSync(path.join(assets,'chat-background.mp4')).toString('base64');
 const fixture=pathToFileURL(path.join(assets,'selftest.html')).href;
 function eligible(value){
  if(selfTest)return value===fixture;
  try{const u=new URL(value);if(u.username||u.password)return false;
   if(u.protocol==='app:'&&u.hostname==='localhost')return !/^\/(artifacts?|preview|oauth|login|auth)(\/|$)/i.test(u.pathname);
   return u.protocol==='https:'&&u.hostname==='claude.ai'&&(!u.port||u.port==='443')&&/^\/(?:$|new(?:\/|$)|chat(?:\/|$)|epitaxy(?:\/|$)|code(?:\/|$)|cowork(?:\/|$)|recents(?:\/|$)|tasks(?:\/|$))/.test(u.pathname);
  }catch{return false;}
 }
 app.on('web-contents-created',(_event,wc)=>{
  tracked.add(wc);wc.once('destroyed',()=>tracked.delete(wc));
  let busy=false;
  async function install(){
   if(busy||wc.isDestroyed()||!eligible(wc.getURL()))return;busy=true;
   try{
    const installed=await wc.executeJavaScriptInIsolatedWorld(24602,[{code:'Boolean(window.__claudeFixedBackground&&(window.__claudeFixedBackground.refresh(),true))'}]);
    if(!installed&&!wc.isDestroyed())await wc.executeJavaScriptInIsolatedWorld(24602,[{code:script+'\ninstallClaudeChatBackground('+JSON.stringify(image)+','+JSON.stringify(video)+','+suspended+');'}]);
    if(process.env.CLAUDE_BACKGROUND_DIAGNOSTICS==='1')for(const delay of [3000,12000])setTimeout(async()=>{
      try{if(wc.isDestroyed()||!eligible(wc.getURL()))return;
       reports[wc.id]={origin:new URL(wc.getURL()).origin,...await wc.executeJavaScriptInIsolatedWorld(24602,[{code:'window.__claudeFixedBackground?.stats()'}])};
       const file=path.join(app.getPath('appData'),'claude-atelier','background-diagnostics.json');fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(reports,null,2));
      }catch{}
    },delay).unref();
   }catch{}finally{busy=false;}
  }
  wc.on('dom-ready',install);wc.on('did-finish-load',install);wc.on('did-navigate-in-page',install);
 });
 function update(){
  const visible=BrowserWindow.getAllWindows().some(w=>w.isVisible()&&!w.isMinimized()&&w.getSize()[0]>=500);
  const pause=suspended||!visible;
  for(const wc of tracked)if(!wc.isDestroyed()&&eligible(wc.getURL()))wc.executeJavaScriptInIsolatedWorld(24602,[{code:'window.__claudeFixedBackground?.setSuspended('+pause+')'}]).catch(()=>{});
 }
 app.on('browser-window-created',(_event,win)=>{for(const event of ['minimize','restore','show','hide','closed'])win.on(event,()=>setImmediate(update));});
 return {setSuspended(value){suspended=Boolean(value);update();}};
};
