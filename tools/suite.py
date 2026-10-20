#!/usr/bin/env python3
"""Shared "suite" shell for Skyler's apps: Kitchen, Grocery, Lift, DishLog, Protocol, Rail.

One top bar, one set of app colors, one set of layout tokens. This script writes
the identical block into every app between <!-- suite:css --> ... <!-- /suite:css -->
and <!-- suite:bar --> ... <!-- /suite:bar --> markers, so a change made here lands
everywhere at once.

    python3 tools/suite.py ../kitchen ../daily_schedule ../the-rail

The first run places the markers (replacing each app's old .applinks nav); later
runs only replace what sits between them.
"""
import io, re, sys, os

SUITE_VERSION = "6"

APPS = [  # key, label, kitchen-repo file, svg body
    ("kitchen", "Kitchen", "index.html",
     '<path d="M4 11h13v4a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/><path d="M17 12.5h3M8 4.5c0 1.5 1.5 1.5 1.5 3M12 4.5c0 1.5 1.5 1.5 1.5 3"/>'),
    ("grocery", "Grocery", "grocery.html",
     '<path d="M3 4h2.2l2.2 11h10.4l2-7.5H6.4"/><circle cx="9.5" cy="19.5" r="1.4"/><circle cx="16.5" cy="19.5" r="1.4"/>'),
    ("lift", "Lift", "workout.html",
     '<path d="M6.5 7v10M17.5 7v10M4 9.5v5M20 9.5v5M6.5 12h11"/>'),
    ("dishlog", "DishLog", "dishlog.html",
     '<path d="M5 3v5a2 2 0 0 0 4 0V3M7 10v11M17 21V3c-2 0-3.5 2.5-3.5 6s1.5 4 3.5 4"/>'),
    ("protocol", "Protocol", None,
     '<rect x="4.5" y="3.5" width="15" height="17" rx="2.5"/><path d="M8 9l1.5 1.5L12 8M8 15l1.5 1.5L12 14M14.5 9.5H16M14.5 15.5H16"/>'),
    ("rail", "Rail", None,
     '<path d="M12 8.2V7.4c0-.5.3-.9.8-1.1.6-.3 1.2-.7 1.2-1.6a2 2 0 0 0-4 0"/><path d="M12 8.2 3.6 14.4c-.9.7-.5 2.1.7 2.1h15.4c1.2 0 1.6-1.4.7-2.1z"/><path d="M8 16.5v3.5h8v-3.5"/>'),
]
KITCHEN_BASE = "https://frostie4life9.github.io/kitchen/"
PROTOCOL_URL = "https://frostie4life9.github.io/daily_schedule/"
# The phone grid shows each app's real home-screen icon, so the menu looks
# like a little home screen. Kitchen-repo icons live in kitchen/icons/;
# Protocol's lives at the root of its own repo (keep its ?v= in step with
# the apple-touch-icon link in daily_schedule/index.html).
PROTOCOL_ICON = "apple-touch-icon.png?v=20261017p"
# The Rail (wardrobe) is its own repo too; its icons live in the-rail/icons/.
RAIL_URL = "https://frostie4life9.github.io/the-rail/"
RAIL_ICON = "icons/rail-180.png?v=1"


def icon_src(key, repo):
    if key == "protocol":
        return PROTOCOL_ICON if repo == "daily_schedule" else PROTOCOL_URL + PROTOCOL_ICON
    if key == "rail":
        return RAIL_ICON if repo == "the-rail" else RAIL_URL + RAIL_ICON
    rel = "icons/%s-180.png" % key
    return rel if repo == "kitchen" else KITCHEN_BASE + rel

CSS = """<!-- suite:css vVERSION · shared by Kitchen, Grocery, Lift, DishLog, Protocol, Rail — edit tools/suite.py in the kitchen repo, not here -->
<style id="suite-css">
/* App colors come from each app's home-screen icon, so the bar, the icon and
   the page all agree. The tab for every app carries its own color, so the
   whole set reads as one color-coded system wherever you are in it. */
.sx-bar{
  --sx-kitchen:#7A2E1E; --sx-grocery:#2D5840; --sx-lift:#A8522B; --sx-dishlog:#6A2347; --sx-protocol:#1E3550; --sx-rail:#3A2A63;
  --sx-on:#FFF8EF;
  --sx-paper:#FAF6F0; --sx-ink:#1F1A14; --sx-dim:#7D7262; --sx-line:#DDD3C2; --sx-hover:#EFE7DA;
}
@media (prefers-color-scheme:dark){ .sx-bar:not(.sx-light){
  --sx-kitchen:#E8987C; --sx-grocery:#7CC39A; --sx-lift:#EE9C66; --sx-dishlog:#DD8DB2; --sx-protocol:#5FE6B0; --sx-rail:#B9A6F2;
  --sx-on:#15120E;
  --sx-paper:#17140F; --sx-ink:#F1EADF; --sx-dim:#A0947F; --sx-line:#3B342B; --sx-hover:#2A251E;
}}
.sx-bar.sx-dark{
  --sx-kitchen:#E8987C; --sx-grocery:#7CC39A; --sx-lift:#EE9C66; --sx-dishlog:#DD8DB2; --sx-protocol:#5FE6B0; --sx-rail:#B9A6F2;
  --sx-on:#15120E;
}
/* layout tokens every app's own layout lines up with. No width cap: on a
   computer the apps use the whole window; each app decides how many columns. */
:root{ --sx-max:100000px; --sx-gut:clamp(16px,2vw,40px); --sx-barh:56px; }

.sx-bar{position:relative;z-index:40;background:var(--sx-paper);border-bottom:1px solid var(--sx-line);
  font-family:'Manrope',system-ui,-apple-system,'Segoe UI',sans-serif;-webkit-font-smoothing:antialiased;color:var(--sx-ink)}
.sx-in{max-width:var(--sx-max);margin:0 auto;box-sizing:border-box;min-height:52px;
  padding:calc(8px + env(safe-area-inset-top,0px)) var(--sx-gut) 8px;display:flex;align-items:center;gap:18px}
.sx-id{display:flex;align-items:center;gap:10px;flex:0 1 auto;min-width:0}
.sx-tile{width:32px;height:32px;border-radius:7.5px;display:block;background:var(--app);flex:0 0 auto;
  box-shadow:0 0 0 .5px rgba(0,0,0,.12),0 2px 6px -2px rgba(0,0,0,.3)}
.sx-name{font-family:'Fraunces',Georgia,serif;font-style:italic;font-weight:600;font-size:21px;letter-spacing:-.01em;line-height:1;color:var(--sx-ink);white-space:nowrap}
.sx-t svg,.sx-gbtn svg{fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}

/* phone: app name on the left, the grid button on the right */
.sx-gbtn{margin-left:auto;flex:0 0 auto;width:40px;height:40px;border-radius:12px;border:1px solid var(--sx-line);background:transparent;
  color:var(--sx-dim);display:grid;place-items:center;cursor:pointer;padding:0;-webkit-tap-highlight-color:transparent;transition:background .15s,color .15s,scale .22s var(--sx-spring)}
.sx-gbtn svg{width:19px;height:19px}
.sx-gbtn[aria-expanded="true"]{background:var(--sx-hover);color:var(--sx-ink)}
.sx-menu{position:fixed;inset:0;z-index:300}
.sx-menu[hidden]{display:none}
.sx-pop{position:absolute;top:calc(56px + env(safe-area-inset-top,0px));right:var(--sx-gut);width:min(300px,calc(100vw - 2 * var(--sx-gut)));
  box-sizing:border-box;padding:10px;border-radius:22px;background:var(--sx-paper);border:1px solid var(--sx-line);
  box-shadow:0 24px 60px -18px rgba(0,0,0,.45);display:grid;grid-template-columns:repeat(3,1fr);gap:4px;
  transform-origin:top right;animation:sx-pop .2s cubic-bezier(.2,.9,.3,1.2)}
@keyframes sx-pop{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:none}}
.sx-cell{display:flex;flex-direction:column;align-items:center;gap:7px;padding:12px 4px 10px;border-radius:16px;text-decoration:none;
  color:var(--sx-ink);font:700 12px/1.1 'Manrope',system-ui,sans-serif;-webkit-tap-highlight-color:transparent}
.sx-cell img{width:54px;height:54px;border-radius:12.5px;display:block;background:var(--c);
  box-shadow:0 0 0 .5px rgba(0,0,0,.12),0 3px 8px -3px rgba(0,0,0,.35)}
.sx-cell:active{background:var(--sx-hover)}
.sx-cell[aria-current="page"]{background:var(--sx-hover)}
.sx-cell[aria-current="page"] b{color:var(--sx-dim);font-weight:700}
.sx-cell b{font-weight:700}
.sx-tabs{display:none}
@media (prefers-reduced-motion:reduce){.sx-pop{animation:none}}

/* computer and tablet: the full bar of tabs */
.sx-t{flex:0 0 auto;display:inline-flex;align-items:center;gap:7px;height:36px;padding:0 14px 0 11px;box-sizing:border-box;
  border-radius:999px;border:1px solid transparent;background:transparent;color:var(--sx-dim);text-decoration:none;
  font:700 12.5px/1 'Manrope',system-ui,sans-serif;letter-spacing:.02em;white-space:nowrap;transition:background .15s,color .15s,border-color .15s,scale .22s var(--sx-spring)}
.sx-t svg{width:16px;height:16px;color:var(--c);flex:0 0 auto}
.sx-t:hover{background:var(--sx-hover);color:var(--sx-ink)}
.sx-t:focus-visible,.sx-gbtn:focus-visible,.sx-cell:focus-visible{outline:2px solid var(--app);outline-offset:2px}
.sx-t[aria-current="page"]{background:var(--c);border-color:var(--c);color:var(--sx-on)}
.sx-t[aria-current="page"] svg{color:inherit}
@media (min-width:900px){
  .sx-bar{position:sticky;top:0;z-index:70;background:color-mix(in srgb,var(--sx-paper) 88%,transparent);
    -webkit-backdrop-filter:saturate(1.4) blur(14px);backdrop-filter:saturate(1.4) blur(14px)}
  .sx-in{min-height:var(--sx-barh)}
  .sx-tabs{display:flex;gap:6px;margin-left:auto;flex:0 1 auto;min-width:0}
  .sx-gbtn,.sx-menu{display:none!important}
}
@media print{.sx-bar{display:none}}

/* Moving between apps: they all live on frostie4life9.github.io, so the
   browser can cross-fade one page into the next instead of cutting. The bar
   is its own layer, so it holds still and just changes color and name,
   while the page underneath settles in. Safari 18.2+ and Chrome; anything
   older just navigates as before. */
@view-transition{navigation:auto}
.sx-bar{view-transition-name:sx-bar}
::view-transition-group(sx-bar){animation-duration:.4s;animation-timing-function:cubic-bezier(.2,.8,.2,1)}
::view-transition-old(root){animation:sx-leave .2s ease-in both}
::view-transition-new(root){animation:sx-arrive .42s cubic-bezier(.2,.8,.2,1) .06s both}
@keyframes sx-leave{to{opacity:0;transform:scale(.985)}}
@keyframes sx-arrive{from{opacity:0;transform:translateY(14px)}}
@media (prefers-reduced-motion:reduce){
  ::view-transition-group(*),::view-transition-old(*),::view-transition-new(*){animation:none!important}
}

/* ---- motion: one feel across every app ----
   Shared curves, a soft press under the finger on anything tappable, and
   colors that ease instead of flipping. Everything here has zero
   specificity (:where), so any app rule that says otherwise wins. The press
   uses the separate `scale` property, so it stacks with whatever transform
   an element already has instead of fighting it. */
:root{ --sx-ease:cubic-bezier(.2,.8,.2,1); --sx-ease-in:cubic-bezier(.4,0,.9,.5); --sx-spring:cubic-bezier(.3,1.35,.5,1); }
:where(button,[role=button],[role=tab],[role=checkbox],summary,select,a.sx-t,.sx-cell,.sx-gbtn){
  transition:background-color .18s var(--sx-ease),color .18s var(--sx-ease),border-color .18s var(--sx-ease),
             box-shadow .22s var(--sx-ease),opacity .2s var(--sx-ease),scale .22s var(--sx-spring)}
:where(button:not(:disabled),[role=button],[role=tab],summary,a.sx-t,.sx-cell,.sx-gbtn):active{scale:.96;transition-duration:.06s}
:where(input,textarea,select){transition:border-color .18s var(--sx-ease),background-color .18s var(--sx-ease),box-shadow .2s var(--sx-ease)}
/* the sliding highlight behind segmented controls and tab rows (SX.pill) */
.sx-pill{position:absolute;left:0;top:0;z-index:0;pointer-events:none;border-radius:10px;will-change:transform,width}
.sx-pilled > :not(.sx-pill){position:relative;z-index:1}
.sx-menu.sx-out .sx-pop{animation:sx-pop-out .14s var(--sx-ease-in) both}
@keyframes sx-pop-out{to{opacity:0;transform:scale(.94)}}
@media (prefers-reduced-motion:reduce){
  :where(*){scale:none!important}
  .sx-menu.sx-out .sx-pop{animation:none}
}
</style>
<!-- /suite:css -->"""


GRID_ICON = '<rect x="4" y="4" width="6" height="6" rx="1.6"/><rect x="14" y="4" width="6" height="6" rx="1.6"/><rect x="4" y="14" width="6" height="6" rx="1.6"/><rect x="14" y="14" width="6" height="6" rx="1.6"/>'

MENU_JS = """<script>
(function(){ /* suite: open/close the app grid on phones */
  var b=document.getElementById('sx-gbtn'), m=document.getElementById('sx-menu'); if(!b||!m) return;
  var t=null;
  function set(o){ b.setAttribute('aria-expanded',o?'true':'false'); clearTimeout(t); m.classList.remove('sx-out');
    if(o){ m.hidden=false; var f=m.querySelector('.sx-cell'); if(f) f.focus({preventScroll:true}); return; }
    if(m.hidden) return;
    /* let the grid shrink away instead of vanishing */
    if(window.SX && !SX.still()){ m.classList.add('sx-out'); t=setTimeout(function(){ m.hidden=true; m.classList.remove('sx-out'); },140); }
    else m.hidden=true; }
  /* a grid that is on its way out counts as closed, so tapping the button
     again mid-close reopens it rather than closing it a second time */
  function shut(){ return m.hidden || m.classList.contains('sx-out'); }
  b.addEventListener('click',function(e){ e.stopPropagation(); set(shut()); });
  m.addEventListener('click',function(e){ if(!e.target.closest('.sx-cell')||e.target.closest('[aria-current]')) set(false); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&!shut()){ set(false); b.focus(); } });
  window.addEventListener('pageshow',function(){ clearTimeout(t); m.classList.remove('sx-out'); m.hidden=true; b.setAttribute('aria-expanded','false'); });
})();
</script>"""

MOTION_JS = """<script>
/* suite motion helpers (window.SX), shared by every app. Each one is a
   no-op extra: if the browser can't animate or you've asked for reduced
   motion, the change just happens, exactly as it did before.
     SX.flip(root, sel, change)  redraw a list and let the items that stay
                                 glide to their new spots; new ones fade in
     SX.enter(root, sel, dir)    play a short staggered entrance on fresh content
     SX.pill(row, activeSel)     slide a highlight to the selected tab/chip
     SX.expand(el, open, apply)  open or close a block by its height
     SX.morph(root, sel, prop, change)  bars and meters ease to their new size
     SX.bump(el)                 a small pop for a value that just changed */
(function(){
  if(window.SX) return;
  var mq=window.matchMedia?matchMedia('(prefers-reduced-motion: reduce)'):null;
  var E='cubic-bezier(.2,.8,.2,1)', SPRING='cubic-bezier(.3,1.25,.5,1)';
  function still(){ return !!(mq&&mq.matches) || typeof Element.prototype.animate!=='function'; }
  function q(x){ return typeof x==='string'?document.querySelector(x):x; }
  function keyOf(el,kf){ return kf?kf(el):(el.getAttribute('data-sx-key')||el.getAttribute('data-id')||el.getAttribute('data-k')||el.id||null); }
  function quietCss(el){ /* a redraw should not replay an entrance the item already did */
    try{ el.getAnimations({subtree:true}).forEach(function(a){ if(a.animationName) a.cancel(); }); }catch(e){} }

  function flip(root,sel,change,o){
    o=o||{}; root=q(root);
    if(!root || still()){ change(); return; }
    var before={}, vh=window.innerHeight;
    root.querySelectorAll(sel).forEach(function(el){
      var k=keyOf(el,o.key); if(k==null || before[k]) return;
      var r=el.getBoundingClientRect(); if(!r.width && !r.height) return;
      before[k]=r;
    });
    change();
    var seen={}, n=0;
    root.querySelectorAll(sel).forEach(function(el){
      var k=keyOf(el,o.key); if(k==null || seen[k]) return; seen[k]=1;
      var b=before[k], r=el.getBoundingClientRect();
      if(!r.width && !r.height) return;
      if(r.bottom<-40 || r.top>vh+40){ if(b) quietCss(el); return; }
      if(b){
        quietCss(el);
        var dx=b.left-r.left, dy=b.top-r.top;
        if(Math.abs(dx)<1 && Math.abs(dy)<1) return;
        if(Math.abs(dy)>vh) dy=dy>0?vh*.5:-vh*.5;
        el.animate([{translate:dx+'px '+dy+'px'},{translate:'0 0'}],{duration:o.dur||340,easing:E});
      } else if(o.enter!==false){
        quietCss(el);
        el.animate([{opacity:0,translate:'0 6px',scale:.985},{opacity:1,translate:'0 0',scale:1}],
                   {duration:260,delay:Math.min(n++,8)*24,easing:E,fill:'backwards'});
      }
    });
  }

  function enter(root,sel,dir,o){
    o=o||{}; root=q(root); if(!root || still()) return;
    var els=sel?root.querySelectorAll(sel):root.children, vh=window.innerHeight, i=0;
    var from=dir==='left'?'-18px 0':dir==='right'?'18px 0':dir==='none'?'0 0':'0 8px';
    Array.prototype.forEach.call(els,function(el){
      if(el.classList && el.classList.contains('sx-pill')) return;
      var r=el.getBoundingClientRect(); if(r.bottom<0 || r.top>vh || !r.height) return;
      quietCss(el);
      el.animate([{opacity:0,translate:from},{opacity:1,translate:'0 0'}],
                 {duration:o.dur||300,delay:Math.min(i++,10)*(o.step==null?30:o.step),easing:E,fill:'backwards'});
    });
  }

  var rows=[];
  function pill(row,activeSel,o){
    row=q(row); if(!row) return;
    var rec=null; rows.forEach(function(x){ if(x.row===row) rec=x; });
    if(!rec){ rec={row:row, sel:activeSel, last:null, o:o||{}}; rows.push(rec); watch(rec); }
    rec.sel=activeSel||rec.sel; place(rec,true);
  }
  function place(rec,animate){
    var row=rec.row, p=row.querySelector(':scope > .sx-pill');
    if(!p){ p=document.createElement('span'); p.className='sx-pill'+(rec.o.cls?' '+rec.o.cls:''); p.setAttribute('aria-hidden','true'); row.insertBefore(p,row.firstChild); }
    if(!row.classList.contains('sx-pilled')){ row.classList.add('sx-pilled');
      if(getComputedStyle(row).position==='static') row.style.position='relative'; }
    var a=row.querySelector(rec.sel);
    if(!a || !a.offsetWidth){ p.style.opacity='0'; rec.last=null; return; }
    var now={x:a.offsetLeft, y:a.offsetTop, w:a.offsetWidth, h:a.offsetHeight}, last=rec.last;
    rec.last=now;
    p.style.opacity='1'; p.style.width=now.w+'px'; p.style.height=now.h+'px';
    p.style.transform='translate('+now.x+'px,'+now.y+'px)';
    if(animate && last && !still() && (last.x!==now.x || last.y!==now.y || last.w!==now.w)){
      p.animate([{transform:'translate('+last.x+'px,'+last.y+'px)',width:last.w+'px',height:last.h+'px'},
                 {transform:'translate('+now.x+'px,'+now.y+'px)',width:now.w+'px',height:now.h+'px'}],
                {duration:360,easing:SPRING});
    }
  }
  function watch(rec){ if(window.ResizeObserver){ new ResizeObserver(function(){ place(rec,false); }).observe(rec.row); } }
  window.addEventListener('resize',function(){ rows.forEach(function(r){ place(r,false); }); });

  function expand(el,open,apply){
    el=q(el); if(!el){ apply(open); return; }
    if(el._sx){ el._sx.cancel(); el._sx=null; }
    if(still()){ apply(open); return; }
    var cs, h, f, a;
    if(open){
      apply(true); cs=getComputedStyle(el); h=el.offsetHeight; if(!h) return;
      f={height:h+'px',paddingTop:cs.paddingTop,paddingBottom:cs.paddingBottom,marginTop:cs.marginTop,marginBottom:cs.marginBottom,opacity:1};
      el.style.overflow='hidden';
      a=el.animate([{height:'0px',paddingTop:'0px',paddingBottom:'0px',marginTop:'0px',marginBottom:'0px',opacity:0},f],{duration:300,easing:E});
    } else {
      cs=getComputedStyle(el); h=el.offsetHeight; if(!h){ apply(false); return; }
      f={height:h+'px',paddingTop:cs.paddingTop,paddingBottom:cs.paddingBottom,marginTop:cs.marginTop,marginBottom:cs.marginBottom,opacity:1};
      el.style.overflow='hidden';
      a=el.animate([f,{height:'0px',paddingTop:'0px',paddingBottom:'0px',marginTop:'0px',marginBottom:'0px',opacity:0}],{duration:240,easing:E});
    }
    el._sx=a;
    a.onfinish=function(){ el._sx=null; el.style.overflow=''; if(!open) apply(false); };
    a.oncancel=function(){ el.style.overflow=''; };
  }

  /* redraw something whose bars or meters are set inline (width:40%), and
     let each one ease from where it was instead of snapping */
  function morph(host,sel,prop,change){
    host=q(host); if(!host){ change(); return; }
    var old=Array.prototype.map.call(host.querySelectorAll(sel),function(e){ return e.style[prop]; });
    change();
    if(still()) return;
    var now=host.querySelectorAll(sel), to=Array.prototype.map.call(now,function(e){ return e.style[prop]; });
    Array.prototype.forEach.call(now,function(e,i){ if(old[i]===to[i]) return; e.style.transition='none'; e.style[prop]=old[i]!=null&&old[i]!==''?old[i]:'0'; });
    void host.offsetWidth;
    Array.prototype.forEach.call(now,function(e,i){ e.style.transition=''; e.style[prop]=to[i]; });
  }

  function bump(el){
    el=q(el); if(!el || still()) return;
    el.animate([{scale:1},{scale:1.08},{scale:1}],{duration:320,easing:SPRING});
  }

  /* <details> sections open and close by height instead of snapping.
     The toggle still happens for real, so anything listening for it works. */
  document.addEventListener('click',function(e){
    var sm=e.target.closest && e.target.closest('summary'); if(!sm || e.defaultPrevented) return;
    var d=sm.parentElement; if(!d || d.tagName!=='DETAILS' || d.hasAttribute('data-sx-still') || still()) return;
    e.preventDefault();
    if(d._sx){ d._sx.cancel(); d._sx=null; }
    var from=d.offsetHeight, opening=!d.open, to;
    d.style.overflow='hidden';
    if(opening){ d.open=true; to=d.offsetHeight; }
    else { d.open=false; to=d.offsetHeight; d.open=true; }
    var a=d.animate([{height:from+'px'},{height:to+'px'}],{duration:opening?320:240,easing:E});
    d._sx=a;
    a.onfinish=function(){ d._sx=null; d.style.overflow=''; if(!opening) d.open=false; };
    a.oncancel=function(){ d.style.overflow=''; };
    if(opening){ Array.prototype.forEach.call(d.children,function(c){ if(c!==sm) c.animate([{opacity:0},{opacity:1}],{duration:260,delay:60,easing:E,fill:'backwards'}); }); }
  });

  window.SX={still:still, flip:flip, enter:enter, pill:pill, expand:expand, morph:morph, bump:bump};
})();
</script>"""


def bar(here, repo):
    tabs, cells = [], []
    cur = None
    for key, label, fname, svg in APPS:
        if key == "protocol":
            href = "./" if repo == "daily_schedule" else PROTOCOL_URL
        elif key == "rail":
            href = "./" if repo == "the-rail" else RAIL_URL
        else:
            href = fname if repo == "kitchen" else KITCHEN_BASE + fname
        attr = ' aria-current="page"' if key == here else ""
        if key == here:
            cur = (label, svg)
        tabs.append('<a class="sx-t" style="--c:var(--sx-%s)" href="%s"%s><svg viewBox="0 0 24 24" aria-hidden="true">%s</svg>%s</a>'
                    % (key, href, attr, svg, label))
        cells.append('<a class="sx-cell" style="--c:var(--sx-%s)" href="%s"%s><img src="%s" alt="" width="54" height="54" decoding="async"><b>%s</b></a>'
                     % (key, href, attr, icon_src(key, repo), label))
    extra = " sx-dark" if here == "protocol" else ""
    return ('<!-- suite:bar -->\n<nav class="sx-bar%s" style="--app:var(--sx-%s)" aria-label="Your apps"><div class="sx-in">\n'
            '  <div class="sx-id"><img class="sx-tile" src="%s" alt="" width="32" height="32"><span class="sx-name">%s</span></div>\n'
            '  <div class="sx-tabs">\n    %s\n  </div>\n'
            '  <button class="sx-gbtn" id="sx-gbtn" type="button" aria-label="Your apps" aria-haspopup="true" aria-expanded="false" aria-controls="sx-menu">'
            '<svg viewBox="0 0 24 24" aria-hidden="true">%s</svg></button>\n'
            '</div>\n<div class="sx-menu" id="sx-menu" hidden><div class="sx-pop">\n    %s\n</div></div>\n</nav>\n%s\n<!-- /suite:bar -->'
            % (extra, here, icon_src(here, repo), cur[0], "\n    ".join(tabs), GRID_ICON, "\n    ".join(cells), MENU_JS + "\n" + MOTION_JS))


TARGETS = {  # (repo, file) -> app key
    ("kitchen", "index.html"): "kitchen",
    ("kitchen", "grocery.html"): "grocery",
    ("kitchen", "workout.html"): "lift",
    ("kitchen", "dishlog.html"): "dishlog",
    ("daily_schedule", "index.html"): "protocol",
    ("the-rail", "index.html"): "rail",
}


def apply(path, repo, here):
    with io.open(path, encoding="utf-8") as f:
        s = f.read()
    css = CSS.replace("VERSION", SUITE_VERSION)
    b = bar(here, repo)
    # CSS: replace between markers, or insert just before </head>
    if "<!-- suite:css" in s:
        s = re.sub(r"<!-- suite:css.*?<!-- /suite:css -->", lambda m: css, s, flags=re.S)
    else:
        i = s.index("</head>")
        s = s[:i] + css + "\n" + s[i:]
    # bar: replace between markers, or place as the first thing in <body>
    if "<!-- suite:bar -->" in s:
        s = re.sub(r"<!-- suite:bar -->.*?<!-- /suite:bar -->", lambda m: b, s, flags=re.S)
    else:
        s = re.sub(r'\s*<nav class="applinks"[^>]*>.*?</nav>\n?', "\n", s, count=1, flags=re.S)
        m = re.search(r"<body[^>]*>", s)
        s = s[:m.end()] + "\n" + b + "\n" + s[m.end():]
    # the old per-app switcher styles are dead once the bar is in
    s = re.sub(r"[ \t]*\.applinks[^{}]*\{[^{}]*\}[ \t]*\n?", "", s)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(s)


if __name__ == "__main__":
    roots = sys.argv[1:] or ["."]
    for root in roots:
        repo = os.path.basename(os.path.abspath(root))
        for (r, fn), key in TARGETS.items():
            if r == repo and os.path.exists(os.path.join(root, fn)):
                apply(os.path.join(root, fn), repo, key)
                print("suite v%s ->" % SUITE_VERSION, repo + "/" + fn)
