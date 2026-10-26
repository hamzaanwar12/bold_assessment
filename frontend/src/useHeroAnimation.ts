import { useEffect, type RefObject } from "react";
import { motionAllowed } from "./motionPrefs";

/**
 * Landing-page intro for the AppShell hero, driven by GSAP. GSAP and
 * ScrollTrigger are loaded with dynamic import() so they never sit in the
 * main bundle, and only when motion is allowed. Targets are found by data
 * attributes, so layout code doesn't depend on this file.
 */
export function useHeroAnimation(scope: RefObject<HTMLElement | null>) {
  useEffect(() => {
    if (!motionAllowed() || !scope.current) return;
    let revert: (() => void) | undefined;
    let cancelled = false;

    Promise.all([import("gsap"), import("gsap/ScrollTrigger")]).then(([{ gsap }, { ScrollTrigger }]) => {
      if (cancelled || !scope.current) return;
      gsap.registerPlugin(ScrollTrigger);

      const ctx = gsap.context(() => {
        gsap
          .timeline({ defaults: { ease: "power3.out" } })
          .from("[data-hero-eyebrow]", { y: 12, autoAlpha: 0, duration: 0.5 })
          .from("[data-hero-title]", { y: 28, autoAlpha: 0, duration: 0.8 }, "-=0.2")
          .from("[data-hero-word]", { y: 18, autoAlpha: 0, stagger: 0.12, duration: 0.5 }, "-=0.4")
          .fromTo(
            "[data-hero-sweep]",
            { scaleX: 0, transformOrigin: "left center" },
            { scaleX: 1, duration: 0.9, ease: "expo.out" },
            "-=0.3",
          );

        gsap.utils.toArray<HTMLElement>("[data-orb]").forEach((orb, i) => {
          gsap.to(orb, {
            x: i % 2 ? -60 : 70,
            y: i % 2 ? 50 : -40,
            scale: 1.15,
            duration: 9 + i * 3,
            repeat: -1,
            yoyo: true,
            ease: "sine.inOut",
          });
        });

        gsap.to("[data-parallax]", {
          yPercent: -18,
          ease: "none",
          scrollTrigger: { trigger: scope.current, start: "top top", end: "bottom top", scrub: true },
        });
      }, scope);
      revert = () => ctx.revert();
    });

    return () => {
      cancelled = true;
      revert?.();
    };
  }, [scope]);
}
