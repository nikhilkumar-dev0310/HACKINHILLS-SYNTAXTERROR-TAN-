"""Pari, the mascot, in the poses the v3.3 demo uses (rendered once to transparent PNGs in ov3/pari/)."""
import os
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
JS = r"""
window.pose = (o) => {
  const lid = 3.4 * (1 - (o.blink || 0)), ey = o.ey || 0;
  const M = { happy: '<path d="M24 38.5q5 4.5 10 0" stroke="#1b1300" stroke-width="2" fill="none" stroke-linecap="round"/>',
    wow: '<ellipse cx="29" cy="40" rx="2.6" ry="3" fill="#1b1300"/>',
    talk: '<path d="M24.5 38q4.5 5.5 9 0z" fill="#1b1300"/>',
    sad: '<path d="M24 41q5 -4 10 0" stroke="#1b1300" stroke-width="2" fill="none" stroke-linecap="round"/>',
    flat: '<path d="M25 40h8" stroke="#1b1300" stroke-width="2" stroke-linecap="round"/>',
    grin: '<path d="M23 37.5q6 7 12 0z" fill="#1b1300"/>' }[o.mouth || 'happy'];
  const A = (d) => `<path d="${d}" stroke="#c98d0c" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  const arms = { none: '', point_r: A('M45 33q7-3 12-9'), point_l: A('M13 33q-7-3-12-9'),
    up: A('M45 30q6-6 7-14') + A('M13 30q-6-6-7-14'), wave0: A('M45 30q7-4 8-10'), wave1: A('M45 30q8-3 11-12'),
    chin: A('M13 34q2 6 9 5') }[o.arms || 'none'];
  const sweat = o.sweat ? '<path d="M47 22q2 4 0 6q-2-2 0-6z" fill="#8fd3ff"/>' : '';
  const glint = o.glint ? '<path d="M50 12l1.5 3 3 1.5-3 1.5-1.5 3-1.5-3-3-1.5 3-1.5z" fill="#fff4cf"/>' : '';
  return `<svg viewBox="-4 4 66 58" width="100%" height="100%"><g>
    <ellipse cx="29" cy="58" rx="20" ry="2.5" fill="rgba(0,0,0,.35)"/>
    <path d="M21 47v9M37 47v9" stroke="#c98d0c" stroke-width="3" stroke-linecap="round"/>
    <path d="M17 56h7M34 56h7" stroke="#c98d0c" stroke-width="3" stroke-linecap="round"/>
    <path d="M15 20h28l8 28H7z" fill="url(#gb)" stroke="#c98d0c" stroke-width="2" stroke-linejoin="round"/>
    <path d="M17 22h24" stroke="rgba(255,240,200,.8)" stroke-width="2" stroke-linecap="round"/>
    <ellipse cx="22.5" cy="${32 + ey}" rx="2.6" ry="${Math.max(.35, lid)}" fill="#1b1300"/><ellipse cx="35.5" cy="${32 + ey}" rx="2.6" ry="${Math.max(.35, lid)}" fill="#1b1300"/>
    ${M}${arms}${sweat}${glint}</g></svg>`;
};
"""
P = {"idle": {}, "blink": {"blink": 1}, "talk": {"mouth": "talk"}, "wow": {"mouth": "wow", "arms": "up"},
     "think": {"mouth": "flat", "ey": -1.6, "arms": "chin"}, "no": {"mouth": "flat"}, "sad": {"mouth": "sad", "sweat": 1},
     "point_r": {"mouth": "talk", "arms": "point_r"}, "point_l": {"mouth": "talk", "arms": "point_l"},
     "cheer": {"mouth": "grin", "arms": "up", "glint": 1}, "wave0": {"mouth": "grin", "arms": "wave0"}, "wave1": {"mouth": "grin", "arms": "wave1"},
     "proud": {"mouth": "grin", "glint": 1}}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 400, "height": 400})
    pg.goto("file://" + os.path.join(HERE, "overlays.html")); pg.add_script_tag(content=JS)
    for k, o in P.items():
        pg.evaluate("o => { document.body.style.background='transparent'; document.getElementById('root').innerHTML = `<div id='pp' style='position:absolute;left:0;top:0;width:264px;height:232px'>${pose(o)}</div>`; }", o)
        pg.locator("#pp").screenshot(path=os.path.join(HERE, "ov3", "pari", k + ".png"), omit_background=True)
    b.close()
print("poses:", len(P))
