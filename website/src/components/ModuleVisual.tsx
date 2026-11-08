import { motion, useReducedMotion } from 'framer-motion';
import type { ModuleContent } from '../content/modules';
import type { CaseVisual } from '../content/story';

type Kind = ModuleContent['visual'] | CaseVisual;
const IVORY = '#F3F0E9', COPPER = '#D97736', LINE = '#3a3a40';

/** Illustrazioni astratte e schematiche: non rappresentano dati reali. */
export function ModuleVisual({ kind, className = '' }: { kind: Kind; className?: string }) {
  const reduce = useReducedMotion();
  const draw = (delay = 0) => ({
    initial: reduce ? false : { pathLength: 0, opacity: 0 },
    whileInView: { pathLength: 1, opacity: 1 },
    viewport: { once: true },
    transition: { duration: 1.4, ease: [0.22, 1, 0.36, 1] as const, delay },
  });
  const pop = (delay = 0) => ({
    initial: reduce ? false : { scale: 0, opacity: 0 },
    whileInView: { scale: 1, opacity: 1 },
    viewport: { once: true },
    transition: { duration: 0.6, delay },
  });

  const body = (() => {
    switch (kind) {
      case 'dashboard':
        return (
          <g>
            {[[20, 20, 130, 70], [160, 20, 140, 70], [20, 100, 90, 80], [120, 100, 180, 80]].map(([x, y, w, h], i) => (
              <motion.rect key={i} x={x} y={y} width={w} height={h} rx="6" fill="none" stroke={i === 1 ? COPPER : LINE} {...draw(i * 0.12)} />
            ))}
            <motion.path d="M130 160 L160 140 L190 150 L220 120 L250 130 L285 110" fill="none" stroke={IVORY} strokeWidth="1.5" {...draw(0.5)} />
            {[0, 1, 2].map((i) => <motion.rect key={i} x={32} y={118 + i * 18} width={50 - i * 12} height="6" rx="3" fill={i ? LINE : IVORY} {...pop(0.6 + i * 0.1)} />)}
          </g>
        );
      case 'folders':
      case 'project':
        return (
          <g>
            {[0, 1, 2].map((i) => (
              <motion.path key={i} d={`M${50 + i * 24} ${150 - i * 26} h70 l10 -12 h110 v-70 h-190 z`} fill="#141417" stroke={i === 2 ? COPPER : LINE} {...draw(i * 0.18)} />
            ))}
            <motion.circle cx="250" cy="60" r="5" fill={COPPER} {...pop(0.8)} />
          </g>
        );
      case 'pages':
      case 'documents':
        return (
          <g>
            {[0, 1, 2].map((i) => (
              <motion.rect key={i} x={70 + i * 34} y={30 + i * 10} width="120" height="150" rx="4" fill="#141417" stroke={i === 2 ? IVORY : LINE} {...draw(i * 0.15)} />
            ))}
            {[0, 1, 2, 3, 4, 5].map((i) => <motion.rect key={i} x="152" y={70 + i * 16} width={i === 2 ? 70 : 84 - (i % 3) * 14} height="5" rx="2.5" fill={i === 2 ? COPPER : '#4a4a50'} {...pop(0.5 + i * 0.06)} />)}
          </g>
        );
      case 'citations':
        return (
          <g>
            {[0, 1, 2, 3].map((i) => (
              <g key={i}>
                <motion.text x="40" y={52 + i * 38} fill={i === 1 ? COPPER : '#6a6a70'} fontSize="16" fontFamily="Instrument Serif, serif" {...pop(i * 0.1)}>[{i + 1}]</motion.text>
                <motion.path d={`M80 ${47 + i * 38} H${270 - (i % 2) * 50}`} stroke={i === 1 ? IVORY : LINE} strokeWidth="5" strokeLinecap="round" {...draw(0.2 + i * 0.1)} />
              </g>
            ))}
            <motion.path d="M270 80 l8 8 l16 -18" fill="none" stroke={COPPER} strokeWidth="2" {...draw(0.9)} />
          </g>
        );
      case 'chart':
        return (
          <g>
            {[50, 90, 130, 170].map((y) => <line key={y} x1="20" x2="300" y1={y} y2={y} stroke="#202024" />)}
            <motion.path d="M20 150 C50 140 60 120 80 125 S110 80 130 90 S160 40 175 60 S200 130 225 120 S260 100 300 70" fill="none" stroke={IVORY} strokeWidth="1.8" {...draw()} />
            <motion.path d="M20 160 C60 150 90 140 130 130 S200 120 300 100" fill="none" stroke={COPPER} strokeWidth="1.4" strokeDasharray="4 5" {...draw(0.4)} />
            <motion.circle cx="175" cy="60" r="4" fill={COPPER} {...pop(1.2)} />
          </g>
        );
      case 'timeline':
        return (
          <g>
            <motion.path d="M20 100 H300" stroke={LINE} strokeWidth="1.5" {...draw()} />
            {[40, 95, 150, 205, 260].map((x, i) => (
              <g key={x}>
                <motion.circle cx={x} cy="100" r={i === 2 ? 7 : 4} fill={i === 2 ? COPPER : IVORY} {...pop(0.3 + i * 0.12)} />
                <motion.path d={`M${x} ${i % 2 ? 108 : 92} V${i % 2 ? 150 : 50}`} stroke={i === 2 ? COPPER : '#4a4a50'} {...draw(0.5 + i * 0.1)} />
                <motion.rect x={x - 26} y={i % 2 ? 152 : 34} width="52" height="10" rx="5" fill={i === 2 ? COPPER : '#2a2a30'} {...pop(0.7 + i * 0.1)} />
              </g>
            ))}
          </g>
        );
      case 'clock':
        return (
          <g>
            <motion.circle cx="160" cy="100" r="72" fill="none" stroke={LINE} {...draw()} />
            <motion.path d="M160 100 L160 44" stroke={IVORY} strokeWidth="2" strokeLinecap="round" {...draw(0.4)} />
            <motion.path d="M160 100 L206 124" stroke={COPPER} strokeWidth="2" strokeLinecap="round" {...draw(0.6)} />
            <motion.path d="M160 28 A72 72 0 0 1 222 136" fill="none" stroke={COPPER} strokeWidth="3" strokeOpacity="0.5" {...draw(0.8)} />
            <motion.circle cx="160" cy="100" r="4" fill={IVORY} {...pop(0.2)} />
            <text x="250" y="60" fill="#6a6a70" fontSize="11" fontFamily="Inter, sans-serif">hidden →</text>
          </g>
        );
      case 'graph': {
        const n = [[60, 60], [150, 40], [250, 70], [100, 140], [200, 150], [160, 100], [280, 150], [40, 160]];
        const e = [[0, 1], [1, 2], [0, 3], [3, 5], [1, 5], [5, 4], [2, 6], [4, 6], [3, 7], [5, 2]];
        return (
          <g>
            {e.map(([a, b], i) => <motion.path key={i} d={`M${n[a][0]} ${n[a][1]} L${n[b][0]} ${n[b][1]}`} stroke={i % 4 === 0 ? COPPER : '#4a4a50'} strokeDasharray={i % 4 === 0 ? '4 4' : undefined} {...draw(i * 0.06)} />)}
            {n.map(([x, y], i) => <motion.circle key={i} cx={x} cy={y} r={i === 5 ? 8 : 5} fill={i === 5 ? COPPER : IVORY} {...pop(0.4 + i * 0.06)} />)}
          </g>
        );
      }
      case 'agents':
        return (
          <g>
            {['P', 'R', 'H', 'E', 'Q', 'S'].map((l, i) => {
              const a = (i / 6) * Math.PI * 2 - Math.PI / 2, x = 160 + Math.cos(a) * 70, y = 100 + Math.sin(a) * 70;
              return (
                <g key={l}>
                  <motion.path d={`M${x} ${y} L160 100`} stroke={l === 'S' ? COPPER : '#4a4a50'} {...draw(0.1 * i)} />
                  <motion.circle cx={x} cy={y} r="15" fill="#141417" stroke={l === 'S' ? COPPER : LINE} {...pop(0.2 + i * 0.08)} />
                  <text x={x} y={y + 4} textAnchor="middle" fill={IVORY} fontSize="11" fontFamily="Inter, sans-serif">{l}</text>
                </g>
              );
            })}
            <motion.circle cx="160" cy="100" r="20" fill={COPPER} {...pop(0.8)} />
            <path d="M152 100 l6 6 l11 -12" fill="none" stroke="#0B0B0D" strokeWidth="2.4" />
          </g>
        );
      case 'fan':
        return (
          <g>
            <motion.path d="M20 120 C80 118 120 110 160 100 S240 30 300 20 L300 180 C240 170 200 140 160 110 S80 122 20 120Z" fill={COPPER} fillOpacity="0.1" stroke="none" {...pop(0.6)} />
            <motion.path d="M20 120 C80 118 120 110 160 100 S240 30 300 20" fill="none" stroke={COPPER} strokeWidth="1" strokeDasharray="3 4" {...draw(0.3)} />
            <motion.path d="M20 120 C80 118 120 110 160 100 S240 100 300 100" fill="none" stroke={IVORY} strokeWidth="2" {...draw()} />
            <motion.path d="M160 110 S240 170 300 180" fill="none" stroke={COPPER} strokeWidth="1" strokeDasharray="3 4" {...draw(0.4)} />
          </g>
        );
      case 'report':
        return (
          <g>
            <motion.rect x="90" y="16" width="140" height="170" rx="4" fill="#F3F0E9" fillOpacity="0.96" {...pop()} />
            <rect x="108" y="34" width="70" height="8" rx="2" fill="#0B0B0D" />
            {[54, 64, 74].map((y) => <rect key={y} x="108" y={y} width="104" height="4" rx="2" fill="#9a968e" />)}
            <motion.path d="M110 130 L135 112 L155 120 L180 96 L208 104" fill="none" stroke={COPPER} strokeWidth="2" {...draw(0.4)} />
            {[148, 158, 168].map((y) => <rect key={y} x="108" y={y} width={y === 168 ? 60 : 104} height="4" rx="2" fill="#bdb9b0" />)}
            <text x="214" y="182" fill={COPPER} fontSize="9" fontFamily="Inter, sans-serif">[1]</text>
          </g>
        );
      case 'radar': {
        const nodes = [[70, 60], [110, 150], [160, 40], [230, 70], [250, 150], [180, 120], [60, 120]];
        return (
          <g>
            {[30, 60, 90].map((r, i) => <motion.circle key={r} cx="160" cy="100" r={r} fill="none" stroke={LINE} {...draw(i * 0.1)} />)}
            <motion.path d="M160 100 L250 100 A90 90 0 0 0 224 37 Z" fill={COPPER} fillOpacity="0.12" style={{ originX: '160px', originY: '100px' }}
              animate={reduce ? undefined : { rotate: 360 }} transition={{ duration: 8, repeat: Infinity, ease: 'linear' }} />
            {[[0, 2], [2, 5], [5, 1], [3, 4]].map(([a, b], i) => (
              <motion.line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} stroke={IVORY} strokeOpacity="0.5" {...draw(0.3 + i * 0.1)} />
            ))}
            <motion.line x1={nodes[5][0]} y1={nodes[5][1]} x2={nodes[3][0]} y2={nodes[3][1]} stroke={COPPER} strokeWidth="1.5" strokeDasharray="4 4" {...draw(0.9)} />
            {nodes.map(([x, y], i) => <motion.circle key={i} cx={x} cy={y} r={i === 5 || i === 3 ? 6 : 4} fill={i === 5 || i === 3 ? COPPER : IVORY} {...pop(0.2 + i * 0.06)} />)}
            <text x="206" y="88" fill={COPPER} fontSize="11" fontFamily="Inter, sans-serif">?</text>
          </g>
        );
      }
      case 'plug':
        return (
          <g>
            {[40, 100, 160].map((y, i) => (
              <g key={y}>
                <motion.rect x="24" y={y - 14} width="80" height="28" rx="14" fill="#141417" stroke={i === 2 ? '#4a4a50' : IVORY} strokeDasharray={i === 2 ? '3 4' : undefined} {...pop(i * 0.1)} />
                <motion.path d={`M104 ${y} C160 ${y} 170 100 216 100`} fill="none" stroke={i === 2 ? '#3a3a40' : i === 0 ? COPPER : IVORY} strokeDasharray={i === 2 ? '3 5' : undefined} {...draw(0.2 + i * 0.15)} />
              </g>
            ))}
            <motion.circle cx="240" cy="100" r="26" fill="none" stroke={COPPER} strokeWidth="1.5" {...draw(0.6)} />
            <motion.circle cx="240" cy="100" r="6" fill={COPPER} {...pop(0.9)} />
          </g>
        );
    }
  })();

  return (
    <svg viewBox="0 0 320 200" className={className} role="img" aria-label="Abstract illustration">
      {body}
    </svg>
  );
}
