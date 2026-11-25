import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { normalizeLinearFormState } from './LinearFormVisualizer';
import { measure } from './linearFormGeometry';
import {
  EPSILON, getWrappedSegments, normalizeTurn, clamp,
  getForbiddenStartSegments, forbiddenStartBackground, maxValueBackground,
  packIntervalsClockwise, scaleIntervalsToTotal,
  moveIntervalStart as moveStart, changeIntervalWidth as resizeInterval, appendInterval,
} from './intervalEditing';
import {
  BASE_COLORS, buildShareUrl, copyText, fallbackColor,
  normalizeColor, readSharedStateFromUrl,
} from './shared';
import {
  CircleArc, CircleAxes, ConfirmDeleteButton, DeferredNumberInput, InlineMath, NumberSlider,
  StateJsonPanel, useCircleDrag, VisualizerHeader,
} from './ui';

const INITIAL_INTERVALS = [
  { id: 1, start: 0.1, width: 0.1, color: BASE_COLORS[0] },
  { id: 2, start: 0.575, width: 0.15, color: BASE_COLORS[1] },
];

function hexToRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b];
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + (1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1);
}

function blendMultipleColors(hexColors: string[]): string {
  if (!hexColors || hexColors.length === 0) return '#000000';
  if (hexColors.length === 1) return hexColors[0];
  let rSum = 0, gSum = 0, bSum = 0;
  hexColors.forEach(hex => {
    const [r, g, b] = hexToRgb(hex);
    rSum += r; gSum += g; bSum += b;
  });
  const count = hexColors.length;
  return rgbToHex(Math.round(rSum / count), Math.round(gSum / count), Math.round(bSum / count));
}

function calculateMeasure(segments: { start: number; end: number }[]): number {
  return clamp(measure(segments.map(seg => [seg.start, seg.end])), 0, 1);
}

function getDisjointSegments(segments: { start: number; end: number; color: string }[]) {
  if (!segments || segments.length === 0) return { measure: 0, pieces: [] };

  const endpoints = new Set<number>();
  segments.forEach(seg => {
    endpoints.add(seg.start);
    endpoints.add(seg.end);
  });
  const pts = Array.from(endpoints).sort((a, b) => a - b);

  const pieces = [];
  let totalMeasure = 0;

  for (let i = 0; i < pts.length - 1; i++) {
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const mid = (p1 + p2) / 2;
    if (p2 - p1 < EPSILON) continue;

    const activeColors: string[] = [];
    segments.forEach(seg => {
      if (seg.start - EPSILON <= mid && mid <= seg.end + EPSILON) {
        activeColors.push(seg.color);
      }
    });

    if (activeColors.length > 0) {
      const w = p2 - p1;
      pieces.push({ width: w, color: blendMultipleColors(activeColors) });
      totalMeasure += w;
    }
  }

  const mergedPieces = [];
  if (pieces.length > 0) {
    let current = { ...pieces[0] };
    for (let i = 1; i < pieces.length; i++) {
      if (pieces[i].color === current.color) {
        current.width += pieces[i].width;
      } else {
        mergedPieces.push(current);
        current = { ...pieces[i] };
      }
    }
    mergedPieces.push(current);
  }

  return { measure: Math.min(totalMeasure, 1), pieces: mergedPieces };
}

function getDefaultSetup() {
  const intervals = INITIAL_INTERVALS.map(interval => ({ ...interval }));
  const targetTotalLength = intervals.reduce((sum, interval) => sum + interval.width, 0);

  return {
    intervals,
    m: 3,
    hiddenMixedComboKeys: [] as string[],
    fixTotalLength: false,
    targetTotalLength,
  };
}

function normalizeSharedIntervals(rawIntervals: unknown) {
  if (!Array.isArray(rawIntervals)) {
    return getDefaultSetup().intervals;
  }

  if (rawIntervals.length === 0) return [];

  const usedIds = new Set<number>();
  let intervals = rawIntervals.map((raw, index) => {
    let id = Number(raw?.id);
    if (!Number.isFinite(id) || usedIds.has(id)) {
      id = index + 1;
      while (usedIds.has(id)) id += 1;
    }
    usedIds.add(id);

    return {
      id,
      start: normalizeTurn(Number(raw?.start) || 0),
      width: clamp(Number(raw?.width) || 0, 0, 1),
      color: normalizeColor(raw?.color, index),
    };
  });

  const total = intervals.reduce((sum, interval) => sum + interval.width, 0);
  if (total > 1 + EPSILON) {
    intervals = scaleIntervalsToTotal(intervals, 1);
  }

  return packIntervalsClockwise(intervals, intervals[0]?.id);
}

function normalizeSharedSetup(shared: any, defaults = getDefaultSetup()) {
  if (!shared || typeof shared !== 'object' || Array.isArray(shared)) {
    throw new Error('Invalid state');
  }

  let intervals = normalizeSharedIntervals(shared?.intervals);
  const sharedMultiplier = shared?.m ?? shared?.lambda;
  const m = Number.isFinite(Number(sharedMultiplier))
    ? Number(sharedMultiplier)
    : defaults.m;
  const fixTotalLength = shared?.fixTotalLength === true;
  let targetTotalLength = clamp(Number(shared?.targetTotalLength), 0, 1);

  if (!Number.isFinite(targetTotalLength)) {
    targetTotalLength = intervals.reduce((sum, interval) => sum + interval.width, 0);
  }

  if (fixTotalLength) {
    intervals = packIntervalsClockwise(scaleIntervalsToTotal(intervals, targetTotalLength), intervals[0]?.id);
  } else {
    targetTotalLength = intervals.reduce((sum, interval) => sum + interval.width, 0);
  }

  const hiddenMixedComboKeys = Array.isArray(shared?.hiddenMixedComboKeys)
    ? shared.hiddenMixedComboKeys.filter((key: unknown) => typeof key === 'string')
    : [];

  return {
    intervals,
    m,
    hiddenMixedComboKeys,
    fixTotalLength,
    targetTotalLength,
  };
}

function readSetupFromUrl() {
  const defaults = getDefaultSetup();
  const shared = readSharedStateFromUrl();
  if (!shared) return defaults;

  try {
    return normalizeSharedSetup(shared, defaults);
  } catch {
    return defaults;
  }
}

export default function IntervalVisualizer({
  onSwitchToCandela,
  onSwitchToLinearForm,
  onSwitchToConstruction,
}: {
  onSwitchToCandela: () => void;
  onSwitchToLinearForm: (setup: unknown) => void;
  onSwitchToConstruction: (setup?: unknown) => void;
}) {
  const [initialSetup] = useState(() => readSetupFromUrl());
  const [intervals, setIntervals] = useState(initialSetup.intervals);
  const [m, setM] = useState(initialSetup.m);
  const [hiddenMixedComboKeys, setHiddenMixedComboKeys] = useState(initialSetup.hiddenMixedComboKeys);
  const [fixTotalLength, setFixTotalLength] = useState(initialSetup.fixTotalLength);
  const [targetTotalLength, setTargetTotalLength] = useState(initialSetup.targetTotalLength);

  const moveIntervalStart = useCallback((id: number, requestedStart: number) => {
    setIntervals(prev => moveStart(prev, id, requestedStart));
  }, []);

  const { svgRef, activePayload: dragPayload, startDrag, clearDrag, svgHandlers } = useCircleDrag<{
    id: number;
    initialStart: number;
  }>((payload, turn, startTurn) => {
    moveIntervalStart(payload.id, payload.initialStart + (turn - startTurn));
  });

  // 1. Calculate A (wrapped segments with colors)
  const renderA = useMemo(() => {
    const result: { id: number; start: number; end: number; color: string }[] = [];
    intervals.forEach(i => {
      const s = i.start;
      const e = i.start + i.width;
      getWrappedSegments(s, e).forEach(seg => {
        result.push({ id: i.id, start: seg[0], end: seg[1], color: i.color });
      });
    });
    return result;
  }, [intervals]);

  // 2. Calculate A + A (blended colors)
  const renderAPlusA = useMemo(() => {
    const result: { start: number; end: number; color: string }[] = [];
    for (let i = 0; i < intervals.length; i++) {
      for (let j = i; j < intervals.length; j++) {
        const int1 = intervals[i];
        const int2 = intervals[j];
        const s = int1.start + int2.start;
        const e = (int1.start + int1.width) + (int2.start + int2.width);
        const blendedColor = blendMultipleColors([int1.color, int2.color]);
        getWrappedSegments(s, e).forEach(seg => {
          result.push({ start: seg[0], end: seg[1], color: blendedColor });
        });
      }
    }
    return result;
  }, [intervals]);

  // 3. Calculate m * A
  const renderMA = useMemo(() => {
    const result: { start: number; end: number; color: string }[] = [];
    intervals.forEach(i => {
      const s = m * i.start;
      const e = m * (i.start + i.width);
      getWrappedSegments(s, e).forEach(seg => {
        result.push({ start: seg[0], end: seg[1], color: i.color });
      });
    });
    return result;
  }, [intervals, m]);

  const mixedCombinations = useMemo(() => {
    const result = [];
    const labels = intervals.length <= 2 ? ['I', 'J'] : intervals.map((_, index) => `A${index + 1}`);
    for (let i = 0; i < intervals.length; i++) {
      for (let j = i; j < intervals.length; j++) {
        for (let ell = 0; ell < intervals.length; ell++) {
          const int1 = intervals[i];
          const int2 = intervals[j];
          const int3 = intervals[ell];
          result.push({
            key: `${int1.id}:${int2.id}:${int3.id}`,
            label: `${labels[i]} + ${labels[j]} - ${m}${labels[ell]}`,
            int1,
            int2,
            int3,
            color: blendMultipleColors([int1.color, int2.color, int3.color]),
          });
        }
      }
    }
    return result;
  }, [intervals, m]);

  const canFilterMixedCombinations = intervals.length >= 1 && intervals.length <= 2;

  // 4. Calculate A + A - m * A (blended colors)
  const renderAPlusAMinusMA = useMemo(() => {
    const result: { start: number; end: number; color: string }[] = [];
    const hiddenKeys = new Set(hiddenMixedComboKeys);
    mixedCombinations.forEach(combo => {
      if (canFilterMixedCombinations && hiddenKeys.has(combo.key)) return;

      const sumStart = combo.int1.start + combo.int2.start;
      const sumEnd = (combo.int1.start + combo.int1.width) + (combo.int2.start + combo.int2.width);
      const scaledStart = -m * combo.int3.start;
      const scaledEnd = -m * (combo.int3.start + combo.int3.width);
      const s = sumStart + Math.min(scaledStart, scaledEnd);
      const e = sumEnd + Math.max(scaledStart, scaledEnd);
      getWrappedSegments(s, e).forEach(seg => {
        result.push({ start: seg[0], end: seg[1], color: combo.color });
      });
    });
    return result;
  }, [mixedCombinations, canFilterMixedCombinations, hiddenMixedComboKeys, m]);

  const disjointA = useMemo(() => getDisjointSegments(renderA), [renderA]);
  const measureA = disjointA.measure;
  const measureAPlusA = useMemo(() => calculateMeasure(renderAPlusA), [renderAPlusA]);
  const measureMA = useMemo(() => calculateMeasure(renderMA), [renderMA]);
  const measureAPlusAMinusMA = useMemo(() => calculateMeasure(renderAPlusAMinusMA), [renderAPlusAMinusMA]);

  const totalIntervalLength = useMemo(
    () => intervals.reduce((sum, interval) => sum + interval.width, 0),
    [intervals],
  );
  const displayedTotalLength = fixTotalLength ? targetTotalLength : totalIntervalLength;

  useEffect(() => {
    if (!fixTotalLength) {
      setTargetTotalLength(totalIntervalLength);
    }
  }, [fixTotalLength, totalIntervalLength]);

  const shareState = useMemo(() => ({
    v: 1,
    mode: 'interval',
    intervals: intervals.map(interval => ({
      id: interval.id,
      start: Number(interval.start.toFixed(6)),
      width: Number(interval.width.toFixed(6)),
      color: interval.color,
    })),
    m,
    fixTotalLength,
    targetTotalLength: Number(displayedTotalLength.toFixed(6)),
    hiddenMixedComboKeys,
  }), [intervals, m, fixTotalLength, displayedTotalLength, hiddenMixedComboKeys]);

  const shareUrl = useMemo(() => buildShareUrl(shareState), [shareState]);
  const currentStateJson = useMemo(() => JSON.stringify(shareState, null, 2), [shareState]);

  const applySetup = useCallback((setup: ReturnType<typeof normalizeSharedSetup>) => {
    setIntervals(setup.intervals);
    setM(setup.m);
    setHiddenMixedComboKeys(setup.hiddenMixedComboKeys);
    setFixTotalLength(setup.fixTotalLength);
    setTargetTotalLength(setup.targetTotalLength);
    clearDrag();
  }, [clearDrag]);

  const handleImportState = useCallback((raw: any) => {
    if (raw?.mode === 'preimage-construction') {
      onSwitchToConstruction(raw);
      return;
    }
    if (raw?.mode === 'linear-form') {
      onSwitchToLinearForm(normalizeLinearFormState(raw));
      return;
    }
    applySetup(normalizeSharedSetup(raw));
  }, [applySetup, onSwitchToLinearForm, onSwitchToConstruction]);

  const addInterval = useCallback(() => {
    setIntervals(prev => appendInterval(prev, {
      id: Date.now(),
      start: 0.5,
      color: fallbackColor(prev.length),
    }, fixTotalLength));
  }, [fixTotalLength]);

  const removeInterval = useCallback((id: number) => {
    setIntervals(prev => {
      const next = prev.filter(i => i.id !== id);
      if (!fixTotalLength) return next;
      return packIntervalsClockwise(scaleIntervalsToTotal(next, targetTotalLength), next[0]?.id);
    });
  }, [fixTotalLength, targetTotalLength]);

  const updateIntervalColor = useCallback((id: number, value: string) => {
    setIntervals(prev => prev.map(i => i.id === id ? { ...i, color: value } : i));
  }, []);

  const changeIntervalWidth = useCallback((id: number, requestedWidth: number) => {
    setIntervals(prev => resizeInterval(prev, id, requestedWidth, fixTotalLength, targetTotalLength));
  }, [fixTotalLength, targetTotalLength]);

  const handleFixTotalLengthChange = useCallback((checked: boolean) => {
    setFixTotalLength(checked);
    if (checked) {
      setIntervals(prev => packIntervalsClockwise(scaleIntervalsToTotal(prev, targetTotalLength), prev[0]?.id));
    }
  }, [targetTotalLength]);

  const handleTargetTotalLengthChange = useCallback((value: number) => {
    const nextTarget = clamp(value, 0, 1);
    setTargetTotalLength(nextTarget);
    setIntervals(prev => packIntervalsClockwise(scaleIntervalsToTotal(prev, nextTarget), prev[0]?.id));
  }, []);

  const toggleMixedCombination = useCallback((key: string) => {
    setHiddenMixedComboKeys(prev => (
      prev.includes(key) ? prev.filter(item => item !== key) : [...prev, key]
    ));
  }, []);

  const RADIUS_A = 60;
  const RADIUS_M = 100;
  const RADIUS_PLUS = 140;
  const RADIUS_MIXED = 180;
  const arcStyle: React.CSSProperties = { mixBlendMode: 'multiply' };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans p-4 md:p-8 flex flex-col items-center">
      <div className="max-w-[1600px] w-full">
        <VisualizerHeader
          title="Circle Group Visualizer"
          description={
            <>
              Explore additive combinatorics on the circle group <InlineMath>{'\\mathbb{T} = \\mathbb{R}/\\mathbb{Z}'}</InlineMath>. Visualizing interval sets <InlineMath>{'A'}</InlineMath>, sumsets <InlineMath>{'A+A'}</InlineMath>, dilations <InlineMath>{'mA'}</InlineMath>, and mixed sets <InlineMath>{'A+A-mA'}</InlineMath>.
            </>
          }
          shareUrl={shareUrl}
          copyText={copyText}
          actions={[
            {
              label: 'Preimage construction',
              onClick: () => onSwitchToConstruction({ coefficients: [1, 1, -m] }),
              disabled: !Number.isSafeInteger(m),
            },
            {
              label: 'General linear form',
              onClick: () => onSwitchToLinearForm({ coefficients: [1, 1, -m], intervals, missingPoint: 0 }),
              disabled: !Number.isSafeInteger(m),
              title: Number.isSafeInteger(m)
                ? 'View this configuration as a general linear form'
                : 'The general linear form mode requires integer coefficients',
            },
            {
              label: 'Candela construction',
              onClick: onSwitchToCandela,
              title: 'Open the Candela construction visualizer',
            },
          ]}
        />

        <div className="flex flex-col xl:flex-row gap-8 items-start">
          <div className="flex flex-col lg:flex-row gap-8 flex-1 min-w-0 w-full">
            {/* Canvas Section */}
            <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col items-center justify-center min-h-[500px]">
              <svg
                ref={svgRef}
                viewBox="-250 -250 500 500"
                className={`w-full max-w-[500px] h-auto overflow-visible touch-none select-none ${dragPayload ? 'cursor-grabbing' : ''}`}
                {...svgHandlers}
              >
                <CircleAxes innerRadius={40} outerRadius={220} labelRadius={235} />

                {/* Background Tracks */}
                {[RADIUS_A, RADIUS_M, RADIUS_PLUS, RADIUS_MIXED].map(radius => (
                  <circle key={radius} cx="0" cy="0" r={radius} stroke="#f1f5f9" strokeWidth="16" fill="none" />
                ))}

                {/* Plotted Arcs */}
                {renderA.map((seg, i) => {
                  const interval = intervals.find(item => item.id === seg.id);
                  return (
                    <CircleArc
                      key={`A-${i}`}
                      radius={RADIUS_A}
                      start={seg.start}
                      end={seg.end}
                      color={seg.color}
                      strokeWidth={16}
                      className={`opacity-60 transition-opacity duration-75 ${dragPayload?.id === seg.id ? 'opacity-100 cursor-grabbing' : 'hover:opacity-100 cursor-grab'}`}
                      style={{ ...arcStyle, touchAction: 'none' }}
                      onPointerDown={(e) => {
                        if (interval) startDrag(e, { id: interval.id, initialStart: interval.start });
                      }}
                    />
                  );
                })}
                {renderMA.map((seg, i) => (
                  <CircleArc key={`L-${i}`} radius={RADIUS_M} start={seg.start} end={seg.end} color={seg.color} strokeWidth={16} className="opacity-60" style={arcStyle} />
                ))}
                {renderAPlusA.map((seg, i) => (
                  <CircleArc key={`P-${i}`} radius={RADIUS_PLUS} start={seg.start} end={seg.end} color={seg.color} strokeWidth={16} className="opacity-60" style={arcStyle} />
                ))}
                {renderAPlusAMinusMA.map((seg, i) => (
                  <CircleArc key={`M-${i}`} radius={RADIUS_MIXED} start={seg.start} end={seg.end} color={seg.color} strokeWidth={16} className="opacity-60" style={arcStyle} />
                ))}
              </svg>

              {/* Legend inside canvas area */}
              <div className="mt-8 flex flex-wrap justify-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="font-medium text-sm text-slate-500">Inner Ring:</div>
                  <span className="font-bold text-sm text-slate-800">Set A.</span>
                  <span className="font-bold text-sm text-slate-500 font-mono">{measureA.toFixed(3)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="font-medium text-sm text-slate-500">Middle Ring:</div>
                  <span className="font-bold text-sm text-slate-800">{m}A.</span>
                  <span className="font-bold text-sm text-slate-500 font-mono">{measureMA.toFixed(3)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="font-medium text-sm text-slate-500">Third Ring:</div>
                  <span className="font-bold text-sm text-slate-800">A + A.</span>
                  <span className="font-bold text-sm text-slate-500 font-mono">{measureAPlusA.toFixed(3)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="font-medium text-sm text-slate-500">Outer Ring:</div>
                  <span className="font-bold text-sm text-slate-800">A + A - {m}A.</span>
                  <span className="font-bold text-sm text-slate-500 font-mono">{measureAPlusAMinusMA.toFixed(3)}</span>
                </div>
              </div>
            </div>

            {/* Controls Section */}
            <div className="w-full lg:w-[400px] flex flex-col gap-6">
              {/* Set A Intervals */}
              <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="font-bold text-lg">Define Intervals (Set A)</h2>
                  <button
                    type="button"
                    onClick={addInterval}
                    className="bg-slate-100 hover:bg-slate-200 text-slate-700 p-1.5 rounded-lg transition-colors flex items-center text-sm font-medium"
                  >
                    <Plus size={16} /> <span className="ml-1 pr-1">Add</span>
                  </button>
                </div>

                <div className="space-y-4">
                  {intervals.map((interval, index) => {
                    const otherIntervals = intervals.filter(i => i.id !== interval.id);
                    const forbiddenSegments = getForbiddenStartSegments(interval.width, otherIntervals);
                    const startBackground = forbiddenStartBackground(forbiddenSegments);
                    const widthBackground = fixTotalLength ? maxValueBackground(targetTotalLength) : undefined;

                    return (
                      <div key={interval.id} className="p-4 bg-slate-50 rounded-xl border border-slate-100 relative group" style={{ borderLeftColor: interval.color, borderLeftWidth: '6px' }}>
                        <div className="flex justify-between items-center mb-3">
                          <div className="flex items-center gap-2">
                            <input
                              type="color"
                              value={interval.color}
                              onChange={(e) => updateIntervalColor(interval.id, e.target.value)}
                              className="w-6 h-6 rounded cursor-pointer p-0 border border-slate-200 bg-white"
                              title="Pick interval color"
                            />
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Interval {index + 1}</h3>
                          </div>
                          <ConfirmDeleteButton
                            ariaLabel={`Remove interval ${index + 1}`}
                            title="Remove interval"
                            onConfirm={() => removeInterval(interval.id)}
                          />
                        </div>

                        <div className="space-y-3">
                          <NumberSlider
                            label="Start Position"
                            inputAriaLabel={`Start position of interval ${index + 1}`}
                            value={interval.start}
                            step={0.01}
                            clampStep={false}
                            onChange={(val) => moveIntervalStart(interval.id, val)}
                            rangeClassName="interval-start-range w-full"
                            rangeStyle={{ background: startBackground }}
                          />
                          <NumberSlider
                            label="Width"
                            inputAriaLabel={`Width of interval ${index + 1}`}
                            value={interval.width}
                            step={0.001}
                            onChange={(val) => changeIntervalWidth(interval.id, val)}
                            rangeClassName={fixTotalLength ? 'interval-start-range w-full' : 'w-full accent-blue-500'}
                            rangeStyle={widthBackground ? { background: widthBackground } : undefined}
                          />
                        </div>
                      </div>
                    );
                  })}

                  {intervals.length === 0 && (
                    <div className="text-center p-6 text-sm text-slate-500 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                      No intervals. The set A is currently empty.
                    </div>
                  )}
                </div>
              </div>

              {/* Total Length Constraint */}
              <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <div className="flex items-center justify-between gap-4 mb-4">
                  <h2 className="font-bold text-lg">Total Length</h2>
                  <label className="flex items-center gap-2 text-sm font-bold text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={fixTotalLength}
                      onChange={(e) => handleFixTotalLengthChange(e.target.checked)}
                      className="h-4 w-4 accent-blue-500"
                    />
                    Fixed
                  </label>
                </div>

                <div className="space-y-3">
                  <NumberSlider
                    label="Total"
                    inputAriaLabel="Target total length"
                    value={displayedTotalLength}
                    step={0.001}
                    onChange={handleTargetTotalLengthChange}
                  />
                  <div className="flex justify-between text-xs font-bold text-slate-500">
                    <span>Current</span>
                    <span className={fixTotalLength ? 'text-blue-600 font-mono' : 'font-mono'}>
                      {totalIntervalLength.toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="w-full xl:w-[420px] xl:shrink-0 flex flex-col gap-6">
            {/* m Multiplier */}
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <h2 className="font-bold text-lg mb-4">Scalar Multiplier (<InlineMath>{'m'}</InlineMath>)</h2>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <label className="font-medium text-slate-700">Value of <InlineMath>{'m'}</InlineMath></label>
                  <span className="text-emerald-600 font-bold font-mono">{m}</span>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setM(value => value - 1)}
                    className="w-10 h-10 flex items-center justify-center bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors font-bold text-lg"
                  >
                    -
                  </button>
                  <DeferredNumberInput
                    aria-label="Scalar multiplier m"
                    integer
                    showSpinners={false}
                    value={m}
                    onCommit={setM}
                    className="w-full text-center text-lg font-mono font-bold bg-slate-50 border border-slate-200 rounded-lg h-10 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <button
                    type="button"
                    onClick={() => setM(value => value + 1)}
                    className="w-10 h-10 flex items-center justify-center bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors font-bold text-lg"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>

            {canFilterMixedCombinations && (
              <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                <div className="flex justify-between items-center mb-4 gap-3">
                  <h2 className="font-bold text-lg">Mixed Ring Terms</h2>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setHiddenMixedComboKeys([])}
                      className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors text-xs font-bold"
                    >
                      All
                    </button>
                    <button
                      type="button"
                      onClick={() => setHiddenMixedComboKeys(mixedCombinations.map(combo => combo.key))}
                      className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors text-xs font-bold"
                    >
                      None
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-2 gap-2">
                  {mixedCombinations.map(combo => (
                    <label
                      key={combo.key}
                      className="flex items-center gap-3 px-3 py-2 bg-slate-50 border border-slate-100 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={!hiddenMixedComboKeys.includes(combo.key)}
                        onChange={() => toggleMixedCombination(combo.key)}
                        className="h-4 w-4 accent-sky-500"
                      />
                      <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: combo.color }} />
                      <span className="text-sm font-bold text-slate-700 font-mono">{combo.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            <StateJsonPanel
              stateJson={currentStateJson}
              onImport={handleImportState}
              copyText={copyText}
              placeholder="Paste state JSON"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
