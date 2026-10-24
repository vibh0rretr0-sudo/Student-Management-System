/* Second layer of the laptop-only restriction (CSS is the first, the server
   user-agent check is the third).  Re-runs on resize and never reloads, so
   widening the window restores the portal with its state intact. */
const MOBILE_UA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|windows phone|mobile|tablet|silk|kindle/i;

export function initDeviceGuard() {
  let frame = null;
  const evaluate = () => {
    frame = null;
    const width = window.innerWidth || document.documentElement.clientWidth;
    const touchTablet = navigator.maxTouchPoints > 1 && width < 1024;
    const blocked = width < 1024 || touchTablet || MOBILE_UA.test(navigator.userAgent);
    document.body.classList.toggle("is-device-blocked", blocked);
  };
  const schedule = () => {
    if (frame !== null) return;
    frame = window.requestAnimationFrame(evaluate);
  };
  evaluate();
  window.addEventListener("resize", schedule, { passive: true });
  window.addEventListener("orientationchange", schedule, { passive: true });
}
