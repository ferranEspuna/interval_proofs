import React, { useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { normalizeTurn, wrappedSegments } from './linearFormGeometry';
import {
  defaultConstructionState, evaluateConstruction, findGuaranteedShift,
  getTargetIntervals, groupCoefficients, makeConstructionTarget,
  MAX_PREIMAGE_ARCS, normalizeConstructionState, openCircleSet,
  resetOptimalWidths, serializeConstructionState, setMeasure,
  suggestNewInterval, suggestNewMultiplier,
} from './preimageConstruction';
import type { ConstructionState, OpenArc, OpenCircleSet } from './preimageConstruction';
import {
  buildShareUrl as defaultBuildShareUrl, circlePoint,
  copyText as defaultCopyText, errorMessage, fallbackColor, formatNumericValue,
} from './shared';
import {
  BUTTON_CLASS, CircleArc, CircleAxes, CircleMarker, CoefficientsForm,
  ConfirmDeleteButton, DeferredNumberInput, NumberSlider, StateJsonPanel,
  useCircleDrag, VisualizerHeader,
} from './ui';

const format = (value: number) => formatNumericValue(value, 9);

function OpenEndpoints({ arcs, radius, color, thickness }: {
  arcs: OpenArc[]; radius: number; color: string; thickness: number;
}) {
  return (
    <>
      {arcs.flatMap((arc, i) => (
        arc.width > 0
          ? [arc.start, arc.start + arc.width].map((turn, j) => {
            const p = circlePoint(radius, turn);
            return (
              <circle
                key={`ep-${i}-${j}`}
                cx={p.x}
                cy={p.y}
                r={Math.max(1.8, thickness * 0.22)}
                fill="white"
                stroke={color}
                strokeWidth={1.2}
                style={{ pointerEvents: 'none' }}
              />
            );
          })
          : []
      ))}
    </>
  );
}

function SetRing({
  set,
  radius,
  color,
  thickness = 10,
  endpoints = true,
}: {
  set: OpenCircleSet;
  radius: number;
  color: string;
  thickness?: number;
  endpoints?: boolean;
}) {
  if (set.full) return <circle r={radius} fill="none" stroke={color} strokeWidth={thickness} />;
  return (
    <g>
      {set.arcs.flatMap((arc, i) => wrappedSegments(arc.start, arc.start + arc.width).map((segment, j) => (
        <CircleArc
          key={`${i}-${j}`}
          radius={radius}
          start={segment[0]}
          end={segment[1]}
          color={color}
          strokeWidth={thickness}
        />
      )))}
      {endpoints && <OpenEndpoints arcs={set.arcs} radius={radius} color={color} thickness={thickness} />}
      {set.points.map((turn, i) => {
        const p = circlePoint(radius, turn);
        return <circle key={`point-${i}`} cx={p.x} cy={p.y} r={4} fill={color} />;
      })}
    </g>
  );
}

function initialConstruction(raw: any): ConstructionState {
  if (!raw) return defaultConstructionState();
  if (typeof raw !== 'object' || Array.isArray(raw)) throw new Error('Provide a construction state object.');
  if (raw.mode === 'preimage-construction' || Object.prototype.hasOwnProperty.call(raw, 'targets')) {
    return normalizeConstructionState(raw);
  }
  // Switching from the free linear-form page retains its chosen form.
  return defaultConstructionState(raw.coefficients);
}

type DragPayload = {
  targetIndex: number;
  intervalIndex: number | null;
  initialStarts: number[];
};

export default function PreimageConstructionVisualizer({
  initialState,
  buildShareUrl = defaultBuildShareUrl,
  copyText = defaultCopyText,
  onSwitchToLinearForm,
  onSwitchToIntervals,
  onSwitchToCandela = undefined,
}: {
  initialState?: unknown;
  buildShareUrl?: (state: unknown) => string;
  copyText?: (text: string) => Promise<void>;
  onSwitchToLinearForm: (setup: unknown) => void;
  onSwitchToIntervals: () => void;
  onSwitchToCandela?: () => void;
}) {
  const [loaded] = useState(() => {
    try { return { setup: initialConstruction(initialState), error: '' }; }
    catch (error) {
      return {
        setup: defaultConstructionState(),
        error: `Could not load the construction: ${errorMessage(error)} The example below is shown instead.`,
      };
    }
  });
  const [setup, setSetup] = useState<ConstructionState>(loaded.setup);
  const [coefficientText, setCoefficientText] = useState(setup.coefficients.join(', '));
  const [loadError, setLoadError] = useState(loaded.error);
  const [status, setStatus] = useState('');

  const { svgRef, activePayload: dragPayload, startDrag, svgHandlers } = useCircleDrag<DragPayload>(
    (payload, turn, startTurn) => {
      const delta = turn - startTurn;
      setSetup(previous => ({
        ...previous,
        targets: previous.targets.map((target, tIndex) => {
          if (tIndex !== payload.targetIndex) return target;
          const arcs = getTargetIntervals(target);
          const nextArcs = arcs.map((arc, iIndex) => (
            payload.intervalIndex === null || payload.intervalIndex === iIndex
              ? { ...arc, start: normalizeTurn((payload.initialStarts[iIndex] ?? arc.start) + delta) }
              : arc
          ));
          return makeConstructionTarget(target.coefficient, nextArcs, target.color);
        }),
      }));
      setStatus('');
    },
  );

  const computed = useMemo(() => {
    try { return { result: evaluateConstruction(setup), error: '' }; }
    catch (error) { return { result: null, error: errorMessage(error) }; }
  }, [setup]);
  const result = computed.result;
  const groups = useMemo(() => groupCoefficients(setup.coefficients), [setup.coefficients]);
  const multiplicity = new Map(groups.map(group => [group.coefficient, group.multiplicity]));
  const groupCount = groups.length;
  const isCanonical = result?.isCanonical ?? false;
  const optimal = isCanonical && setup.targets.every(target => (
    Math.abs(target.width - 1 / (groupCount * multiplicity.get(target.coefficient)!)) < 1e-12
  ));
  const aRadius = 90 + setup.targets.length * 44;
  const imageRadius = aRadius + 42;
  const extent = imageRadius + 40;
  const serialized = useMemo(() => serializeConstructionState(setup), [setup]);
  const stateJson = useMemo(() => JSON.stringify(serialized, null, 2), [serialized]);
  const shareUrl = useMemo(() => buildShareUrl(serialized), [buildShareUrl, serialized]);
  const witness = result?.missingPoint;
  const isEmpty = result && !result.a.full && !result.a.arcs.length && !result.a.points.length;
  const canRemoveTarget = setup.targets.length > 1 || groupCount === 0;

  function mutateTarget(
    targetIndex: number,
    updater: (target: ConstructionState['targets'][number], intervals: OpenArc[]) => ConstructionState['targets'][number],
  ) {
    setSetup(previous => ({
      ...previous,
      targets: previous.targets.map((target, index) => (
        index === targetIndex ? updater(target, getTargetIntervals(target)) : target
      )),
    }));
    setStatus('');
  }

  function updateIntervalField(targetIndex: number, intervalIndex: number, field: 'start' | 'width', value: number) {
    if (!Number.isFinite(value)) return;
    mutateTarget(targetIndex, (target, intervals) => {
      const nextArcs = intervals.map((arc, i) => (
        i === intervalIndex
          ? { ...arc, [field]: field === 'start' ? normalizeTurn(value) : Math.min(1, Math.max(0, value)) }
          : arc
      ));
      return makeConstructionTarget(target.coefficient, nextArcs, target.color);
    });
  }

  function shiftTargetAll(targetIndex: number, delta: number) {
    mutateTarget(targetIndex, (target, intervals) => {
      const nextArcs = intervals.map(arc => ({ ...arc, start: normalizeTurn(arc.start + delta) }));
      return makeConstructionTarget(target.coefficient, nextArcs, target.color);
    });
  }

  function updateMultiplier(targetIndex: number, nextMultiplier: number) {
    if (!Number.isSafeInteger(nextMultiplier) || nextMultiplier === 0 || Math.abs(nextMultiplier) > MAX_PREIMAGE_ARCS) {
      return;
    }
    mutateTarget(targetIndex, (target, intervals) => (
      makeConstructionTarget(nextMultiplier, intervals, target.color)
    ));
  }

  function updateTargetColor(targetIndex: number, color: string) {
    mutateTarget(targetIndex, (target, intervals) => (
      makeConstructionTarget(target.coefficient, intervals, color)
    ));
  }

  function addIntervalToTarget(targetIndex: number) {
    mutateTarget(targetIndex, (target, intervals) => {
      const nextArc = suggestNewInterval(intervals);
      return makeConstructionTarget(target.coefficient, [...intervals, nextArc], target.color);
    });
  }

  function removeIntervalFromTarget(targetIndex: number, intervalIndex: number) {
    mutateTarget(targetIndex, (target, intervals) => {
      if (intervals.length <= 1) return target;
      const nextArcs = intervals.filter((_, i) => i !== intervalIndex);
      return makeConstructionTarget(target.coefficient, nextArcs, target.color);
    });
  }

  function addPreimageFactor() {
    setSetup(previous => {
      const multiplier = suggestNewMultiplier(previous.targets, previous.coefficients);
      const nextTarget = makeConstructionTarget(
        multiplier,
        [{ start: 0, width: 0.5 }],
        fallbackColor(previous.targets.length),
      );
      return { ...previous, targets: [...previous.targets, nextTarget] };
    });
    setStatus('');
  }

  function removePreimageFactor(targetIndex: number) {
    setSetup(previous => {
      if (previous.targets.length <= 1 && groupCount > 0) return previous;
      return {
        ...previous,
        targets: previous.targets.filter((_, index) => index !== targetIndex),
      };
    });
    setStatus('');
  }

  function findShift() {
    try {
      const next = findGuaranteedShift(setup);
      setSetup(next);
      setStatus('Optimal widths restored and a partition shift attaining the density bound selected.');
      setLoadError('');
    } catch (error) { setStatus(errorMessage(error)); }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-800 font-sans p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <VisualizerHeader
          eyebrow="Explicit construction"
          title="Preimage intersection construction"
          description={
            <>
              Choose target unions U<sub>j</sub> and multipliers d<sub>j</sub>, form A = ⋂ d<sub>j</sub><sup>−1</sup>(U<sub>j</sub>), and see L(A) on the outer ring.
            </>
          }
          shareUrl={shareUrl}
          copyLabel="Copy link"
          copyText={copyText}
          onCopyResult={(ok) => setStatus(ok ? 'Link copied.' : 'Copy failed. Select and copy the configuration JSON below.')}
          actions={[
            {
              label: 'Linear form visualizer',
              disabled: !result,
              onClick: () => onSwitchToLinearForm(result ? {
                coefficients: setup.coefficients,
                intervals: result.intervals,
                missingPoint: result.missingPoint ?? 0,
              } : { coefficients: setup.coefficients, intervals: [], missingPoint: 0 }),
            },
            { label: 'A + A − mA visualizer', onClick: onSwitchToIntervals },
            ...(onSwitchToCandela ? [{ label: 'Candela construction', onClick: onSwitchToCandela }] : []),
          ]}
        />

        {loadError && (
          <p role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            {loadError}
          </p>
        )}

        <div className="grid xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,1fr)] gap-6 items-start">
          <section className="bg-white border border-slate-200 rounded-xl p-4 md:p-6">
            <h2 className="font-semibold mb-1">Targets → preimages → intersection → image</h2>
            <p className="text-sm text-slate-500 mb-3">
              Drag a colored arc to move that interval, or drag the ring track to shift all intervals in that target together. Thin rings show each preimage.
            </p>
            <svg
              ref={svgRef}
              viewBox={`${-extent} ${-extent} ${2 * extent} ${2 * extent}`}
              role="group"
              aria-label="Interactive construction: target and preimage rings inside A and its linear-form image"
              className={`w-full mx-auto touch-none select-none ${dragPayload ? 'cursor-grabbing' : ''}`}
              {...svgHandlers}
            >
              <title>Preimage intersection construction on the circle</title>
              <desc>
                Each pair of inner rings shows a target union of open intervals and its preimage under multiplication by its chosen multiplier. The next to outer ring is A; the outer ring is L(A).
              </desc>
              {setup.targets.map((target, targetIndex) => {
                const radius = 70 + targetIndex * 44;
                const intervals = getTargetIntervals(target);
                const preimageSet = result?.preimages[targetIndex];
                let targetSet = result?.targetSets[targetIndex];
                if (!targetSet) {
                  try { targetSet = openCircleSet(intervals); }
                  catch { targetSet = { arcs: intervals.filter(a => a.width > 0), full: false, points: [] }; }
                }
                const initialStarts = intervals.map(arc => arc.start);
                const isDraggingRing = dragPayload?.targetIndex === targetIndex;

                return (
                  <g key={targetIndex}>
                    <g
                      data-target-coefficient={target.coefficient}
                      data-ring-radius={radius}
                      tabIndex={0}
                      role="slider"
                      aria-label={`Shift target union for multiplier ${target.coefficient}`}
                      aria-valuemin={0}
                      aria-valuemax={1}
                      aria-valuenow={intervals[0]?.start ?? 0}
                      aria-valuetext={`${format(intervals[0]?.start ?? 0)} turns; use arrow keys to shift`}
                      className={`outline-none focus:opacity-70 ${isDraggingRing ? 'cursor-grabbing' : 'cursor-grab'}`}
                      onPointerDown={event => startDrag(event, { targetIndex, intervalIndex: null, initialStarts })}
                      onKeyDown={event => {
                        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
                        event.preventDefault();
                        const direction = event.key === 'ArrowRight' || event.key === 'ArrowUp' ? 1 : -1;
                        shiftTargetAll(targetIndex, direction * (event.shiftKey ? 0.01 : 0.001));
                      }}
                    >
                      <circle r={radius} fill="none" stroke="#e2e8f0" strokeWidth={12} />
                      <circle r={radius} fill="none" stroke="transparent" strokeWidth={18} />
                      {targetSet.full ? (
                        <circle r={radius} fill="none" stroke={target.color} strokeWidth={12} />
                      ) : (
                        <>
                          {intervals.flatMap((arc, intervalIndex) => (
                            arc.width > 0
                              ? wrappedSegments(arc.start, arc.start + arc.width).map((segment, segIndex) => (
                                <CircleArc
                                  key={`${intervalIndex}-${segIndex}`}
                                  radius={radius}
                                  start={segment[0]}
                                  end={segment[1]}
                                  color={target.color}
                                  strokeWidth={12}
                                  className={
                                    isDraggingRing && (dragPayload?.intervalIndex === null || dragPayload?.intervalIndex === intervalIndex)
                                      ? 'cursor-grabbing'
                                      : 'cursor-grab'
                                  }
                                  onPointerDown={event => startDrag(event, {
                                    targetIndex,
                                    intervalIndex: intervals.length > 1 ? intervalIndex : null,
                                    initialStarts,
                                  })}
                                />
                              ))
                              : []
                          ))}
                          <OpenEndpoints arcs={targetSet.arcs} radius={radius} color={target.color} thickness={12} />
                        </>
                      )}
                    </g>
                    <circle r={radius + 19} fill="none" stroke="#f1f5f9" strokeWidth={6} />
                    {preimageSet && (
                      <g opacity={0.65}>
                        <SetRing set={preimageSet} radius={radius + 19} color={target.color} thickness={6} />
                      </g>
                    )}
                  </g>
                );
              })}
              <circle r={aRadius} fill="none" stroke="#e2e8f0" strokeWidth={13} />
              <circle r={imageRadius} fill="none" stroke="#e2e8f0" strokeWidth={13} />
              {result && (
                <>
                  <SetRing set={result.a} radius={aRadius} color="#0f766e" thickness={13} />
                  <SetRing set={result.image} radius={imageRadius} color="#7c3aed" thickness={13} />
                </>
              )}
              <CircleAxes
                labelRadius={imageRadius + 29}
                labels={[0, 0.25, 0.5, 0.75]}
                showLines={false}
                labelClassName="fill-slate-500"
                labelFontSize={12}
              />
              {witness != null && (
                <CircleMarker radius={imageRadius} turn={witness} ariaLabel={`Missing point ${format(witness)}`} />
              )}
              <text y={-9} textAnchor="middle" fontSize={11} fill="#64748b">Measure of A</text>
              <text y={14} textAnchor="middle" fontSize={19} fontWeight="bold" fill="#0f766e">
                {result ? format(result.density) : '—'}
              </text>
            </svg>
            <div className="flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm">
              <span className="text-teal-700 font-semibold">Next to outer ring: A</span>
              <span className="text-violet-700 font-semibold">Outermost: L(A)</span>
              <span>Black mark: missing point</span>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-5">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Measure of L(A)</p>
                <p className="font-mono text-lg mt-1">{result ? format(result.imageMeasure) : '—'}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Missing point (mod 1)</p>
                <p className="font-mono text-lg mt-1">{result ? witness == null ? 'None' : format(witness) : '—'}</p>
              </div>
            </div>
            {computed.error ? (
              <p className="mt-4 text-sm text-red-800" role="alert">{computed.error}</p>
            ) : result?.image.full ? (
              <p className="mt-4 text-sm text-amber-800">
                L(A) covers the whole circle. There is no missing point for these widths and shifts.
              </p>
            ) : isEmpty ? (
              <p className="mt-4 text-sm text-amber-800">
                A is empty for these shifts. Use “Find guaranteed shift” to obtain a set with the guaranteed positive measure.
              </p>
            ) : (
              <p className="mt-4 text-sm text-teal-800">
                The marked point lies outside L(A). {result?.imageMeasure === 1 ? 'Measure one can still leave excluded endpoints.' : ''}
              </p>
            )}
            <p className="mt-3 text-xs text-slate-500">
              Intervals are open; hollow endpoints are excluded. Type decimals or fractions (e.g. 1/3) and press Enter to confirm. This page calculates with floating-point coordinates; use the Python construction for exact rational verification.
            </p>
          </section>

          <div className="space-y-6">
            <section className="bg-white border border-slate-200 rounded-xl p-5">
              <CoefficientsForm
                id="construction-coefficients"
                label="Integer coefficients of L"
                value={coefficientText}
                onChange={setCoefficientText}
                onApply={(coefficients) => {
                  const next = defaultConstructionState(coefficients);
                  setSetup(next);
                  setLoadError('');
                  setStatus('Form updated with optimal widths and a guaranteed shift.');
                }}
                onError={(error) => setStatus(errorMessage(error))}
                helpText="Each coefficient acts on an independent point of A. Applying updates the Ruzsa targets; you can then freely change each preimage multiplier or add intervals below."
              />
            </section>

            <section className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                <h2 className="font-semibold">Preimage factors &amp; target unions</h2>
                <button
                  type="button"
                  onClick={addPreimageFactor}
                  className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1.5 rounded-lg transition-colors flex items-center gap-1 text-xs font-semibold"
                >
                  <Plus size={14} /> Add preimage
                </button>
              </div>
              {!setup.targets.length && (
                <p className="text-sm text-slate-600">
                  All coefficients are zero. There are no target constraints: A is the full circle and L(A) is the single point 0.
                </p>
              )}
              <div className="space-y-5">
                {setup.targets.map((target, targetIndex) => {
                  const intervals = getTargetIntervals(target);
                  const absCoeff = Math.abs(target.coefficient);
                  const mult = target.coefficient > 0 ? multiplicity.get(target.coefficient) : undefined;
                  const targetSet = result?.targetSets[targetIndex];
                  const preimageSet = result?.preimages[targetIndex];
                  const unionMeasure = targetSet ? setMeasure(targetSet) : intervals.reduce((s, a) => s + a.width, 0);

                  return (
                    <div
                      key={targetIndex}
                      className="border-l-4 pl-3 space-y-3"
                      style={{ borderColor: target.color }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <div className="flex items-center gap-2 flex-wrap">
                          <input
                            type="color"
                            value={target.color}
                            onChange={event => updateTargetColor(targetIndex, event.target.value)}
                            className="w-5 h-5 rounded cursor-pointer p-0 border border-slate-200 bg-white"
                            title="Pick preimage color"
                            aria-label={`Color for preimage ${targetIndex + 1}`}
                          />
                          <label className="flex items-center gap-1.5 font-semibold" style={{ color: target.color }}>
                            <span>Multiplier</span>
                            <DeferredNumberInput
                              aria-label={`Multiplier of preimage ${targetIndex + 1}`}
                              integer
                              step={1}
                              value={target.coefficient}
                              validate={v => v !== 0 && Math.abs(v) <= MAX_PREIMAGE_ARCS}
                              onCommit={next => updateMultiplier(targetIndex, next)}
                              className="w-24"
                              inputClassName="px-2 py-0.5 text-slate-800 font-mono text-sm"
                            />
                            <span className="font-normal text-slate-500">x mod 1</span>
                          </label>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-500">
                            {mult !== undefined
                              ? `${mult} term${mult === 1 ? '' : 's'}`
                              : 'custom'} · rings {2 * targetIndex + 1}–{2 * targetIndex + 2}
                          </span>
                          <button
                            type="button"
                            onClick={() => addIntervalToTarget(targetIndex)}
                            className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-1 rounded-md text-xs font-semibold flex items-center gap-1"
                            title="Add another open interval to this preimage target union"
                          >
                            <Plus size={12} /> Interval
                          </button>
                          {canRemoveTarget && (
                            <ConfirmDeleteButton
                              ariaLabel={`Remove preimage ${targetIndex + 1}`}
                              title="Remove preimage factor"
                              onConfirm={() => removePreimageFactor(targetIndex)}
                            />
                          )}
                        </div>
                      </div>

                      <div className="space-y-3">
                        {intervals.map((arc, intervalIndex) => (
                          <div
                            key={intervalIndex}
                            className={intervals.length > 1 ? 'rounded-lg bg-slate-50 border border-slate-200/80 p-2.5 space-y-2' : ''}
                          >
                            {intervals.length > 1 && (
                              <div className="flex items-center justify-between text-xs text-slate-500">
                                <span className="font-semibold">
                                  Interval {intervalIndex + 1} of {intervals.length}
                                </span>
                                <ConfirmDeleteButton
                                  ariaLabel={`Remove interval ${intervalIndex + 1} from preimage ${targetIndex + 1}`}
                                  title="Remove interval"
                                  onConfirm={() => removeIntervalFromTarget(targetIndex, intervalIndex)}
                                />
                              </div>
                            )}
                            <div className="grid grid-cols-2 gap-3">
                              <NumberSlider
                                layout="stacked"
                                label="Start / shift"
                                clampStep={false}
                                value={arc.start}
                                onChange={value => updateIntervalField(targetIndex, intervalIndex, 'start', value)}
                                inputAriaLabel={
                                  intervals.length === 1
                                    ? `Start of target ${target.coefficient}`
                                    : `Start of target ${target.coefficient} interval ${intervalIndex + 1}`
                                }
                                sliderAriaLabel={`Shift target ${target.coefficient}${intervals.length > 1 ? ` interval ${intervalIndex + 1}` : ''}`}
                              />
                              <NumberSlider
                                layout="stacked"
                                label="Width"
                                value={arc.width}
                                onChange={value => updateIntervalField(targetIndex, intervalIndex, 'width', value)}
                                inputAriaLabel={
                                  intervals.length === 1
                                    ? `Width of target ${target.coefficient}`
                                    : `Width of target ${target.coefficient} interval ${intervalIndex + 1}`
                                }
                                sliderAriaLabel={`Resize target ${target.coefficient}${intervals.length > 1 ? ` interval ${intervalIndex + 1}` : ''}`}
                              />
                            </div>
                          </div>
                        ))}
                      </div>

                      <p className="text-xs text-slate-500">
                        {isCanonical && mult !== undefined ? (
                          <>
                            Optimal width: 1/{groupCount * mult}. Preimage: up to {absCoeff} open arcs, each of width {format(intervals[0].width / absCoeff)}.
                          </>
                        ) : (
                          <>
                            Target union measure: {format(unionMeasure)} ({intervals.length} interval{intervals.length === 1 ? '' : 's'}).
                            {' '}Preimage: {preimageSet?.full ? 'full circle' : `${preimageSet?.arcs.length ?? 0} open arc${preimageSet?.arcs.length === 1 ? '' : 's'}`}.
                          </>
                        )}
                      </p>
                    </div>
                  );
                })}
              </div>

              <div className="flex flex-wrap gap-2 mt-5">
                <button
                  type="button"
                  className={BUTTON_CLASS}
                  onClick={() => {
                    try {
                      const wasCanonical = isCanonical;
                      setSetup(resetOptimalWidths(setup));
                      setStatus(wasCanonical
                        ? 'Optimal widths restored; target shifts retained.'
                        : 'Canonical Ruzsa targets and optimal widths restored.');
                    } catch (error) { setStatus(errorMessage(error)); }
                  }}
                >
                  Reset optimal widths
                </button>
                <button
                  type="button"
                  className="rounded-lg px-3 py-2 text-sm font-semibold bg-indigo-700 text-white hover:bg-indigo-800"
                  onClick={findShift}
                >
                  Find guaranteed shift
                </button>
              </div>
            </section>

            <section className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
              <h2 className="font-semibold text-indigo-950 mb-3">Why this construction has a missing point</h2>
              {groupCount ? (
                <>
                  <p className="text-sm text-indigo-950">
                    With g = {groupCount} distinct absolute coefficients and multiplicities r<sub>d</sub>, the optimal target widths are w<sub>d</sub> = 1/(g r<sub>d</sub>).
                  </p>
                  <p className="text-sm text-indigo-950 mt-2">
                    If Σ r<sub>d</sub>w<sub>d</sub> ≤ 1, the signed sum of target intervals leaves a point out. Since L(A) lies in that sum, every choice of shifts has a missing point.
                  </p>
                  <p className="text-sm text-indigo-950 mt-2">
                    At the optimal widths, the preimages of the interval partitions partition the circle up to endpoints. Pigeonhole gives a choice with measure of A ≥ ∏ w<sub>d</sub>. “Find guaranteed shift” selects a largest such cell.
                  </p>
                </>
              ) : (
                <p className="text-sm text-indigo-950">
                  The zero form always has image {'{0}'} on a nonempty A, so any other point is missing.
                </p>
              )}
              <dl className="text-sm grid grid-cols-2 gap-3 mt-4">
                <div>
                  <dt className="text-indigo-700">Weighted width Σ r<sub>d</sub>w<sub>d</sub></dt>
                  <dd className="font-mono font-semibold mt-1">
                    {result && result.boundWidth !== null ? format(result.boundWidth) : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-indigo-700">Guaranteed density at optimal widths</dt>
                  <dd className="font-mono font-semibold mt-1">
                    {result ? format(result.guaranteedDensity) : '—'}
                  </dd>
                </div>
              </dl>
              {result && (
                <p className="text-xs text-indigo-950 mt-3">
                  {!isCanonical
                    ? 'Custom multipliers or multi-interval target unions are active. The outer ring shows the directly computed image L(A); use “Find guaranteed shift” to restore canonical Ruzsa targets.'
                    : `${optimal ? 'Optimal widths are active.' : 'Widths have been changed.'} ${
                      result.widthGuarantee
                        ? 'The target-width condition guarantees a missing point.'
                        : 'The target-width condition does not guarantee avoidance; the outer ring shows the computed image.'
                    }`}
                </p>
              )}
            </section>
          </div>
        </div>

        <StateJsonPanel
          layout="split"
          title="Share or import this construction"
          exportId="construction-export"
          importId="construction-import"
          exportLabel="Current targets and coefficients"
          importLabel="Import construction JSON"
          stateJson={stateJson}
          copyText={copyText}
          statusMessage={status}
          onStatusMessage={setStatus}
          onImport={(raw) => {
            const next = normalizeConstructionState(raw);
            setSetup(next);
            setCoefficientText(next.coefficients.join(', '));
            setLoadError('');
            return 'Construction imported.';
          }}
        />
      </div>
    </main>
  );
}
