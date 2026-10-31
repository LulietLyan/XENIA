import { addGlobalTicker } from "./globalTicker";
import gsap from "gsap";
import SplitText from "gsap/SplitText";

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

const observer = new IntersectionObserver(intersectCallback, {
  root: null,
  rootMargin: '0px 0px',
  threshold: 0,
})

const map = new WeakMap<HTMLElement, ((entries: IntersectionObserverEntry) => void)[]>();

function intersectCallback(entries: IntersectionObserverEntry[]) {
  entries.forEach(ent => {
    (map.get(ent.target as HTMLElement) || []).forEach(fn => fn(ent))
  })
}

function visibilityObserve(element: HTMLElement, onChange: (entries: IntersectionObserverEntry) => void) {
  const fns = map.get(element) || [];
  fns.push(onChange)
  map.set(element, fns)

  observer.observe(element)
}

function visibilityUnobserve(element: HTMLElement, onChange: (entries: IntersectionObserverEntry) => void) {
  const fns = (map.get(element) || []).filter((fn) => fn !== onChange);

  if (fns.length) {
    map.set(element, fns)
  } else {
    map.delete(element)
    observer.unobserve(element)
  }
}


const stagger = 100;
const toReveal: { el: HTMLElement; shouldReveal: boolean, inFn?: () => void }[] = [];

const stMap = new WeakMap<HTMLElement, InstanceType<typeof SplitText>>()
const wholeRevealElements = new WeakSet<HTMLElement>();

function revealWholeText(el: HTMLElement) {
  wholeRevealElements.add(el);

  return {
    in() {
      gsap.killTweensOf(el);
      gsap.fromTo(el, { opacity: 0, y: 12 }, {
        opacity: 1,
        y: 0,
        duration: 0.5,
        ease: "power3.out",
        clearProps: "opacity,transform",
      });
    },
    out(next: () => void) {
      gsap.killTweensOf(el);
      gsap.to(el, {
        opacity: 0,
        y: -8,
        duration: 0.3,
        ease: "power3.out",
        onComplete() {
          next();
          gsap.set(el, { clearProps: "opacity,transform" });
        },
      });
    },
  };
}

function getSt(el: HTMLElement, type: "words" | "lines"): SplitText {
  if (stMap.has(el)) {
    return stMap.get(el)!
  }

  const st = new SplitText(el, {
    aria: "none",
    tag: "span",
    autoSplit: true,
    mask: type,
    wordsClass: "i",
    linesClass: "i",
    onSplit(_st) {
      _st.masks.forEach((m) => {
        (m as HTMLElement).style.overflow = '';
      })

      stMap.set(el, _st)
    },
    type
  });

  stMap.set(el, st)

  return st;
}

const fns = {
  words(el: HTMLElement) {
    if (/\p{Script=Han}/u.test(el.textContent ?? "")) return revealWholeText(el);
    getSt(el, "words");

    let lastOut: ReturnType<typeof gsap.to> | null = null

    return {
      in() {
        const st = getSt(el, "words");

        if (lastOut) {
          lastOut.kill();
          lastOut = null
        }

        gsap.fromTo(
          st.words,
          {
            opacity: 1,
            rotate: 5,
            yPercent: 120,
          },
          {
            rotate: 0,
            yPercent: 0,
            ease: 'power3.out',
            duration: 0.5,
            stagger: {
              each: 0.05,
            },
          },
        );
      },
      out(next: () => void) {
        const st = getSt(el, "words");

        lastOut = gsap.to(
          st.words,
          {
            opacity: 0,
            ease: 'power3.out',
            duration: 0.5,
            stagger: {
              each: 0.05,
            },
            onComplete() {
              next()
            },
          },
        );
      },
    };
  },
  lines(el: HTMLElement) {
    if (/\p{Script=Han}/u.test(el.textContent ?? "")) return revealWholeText(el);
    getSt(el, "lines");

    let lastOut: ReturnType<typeof gsap.to> | null = null

    return {
      in() {
        const st = getSt(el, "lines");

        if (lastOut) {
          lastOut.kill();
          lastOut = null
        }

        gsap.fromTo(
          st.lines,
          {
            rotateX: 45,
            yPercent: 120,
          },
          {
            rotateX: 0,
            yPercent: 0,
            ease: 'power3.out',
            duration: 0.5,
            stagger: {
              each: 0.05,
            },
          },
        );
      },
      out(next: () => void) {
        const st = getSt(el, "lines");

        lastOut = gsap.fromTo(
          st.lines,
          {
            rotateX: 45,
            yPercent: 0,
          },
          {
            rotateX: 0,
            yPercent: -120,
            ease: 'power4.out',
            duration: 0.5,
            stagger: {
              each: 0.05,
            },
            onComplete() {
              next()
            },
          },
        );
      }
    }
  }
}

function onVisibilityChange(ent: IntersectionObserverEntry) {
  const el = ent.target as HTMLElement;
  if (reducedMotion.matches) {
    el.classList.add("is-in");
    visibilityUnobserve(el, onVisibilityChange);
    return;
  }

  if (ent.isIntersecting) {
    const fn = el.dataset.syReveal as keyof typeof fns | undefined;

    toReveal.push({
      el,
      shouldReveal: false,
      inFn: fn && fns[fn] ? fns[fn](el).in : undefined,
    });

    setTimeout(() => {
      const i = toReveal.findIndex((i) => i.el === el);
      if (i >= 0) {
        toReveal[i].shouldReveal = true;
      }
    }, Math.min(toReveal.length * stagger));
  } else {
    const i = toReveal.findIndex((i) => i.el === el);
    if (i >= 0 && toReveal[i].shouldReveal === false) {
      toReveal.splice(i, 1);
    }
  }
}

addGlobalTicker(() => {
  if (reducedMotion.matches) return;
  toReveal.forEach(({ el, shouldReveal, inFn }, i) => {
    if (shouldReveal) {
      el.classList.add("is-in");
      inFn && inFn()
      toReveal.splice(i, 1);
      visibilityUnobserve(el, onVisibilityChange);
    }
  });
});

function showWithoutMotion() {
  observer.disconnect();
  toReveal.length = 0;
  document.querySelectorAll<HTMLElement>("[data-sy-reveal]").forEach((elem) => {
    if (wholeRevealElements.has(elem)) {
      gsap.killTweensOf(elem);
      gsap.set(elem, { clearProps: "opacity,transform" });
    }
    const split = stMap.get(elem);
    if (split) {
      gsap.killTweensOf([...split.words, ...split.lines]);
      split.revert();
      stMap.delete(elem);
    }
    elem.classList.add("is-in");
  });
}

if (reducedMotion.matches) showWithoutMotion();
reducedMotion.addEventListener("change", () => {
  if (reducedMotion.matches) showWithoutMotion();
});

document.fonts.ready.then(() => {
  if (reducedMotion.matches) {
    showWithoutMotion();
    return;
  }
  document.querySelectorAll<HTMLHtmlElement>("[data-sy-reveal]").forEach((elem) => {
    if (elem.hasAttribute('data-sy-reveal-manual')) {
      const _fn = elem.dataset.syReveal as keyof typeof fns | undefined;
      const fn = _fn && fns[_fn] && fns[_fn](elem);

      elem.addEventListener('reveal-in', () => {
        !reducedMotion.matches && fn && fn.in()
        elem.classList.add("is-in");
      });

      elem.addEventListener('reveal-out', () => {
        if (reducedMotion.matches) {
          elem.classList.add("is-in");
          return;
        }
        if (fn) {
          fn.out(() => {
            elem.classList.remove("is-in");
          });
        } else {
          elem.classList.remove("is-in");
        }
      });

    } else {
      visibilityObserve(elem, onVisibilityChange);
    }
  });
})

export function manualRevealIn(elem: HTMLElement) {
  elem.dispatchEvent(new Event('reveal-in'));
}

export function manualRevealOut(elem: HTMLElement) {
  elem.dispatchEvent(new Event('reveal-out'));
}
