import { useEffect, useRef } from 'react';

/**
 * Rete di nodi tridimensionale disegnata su canvas 2D (nessuna libreria 3D: pagina leggera).
 * Rotazione lenta, impulsi color rame lungo i collegamenti, accelerazione con lo scroll.
 * Si ferma quando non è visibile e rispetta prefers-reduced-motion.
 */
export function HeroGraph({ className = '' }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const small = window.innerWidth < 768;
    const N = small ? 54 : 96;

    // Punti su una sfera (spirale di Fibonacci) con leggera irregolarità.
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const pts = Array.from({ length: N }, (_, i) => {
      const y = 1 - (i / (N - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const th = Math.PI * (3 - Math.sqrt(5)) * i;
      const k = 0.82 + rnd() * 0.3;
      return { x: Math.cos(th) * r * k, y: y * k, z: Math.sin(th) * r * k, hub: rnd() < 0.09 };
    });
    const edges: [number, number][] = [];
    const seen = new Set<string>();
    pts.forEach((p, i) => {
      pts
        .map((q, j) => ({ j, d: (p.x - q.x) ** 2 + (p.y - q.y) ** 2 + (p.z - q.z) ** 2 }))
        .filter((o) => o.j !== i)
        .sort((a, b) => a.d - b.d)
        .slice(0, 3)
        .forEach(({ j }) => {
          const key = i < j ? `${i}-${j}` : `${j}-${i}`;
          if (!seen.has(key)) { seen.add(key); edges.push([i, j]); }
        });
    });
    const pulses = Array.from({ length: small ? 6 : 12 }, () => ({ e: Math.floor(rnd() * edges.length), t: rnd(), v: 0.004 + rnd() * 0.006 }));

    let w = 0, h = 0, dpr = 1, angle = 0.6, tilt = 0.32, targetTilt = 0.32, raf = 0, visible = true;
    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const project = (p: { x: number; y: number; z: number }) => {
      const ca = Math.cos(angle), sa = Math.sin(angle), ct = Math.cos(tilt), st = Math.sin(tilt);
      const x1 = p.x * ca + p.z * sa, z1 = -p.x * sa + p.z * ca;
      const y1 = p.y * ct - z1 * st, z2 = p.y * st + z1 * ct;
      const R = Math.min(w, h) * 0.42, f = 3.2, s = f / (f + z2);
      return { x: w / 2 + x1 * R * s, y: h / 2 + y1 * R * s, z: z2, s };
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      const P = pts.map(project);
      for (const [a, b] of edges) {
        const depth = (2 - (P[a].z + P[b].z) / 2) / 3;
        ctx.strokeStyle = `rgba(243,240,233,${0.05 + depth * 0.16})`;
        ctx.lineWidth = 0.7;
        ctx.beginPath(); ctx.moveTo(P[a].x, P[a].y); ctx.lineTo(P[b].x, P[b].y); ctx.stroke();
      }
      for (const pu of pulses) {
        const [a, b] = edges[pu.e];
        const x = P[a].x + (P[b].x - P[a].x) * pu.t, y = P[a].y + (P[b].y - P[a].y) * pu.t;
        ctx.fillStyle = 'rgba(217,119,54,0.95)';
        ctx.beginPath(); ctx.arc(x, y, 1.8, 0, Math.PI * 2); ctx.fill();
      }
      P.map((p, i) => ({ p, i })).sort((a, b) => b.p.z - a.p.z).forEach(({ p, i }) => {
        const depth = (2 - p.z) / 3;
        const hub = pts[i].hub;
        ctx.fillStyle = hub ? `rgba(217,119,54,${0.55 + depth * 0.45})` : `rgba(243,240,233,${0.25 + depth * 0.7})`;
        ctx.beginPath(); ctx.arc(p.x, p.y, (hub ? 3.2 : 1.6) * p.s * 1.3, 0, Math.PI * 2); ctx.fill();
        if (hub) {
          ctx.strokeStyle = `rgba(217,119,54,${0.2 * depth})`;
          ctx.beginPath(); ctx.arc(p.x, p.y, 9 * p.s, 0, Math.PI * 2); ctx.stroke();
        }
      });
    };

    const tick = () => {
      const boost = 1 + Math.min(window.scrollY / Math.max(h, 1), 1.5) * 3;
      angle += 0.0016 * boost;
      tilt += (targetTilt - tilt) * 0.04;
      for (const pu of pulses) {
        pu.t += pu.v;
        if (pu.t > 1) { pu.t = 0; pu.e = Math.floor(Math.random() * edges.length); }
      }
      draw();
      if (visible && !document.hidden) raf = requestAnimationFrame(tick);
    };

    const onPointer = (e: PointerEvent) => { targetTilt = 0.32 + (e.clientY / window.innerHeight - 0.5) * 0.35; };
    const start = () => { cancelAnimationFrame(raf); if (!reduce) raf = requestAnimationFrame(tick); };
    const io = new IntersectionObserver(([en]) => { visible = en.isIntersecting; if (visible) start(); else cancelAnimationFrame(raf); });
    const onVis = () => (document.hidden ? cancelAnimationFrame(raf) : start());

    resize();
    draw();
    io.observe(canvas);
    window.addEventListener('resize', resize);
    if (!small) window.addEventListener('pointermove', onPointer);
    document.addEventListener('visibilitychange', onVis);
    start();
    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      window.removeEventListener('resize', resize);
      window.removeEventListener('pointermove', onPointer);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, []);

  return <canvas ref={ref} className={className} aria-hidden />;
}
