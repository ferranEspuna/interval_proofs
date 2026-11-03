import React, { useMemo, useRef, useState } from 'react';
import { normalizeTurn, wrappedSegments } from './linearFormGeometry';
import type { Segment } from './linearFormGeometry';
import {
  defaultConstructionState, evaluateConstruction, findGuaranteedShift,
  groupCoefficients, normalizeConstructionState, resetOptimalWidths,
} from './preimageConstruction';
import type { ConstructionState, ConstructionTarget, OpenCircleSet } from './preimageConstruction';

const buttonClass = 'border border-slate-300 rounded-lg px-3 py-2 bg-white hover:bg-slate-100 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed';
const fieldClass = 'border border-slate-300 rounded-md px-2 py-1.5 w-full bg-white';
const format = (value: number) => Number.isFinite(value) ? Number(value.toPrecision(9)).toString() : '—';
const message = (error: unknown) => error instanceof Error ? error.message : String(error);

function point(radius: number, turn: number) {
  return { x: radius * Math.sin(2 * Math.PI * turn), y: -radius * Math.cos(2 * Math.PI * turn) };
}

function Arc({ segment, radius, color, thickness }: {
  segment: Segment; radius: number; color: string; thickness: number;
}) {
  const [start, end] = segment;
  if (end <= start) return null;
  if (end - start >= 1 - 1e-12) return <circle r={radius} fill="none" stroke={color} strokeWidth={thickness} />;
  const a = point(radius, start);
  const b = point(radius, end);
  return <path d={`M ${a.x} ${a.y} A ${radius} ${radius} 0 ${end - start > 0.5 ? 1 : 0} 1 ${b.x} ${b.y}`}
    fill="none" stroke={color} strokeWidth={thickness} />;
}

function SetRing({ set, radius, color, thickness = 10, endpoints = true }: {
  set: OpenCircleSet; radius: number; color: string; thickness?: number; endpoints?: boolean;
}) {
  if (set.full) return <circle r={radius} fill="none" stroke={color} strokeWidth={thickness} />;
  return <g>
    {set.arcs.flatMap((arc, i) => wrappedSegments(arc.start, arc.start + arc.width).map((segment, j) => (
      <Arc key={`${i}-${j}`} segment={segment} radius={radius} color={color} thickness={thickness} />
    )))}
    {endpoints && set.arcs.flatMap((arc, i) => arc.width > 0
      ? [arc.start, arc.start + arc.width].map((turn, j) => {
        const p = point(radius, turn);
        return <circle key={`${i}-${j}`} cx={p.x} cy={p.y} r={Math.max(1.8, thickness * 0.22)}
          fill="white" stroke={color} strokeWidth={1.2} />;
      }) : [])}
    {set.points.map((turn, i) => {
      const p = point(radius, turn);
      return <circle key={`point-${i}`} cx={p.x} cy={p.y} r={4} fill={color} />;
    })}
  </g>;
}

function initialConstruction(raw): ConstructionState {
  if (!raw) return defaultConstructionState();
  if (typeof raw !== 'object' || Array.isArray(raw)) throw new Error('Provide a construction state object.');
  if (raw.mode === 'preimage-construction' || Object.prototype.hasOwnProperty.call(raw, 'targets')) {
    return normalizeConstructionState(raw);
  }
  // Switching from the free linear-form page retains its chosen form.
  return defaultConstructionState(raw.coefficients);
}

export default function PreimageConstructionVisualizer({
  initialState, buildShareUrl, copyText, onSwitchToLinearForm, onSwitchToIntervals,
}) {
  const [loaded] = useState(() => {
    try { return { setup: initialConstruction(initialState), error: '' }; }
    catch (error) {
      return { setup: defaultConstructionState(), error: `Could not load the construction: ${message(error)} The example below is shown instead.` };
    }
  });
  const [setup, setSetup] = useState<ConstructionState>(loaded.setup);
  const [coefficientText, setCoefficientText] = useState(setup.coefficients.join(', '));
  const [loadError, setLoadError] = useState(loaded.error);
  const [status, setStatus] = useState('');
  const [inputJson, setInputJson] = useState('');
  const [dragging, setDragging] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ coefficient: number; pointerId: number; offset: number } | null>(null);
  const computed = useMemo(() => {
    try { return { result: evaluateConstruction(setup), error: '' }; }
    catch (error) { return { result: null, error: message(error) }; }
  }, [setup]);
  const result = computed.result;
  const groups = useMemo(() => groupCoefficients(setup.coefficients), [setup.coefficients]);
  const multiplicity = new Map(groups.map(group => [group.coefficient, group.multiplicity]));
  const groupCount = groups.length;
  const optimal = setup.targets.every(target => Math.abs(target.width - 1 / (groupCount * multiplicity.get(target.coefficient)!)) < 1e-12);
  const aRadius = 90 + setup.targets.length * 44;
  const imageRadius = aRadius + 42;
  const extent = imageRadius + 40;
  const state = { v: 1, mode: 'preimage-construction', ...setup };
  const stateJson = JSON.stringify(state, null, 2);
  const shareUrl = buildShareUrl(state);
  const witness = result?.missingPoint;
  const isEmpty = result && !result.a.full && !result.a.arcs.length && !result.a.points.length;

  function updateTarget(coefficient: number, field: 'start' | 'width', value: number) {
    if (!Number.isFinite(value)) return;
    setSetup(previous => ({
      ...previous,
      targets: previous.targets.map(target => target.coefficient === coefficient
        ? { ...target, [field]: field === 'start' ? normalizeTurn(value) : Math.min(1, Math.max(0, value)) }
        : target),
    }));
    setStatus('');
  }

  function pointerTurn(event: React.PointerEvent<SVGElement>) {
    const svg = svgRef.current;
    const transform = svg?.getScreenCTM();
    if (!svg || !transform) return null;
    const cursor = svg.createSVGPoint();
    cursor.x = event.clientX;
    cursor.y = event.clientY;
    const local = cursor.matrixTransform(transform.inverse());
    return normalizeTurn(Math.atan2(local.x, -local.y) / (2 * Math.PI));
  }

  function startDrag(event: React.PointerEvent<SVGElement>, target: ConstructionTarget) {
    if (event.button !== 0 || dragRef.current) return;
    const turn = pointerTurn(event);
    if (turn === null) return;
    event.preventDefault();
    svgRef.current!.setPointerCapture(event.pointerId);
    dragRef.current = { coefficient: target.coefficient, pointerId: event.pointerId, offset: turn - target.start };
    setDragging(target.coefficient);
  }

  function moveDrag(event: React.PointerEvent<SVGSVGElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (event.pointerType === 'mouse' && (event.buttons & 1) === 0) {
      finishDrag(event);
      return;
    }
    const turn = pointerTurn(event);
    if (turn !== null) updateTarget(drag.coefficient, 'start', turn - drag.offset);
  }

  function finishDrag(event: React.PointerEvent<SVGSVGElement>) {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    dragRef.current = null;
    setDragging(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }

  async function copy(value: string, description: string) {
    try { await copyText(value); setStatus(`${description} copied.`); }
    catch { setStatus('Copy failed. Select and copy the configuration JSON below.'); }
  }

  function findShift() {
    try {
      const next = findGuaranteedShift(setup);
      setSetup(next);
      setStatus('Optimal widths restored and a partition shift attaining the density bound selected.');
      setLoadError('');
    } catch (error) { setStatus(message(error)); }
  }

  return <main className="min-h-screen bg-slate-50 text-slate-800 font-sans p-4 md:p-8">
    <div className="max-w-7xl mx-auto">
      <header className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-widest font-semibold text-indigo-700 mb-2">Explicit construction</p>
          <h1 className="text-3xl font-bold mb-2">Preimage intersection construction</h1>
          <p className="text-slate-600">Choose target intervals I<sub>d</sub>, form A = ⋂ d<sup>−1</sup>(I<sub>d</sub>), and see L(A) on the outer ring.</p>
        </div>
        <nav aria-label="Visualizer pages" className="flex flex-wrap gap-2">
          <button className={buttonClass} disabled={!result} onClick={() => onSwitchToLinearForm(result ? {
            coefficients: setup.coefficients, intervals: result.intervals, missingPoint: result.missingPoint ?? 0,
          } : { coefficients: setup.coefficients, intervals: [], missingPoint: 0 })}>Linear form visualizer</button>
          <button className={buttonClass} onClick={onSwitchToIntervals}>A + A − mA visualizer</button>
          <button className={buttonClass} onClick={() => copy(shareUrl, 'Link')}>Copy link</button>
        </nav>
      </header>
      {loadError && <p role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{loadError}</p>}

      <div className="grid xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,1fr)] gap-6 items-start">
        <section className="bg-white border border-slate-200 rounded-xl p-4 md:p-6">
          <h2 className="font-semibold mb-1">Targets → preimages → intersection → image</h2>
          <p className="text-sm text-slate-500 mb-3">Drag a thick colored target ring. Thin rings show its preimage.</p>
          <svg ref={svgRef} viewBox={`${-extent} ${-extent} ${2 * extent} ${2 * extent}`}
            role="group" aria-label="Interactive construction: target and preimage rings inside A and its linear-form image"
            className={`w-full mx-auto touch-none select-none ${dragging === null ? '' : 'cursor-grabbing'}`}
            onPointerMove={moveDrag} onPointerUp={finishDrag} onPointerCancel={finishDrag} onLostPointerCapture={finishDrag}>
            <title>Preimage intersection construction on the circle</title>
            <desc>Each pair of inner rings shows a target open interval and its preimage under multiplication by its absolute coefficient. The next to outer ring is A; the outer ring is L(A).</desc>
            {setup.targets.map((target, i) => {
              const radius = 70 + i * 44;
              const preimage = result?.preimages[i];
              return <g key={target.coefficient}>
                <g data-target-coefficient={target.coefficient} data-ring-radius={radius}
                  tabIndex={0} role="slider" aria-label={`Shift target interval for coefficient ${target.coefficient}`}
                  aria-valuemin={0} aria-valuemax={1} aria-valuenow={target.start}
                  aria-valuetext={`${format(target.start)} turns; use arrow keys to shift`}
                  className={`outline-none focus:opacity-70 ${dragging === target.coefficient ? 'cursor-grabbing' : 'cursor-grab'}`}
                  onPointerDown={event => startDrag(event, target)}
                  onKeyDown={event => {
                    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
                    event.preventDefault();
                    const direction = event.key === 'ArrowRight' || event.key === 'ArrowUp' ? 1 : -1;
                    updateTarget(target.coefficient, 'start', target.start + direction * (event.shiftKey ? 0.01 : 0.001));
                  }}>
                  <circle r={radius} fill="none" stroke="#e2e8f0" strokeWidth={12} />
                  <SetRing set={{ arcs: target.width ? [{ start: target.start, width: target.width }] : [], full: false, points: [] }}
                    radius={radius} color={target.color} thickness={12} />
                  <circle r={radius} fill="none" stroke="transparent" strokeWidth={18} />
                </g>
                <circle r={radius + 19} fill="none" stroke="#f1f5f9" strokeWidth={6} />
                {preimage && <g opacity={0.65}><SetRing set={preimage} radius={radius + 19} color={target.color} thickness={6} /></g>}
              </g>;
            })}
            <circle r={aRadius} fill="none" stroke="#e2e8f0" strokeWidth={13} />
            <circle r={imageRadius} fill="none" stroke="#e2e8f0" strokeWidth={13} />
            {result && <>
              <SetRing set={result.a} radius={aRadius} color="#0f766e" thickness={13} />
              <SetRing set={result.image} radius={imageRadius} color="#7c3aed" thickness={13} />
            </>}
            {[0, 0.25, 0.5, 0.75].map(turn => {
              const p = point(imageRadius + 29, turn);
              return <text key={turn} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle" fontSize={12} fill="#64748b">{turn}</text>;
            })}
            {witness != null && (() => {
              const inner = point(imageRadius - 12, witness);
              const outer = point(imageRadius + 13, witness);
              const marker = point(imageRadius, witness);
              return <g aria-label={`Missing point ${format(witness)}`}>
                <line x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="#0f172a" strokeWidth={2.5} />
                <circle cx={marker.x} cy={marker.y} r={4.5} fill="white" stroke="#0f172a" strokeWidth={2} />
              </g>;
            })()}
            <text y={-9} textAnchor="middle" fontSize={11} fill="#64748b">Measure of A</text>
            <text y={14} textAnchor="middle" fontSize={19} fontWeight="bold" fill="#0f766e">{result ? format(result.density) : '—'}</text>
          </svg>
          <div className="flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm">
            <span className="text-teal-700 font-semibold">Next to outer ring: A</span>
            <span className="text-violet-700 font-semibold">Outermost: L(A)</span>
            <span>Black mark: missing point</span>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-5">
            <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Measure of L(A)</p>
              <p className="font-mono text-lg mt-1">{result ? format(result.imageMeasure) : '—'}</p></div>
            <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Missing point (mod 1)</p>
              <p className="font-mono text-lg mt-1">{result ? witness == null ? 'None' : format(witness) : '—'}</p></div>
          </div>
          {computed.error ? <p className="mt-4 text-sm text-red-800" role="alert">{computed.error}</p>
            : result?.image.full ? <p className="mt-4 text-sm text-amber-800">L(A) covers the whole circle. There is no missing point for these widths and shifts.</p>
            : isEmpty ? <p className="mt-4 text-sm text-amber-800">A is empty for these shifts. Use “Find guaranteed shift” to obtain a set with the guaranteed positive measure.</p>
            : <p className="mt-4 text-sm text-teal-800">The marked point lies outside L(A). {result?.imageMeasure === 1 ? 'Measure one can still leave excluded endpoints.' : ''}</p>}
          <p className="mt-3 text-xs text-slate-500">Intervals are open; hollow endpoints are excluded. This page calculates with floating-point coordinates. Use the Python construction for exact rational verification.</p>
        </section>

        <div className="space-y-6">
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <form onSubmit={event => {
              event.preventDefault();
              try {
                const tokens = coefficientText.trim().split(/[\s,]+/);
                if (!coefficientText.trim() || tokens.some(token => !/^[+-]?\d+$/.test(token))) throw new Error('Use integer coefficients separated by spaces or commas.');
                const next = defaultConstructionState(tokens.map(Number));
                setSetup(next); setLoadError(''); setStatus('Form updated with optimal widths and a guaranteed shift.');
              } catch (error) { setStatus(message(error)); }
            }}>
              <label htmlFor="construction-coefficients" className="block font-semibold mb-2">Integer coefficients of L</label>
              <div className="flex gap-2"><input id="construction-coefficients" className={fieldClass} value={coefficientText}
                onChange={event => setCoefficientText(event.target.value)} /><button type="submit" className={buttonClass}>Apply</button></div>
            </form>
            <p className="text-xs text-slate-500 mt-3">Each coefficient acts on an independent point of A. Equal absolute coefficients share one target; negative terms use its reflection. Zero terms impose no constraint.</p>
          </section>

          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="font-semibold mb-4">Target intervals and shifts</h2>
            {!setup.targets.length && <p className="text-sm text-slate-600">All coefficients are zero. There are no target constraints: A is the full circle and L(A) is the single point 0.</p>}
            <div className="space-y-5">
              {setup.targets.map((target, i) => <div key={target.coefficient} className="border-l-4 pl-3" style={{ borderColor: target.color }}>
                <div className="flex flex-wrap justify-between gap-2 mb-2 text-sm">
                  <h3 className="font-semibold" style={{ color: target.color }}>I<sub>{target.coefficient}</sub> · {target.coefficient}x mod 1</h3>
                  <span className="text-slate-500">{multiplicity.get(target.coefficient)} term{multiplicity.get(target.coefficient) === 1 ? '' : 's'} · rings {2 * i + 1}–{2 * i + 2}</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <label className="text-xs text-slate-600">Start / shift
                    <input aria-label={`Start of target ${target.coefficient}`} type="number" step="any" value={target.start}
                      className={`${fieldClass} mt-1 text-sm`} onChange={event => updateTarget(target.coefficient, 'start', Number(event.target.value))} />
                    <input aria-label={`Shift target ${target.coefficient}`} className="w-full mt-2" type="range" min={0} max={1} step={0.001}
                      value={target.start} onChange={event => updateTarget(target.coefficient, 'start', Number(event.target.value))} />
                  </label>
                  <label className="text-xs text-slate-600">Width
                    <input aria-label={`Width of target ${target.coefficient}`} type="number" min={0} max={1} step="any" value={target.width}
                      className={`${fieldClass} mt-1 text-sm`} onChange={event => updateTarget(target.coefficient, 'width', Number(event.target.value))} />
                    <input aria-label={`Resize target ${target.coefficient}`} className="w-full mt-2" type="range" min={0} max={1} step={0.001}
                      value={target.width} onChange={event => updateTarget(target.coefficient, 'width', Number(event.target.value))} />
                  </label>
                </div>
                <p className="text-xs text-slate-500">Optimal width: 1/{groupCount * multiplicity.get(target.coefficient)!}.
                  {' '}Preimage: up to {target.coefficient} open arcs, each of width {format(target.width / target.coefficient)}.</p>
              </div>)}
            </div>
            <div className="flex flex-wrap gap-2 mt-5">
              <button className={buttonClass} onClick={() => {
                try { setSetup(resetOptimalWidths(setup)); setStatus('Optimal widths restored; target shifts retained.'); }
                catch (error) { setStatus(message(error)); }
              }}>Reset optimal widths</button>
              <button className="rounded-lg px-3 py-2 text-sm font-semibold bg-indigo-700 text-white hover:bg-indigo-800" onClick={findShift}>Find guaranteed shift</button>
            </div>
          </section>

          <section className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
            <h2 className="font-semibold text-indigo-950 mb-3">Why this construction has a missing point</h2>
            {groupCount ? <>
              <p className="text-sm text-indigo-950">With g = {groupCount} distinct absolute coefficients and multiplicities r<sub>d</sub>, the optimal target widths are w<sub>d</sub> = 1/(g r<sub>d</sub>).</p>
              <p className="text-sm text-indigo-950 mt-2">If Σ r<sub>d</sub>w<sub>d</sub> ≤ 1, the signed sum of target intervals leaves a point out. Since L(A) lies in that sum, every choice of shifts has a missing point.</p>
              <p className="text-sm text-indigo-950 mt-2">At the optimal widths, the preimages of the interval partitions partition the circle up to endpoints. Pigeonhole gives a choice with measure of A ≥ ∏ w<sub>d</sub>. “Find guaranteed shift” selects a largest such cell.</p>
            </> : <p className="text-sm text-indigo-950">The zero form always has image {'{0}'} on a nonempty A, so any other point is missing.</p>}
            <dl className="text-sm grid grid-cols-2 gap-3 mt-4">
              <div><dt className="text-indigo-700">Weighted width Σ r<sub>d</sub>w<sub>d</sub></dt><dd className="font-mono font-semibold mt-1">{result ? format(result.boundWidth) : '—'}</dd></div>
              <div><dt className="text-indigo-700">Guaranteed density at optimal widths</dt><dd className="font-mono font-semibold mt-1">{result ? format(result.guaranteedDensity) : '—'}</dd></div>
            </dl>
            {result && <p className="text-xs text-indigo-950 mt-3">{optimal ? 'Optimal widths are active.' : 'Widths have been changed.'}{' '}
              {result.widthGuarantee ? 'The target-width condition guarantees a missing point.' : 'The target-width condition does not guarantee avoidance; the outer ring shows the computed image.'}</p>}
          </section>
        </div>
      </div>

      <section className="mt-6 bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold mb-3">Share or import this construction</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div><label htmlFor="construction-export" className="text-sm">Current targets and coefficients</label>
            <textarea id="construction-export" className={`${fieldClass} mt-2 font-mono text-xs`} rows={7} readOnly value={stateJson} />
            <button className={`${buttonClass} mt-2`} onClick={() => copy(stateJson, 'Configuration JSON')}>Copy JSON</button></div>
          <div><label htmlFor="construction-import" className="text-sm">Import construction JSON</label>
            <textarea id="construction-import" className={`${fieldClass} mt-2 font-mono text-xs`} rows={7} value={inputJson} onChange={event => setInputJson(event.target.value)} />
            <button className={`${buttonClass} mt-2`} onClick={() => {
              try {
                const next = normalizeConstructionState(JSON.parse(inputJson));
                setSetup(next); setCoefficientText(next.coefficients.join(', ')); setLoadError(''); setStatus('Construction imported.');
              } catch (error) { setStatus(`Import failed: ${message(error)}`); }
            }}>Import JSON</button></div>
        </div>
        <p role="status" aria-live="polite" className="mt-3 text-sm text-slate-600">{status}</p>
      </section>
    </div>
  </main>;
}
