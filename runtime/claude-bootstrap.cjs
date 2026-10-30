'use strict';
// Startup animation and a fixed chat background; native chat controls remain intact.
const {app,BrowserWindow,nativeImage}=require('electron');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const selfTest=process.argv.includes('--claude-splash-self-test');
const testRoot=selfTest?fs.mkdtempSync(path.join(os.tmpdir(),'claude-splash-test-')):null;
if(selfTest)app.setPath('userData',path.join(testRoot,'profile'));
const assets=path.join(process.resourcesPath,'atelier');
const background=require('./chat-background.cjs')(app,assets,{selfTest});
const icon=nativeImage.createFromPath(path.join(assets,'splash','assets','icon.png'));
let quitting=false,startupCover=null,splashUsed=false;
function diagnostic(code){
 try{
  const file=path.join(app.getPath('appData'),'claude-atelier','status.json');
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o700});
  fs.writeFileSync(file,JSON.stringify({name:'Claude',mode:'splash-and-background',code}),{mode:0o600});
 }catch{}
}
app.on('browser-window-created',(_event,win)=>{
 if(!icon.isEmpty()){
  win.setIcon(icon);
  win.once('ready-to-show',()=>{if(!win.isDestroyed())win.setIcon(icon);});
 }
 if(selfTest||splashUsed||quitting||!app.hasSingleInstanceLock()||win.getParentWindow())return;
 const [width,height]=win.getSize();if(width<500||height<350)return;
 splashUsed=true;
 try{
  background.setSuspended(true);
  startupCover=require('./startup-cover.cjs')(win,{assets,sound:true,
   onError:()=>diagnostic('splash_unavailable'),
   onClose:()=>{startupCover=null;background.setSuspended(false);diagnostic('splash_finished');}});
  diagnostic('splash_attached');
 }catch{background.setSuspended(false);diagnostic('splash_unavailable');}
});
app.on('before-quit',()=>{quitting=true;startupCover?.close('quit');startupCover=null;});
if(selfTest)app.whenReady().then(()=>require('./splash-self-test.cjs')({app,BrowserWindow,assets,testRoot}));
else require('./.vite/build/index.pre.js');
