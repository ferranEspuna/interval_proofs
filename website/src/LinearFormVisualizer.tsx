import React, { useMemo, useState } from 'react';
import { intervalSegments, linearFormSegments, measure, normalizeTurn, wrappedSegments } from './linearFormGeometry';
import type { Interval, Segment } from './linearFormGeometry';
import {
  EPSILON, appendInterval, changeIntervalWidth, moveIntervalStart,
  packIntervalsClockwise, scaleIntervalsToTotal,
} from './intervalEditing';
import {
  BASE_COLORS, buildShareUrl as defaultBuildShareUrl,
  copyText as defaultCopyText, errorMessage, fallbackColor, normalizeColor,
} from './shared';
import {
  BUTTON_CLASS, CircleArc, CircleAxes, CircleMarker, CoefficientsForm,
  ConfirmDeleteButton, DeferredNumberInput, StateJsonPanel, useCircleDrag, VisualizerHeader,
} from './ui';

const DEFAULT_STATE = {
  coefficients: [1, 1, -3],
  missingPoint: 0,
  intervals: [{ id: 1, start: 0.4, width: 0.2, color: BASE_COLORS[0] }],
};

export function normalizeLinearFormState(raw: any) {
  if (!raw || !Array.isArray(raw.coefficients) || !raw.coefficients.length
      || !raw.coefficients.every((value: unknown) => Number.isSafeInteger(value))) {
    throw new Error('Provide a nonempty list of integer coefficients.');
  }
  if (!Array.isArray(raw.intervals)) throw new Error('State must include an intervals array.');
  let intervals: Interval[] = raw.intervals.map((item: any, index: number) => {
    if (!Number.isFinite(item?.start) || !Number.isFinite(item?.width) || item.width < 0 || item.width > 1) {
      throw new Error('Interval starts and widths must be finite; widths must lie between 0 and 1.');
    }
    return {
      id: index + 1,
      start: normalizeTurn(item.start),
      width: item.width,
      color: normalizeColor(item.color, index),
    };
  });
  const missingPoint = raw.missingPoint ?? 0;
  if (!Number.isFinite(missingPoint)) throw new Error('The missing point must be finite.');
  const total = intervals.reduce((sum, interval) => sum + interval.width, 0);
  if (total > 1 + EPSILON) intervals = scaleIntervalsToTotal(intervals, 1);
  intervals = packIntervalsClockwise(intervals, intervals[0]?.id);
  return { coefficients: [...raw.coefficients], intervals, missingPoint: normalizeTurn(missingPoint) };
}

export default function LinearFormVisualizer({
  initialState,
  buildShareUrl = defaultBuildShareUrl,
  copyText = defaultCopyText,
  onSwitchToIntervals,
  onSwitchToConstruction = undefined,
  onSwitchToCandela = undefined,
}: {
  initialState?: unknown;
  buildShareUrl?: (state: unknown) => string;
  copyText?: (text: string) => Promise<void>;
  onSwitchToIntervals: () => void;
  onSwitchToConstruction?: (setup?: unknown) => void;
  onSwitchToCandela?: () => void;
}) {
  const [loaded] = useState(() => {
    try { return { setup: normalizeLinearFormState(initialState ?? DEFAULT_STATE), error: '' }; }
    catch (error) {
      return {
        setup: normalizeLinearFormState(DEFAULT_STATE),
        error: `Could not load the shared configuration: ${errorMessage(error)} The example below is shown instead.`,
      };
    }
  });
  const [setup, setSetup] = useState(loaded.setup);
  const [loadError, setLoadError] = useState(loaded.error);
  const [coefficientText, setCoefficientText] = useState(setup.coefficients.join(', '));
  const [status, setStatus] = useState('');

  const { svgRef, activePayload: dragPayload, startDrag, svgHandlers } = useCircleDrag<{
    id: number;
    initialStart: number;
  }>((payload, turn, startTurn) => {
    setSetup(previous => ({
      ...previous,
      intervals: moveIntervalStart(previous.intervals, payload.id, payload.initialStart + (turn - startTurn)),
    }));
  });

  const aSegments = useMemo(() => intervalSegments(setup.intervals), [setup.intervals]);
  const image = useMemo(() => {
    try { return { segments: linearFormSegments(setup.intervals, setup.coefficients), error: '' }; }
    catch (error) { return { segments: [] as Segment[], error: errorMessage(error) }; }
  }, [setup]);
  const density = measure(aSegments);
  const state = {
    v: 1,
    mode: 'linear-form',
    ...setup,
    fixTotalLength: false,
    targetTotalLength: density,
    hiddenMixedComboKeys: [],
  };
  const stateJson = JSON.stringify(state, null, 2);
  const shareUrl = buildShareUrl(state);

  function updateInterval(index: number, field: 'start' | 'width', numeric: number) {
    if (!Number.isFinite(numeric)) return;
    setSetup(previous => {
      const interval = previous.intervals[index];
      if (!interval) return previous;
      return {
        ...previous,
        intervals: field === 'start'
          ? moveIntervalStart(previous.intervals, interval.id, numeric)
          : changeIntervalWidth(previous.intervals, interval.id, numeric),
      };
    });
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-800 font-sans p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <VisualizerHeader
          title="Linear Form Visualizer"
          description={<>Explore L(A) = c₁A + ··· + cₖA on the circle <span className="whitespace-nowrap">ℝ/ℤ</span>.</>}
          shareUrl={shareUrl}
          copyLabel="Copy link"
          copyText={copyText}
          onCopyResult={(ok) => setStatus(ok ? 'Link copied.' : 'Copy failed. Select and copy the state JSON below.')}
          actions={[
            { label: 'A + A − mA visualizer', onClick: onSwitchToIntervals },
            ...(onSwitchToConstruction ? [{
              label: 'Preimage construction',
              onClick: () => onSwitchToConstruction({ coefficients: setup.coefficients }),
            }] : []),
            ...(onSwitchToCandela ? [{
              label: 'Candela construction',
              onClick: onSwitchToCandela,
            }] : []),
          ]}
        />
        {loadError && (
          <p role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            {loadError}
          </p>
        )}
        <div className="grid lg:grid-cols-2 gap-6">
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <svg
              ref={svgRef}
              viewBox="-210 -210 420 420"
              role="img"
              aria-label="Circle showing A on the inner ring, its linear image on the outer ring, and the chosen missing point"
              className={`w-full max-w-lg mx-auto touch-none select-none ${dragPayload ? 'cursor-grabbing' : ''}`}
              {...svgHandlers}
            >
              {[100, 160].map(radius => (
                <circle key={radius} r={radius} stroke="#e2e8f0" strokeWidth={14} fill="none" />
              ))}
              {setup.intervals.flatMap(interval => wrappedSegments(interval.start, interval.start + interval.width).map((segment, index) => (
                <CircleArc
                  key={`${interval.id}-${index}`}
                  radius={100}
                  start={segment[0]}
                  end={segment[1]}
                  color={interval.color}
                  strokeWidth={14}
                  showZeroWidthDot
                  className={dragPayload?.id === interval.id ? 'cursor-grabbing' : 'cursor-grab'}
                  onPointerDown={event => startDrag(event, { id: interval.id, initialStart: interval.start })}
                />
              )))}
              {image.segments.map((segment, index) => (
                <CircleArc
                  key={index}
                  radius={160}
                  start={segment[0]}
                  end={segment[1]}
                  color="#7c3aed"
                  strokeWidth={14}
                  showZeroWidthDot
                />
              ))}
              <CircleAxes
                labelRadius={195}
                labels={[0, 0.25, 0.5, 0.75]}
                showLines={false}
                labelClassName="fill-slate-500"
                labelFontSize={13}
              />
              <CircleMarker radius={170} turn={setup.missingPoint} innerOffset={-27} outerOffset={7} dotRadius={4} hollow={false} />
              <text y={-8} textAnchor="middle" fontSize={14} fill="#64748b">Density of A</text>
              <text y={24} textAnchor="middle" fontSize={27} fontWeight="bold">{density.toPrecision(9)}</text>
            </svg>
            <div className="flex flex-wrap gap-4 justify-center text-sm">
              <span>Inner ring: A</span>
              <span className="text-violet-700">Outer ring: L(A)</span>
              <span>Black mark: missing point</span>
            </div>
            <p className="text-sm text-slate-600 text-center mt-3">
              Drag a colored interval on the inner ring to move it. Change its width in the table.
            </p>
            {image.error ? (
              <p className="text-amber-800 mt-4" role="alert">{image.error}</p>
            ) : (
              <p className="text-sm text-slate-600 text-center mt-4">
                Measure of L(A): {measure(image.segments).toPrecision(9)}
              </p>
            )}
            <p className="text-xs text-slate-500 mt-4">
              Closed endpoints and zero-width intervals are shown. With ε = 0, a solver solution may touch the marked point; the numerical supremum need not itself be a strict avoidance construction.
            </p>
          </section>

          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-5">
            <CoefficientsForm
              id="linear-coefficients"
              label="Integer coefficients"
              value={coefficientText}
              onChange={setCoefficientText}
              onApply={(coefficients) => {
                setSetup(normalizeLinearFormState({ ...setup, coefficients }));
                setLoadError('');
                setStatus('Coefficients updated.');
              }}
              onError={(error) => setStatus(errorMessage(error))}
              helpText="Each coefficient acts on one independently chosen point of A. For example: 1, 1, −3."
            />

            <label className="block text-sm font-semibold">
              Missing point (mod 1)
              <DeferredNumberInput
                aria-label="Missing point (mod 1)"
                step={0.001}
                value={setup.missingPoint}
                onCommit={(value) => setSetup({ ...setup, missingPoint: normalizeTurn(value) })}
                className="w-full mt-2"
                inputClassName="px-2 py-1.5 font-mono font-normal text-sm"
              />
            </label>

            <div>
              <h2 className="font-semibold mb-2">Intervals</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left">
                      <th className="p-1">Interval</th>
                      <th className="p-1">Start</th>
                      <th className="p-1">Width</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {setup.intervals.map((interval, index) => (
                      <tr key={interval.id}>
                        <td className="p-1 font-semibold" style={{ color: interval.color }}>I{index}</td>
                        <td className="p-1">
                          <DeferredNumberInput
                            aria-label={`Start of interval ${index}`}
                            step={0.001}
                            value={interval.start}
                            onCommit={value => updateInterval(index, 'start', value)}
                            className="w-full min-w-[7rem]"
                            inputClassName="px-2 py-1.5 font-mono text-sm"
                          />
                        </td>
                        <td className="p-1">
                          <DeferredNumberInput
                            aria-label={`Width of interval ${index}`}
                            step={0.001}
                            min={0}
                            max={1}
                            value={interval.width}
                            onCommit={value => updateInterval(index, 'width', value)}
                            className="w-full min-w-[7rem]"
                            inputClassName="px-2 py-1.5 font-mono text-sm"
                          />
                        </td>
                        <td className="p-1">
                          <ConfirmDeleteButton
                            ariaLabel={`Delete interval ${index}`}
                            title="Delete interval"
                            confirmLabel="Delete"
                            onConfirm={() => setSetup({ ...setup, intervals: setup.intervals.filter((_, i) => i !== index) })}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button
                type="button"
                className={`${BUTTON_CLASS} mt-3`}
                onClick={() => setSetup(previous => ({
                  ...previous,
                  intervals: appendInterval(previous.intervals, {
                    id: Math.max(0, ...previous.intervals.map(interval => interval.id)) + 1,
                    start: 0.5,
                    color: fallbackColor(previous.intervals.length),
                  }),
                }))}
              >
                Add interval
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Intervals stay disjoint: moves snap to free space, and resizing moves neighboring intervals as needed. Press Enter to confirm typed values. Editing the picture does not rerun the optimizer.
            </p>
          </section>
        </div>

        <StateJsonPanel
          layout="split"
          title="Share or import a configuration"
          exportId="linear-export"
          importId="linear-import"
          exportLabel="Current state"
          importLabel="Import state JSON"
          stateJson={stateJson}
          copyText={copyText}
          statusMessage={status}
          onStatusMessage={setStatus}
          onImport={(raw) => {
            const imported = normalizeLinearFormState(raw);
            setSetup(imported);
            setCoefficientText(imported.coefficients.join(', '));
            setLoadError('');
            return 'State imported.';
          }}
        />
      </div>
    </main>
  );
}
