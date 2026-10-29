import React, { useMemo, useState } from 'react';
import { intervalSegments, linearFormSegments, measure, normalizeTurn, wrappedSegments } from './linearFormGeometry';
import type { Interval, Segment } from './linearFormGeometry';

const COLORS = ['#ef4444', '#3b82f6', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4'];
const DEFAULT_STATE = {
  coefficients: [1, 1, -3], missingPoint: 0,
  intervals: [{ id: 1, start: 0.4, width: 0.2, color: COLORS[0] }],
};

export function normalizeLinearFormState(raw) {
  if (!raw || !Array.isArray(raw.coefficients) || !raw.coefficients.length
      || !raw.coefficients.every(value => Number.isSafeInteger(value))) {
    throw new Error('Provide a nonempty list of integer coefficients.');
  }
  if (!Array.isArray(raw.intervals)) throw new Error('State must include an intervals array.');
  const intervals: Interval[] = raw.intervals.map((item, index) => {
    if (!Number.isFinite(item?.start) || !Number.isFinite(item?.width) || item.width < 0 || item.width > 1) {
      throw new Error('Interval starts and widths must be finite; widths must lie between 0 and 1.');
    }
    return {
      id: index + 1, start: normalizeTurn(item.start), width: item.width,
      color: /^#[0-9a-f]{6}$/i.test(item.color) ? item.color : COLORS[index % COLORS.length],
    };
  });
  const missingPoint = raw.missingPoint ?? 0;
  if (!Number.isFinite(missingPoint)) throw new Error('The missing point must be finite.');
  return { coefficients: [...raw.coefficients], intervals, missingPoint: normalizeTurn(missingPoint) };
}

function point(radius, turn) {
  return { x: radius * Math.sin(2 * Math.PI * turn), y: -radius * Math.cos(2 * Math.PI * turn) };
}

function SegmentArc({ segment, radius, color }: { segment: Segment; radius: number; color: string }) {
  const [start, end] = segment;
  if (end - start >= 1 - 1e-12) return <circle r={radius} fill="none" stroke={color} strokeWidth={14} />;
  const a = point(radius, start);
  if (end - start <= 1e-12) return <circle cx={a.x} cy={a.y} r={4} fill={color} />;
  const b = point(radius, end);
  return <path d={`M ${a.x} ${a.y} A ${radius} ${radius} 0 ${end - start > 0.5 ? 1 : 0} 1 ${b.x} ${b.y}`} fill="none" stroke={color} strokeWidth={14} />;
}

export default function LinearFormVisualizer({ initialState, buildShareUrl, copyText, onSwitchToIntervals }) {
  const [loaded] = useState(() => {
    try { return { setup: normalizeLinearFormState(initialState ?? DEFAULT_STATE), error: '' }; }
    catch (error) {
      return { setup: normalizeLinearFormState(DEFAULT_STATE), error: `Could not load the shared configuration: ${error.message} The example below is shown instead.` };
    }
  });
  const [setup, setSetup] = useState(loaded.setup);
  const [loadError, setLoadError] = useState(loaded.error);
  const [coefficientText, setCoefficientText] = useState(setup.coefficients.join(', '));
  const [inputJson, setInputJson] = useState('');
  const [status, setStatus] = useState('');
  const aSegments = useMemo(() => intervalSegments(setup.intervals), [setup.intervals]);
  const image = useMemo(() => {
    try { return { segments: linearFormSegments(setup.intervals, setup.coefficients), error: '' }; }
    catch (error) { return { segments: [] as Segment[], error: String(error.message) }; }
  }, [setup]);
  const density = measure(aSegments);
  const state = { v: 1, mode: 'linear-form', ...setup, fixTotalLength: false, targetTotalLength: density, hiddenMixedComboKeys: [] };
  const stateJson = JSON.stringify(state, null, 2);
  const shareUrl = buildShareUrl(state);
  const marker = point(170, setup.missingPoint);
  const textClass = 'border border-slate-300 rounded-md px-2 py-1 w-full bg-white';
  const buttonClass = 'border border-slate-300 rounded-lg px-3 py-2 bg-white hover:bg-slate-100 text-sm font-semibold';

  function updateInterval(index, field, value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return;
    setSetup(previous => ({ ...previous, intervals: previous.intervals.map((interval, i) => (
      i === index ? { ...interval, [field]: field === 'start' ? normalizeTurn(numeric) : Math.min(1, Math.max(0, numeric)) } : interval
    )) }));
  }

  async function copy(value, description) {
    try { await copyText(value); setStatus(`${description} copied.`); }
    catch { setStatus('Copy failed. Select and copy the state JSON below.'); }
  }

  return <main className="min-h-screen bg-slate-50 text-slate-800 font-sans p-4 md:p-8">
    <div className="max-w-6xl mx-auto">
      <header className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <div><h1 className="text-3xl font-bold mb-2">Linear Form Visualizer</h1>
          <p className="text-slate-600">Explore L(A) = c₁A + ··· + cₖA on the circle ℝ/ℤ.</p></div>
        <div className="flex flex-wrap gap-2"><button className={buttonClass} onClick={onSwitchToIntervals}>A + A − mA visualizer</button>
          <button className={buttonClass} onClick={() => copy(shareUrl, 'Link')}>Copy link</button></div>
      </header>
      {loadError && <p role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{loadError}</p>}
      <div className="grid lg:grid-cols-2 gap-6">
        <section className="bg-white border border-slate-200 rounded-xl p-5">
          <svg viewBox="-210 -210 420 420" role="img" aria-label="Circle showing A on the inner ring, its linear image on the outer ring, and the chosen missing point" className="w-full max-w-lg mx-auto">
            {[100, 160].map(radius => <circle key={radius} r={radius} stroke="#e2e8f0" strokeWidth={14} fill="none" />)}
            {setup.intervals.flatMap(interval => wrappedSegments(interval.start, interval.start + interval.width).map((segment, index) => (
              <SegmentArc key={`${interval.id}-${index}`} segment={segment} radius={100} color={interval.color} />
            )))}
            {image.segments.map((segment, index) => <SegmentArc key={index} segment={segment} radius={160} color="#7c3aed" />)}
            {[0, 0.25, 0.5, 0.75].map(turn => {
              const position = point(195, turn);
              return <text key={turn} x={position.x} y={position.y} textAnchor="middle" dominantBaseline="middle" fontSize={13} fill="#64748b">{turn}</text>;
            })}
            <line x1={marker.x * 0.84} y1={marker.y * 0.84} x2={marker.x * 1.04} y2={marker.y * 1.04} stroke="#0f172a" strokeWidth={3} />
            <circle cx={marker.x} cy={marker.y} r={4} fill="#0f172a" />
            <text y={-8} textAnchor="middle" fontSize={14} fill="#64748b">Density of A</text>
            <text y={24} textAnchor="middle" fontSize={27} fontWeight="bold">{density.toPrecision(9)}</text>
          </svg>
          <div className="flex flex-wrap gap-4 justify-center text-sm"><span>Inner ring: A</span><span className="text-violet-700">Outer ring: L(A)</span><span>Black mark: missing point</span></div>
          {image.error ? <p className="text-amber-800 mt-4" role="alert">{image.error}</p>
            : <p className="text-sm text-slate-600 text-center mt-4">Measure of L(A): {measure(image.segments).toPrecision(9)}</p>}
          <p className="text-xs text-slate-500 mt-4">Closed endpoints and zero-width intervals are shown. With ε = 0, a solver solution may touch the marked point; the numerical supremum need not itself be a strict avoidance construction.</p>
        </section>
        <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-5">
          <form onSubmit={event => {
            event.preventDefault();
            try {
              const tokens = coefficientText.trim().split(/[\s,]+/);
              if (!coefficientText.trim() || tokens.some(token => !/^[+-]?\d+$/.test(token))) throw new Error('Use integer coefficients separated by spaces or commas.');
              setSetup(normalizeLinearFormState({ ...setup, coefficients: tokens.map(Number) })); setLoadError(''); setStatus('Coefficients updated.');
            } catch (error) { setStatus(error.message); }
          }}>
            <label className="block text-sm font-semibold mb-2" htmlFor="linear-coefficients">Integer coefficients</label>
            <div className="flex gap-2"><input id="linear-coefficients" className={textClass} value={coefficientText} onChange={event => setCoefficientText(event.target.value)} />
              <button className={buttonClass} type="submit">Apply</button></div>
            <p className="text-xs text-slate-500 mt-2">Each coefficient acts on one independently chosen point of A. For example: 1, 1, −3.</p>
          </form>
          <label className="block text-sm font-semibold">Missing point (mod 1)
            <input className={`${textClass} mt-2`} type="number" step="any" value={setup.missingPoint} onChange={event => {
              const value = Number(event.target.value);
              if (Number.isFinite(value)) setSetup({ ...setup, missingPoint: normalizeTurn(value) });
            }} /></label>
          <div><h2 className="font-semibold mb-2">Intervals</h2><div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="text-left"><th className="p-1">Interval</th><th className="p-1">Start</th><th className="p-1">Width</th><th /></tr></thead>
            <tbody>{setup.intervals.map((interval, index) => <tr key={interval.id}>
              <td className="p-1 font-semibold" style={{ color: interval.color }}>I{index}</td>
              <td className="p-1"><input aria-label={`Start of interval ${index}`} className={textClass} type="number" step="any" value={interval.start} onChange={event => updateInterval(index, 'start', event.target.value)} /></td>
              <td className="p-1"><input aria-label={`Width of interval ${index}`} className={textClass} type="number" min={0} max={1} step="any" value={interval.width} onChange={event => updateInterval(index, 'width', event.target.value)} /></td>
              <td className="p-1"><button aria-label={`Delete interval ${index}`} className="text-red-600 px-2" onClick={() => setSetup({ ...setup, intervals: setup.intervals.filter((_, i) => i !== index) })}>×</button></td>
            </tr>)}</tbody></table></div>
            <button className={`${buttonClass} mt-3`} onClick={() => setSetup({ ...setup, intervals: [...setup.intervals, { id: Math.max(0, ...setup.intervals.map(interval => interval.id)) + 1, start: 0, width: 0.05, color: COLORS[setup.intervals.length % COLORS.length] }] })}>Add interval</button>
          </div>
          <p className="text-xs text-slate-500">Editing the picture does not rerun the optimizer. Density is the measure of the union, including any overlaps introduced by edits.</p>
        </section>
      </div>
      <section className="mt-6 bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold mb-3">Share or import a configuration</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div><label htmlFor="linear-export" className="text-sm">Current state</label><textarea id="linear-export" className={`${textClass} mt-2 font-mono text-xs`} rows={8} readOnly value={stateJson} />
            <button className={`${buttonClass} mt-2`} onClick={() => copy(stateJson, 'State JSON')}>Copy JSON</button></div>
          <div><label htmlFor="linear-import" className="text-sm">Import state JSON</label><textarea id="linear-import" className={`${textClass} mt-2 font-mono text-xs`} rows={8} value={inputJson} onChange={event => setInputJson(event.target.value)} />
            <button className={`${buttonClass} mt-2`} onClick={() => {
              try {
                const imported = normalizeLinearFormState(JSON.parse(inputJson));
                setSetup(imported); setCoefficientText(imported.coefficients.join(', ')); setLoadError(''); setStatus('State imported.');
              } catch (error) { setStatus(`Import failed: ${error.message}`); }
            }}>Import JSON</button></div>
        </div><p role="status" className="mt-3 text-sm text-slate-600">{status}</p>
      </section>
    </div>
  </main>;
}
