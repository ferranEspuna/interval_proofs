import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { clamp } from './intervalEditing';
import {
  buildShareUrl, circlePoint, copyText, readSharedStateFromUrl,
} from './shared';
import {
  CircleAxes, InlineMath, NumberSlider, StateJsonPanel, VisualizerHeader,
} from './ui';

const MIN_M = 3;
const MAX_P = 12000;
const MAX_M = Math.floor(Math.sqrt((MAX_P - 1) / 4));
const COLORS = {
  a: '#ef4444',
  tail: '#f97316',
  ma: '#059669',
  sum: '#2563eb',
  mixed: '#7c3aed',
};

function clampInt(value: unknown, min: number, max: number, fallback: number): number {
  const parsed = Math.round(Number(value));
  if (!Number.isFinite(parsed)) return fallback;
  return clamp(parsed, min, max);
}

function mod(value: number, modulus: number): number {
  return ((value % modulus) + modulus) % modulus;
}

function gcd(a: number, b: number): number {
  let x = Math.abs(a);
  let y = Math.abs(b);
  while (y !== 0) {
    const next = x % y;
    x = y;
    y = next;
  }
  return x;
}

function isPrime(value: number): boolean {
  if (value < 2) return false;
  if (value === 2 || value === 3) return true;
  if (value % 2 === 0 || value % 3 === 0) return false;
  for (let divisor = 5; divisor * divisor <= value; divisor += 6) {
    if (value % divisor === 0 || value % (divisor + 2) === 0) return false;
  }
  return true;
}

function pFor(m: number, n: number): number {
  return 4 * m * m * n + 1;
}

function maxNForM(m: number): number {
  return Math.max(1, Math.floor((MAX_P - 1) / (4 * m * m)));
}

function possiblePrimeValues(m: number) {
  const options = [];
  const maxN = maxNForM(m);
  for (let n = 1; n <= maxN; n += 1) {
    const p = pFor(m, n);
    if (isPrime(p)) options.push({ n, p });
  }
  return options;
}

function lemmaPreset(m: number) {
  const residue = mod(m, 4);
  if (residue === 0) return { lambda: m, mu: m / 4, extra: 'none' };
  if (residue === 1) return { lambda: m, mu: (m - 1) / 4, extra: 'none' };
  if (residue === 2) return { lambda: m - 1, mu: (m - 2) / 4, extra: 'tail-2' };
  return { lambda: m, mu: (m - 3) / 4, extra: 'tail-3' };
}

function remarkPreset(m: number) {
  const residue = mod(m, 4);
  if (residue === 0) return lemmaPreset(m);
  if (residue === 1) return { lambda: Math.max(3, m - 3), mu: (m + 3) / 4, extra: 'none' };
  if (residue === 2) return { lambda: Math.max(3, m - 2), mu: (m + 2) / 4, extra: 'none' };
  return { lambda: Math.max(3, m - 1), mu: (m + 1) / 4, extra: 'none' };
}

function getRecipePreset(recipe: string, m: number, manualLambda: unknown, manualMu: unknown) {
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

function unionSets(...sets: Set<number>[]) {
  const result = new Set<number>();
  sets.forEach(values => {
    values.forEach(value => result.add(value));
  });
  return result;
}

function buildCandelaSet({ m, n, p, lambda, mu, extra }: {
  m: number; n: number; p: number; lambda: number; mu: number; extra: string;
}) {
  const base = new Set<number>();
  const tail = new Set<number>();
  const start = 4 * m * n + 1;
  const end = 2 * lambda * m * n;

  for (let x = start; x <= end; x += 1) {
    if (mod(x, m) <= mu) {
      base.add(mod(x, p));
    }
  }

  if (extra === 'tail-2' && mod(m, 4) === 2) {
    const residue = (m + 2) / 4;
    for (let t = m * n; t <= 2 * (m - 1) * n - 1; t += 1) {
      tail.add(mod(t * m + residue, p));
    }
  }

  if (extra === 'tail-3' && mod(m, 4) === 3) {
    const residue = (m + 1) / 4;
    for (let t = m * n; t <= 2 * m * n - 1; t += 1) {
      tail.add(mod(t * m + residue, p));
    }
  }

  return {
    base,
    tail,
    all: unionSets(base, tail),
  };
}

function multiplySet(values: Set<number>, factor: number, p: number) {
  const result = new Set<number>();
  values.forEach(value => {
    result.add(mod(value * factor, p));
  });
  return result;
}

function sumset(values: Set<number>, p: number) {
  const arr = Array.from<number>(values);
  const result = new Set<number>();
  for (let i = 0; i < arr.length; i += 1) {
    for (let j = i; j < arr.length; j += 1) {
      result.add(mod(arr[i] + arr[j], p));
    }
  }
  return result;
}

function differenceSet(leftValues: Set<number>, rightValues: Set<number>, p: number) {
  const result = new Set<number>();
  leftValues.forEach(left => {
    rightValues.forEach(right => {
      result.add(mod(left - right, p));
    });
  });
  return result;
}

function intersectionSize(leftValues: Set<number>, rightValues: Set<number>): number {
  let count = 0;
  leftValues.forEach(value => {
    if (rightValues.has(value)) count += 1;
  });
  return count;
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

function normalizeCandelaSetup(raw: any) {
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
  const shared = readSharedStateFromUrl();
  if (!shared) return getDefaultCandelaSetup();
  try {
    return normalizeCandelaSetup(shared);
  } catch {
    return getDefaultCandelaSetup();
  }
}

function DiscreteRing({
  radius,
  p,
  residues,
  color,
  accentResidues = null,
  accentColor = null,
}: {
  radius: number;
  p: number;
  residues: Set<number>;
  color: string;
  accentResidues?: Set<number> | null;
  accentColor?: string | null;
}) {
  const dotRadius = p <= 720 ? 1.05 : p <= 1500 ? 0.75 : p <= 3000 ? 0.55 : p <= 8000 ? 0.38 : 0.3;
  const dots = useMemo(() => {
    const result = [];
    for (let value = 0; value < p; value += 1) {
      const point = circlePoint(radius, value / p);
      const isPresent = residues.has(value);
      const isAccent = accentResidues?.has(value);
      result.push(
        <circle
          key={value}
          cx={point.x}
          cy={point.y}
          r={dotRadius}
          fill={isAccent && accentColor ? accentColor : isPresent ? color : '#cbd5e1'}
          opacity={isPresent ? 0.98 : 0.58}
        />,
      );
    }
    return result;
  }, [radius, p, residues, color, accentResidues, accentColor, dotRadius]);

  return (
    <g>
      <circle cx="0" cy="0" r={radius} stroke="#f1f5f9" strokeWidth="12" fill="none" />
      {dots}
    </g>
  );
}

function Stat({ label, value, tone = 'slate' }: { label: string; value: React.ReactNode; tone?: 'slate' | 'good' | 'bad' }) {
  const toneClass = tone === 'good' ? 'text-emerald-600' : tone === 'bad' ? 'text-red-500' : 'text-slate-700';
  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <span className="text-sm text-slate-500">{label}</span>
      <span className={`text-sm font-bold font-mono ${toneClass}`}>{value}</span>
    </div>
  );
}

export default function CandelaVisualizer({
  onSwitchToIntervals,
  onSwitchToLinearForm = undefined,
  onSwitchToConstruction = undefined,
}: {
  onSwitchToIntervals: () => void;
  onSwitchToLinearForm?: (setup?: unknown) => void;
  onSwitchToConstruction?: () => void;
}) {
  const [initialSetup] = useState(() => readCandelaSetupFromUrl());
  const [m, setM] = useState(initialSetup.m);
  const [n, setN] = useState(initialSetup.n);
  const [recipe, setRecipe] = useState(initialSetup.recipe);
  const [manualLambda, setManualLambda] = useState(initialSetup.manualLambda);
  const [manualMu, setManualMu] = useState(initialSetup.manualMu);
  const [dilation, setDilation] = useState(initialSetup.dilation);

  const maxN = useMemo(() => maxNForM(m), [m]);
  const p = useMemo(() => pFor(m, n), [m, n]);
  const primeOptions = useMemo(() => possiblePrimeValues(m), [m]);
  const pIsPrime = useMemo(() => isPrime(p), [p]);
  const dilationGcd = useMemo(() => gcd(dilation, p), [dilation, p]);

  const activePreset = useMemo(
    () => getRecipePreset(recipe, m, manualLambda, manualMu),
    [recipe, m, manualLambda, manualMu],
  );

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
    const aTail = multiplySet(rawA.tail, dilation, p);
    const a = multiplySet(rawA.all, dilation, p);
    const ma = multiplySet(a, m, p);
    const aa = sumset(a, p);
    const mixed = differenceSet(aa, ma, p);
    const overlap = intersectionSize(aa, ma);

    return {
      a,
      aTail,
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

  const setMClamped = useCallback((value: number) => {
    setM(clampInt(value, MIN_M, MAX_M, m));
  }, [m]);

  const setNClamped = useCallback((value: number) => {
    setN(clampInt(value, 1, maxNForM(m), n));
  }, [m, n]);

  const handleImportState = useCallback((raw: unknown) => {
    const setup = normalizeCandelaSetup(raw);
    setM(setup.m);
    setN(setup.n);
    setRecipe(setup.recipe);
    setManualLambda(setup.manualLambda);
    setManualMu(setup.manualMu);
    setDilation(setup.dilation);
  }, []);

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
        <VisualizerHeader
          title="Candela Construction Visualizer"
          description={
            <>
              Work in <InlineMath>{'\\mathbb Z/p\\mathbb Z'}</InlineMath> with <InlineMath>{'p=4m^2n+1'}</InlineMath>. The set is built from <InlineMath>{'J=\\{4mn+1,\\ldots,2\\lambda mn\\}'}</InlineMath> by residue classes modulo <InlineMath>{'m'}</InlineMath>, then dilated by <InlineMath>{'c\\ne 0'}</InlineMath>.
            </>
          }
          shareUrl={shareUrl}
          copyText={copyText}
          actions={[
            ...(onSwitchToConstruction ? [{
              label: 'Preimage construction',
              onClick: onSwitchToConstruction,
            }] : []),
            ...(onSwitchToLinearForm ? [{
              label: 'General linear form',
              onClick: () => onSwitchToLinearForm(),
            }] : []),
            {
              label: <><RotateCcw size={16} />Circle intervals</>,
              onClick: onSwitchToIntervals,
              title: 'Open the circle interval visualizer',
            },
          ]}
        />

        <div className="flex flex-col xl:flex-row gap-8 items-start">
          <div className="flex flex-col lg:flex-row gap-8 flex-1 min-w-0 w-full">
            <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col items-center justify-center min-h-[560px]">
              <svg viewBox="-265 -265 530 530" className="w-full max-w-[560px] h-auto overflow-visible">
                <CircleAxes
                  innerRadius={38}
                  outerRadius={228}
                  labelRadius={248}
                  labels={[0, Math.floor(p / 4), Math.floor(p / 2), Math.floor((3 * p) / 4)]}
                />

                <DiscreteRing radius={RADIUS_A} p={p} residues={data.a} color={COLORS.a} accentResidues={data.aTail} accentColor={COLORS.tail} />
                <DiscreteRing radius={RADIUS_MA} p={p} residues={data.ma} color={COLORS.ma} />
                <DiscreteRing radius={RADIUS_SUM} p={p} residues={data.aa} color={COLORS.sum} />
                <DiscreteRing radius={RADIUS_MIXED} p={p} residues={data.mixed} color={COLORS.mixed} />

                <circle cx="0" cy={-RADIUS_MIXED} r="5" fill={data.zeroInMixed ? '#ef4444' : '#0f172a'} stroke="#ffffff" strokeWidth="2" />
              </svg>

              <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 w-full max-w-2xl">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.a }} />
                  <span className="font-bold text-sm text-slate-800">Inner:</span>
                  <span className="text-sm text-slate-600"><InlineMath>{'cA'}</InlineMath></span>
                  <span className="font-bold text-sm text-slate-500 font-mono ml-auto">{data.a.size}</span>
                </div>
                {data.aTail.size > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.tail }} />
                    <span className="font-bold text-sm text-slate-800">Tail:</span>
                    <span className="text-sm text-slate-600"><InlineMath>{'cB'}</InlineMath></span>
                    <span className="font-bold text-sm text-slate-500 font-mono ml-auto">{data.aTail.size}</span>
                  </div>
                )}
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
                          type="button"
                          onClick={() => value === 'manual' ? useCurrentParametersAsManual() : setRecipe(value)}
                          className={`px-3 py-2 rounded-lg border text-sm font-bold transition-colors ${recipe === value ? 'bg-slate-900 text-white border-slate-900' : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'}`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <NumberSlider integer step={1} label="m" value={m} min={MIN_M} max={MAX_M} onChange={setMClamped} />
                  <NumberSlider integer step={1} label="n" value={n} min={1} max={maxN} onChange={setNClamped} />

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

                  <NumberSlider integer step={1} label="lambda" value={lambda} min={3} max={m} onChange={v => setManualLambda(clampInt(v, 3, m, lambda))} disabled={recipe !== 'manual'} />
                  <NumberSlider integer step={1} label="mu" value={mu} min={0} max={m - 1} onChange={v => setManualMu(clampInt(v, 0, m - 1, mu))} disabled={recipe !== 'manual'} />
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <h2 className="font-bold text-lg mb-4">Dilate the Set</h2>
                <NumberSlider integer step={1} label="c" value={dilation} min={1} max={Math.max(1, p - 1)} onChange={v => setDilation(clampInt(v, 1, Math.max(1, p - 1), dilation))} />
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
                <Stat label="|tail|" value={data.aTail.size} />
                <Stat label="|A| / p" value={density.toFixed(6)} />
                <Stat label="|A| / (p - 1)" value={paperDensity.toFixed(6)} />
                <Stat label="|A + A|" value={data.aa.size} />
                <Stat label="|mA|" value={data.ma.size} />
                <Stat label="intersection size" value={data.overlap} tone={data.overlap === 0 ? 'good' : 'bad'} />
                <Stat label="0 in A + A - mA" value={data.zeroInMixed ? 'yes' : 'no'} tone={data.zeroInMixed ? 'bad' : 'good'} />
              </div>
            </div>

            <StateJsonPanel
              stateJson={currentStateJson}
              onImport={handleImportState}
              copyText={copyText}
              placeholder="Paste Candela state JSON"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
