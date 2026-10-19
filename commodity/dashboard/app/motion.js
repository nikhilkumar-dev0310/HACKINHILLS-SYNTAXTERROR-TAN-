/* MOTION v3 (19 Oct 2026): the interactions award-winning sites share, kept quiet enough for a data site.
   Desktop pointer only: smooth wheel scrolling and buttons that lean a little toward the pointer. Everywhere: the
   CSS layer in styles.css (headlines that rise word by word, background lights that drift with scroll).
   Every hook does nothing under prefers-reduced-motion, and each moves only transform/translate (composited). */
import { useEffect } from "react";
import { reducedMotion } from "./lib.js";

const finePointer = () => matchMedia("(hover: hover) and (pointer: fine)").matches;
const ease = (dt, tau) => 1 - Math.exp(-dt / tau);          // frame-rate independent approach to a target

/* Smooth wheel scrolling, as Lenis does it: the wheel moves a target and the page glides to it on a critically
   damped curve. Native scrolling still owns keyboard, scrollbar, find-in-page, anchors and touch; any scroll we
   did not cause hands control straight back. Inner scrollers (tables, the search list) keep their own wheel. */
export function useSmoothScroll() {
  useEffect(() => {
    if (reducedMotion() || !finePointer()) return;
    let target = scrollY, cur = scrollY, raf = 0, last = 0, ours = -1;
    const max = () => document.documentElement.scrollHeight - innerHeight;
    const innerCanScroll = (el, dy) => {
      for (; el && el !== document.body && el !== document.documentElement; el = el.parentElement) {
        if (el.scrollHeight <= el.clientHeight + 1) continue;
        const oy = getComputedStyle(el).overflowY;
        if (oy !== "auto" && oy !== "scroll") continue;
        if (dy > 0 ? el.scrollTop + el.clientHeight < el.scrollHeight - 1 : el.scrollTop > 0) return true;
      }
      return false;
    };
    const stop = () => { cancelAnimationFrame(raf); raf = 0; last = 0; cur = target = scrollY; };
    const frame = now => {
      raf = 0;
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 1 / 60; last = now;
      cur += (target - cur) * ease(dt, 0.1);
      if (Math.abs(target - cur) < 0.4) cur = target;
      ours = Math.round(cur); scrollTo(0, cur);
      if (cur !== target) raf = requestAnimationFrame(frame); else last = 0;
    };
    const wheel = e => {
      if (e.ctrlKey || e.metaKey || e.defaultPrevented || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      if (document.querySelector(".overlay") || innerCanScroll(e.target, e.deltaY)) return;
      e.preventDefault();
      if (!raf) cur = target = scrollY;
      const d = e.deltaMode === 1 ? e.deltaY * 40 : e.deltaMode === 2 ? e.deltaY * innerHeight : e.deltaY;
      target = Math.max(0, Math.min(max(), target + d));
      if (!raf) raf = requestAnimationFrame(frame);
    };
    const onScroll = () => { if (raf && Math.abs(scrollY - ours) > 2) stop(); };   // someone else scrolled: yield
    addEventListener("wheel", wheel, { passive: false });
    addEventListener("scroll", onScroll, { passive: true });
    return () => { removeEventListener("wheel", wheel); removeEventListener("scroll", onScroll); cancelAnimationFrame(raf); };
  }, []);
}

/* Magnetic controls: a button leans toward the pointer (at most 3 px) and springs back when it leaves. It moves
   with the CSS `translate` property, so the press-in `transform` on the same buttons still works. */
const MAG = ".btn,.search,.iconbtn,.theme,.go,.pager button,.linkbtn.kq";
export function useMagnetic() {
  useEffect(() => {
    if (reducedMotion() || !finePointer()) return;
    const live = new Map();                       // element -> {x, y, tx, ty}
    let raf = 0, last = 0, cur = null;
    const frame = now => {
      raf = 0;
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 1 / 60; last = now;
      const a = ease(dt, 0.09); let moving = false;
      live.forEach((o, el) => {
        o.x += (o.tx - o.x) * a; o.y += (o.ty - o.y) * a;
        const rest = Math.abs(o.tx - o.x) + Math.abs(o.ty - o.y) < 0.05;
        if (rest && o.tx === 0 && o.ty === 0) { el.style.translate = ""; live.delete(el); return; }
        el.style.translate = `${o.x.toFixed(2)}px ${o.y.toFixed(2)}px`;
        if (!rest) moving = true;
      });
      if (moving) raf = requestAnimationFrame(frame); else last = 0;
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
    const move = e => {
      if (e.pointerType !== "mouse") return;
      const el = e.target.closest ? e.target.closest(MAG) : null;
      if (cur && cur !== el) { const o = live.get(cur); if (o) { o.tx = 0; o.ty = 0; } }
      cur = el;
      if (el) {
        const r = el.getBoundingClientRect(), o = live.get(el) || { x: 0, y: 0 };
        // measure from the untranslated box, so the pull doesn't feed back into itself
        const cx = r.left + r.width / 2 - o.x, cy = r.top + r.height / 2 - o.y;
        const k = Math.min(0.32, 14 / Math.max(r.width, 24));
        o.tx = Math.max(-3, Math.min(3, (e.clientX - cx) * k * .5)); o.ty = Math.max(-2.5, Math.min(2.5, (e.clientY - cy) * k * .6));
        live.set(el, o);
      }
      kick();
    };
    const leave = () => { live.forEach(o => { o.tx = 0; o.ty = 0; }); cur = null; kick(); };
    document.addEventListener("pointermove", move, { passive: true });
    document.documentElement.addEventListener("mouseleave", leave, { passive: true });
    addEventListener("scroll", leave, { passive: true });
    return () => {
      document.removeEventListener("pointermove", move); document.documentElement.removeEventListener("mouseleave", leave);
      removeEventListener("scroll", leave); cancelAnimationFrame(raf); live.forEach((o, el) => { el.style.translate = ""; });
    };
  }, []);
}
