import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Copy, RotateCcw } from 'lucide-react';
import katex from 'katex';

const MIN_M = 3;
const MAX_P = 12000;
const MAX_M = Math.floor(Math.sqrt((MAX_P - 1) / 4));
const COLORS = {
  a: '#ef4444',
  ma: '#059669',
  sum: '#2563eb',
  mixed: '#7c3aed',
};

function InlineMath({ children, className = '' }) {
  const html = katex.renderToString(String(children), {
    throwOnError: false,
    strict: false,
  });

  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function clampInt(value, min, max, fallback) {
  const parsed = Math.round(Number(value));
  if (!Number.isFinite(parsed)) return fallback;
  return clamp(parsed, min, max);
}

function mod(value, modulus) {
  return ((value % modulus) + modulus) % modulus;
}

function gcd(a, b) {
  let x = Math.abs(a);
  let y = Math.abs(b);
  while (y !== 0) {
    const next = x % y;
    x = y;
    y = next;
  }
  return x;
}

function isPrime(value) {
  if (value < 2) return false;
  if (value === 2 || value === 3) return true;
  if (value % 2 === 0 || value % 3 === 0) return false;
  for (let divisor = 5; divisor * divisor <= value; divisor += 6) {
    if (value % divisor === 0 || value % (divisor + 2) === 0) return false;
  }
  return true;
}

function pFor(m, n) {
  return 4 * m * m * n + 1;
}

function maxNForM(m) {
  return Math.max(1, Math.floor((MAX_P - 1) / (4 * m * m)));
}

function possiblePrimeValues(m) {
  const options = [];
  const maxN = maxNForM(m);
  for (let n = 1; n <= maxN; n += 1) {
    const p = pFor(m, n);
    if (isPrime(p)) options.push({ n, p });
  }
  return options;
}

function lemmaPreset(m) {
  const residue = mod(m, 4);
  if (residue === 0) return { lambda: m, mu: m / 4, extra: 'none' };
  if (residue === 1) return { lambda: m, mu: (m - 1) / 4, extra: 'none' };
  if (residue === 2) return { lambda: m - 1, mu: (m - 2) / 4, extra: 'tail-2' };
  return { lambda: m, mu: (m - 3) / 4, extra: 'tail-3' };
}

function remarkPreset(m) {
  const residue = mod(m, 4);
  if (residue === 0) return lemmaPreset(m);
  if (residue === 1) return { lambda: Math.max(3, m - 3), mu: (m + 3) / 4, extra: 'none' };
  if (residue === 2) return { lambda: Math.max(3, m - 2), mu: (m + 2) / 4, extra: 'none' };
  return { lambda: Math.max(3, m - 1), mu: (m + 1) / 4, extra: 'none' };
}

function getRecipePreset(recipe, m, manualLambda, manualMu) {
  if (recipe === 'remark') return remarkPreset(m);
  if (recipe === 'manual') {
    return {
      lambda: clampInt(manualLambda, 3, m, Math.min(m, 7)),
      mu: clampInt(manualMu, 0, m - 1, 0),
      extra: 'none',
    };
  }
  return lemmaPreset(m);
}

function buildCandelaSet({ m, n, p, lambda, mu, extra }) {
  const result = new Set();
  const start = 4 * m * n + 1;
  const end = 2 * lambda * m * n;

  for (let x = start; x <= end; x += 1) {
    if (mod(x, m) <= mu) {
      result.add(mod(x, p));
    }
  }

  if (extra === 'tail-2' && mod(m, 4) === 2) {
    const residue = (m + 2) / 4;
    for (let t = m * n; t <= 2 * (m - 1) * n - 1; t += 1) {
      result.add(mod(t * m + residue, p));
    }
  }

  if (extra === 'tail-3' && mod(m, 4) === 3) {
    const residue = (m + 1) / 4;
    for (let t = m * n; t <= 2 * m * n - 1; t += 1) {
      result.add(mod(t * m + residue, p));
    }
  }

  return result;
}

function multiplySet(values, factor, p) {
  const result = new Set();
  values.forEach(value => {
    result.add(mod(value * factor, p));
  });
  return result;
}

function sumset(values, p) {
  const arr = Array.from(values);
  const result = new Set();
  for (let i = 0; i < arr.length; i += 1) {
    for (let j = i; j < arr.length; j += 1) {
      result.add(mod(arr[i] + arr[j], p));
    }
  }
  return result;
}

function differenceSet(leftValues, rightValues, p) {
  const result = new Set();
  leftValues.forEach(left => {
    rightValues.forEach(right => {
      result.add(mod(left - right, p));
    });
  });
  return result;
}

function intersectionSize(leftValues, rightValues) {
  let count = 0;
  leftValues.forEach(value => {
    if (rightValues.has(value)) count += 1;
  });
  return count;
}

function polarToCartesian(cx, cy, r, angleInTurns) {
  const angleInRadians = (angleInTurns - 0.25) * 2 * Math.PI;
  return {
    x: cx + r * Math.cos(angleInRadians),
    y: cy + r * Math.sin(angleInRadians),
  };
}

function encodeShareState(state) {
  const json = JSON.stringify(state);
  const bytes = encodeURIComponent(json).replace(/%([0-9A-F]{2})/g, (_, hex) => (
    String.fromCharCode(parseInt(hex, 16))
  ));

  return btoa(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function decodeShareState(value) {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(value.length / 4) * 4, '=');
  const bytes = atob(padded);
  const escaped = Array.from(bytes, char => (
    `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`
  )).join('');

  return JSON.parse(decodeURIComponent(escaped));
}

function buildShareUrl(state) {
  if (typeof window === 'undefined') return '';

  const url = new URL(window.location.href);
  url.search = '';
  url.searchParams.set('state', encodeShareState(state));
  return url.toString();
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Fall back for local/dev contexts where clipboard permission is denied.
    }
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}

function getDefaultCandelaSetup() {
  const m = 7;
  const n = 1;
  const preset = lemmaPreset(m);
  return {
    m,
    n,
    recipe: 'lemma',
    manualLambda: preset.lambda,
    manualMu: preset.mu,
    dilation: 1,
  };
}

function normalizeCandelaSetup(raw) {
  const defaults = getDefaultCandelaSetup();
  const m = clampInt(raw?.m, MIN_M, MAX_M, defaults.m);
  const n = clampInt(raw?.n, 1, maxNForM(m), defaults.n);
  const p = pFor(m, n);
  const recipe = ['lemma', 'remark', 'manual'].includes(raw?.recipe) ? raw.recipe : defaults.recipe;
  const preset = getRecipePreset(recipe, m, raw?.manualLambda ?? raw?.lambda, raw?.manualMu ?? raw?.mu);

  return {
    m,
    n,
    recipe,
    manualLambda: clampInt(raw?.manualLambda ?? raw?.lambda, 3, m, preset.lambda),
    manualMu: clampInt(raw?.manualMu ?? raw?.mu, 0, m - 1, preset.mu),
    dilation: clampInt(raw?.dilation, 1, p - 1, defaults.dilation),
  };
}

function readCandelaSetupFromUrl() {
  if (typeof window === 'undefined') return getDefaultCandelaSetup();

  const rawState = new URLSearchParams(window.location.search).get('state');
  if (!rawState) return getDefaultCandelaSetup();

  try {
    return normalizeCandelaSetup(decodeShareState(rawState));
  } catch {
    return getDefaultCandelaSetup();
  }
}

function DiscreteTrack({ radius, p }) {
  const fullTicks = p <= 720;
  const count = fullTicks ? p : 240;
  const ticks = [];

  for (let i = 0; i < count; i += 1) {
    const turn = fullTicks ? i / p : i / count;
    const point = polarToCartesian(0, 0, radius, turn);
    ticks.push(
      <circle
        key={i}
        cx={point.x}
        cy={point.y}
        r={fullTicks ? 1.05 : 0.8}
        fill="#cbd5e1"
        opacity={fullTicks ? 0.8 : 0.45}
      />
    );
  }

  return (
    <g>
      <circle cx="0" cy="0" r={radius} stroke="#f1f5f9" strokeWidth="12" fill="none" />
      {ticks}
    </g>
  );
}

function ResidueRing({ radius, p, residues, color }) {
  const values = useMemo(() => Array.from(residues).sort((a, b) => a - b), [residues]);
  const dotRadius = p <= 240 ? 3.4 : p <= 900 ? 2.3 : p <= 3000 ? 1.55 : 1.05;

  return (
    <g>
      {values.map(value => {
        const point = polarToCartesian(0, 0, radius, value / p);
        return (
          <circle
            key={value}
            cx={point.x}
            cy={point.y}
            r={dotRadius}
            fill={color}
            opacity="0.78"
          />
        );
      })}
    </g>
  );
}

function NumberSlider({ label, value, min, max, onChange, disabled = false }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <label className="font-medium text-slate-700">{label}</label>
        <input
          type="number"
          step="1"
          min={min}
          max={max}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(clampInt(e.target.value, min, max, value))}
          className="w-24 px-2 py-1 text-right border border-slate-200 rounded-lg font-mono text-sm text-slate-700 disabled:bg-slate-100 disabled:text-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step="1"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(clampInt(e.target.value, min, max, value))}
        className="w-full accent-blue-500 disabled:opacity-50"
      />
    </div>
  );
}

function Stat({ label, value, tone = 'slate' }) {
  const toneClass = tone === 'good' ? 'text-emerald-600' : tone === 'bad' ? 'text-red-500' : 'text-slate-700';
  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <span className="text-sm text-slate-500">{label}</span>
      <span className={`text-sm font-bold font-mono ${toneClass}`}>{value}</span>
    </div>
  );
}

export default function CandelaVisualizer({ onSwitchToIntervals }) {
  const [initialSetup] = useState(() => readCandelaSetupFromUrl());
  const [m, setM] = useState(initialSetup.m);
  const [n, setN] = useState(initialSetup.n);
  const [recipe, setRecipe] = useState(initialSetup.recipe);
  const [manualLambda, setManualLambda] = useState(initialSetup.manualLambda);
  const [manualMu, setManualMu] = useState(initialSetup.manualMu);
  const [dilation, setDilation] = useState(initialSetup.dilation);
  const [copyStatus, setCopyStatus] = useState('idle');
  const [jsonInput, setJsonInput] = useState('');
  const [jsonStatus, setJsonStatus] = useState('idle');

  const maxN = useMemo(() => maxNForM(m), [m]);
  const p = useMemo(() => pFor(m, n), [m, n]);
  const primeOptions = useMemo(() => possiblePrimeValues(m), [m]);
  const pIsPrime = useMemo(() => isPrime(p), [p]);
  const dilationGcd = useMemo(() => gcd(dilation, p), [dilation, p]);

  const activePreset = useMemo(() => (
    getRecipePreset(recipe, m, manualLambda, manualMu)
  ), [recipe, m, manualLambda, manualMu]);

  const lambda = activePreset.lambda;
  const mu = activePreset.mu;
  const extra = activePreset.extra;

  useEffect(() => {
    setN(current => clamp(current, 1, maxNForM(m)));
    setManualLambda(current => clamp(current, 3, m));
    setManualMu(current => clamp(current, 0, m - 1));
  }, [m]);

  useEffect(() => {
    setDilation(current => clamp(current, 1, Math.max(1, p - 1)));
  }, [p]);

  const data = useMemo(() => {
    const rawA = buildCandelaSet({ m, n, p, lambda, mu, extra });
    const a = multiplySet(rawA, dilation, p);
    const ma = multiplySet(a, m, p);
    const aa = sumset(a, p);
    const mixed = differenceSet(aa, ma, p);
    const overlap = intersectionSize(aa, ma);

    return {
      a,
      ma,
      aa,
      mixed,
      overlap,
      zeroInMixed: mixed.has(0),
    };
  }, [m, n, p, lambda, mu, extra, dilation]);

  const density = data.a.size / p;
  const paperDensity = data.a.size / (p - 1);

  const shareState = useMemo(() => ({
    v: 2,
    mode: 'candela',
    m,
    n,
    p,
    recipe,
    lambda,
    mu,
    manualLambda,
    manualMu,
    dilation,
  }), [m, n, p, recipe, lambda, mu, manualLambda, manualMu, dilation]);

  const shareUrl = useMemo(() => buildShareUrl(shareState), [shareState]);
  const currentStateJson = useMemo(() => JSON.stringify(shareState, null, 2), [shareState]);

  const setMClamped = useCallback((value) => {
    const nextM = clampInt(value, MIN_M, MAX_M, m);
    setM(nextM);
  }, [m]);

  const setNClamped = useCallback((value) => {
    setN(clampInt(value, 1, maxNForM(m), n));
  }, [m, n]);

  const applyJson = useCallback(() => {
    try {
      const setup = normalizeCandelaSetup(JSON.parse(jsonInput));
      setM(setup.m);
      setN(setup.n);
      setRecipe(setup.recipe);
      setManualLambda(setup.manualLambda);
      setManualMu(setup.manualMu);
      setDilation(setup.dilation);
      setJsonStatus('imported');
    } catch {
      setJsonStatus('invalid');
    }
    window.setTimeout(() => setJsonStatus('idle'), 2200);
  }, [jsonInput]);

  const copyShareLink = useCallback(async () => {
    try {
      await copyText(shareUrl);
      setCopyStatus('copied');
    } catch {
      setCopyStatus('failed');
    }
    window.setTimeout(() => setCopyStatus('idle'), 1600);
  }, [shareUrl]);

  const copyStateJson = useCallback(async () => {
    try {
      await copyText(currentStateJson);
      setJsonStatus('copied');
    } catch {
      setJsonStatus('copy-failed');
    }
    window.setTimeout(() => setJsonStatus('idle'), 1600);
  }, [currentStateJson]);

  const useCurrentParametersAsManual = useCallback(() => {
    setManualLambda(lambda);
    setManualMu(mu);
    setRecipe('manual');
  }, [lambda, mu]);

  const RADIUS_A = 60;
  const RADIUS_MA = 105;
  const RADIUS_SUM = 150;
  const RADIUS_MIXED = 195;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans p-4 md:p-8 flex flex-col items-center">
      <div className="max-w-[1600px] w-full">
        <header className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 mb-2">Candela Construction Visualizer</h1>
              <p className="text-slate-600">
                Work in <InlineMath>{'\\mathbb Z/p\\mathbb Z'}</InlineMath> with <InlineMath>{'p=4m^2n+1'}</InlineMath>. The set is built from <InlineMath>{'J=\\{4mn+1,\\ldots,2\\lambda mn\\}'}</InlineMath> by residue classes modulo <InlineMath>{'m'}</InlineMath>, then dilated by <InlineMath>{'c\\ne 0'}</InlineMath>.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <button
                onClick={onSwitchToIntervals}
                className="shrink-0 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm font-bold"
                title="Open the circle interval visualizer"
              >
                <RotateCcw size={16} />
                Circle intervals
              </button>
              <button
                onClick={copyShareLink}
                className="shrink-0 bg-slate-900 hover:bg-slate-700 text-white px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm font-bold"
                title="Copy shareable setup link"
              >
                {copyStatus === 'copied' ? <Check size={16} /> : <Copy size={16} />}
                {copyStatus === 'copied' ? 'Copied' : copyStatus === 'failed' ? 'Copy Failed' : 'Copy current state link'}
              </button>
            </div>
          </div>
        </header>

        <div className="flex flex-col xl:flex-row gap-8 items-start">
          <div className="flex flex-col lg:flex-row gap-8 flex-1 min-w-0 w-full">
            <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col items-center justify-center min-h-[560px]">
              <svg viewBox="-265 -265 530 530" className="w-full max-w-[560px] h-auto overflow-visible">
                {[0, 0.25, 0.5, 0.75].map(turn => {
                  const p1 = polarToCartesian(0, 0, 38, turn);
                  const p2 = polarToCartesian(0, 0, 228, turn);
                  return <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#e2e8f0" strokeWidth="2" strokeDasharray="4 4" key={`axis-${turn}`} />;
                })}

                <text x="0" y="-248" textAnchor="middle" className="text-sm font-semibold fill-slate-400">0</text>
                <text x="248" y="0" textAnchor="start" alignmentBaseline="middle" className="text-sm font-semibold fill-slate-400">{Math.floor(p / 4)}</text>
                <text x="0" y="248" textAnchor="middle" alignmentBaseline="hanging" className="text-sm font-semibold fill-slate-400">{Math.floor(p / 2)}</text>
                <text x="-248" y="0" textAnchor="end" alignmentBaseline="middle" className="text-sm font-semibold fill-slate-400">{Math.floor(3 * p / 4)}</text>

                <DiscreteTrack radius={RADIUS_A} p={p} />
                <DiscreteTrack radius={RADIUS_MA} p={p} />
                <DiscreteTrack radius={RADIUS_SUM} p={p} />
                <DiscreteTrack radius={RADIUS_MIXED} p={p} />

                <ResidueRing radius={RADIUS_A} p={p} residues={data.a} color={COLORS.a} />
                <ResidueRing radius={RADIUS_MA} p={p} residues={data.ma} color={COLORS.ma} />
                <ResidueRing radius={RADIUS_SUM} p={p} residues={data.aa} color={COLORS.sum} />
                <ResidueRing radius={RADIUS_MIXED} p={p} residues={data.mixed} color={COLORS.mixed} />

                <circle cx="0" cy={-RADIUS_MIXED} r="5" fill={data.zeroInMixed ? '#ef4444' : '#0f172a'} stroke="#ffffff" strokeWidth="2" />
              </svg>

              <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 w-full max-w-2xl">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.a }} />
                  <span className="font-bold text-sm text-slate-800">Inner:</span>
                  <span className="text-sm text-slate-600"><InlineMath>{'cA'}</InlineMath></span>
                  <span className="font-bold text-sm text-slate-500 font-mono ml-auto">{data.a.size}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.ma }} />
                  <span className="font-bold text-sm text-slate-800">Second:</span>
                  <span className="text-sm text-slate-600"><InlineMath>{'m(cA)'}</InlineMath></span>
                  <span className="font-bold text-sm text-slate-500 font-mono ml-auto">{data.ma.size}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.sum }} />
                  <span className="font-bold text-sm text-slate-800">Third:</span>
                  <span className="text-sm text-slate-600"><InlineMath>{'cA+cA'}</InlineMath></span>
                  <span className="font-bold text-sm text-slate-500 font-mono ml-auto">{data.aa.size}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.mixed }} />
                  <span className="font-bold text-sm text-slate-800">Outer:</span>
                  <span className="text-sm text-slate-600"><InlineMath>{'cA+cA-m(cA)'}</InlineMath></span>
                  <span className="font-bold text-sm text-slate-500 font-mono ml-auto">{data.mixed.size}</span>
                </div>
              </div>
            </div>

            <div className="w-full lg:w-[400px] flex flex-col gap-6">
              <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <h2 className="font-bold text-lg mb-4">Paper Parameters</h2>
                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Recipe</label>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        ['lemma', 'Lemma'],
                        ['remark', 'Remark'],
                        ['manual', 'Manual'],
                      ].map(([value, label]) => (
                        <button
                          key={value}
                          onClick={() => value === 'manual' ? useCurrentParametersAsManual() : setRecipe(value)}
                          className={`px-3 py-2 rounded-lg border text-sm font-bold transition-colors ${recipe === value ? 'bg-slate-900 text-white border-slate-900' : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'}`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <NumberSlider label="m" value={m} min={MIN_M} max={MAX_M} onChange={setMClamped} />
                  <NumberSlider label="n" value={n} min={1} max={maxN} onChange={setNClamped} />

                  <div className="grid grid-cols-2 gap-3 rounded-xl bg-slate-50 border border-slate-100 p-3">
                    <Stat label="p" value={p} tone={pIsPrime ? 'good' : 'bad'} />
                    <Stat label="prime" value={pIsPrime ? 'yes' : 'no'} tone={pIsPrime ? 'good' : 'bad'} />
                    <Stat label="max n" value={maxN} />
                    <Stat label="p cap" value={MAX_P} />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Prime values for this <InlineMath>{'m'}</InlineMath></label>
                    <select
                      value={pIsPrime ? n : ''}
                      onChange={(e) => {
                        const next = parseInt(e.target.value, 10);
                        if (!Number.isNaN(next)) setNClamped(next);
                      }}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select prime p</option>
                      {primeOptions.map(option => (
                        <option key={option.n} value={option.n}>
                          n={option.n}, p={option.p}
                        </option>
                      ))}
                    </select>
                  </div>

                  <NumberSlider label="lambda" value={lambda} min={3} max={m} onChange={setManualLambda} disabled={recipe !== 'manual'} />
                  <NumberSlider label="mu" value={mu} min={0} max={m - 1} onChange={setManualMu} disabled={recipe !== 'manual'} />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <h2 className="font-bold text-lg mb-4">Dilate the Set</h2>
                <NumberSlider label="c" value={dilation} min={1} max={Math.max(1, p - 1)} onChange={setDilation} />
                <div className="mt-3 rounded-xl bg-slate-50 border border-slate-100 p-3">
                  <Stat label="gcd(c,p)" value={dilationGcd} tone={dilationGcd === 1 ? 'good' : 'bad'} />
                </div>
              </div>
            </div>
          </div>

          <div className="w-full xl:w-[420px] xl:shrink-0 flex flex-col gap-6">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <h2 className="font-bold text-lg mb-4">Discrete Counts</h2>
              <div className="space-y-1">
                <Stat label="|A|" value={data.a.size} />
                <Stat label="|A| / p" value={density.toFixed(6)} />
                <Stat label="|A| / (p - 1)" value={paperDensity.toFixed(6)} />
                <Stat label="|A + A|" value={data.aa.size} />
                <Stat label="|mA|" value={data.ma.size} />
                <Stat label="intersection size" value={data.overlap} tone={data.overlap === 0 ? 'good' : 'bad'} />
                <Stat label="0 in A + A - mA" value={data.zeroInMixed ? 'yes' : 'no'} tone={data.zeroInMixed ? 'bad' : 'good'} />
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                <h2 className="font-bold text-lg">State JSON</h2>
                <button
                  onClick={copyStateJson}
                  className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm font-bold"
                >
                  {jsonStatus === 'copied' ? <Check size={16} /> : <Copy size={16} />}
                  {jsonStatus === 'copied' ? 'Copied' : jsonStatus === 'copy-failed' ? 'Copy Failed' : 'Copy current JSON'}
                </button>
              </div>

              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                placeholder="Paste Candela state JSON"
                spellCheck="false"
                className="w-full min-h-40 resize-y rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              <div className="mt-3 flex items-center justify-between gap-3">
                <button
                  onClick={applyJson}
                  disabled={!jsonInput.trim()}
                  className="bg-slate-900 hover:bg-slate-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white px-3 py-2 rounded-lg transition-colors text-sm font-bold"
                >
                  Import JSON
                </button>
                <div className="min-h-5 text-right text-xs font-bold">
                  {jsonStatus === 'imported' && <span className="text-emerald-600">Imported</span>}
                  {jsonStatus === 'invalid' && <span className="text-red-500">Invalid JSON</span>}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
