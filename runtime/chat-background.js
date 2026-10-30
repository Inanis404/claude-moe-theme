'use strict';
function installClaudeChatBackground(poster, encodedVideo, suspended=false) {
  const SLOT='__claudeFixedBackground';
  if(window[SLOT]){window[SLOT].refresh();return true;}
  let source=null,frame=null,timer=null,active=null,scanCount=0;
  const scopes=new Map();
  const anchors='[data-chat-transcript],[data-epitaxy-transcript-region],[data-testid="chat-transcript"],[data-chat-input-container],[data-chat-dock],[contenteditable="true"][role="textbox"],main [contenteditable="true"],main textarea,[role="main"] textarea';
  const boundary='main,[role="main"],.epitaxy-root,.dframe-content-inner,.dframe-content';
  const excluded='aside,nav,header,[role="banner"],.dframe-sidebar,[role="dialog"],[data-artifact-viewer-mode],pre,code';
  const marked=new Set();
  function mediaSource(){
    if(source)return source;
    let bytes;
    if(Uint8Array.fromBase64)bytes=Uint8Array.fromBase64(encodedVideo);
    else {const binary=atob(encodedVideo);bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);}
    source=URL.createObjectURL(new Blob([bytes],{type:'video/mp4'}));encodedVideo=null;return source;
  }
  function updateTheme(){
    if(!active)return;
    const root=document.documentElement;
    const dark=root.classList.contains('dark')||root.getAttribute('data-mode')==='dark'||(root.getAttribute('data-mode')==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);
    active.wash.style.background=dark?'rgba(28,25,23,.74)':'rgba(250,248,244,.70)';
  }
  function geometry(){
    frame=null;if(!active)return;
    const {host,layer,video}=active,r=host.getBoundingClientRect(),doc=host.ownerDocument;
    const left=Math.max(0,r.left),top=Math.max(0,r.top),right=Math.min(doc.documentElement.clientWidth,r.right),bottom=Math.min(doc.documentElement.clientHeight,r.bottom);
    const width=Math.max(0,right-left),height=Math.max(0,bottom-top),visible=width>=240&&height>=160&&!doc.hidden;
    if(visible!==active.visible){active.visible=visible;layer.style.display=visible?'block':'none';}
    if(visible&&!suspended){if(video.paused)video.play().catch(()=>{});}else if(!video.paused)video.pause();
  }
  function scheduleGeometry(){if(!frame)frame=requestAnimationFrame(geometry);}
  function clearMarks(){for(const node of marked)node.removeAttribute('data-claude-background');marked.clear();}
  function mark(node,host){
    if(!node||!host.contains(node))return;
    for(let depth=0;node&&depth<28;node=node.parentElement,depth++){
      if(node.matches('html,body')||node.closest(excluded))break;
      node.setAttribute('data-claude-background','');marked.add(node);if(node===host)break;
    }
  }
  function removeLayer(){
    if(!active)return;const {host,video,layer,resize}=active;
    video.pause();video.removeAttribute('src');video.load();resize.disconnect();layer.remove();
    host.removeAttribute('data-claude-video-host');host.removeAttribute('data-claude-relative-host');active=null;clearMarks();
  }
  function addLayer(host){
    if(active?.host===host)return;
    removeLayer();
    const doc=host.ownerDocument,layer=doc.createElement('div'),video=doc.createElement('video'),wash=doc.createElement('div');
    layer.setAttribute('data-claude-video-layer','');layer.setAttribute('aria-hidden','true');layer.inert=true;
    host.setAttribute('data-claude-video-host','');
    if(getComputedStyle(host).position==='static')host.setAttribute('data-claude-relative-host','');
    video.setAttribute('data-claude-background-video','');video.muted=true;video.defaultMuted=true;video.loop=true;video.playsInline=true;
    video.preload='auto';video.controls=false;video.disablePictureInPicture=true;video.tabIndex=-1;video.poster=poster;video.src=mediaSource();
    // Anchor to the chat container itself. Viewport offsets are wrong when a
    // transformed/contained ancestor becomes the fixed-position containing block.
    Object.assign(layer.style,{position:'absolute',inset:'0',overflow:'hidden',pointerEvents:'none',zIndex:'-1',borderRadius:'inherit'});
    for(const node of [video,wash])Object.assign(node.style,{position:'absolute',inset:'0',width:'100%',height:'100%',pointerEvents:'none'});
    video.style.objectFit='cover';layer.append(video,wash);host.append(layer);
    const resize=new ResizeObserver(scheduleGeometry);resize.observe(host);
    active={host,layer,video,wash,resize};updateTheme();scheduleGeometry();
  }
  function relevant(node){return node.nodeType===1&&!node.closest('[data-claude-video-layer]')&&(node.matches(anchors+',iframe')||node.querySelector(anchors+',iframe'));}
  function discover(node){
    if(node.nodeType!==1&&node.nodeType!==9&&node.nodeType!==11)return;
    if(node.shadowRoot)addScope(node.shadowRoot);
    for(const child of node.querySelectorAll('*'))if(child.shadowRoot)addScope(child.shadowRoot);
    for(const iframe of node.querySelectorAll('iframe:not([sandbox])')){
      const connect=()=>{try{const doc=iframe.contentDocument;if(doc?.body&&doc.location.origin===location.origin&&/^\/(epitaxy|chat|code|new)(\/|$)/.test(doc.location.pathname))addScope(doc);}catch{}};
      connect();iframe.addEventListener('load',connect,{once:true});
    }
  }
  function addScope(scope){
    if(scopes.has(scope))return;
    const doc=scope.nodeType===9?scope:scope.ownerDocument;if(!doc.head||!doc.body)return;
    const style=doc.createElement('style');style.setAttribute('data-claude-background-style','');
    const nonce=doc.querySelector('style[nonce],script[nonce]')?.nonce;if(nonce)style.nonce=nonce;
    style.textContent='[data-claude-background]{background-color:transparent!important;background-image:none!important}[data-claude-video-host]{isolation:isolate!important}[data-claude-relative-host]{position:relative!important}[data-claude-video-layer]{pointer-events:none!important}';
    (scope.nodeType===9?doc.head:scope).appendChild(style);
    const observer=new MutationObserver(records=>{
      let dirty=active&&!active.host.isConnected;
      for(const record of records){
        if(record.target.nodeType===1&&record.target.closest('[data-claude-video-layer]'))continue;
        for(const node of record.addedNodes){if(relevant(node))dirty=true;if(node.nodeType===1&&!node.hasAttribute('data-claude-video-layer'))discover(node);}
        for(const node of record.removedNodes)if(relevant(node))dirty=true;
      }
      if(dirty)schedule();
    });
    observer.observe(scope.nodeType===9?doc.body:scope,{childList:true,subtree:true});scopes.set(scope,{style,observer});
    doc.addEventListener('scroll',scheduleGeometry,{capture:true,passive:true});doc.addEventListener('visibilitychange',scheduleGeometry);
    doc.defaultView.addEventListener('resize',()=>{schedule();scheduleGeometry();},{passive:true});
    discover(scope);schedule();
  }
  function refresh(){
    clearTimeout(timer);timer=null;scanCount++;
    const candidates=[];
    for(const scope of scopes.keys())for(const anchor of scope.querySelectorAll(anchors)){
      if(anchor.closest(excluded))continue;
      const host=anchor.closest(boundary);if(!host||host.closest(excluded))continue;
      const r=host.getBoundingClientRect();if(r.width<240||r.height<160)continue;
      candidates.push({anchor,host,area:r.width*r.height});
    }
    candidates.sort((a,b)=>b.area-a.area);
    if(!candidates.length){removeLayer();return;}
    const host=candidates[0].host;addLayer(host);clearMarks();mark(host,host);
    for(const {anchor} of candidates)if(host.contains(anchor)){
      const input=anchor.matches('[contenteditable],textarea,[data-chat-input-container],[data-chat-dock]');
      const start=input?(anchor.closest('[data-chat-input-container],[data-chat-dock],form')||anchor.parentElement)?.parentElement:anchor;
      mark(start,host);
    }
    scheduleGeometry();
  }
  function schedule(){if(!timer)timer=setTimeout(refresh,250);}
  addScope(document);
  new MutationObserver(updateTheme).observe(document.documentElement,{attributes:true,attributeFilter:['class','data-mode']});
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change',updateTheme);
  window.addEventListener('unload',()=>{active?.video.pause();if(source)URL.revokeObjectURL(source);},{once:true});
  window[SLOT]={refresh,setSuspended(value){suspended=Boolean(value);geometry();},stats(){
    const v=active?.video,r=active?.host.getBoundingClientRect(),b=active?.layer.getBoundingClientRect();return {players:active?1:0,scans:scanCount,suspended,
      host:active?{tag:active.host.tagName,classes:active.host.className,x:r.x,y:r.y,width:r.width,height:r.height}:null,
      layer:active?{x:b.x,y:b.y,width:b.width,height:b.height,maxEdgeError:Math.max(...['left','top','right','bottom'].map(k=>Math.abs(r[k]-b[k])))}:null,
      video:v?{width:v.videoWidth,height:v.videoHeight,time:v.currentTime,paused:v.paused,error:v.error?.code||null,...v.getVideoPlaybackQuality()}:null};
  }};refresh();return true;
}
