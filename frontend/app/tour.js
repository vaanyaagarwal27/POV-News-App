// First-time guide: three tip bubbles, one at a time.
// Reads the page through data-tour markers and never touches app state; the only thing it does
// on the app's behalf is click the real "Open the story" button so the story-screen steps can show.
(function () {
  var KEY = 'pov.tour.done';
  var STEPS = [
    { key: 'open',   text: 'Tap “Open the story” to read the full story.' },
    { key: 'listen', text: 'Tap Listen to hear this story read aloud.' },
    { key: 'differ', text: 'Tap here to see where the papers disagree.' },
  ];

  // localStorage can throw (private mode, blocked storage): the guide then just shows on every visit
  function seen() { try { return localStorage.getItem(KEY) === '1'; } catch (e) { return false; } }
  function remember() { try { localStorage.setItem(KEY, '1'); } catch (e) {} }
  function reduced() { return !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches); }

  var forced = /[?&]tour=1(&|$)/.test(location.search);
  if (!forced && seen()) return;

  var CSS = [
    '@keyframes povTourIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}',
    '@keyframes povTourPulse{0%{box-shadow:0 0 0 0 rgba(140,59,72,.55)}70%,100%{box-shadow:0 0 0 14px rgba(140,59,72,0)}}',
    '.pov-tour{position:fixed;inset:0;z-index:1000;pointer-events:none;visibility:hidden}',
    '.pov-tour-dot{position:fixed;left:0;top:0;width:14px;height:14px;margin:-7px 0 0 -7px;box-sizing:border-box;border-radius:50%;background:#8C3B48;border:2px solid #fff;animation:povTourPulse 1.6s ease-out infinite}',
    '.pov-tour-bubble{position:fixed;left:0;top:0;pointer-events:auto;-webkit-tap-highlight-color:transparent}',
    '.pov-tour-card{box-sizing:border-box;padding:14px 8px 4px 18px;border-radius:22px;background:rgba(255,255,255,.45);backdrop-filter:blur(20px) saturate(180%);-webkit-backdrop-filter:blur(20px) saturate(180%);border:1px solid rgba(255,255,255,.65);box-shadow:inset 0 1px 0 rgba(255,255,255,.7),0 6px 18px rgba(0,0,0,.14);animation:povTourIn .28s ease both}',
    '.pov-tour-text{margin:0 10px 2px 0;font:500 14.5px/1.4 "DM Sans",system-ui,sans-serif;color:#101010}',
    '.pov-tour-row{display:flex;align-items:center;gap:4px}',
    '.pov-tour-dots{flex:1;display:flex;align-items:center;gap:6px}',
    '.pov-tour-dots i{display:block;width:6px;height:6px;border-radius:3px;background:rgba(0,0,0,.22);transition:width .2s ease,background .2s ease}',
    '.pov-tour-dots i.on{width:16px;background:#101010}',
    '.pov-tour button{box-sizing:border-box;min-height:44px;border:0;font:500 12px "IBM Plex Mono",monospace;cursor:pointer;touch-action:manipulation;-webkit-tap-highlight-color:transparent}',
    '.pov-tour button:focus-visible{outline:2px solid #8C3B48;outline-offset:2px}',
    '.pov-tour-skip{padding:0 14px;background:transparent;color:rgba(0,0,0,.6)}',
    '.pov-tour-next{min-width:76px;padding:0 20px;border-radius:22px;background:#101010;color:#fff;margin-bottom:6px;min-height:44px}',
    '.pov-tour-next:active{background:#8C3B48}',
    '@media (prefers-reduced-motion: reduce){',
    '.pov-tour-card,.pov-tour-dot{animation:none !important}',
    '.pov-tour-dot{box-shadow:0 0 0 5px rgba(140,59,72,.25)}',
    '.pov-tour-dots i{transition:none}',
    '}',
  ].join('\n');

  var root, dot, bubble, card, textEl, dotsEl, nextBtn, skipBtn;
  var active = false, visible = false, idx = 0, shown = 0, raf = 0, waitToken = 0, busy = false;

  // the feed keeps a second, non-interactive "peeking" card behind the front one: ignore anything with pointer-events:none
  function candidates(key) {
    var out = [], list = document.querySelectorAll('[data-tour="' + key + '"]');
    for (var i = 0; i < list.length; i++) {
      var r = list[i].getBoundingClientRect();
      if (r.width >= 8 && r.height >= 8 && getComputedStyle(list[i]).pointerEvents !== 'none') out.push(list[i]);
    }
    return out;
  }

  // fully inside the window and actually the thing under its own centre (not clipped by a scroller or covered)
  function usable(el) {
    var r = el.getBoundingClientRect();
    if (r.top < 0 || r.left < 0 || r.bottom > window.innerHeight || r.right > window.innerWidth) return false;
    if (!document.elementsFromPoint) return true;
    var hit = document.elementsFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return hit.some(function (n) { return n === el || el.contains(n); });
  }

  // resolves with the element once it is on screen (scrolling it into view once if needed), or null after ~1.5s
  function waitFor(step, cb) {
    var token = ++waitToken, tries = 0, scrolled = false;
    (function poll() {
      if (token !== waitToken || !active) return;
      var list = candidates(step.key), on = null;
      for (var i = 0; i < list.length && !on; i++) if (usable(list[i])) on = list[i];
      if (on) return cb(on);
      if (list.length && !scrolled) {
        scrolled = true;
        list[0].scrollIntoView({ block: 'center', behavior: reduced() ? 'auto' : 'smooth' });
      }
      if (++tries > 15) return cb(null);
      setTimeout(poll, 100);
    })();
  }

  function build() {
    var sty = document.createElement('style');
    sty.textContent = CSS;
    document.head.appendChild(sty);
    root = document.createElement('div');
    root.className = 'pov-tour';
    root.innerHTML = '<div class="pov-tour-dot"></div>'
      + '<div class="pov-tour-bubble" role="dialog" aria-label="Quick guide"><div class="pov-tour-card">'
      + '<p class="pov-tour-text" aria-live="polite"></p>'
      + '<div class="pov-tour-row"><div class="pov-tour-dots" role="img"></div>'
      + '<button type="button" class="pov-tour-skip">Skip</button>'
      + '<button type="button" class="pov-tour-next">Next</button></div></div></div>';
    dot = root.querySelector('.pov-tour-dot');
    bubble = root.querySelector('.pov-tour-bubble');
    card = root.querySelector('.pov-tour-card');
    textEl = root.querySelector('.pov-tour-text');
    dotsEl = root.querySelector('.pov-tour-dots');
    skipBtn = root.querySelector('.pov-tour-skip');
    nextBtn = root.querySelector('.pov-tour-next');
    STEPS.forEach(function () { dotsEl.appendChild(document.createElement('i')); });
    skipBtn.addEventListener('click', finish);
    nextBtn.addEventListener('click', next);
    document.body.appendChild(root);
  }

  // left/right limits for the bubble: the phone screen the feature sits in (the nearest big clipping box), else the window
  function span(el) {
    for (var n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      var r = n.getBoundingClientRect();
      if (r.width >= 250 && r.height >= 500 && getComputedStyle(n).overflow === 'hidden') {
        return [Math.max(0, r.left) + 10, Math.min(window.innerWidth, r.right) - 10];
      }
    }
    return [12, window.innerWidth - 12];
  }

  // dot sits on the feature's top-right corner; bubble goes below it, or above when there is no room
  function place(el) {
    var r = el.getBoundingClientRect(), vh = window.innerHeight, lim = span(el);
    var w = Math.min(320, lim[1] - lim[0]);
    bubble.style.width = w + 'px';
    var h = bubble.offsetHeight;
    dot.style.left = (r.right - 16) + 'px';
    dot.style.top = (r.top + 2) + 'px';
    var below = r.bottom + 14 + h <= vh - 12;
    var top = below ? r.bottom + 14 : r.top - 14 - h;
    bubble.style.left = Math.max(lim[0], Math.min(lim[1] - w, r.left + r.width / 2 - w / 2)) + 'px';
    bubble.style.top = Math.max(12, Math.min(vh - h - 12, top)) + 'px';
    root.style.visibility = visible && r.bottom > 0 && r.top < vh ? 'visible' : 'hidden';
  }

  function tick() {
    raf = requestAnimationFrame(tick);
    if (!visible) return;
    var el = candidates(STEPS[idx].key)[0];
    if (!el) { visible = false; root.style.visibility = 'hidden'; goTo(idx + 1); return; }   // the feature went away: move on
    place(el);
  }

  function replayIn() {
    [card, dot].forEach(function (n) { n.style.animation = 'none'; void n.offsetWidth; n.style.animation = ''; });
  }

  function show(j, el) {
    idx = j; shown++;
    textEl.textContent = STEPS[j].text;
    dotsEl.setAttribute('aria-label', 'Step ' + (j + 1) + ' of ' + STEPS.length);
    Array.prototype.forEach.call(dotsEl.children, function (d, k) { d.className = k === j ? 'on' : ''; });
    nextBtn.textContent = j === STEPS.length - 1 ? 'Done' : 'Next';
    visible = true;
    place(el);
    replayIn();
  }

  // show the first step from j onward whose feature is on screen; none left means the tour is over
  function goTo(j) {
    if (!active) return;
    if (j >= STEPS.length) return finish();
    visible = false;
    root.style.visibility = 'hidden';
    waitFor(STEPS[j], function (el) { if (el) show(j, el); else goTo(j + 1); });
  }

  function next() {
    if (!active) return;
    if (STEPS[idx].key === 'open') {
      // the next steps live on the story screen, so do exactly what tapping the button does
      var btn = candidates('open')[0];
      if (btn) { busy = true; try { btn.click(); } finally { busy = false; } }
    }
    goTo(idx + 1);
  }

  // a tap anywhere outside the bubble closes the guide and still reaches the app underneath
  function onOutside(e) { if (!busy && !bubble.contains(e.target)) finish(); }
  function onKey(e) { if (e.key === 'Escape') finish(); }

  function finish() {
    if (!active) return;
    active = false; visible = false; waitToken++;
    cancelAnimationFrame(raf);
    document.removeEventListener('click', onOutside, true);
    document.removeEventListener('keydown', onKey, true);
    if (root && root.parentNode) root.parentNode.removeChild(root);
    if (shown > 0) remember();
  }

  function start() {
    active = true;
    build();
    document.addEventListener('click', onOutside, true);
    document.addEventListener('keydown', onKey, true);
    raf = requestAnimationFrame(tick);
    goTo(0);
  }

  // wait until the user reaches the feed (its "Open the story" button exists), then start once
  var hits = 0, poll = setInterval(function () {
    hits = candidates('open').length ? hits + 1 : 0;
    if (hits >= 2) { clearInterval(poll); start(); }   // two checks in a row: the feed has settled
  }, 400);
})();
