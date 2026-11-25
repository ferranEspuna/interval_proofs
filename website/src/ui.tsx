/** Shared React UI components and SVG hooks reused across all visualizer modes. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, ChevronUp, Copy } from 'lucide-react';
import katex from 'katex';
import { normalizeTurn } from './linearFormGeometry';
import {
  circlePoint, copyText as defaultCopyText, errorMessage,
  formatNumericValue, parseIntegerList, parseNumericInput, polarToCartesian,
} from './shared';

export type VisualizerMode = 'candela' | 'interval' | 'linear-form' | 'preimage-construction';

export const BUTTON_CLASS =
  'border border-slate-300 rounded-lg px-3 py-2 bg-white hover:bg-slate-100 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors';
export const FIELD_CLASS =
  'border border-slate-300 rounded-md px-2 py-1.5 w-full bg-white focus:outline-none focus:ring-1 focus:ring-blue-500';

export function InlineMath({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const html = katex.renderToString(String(children), {
    throwOnError: false,
    strict: false,
  });

  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

/**
 * Numeric text input that lets the user type freely without applying changes mid-edit.
 * Commits on Enter (or blur if edited to a valid value); cancels on Escape.
 * Includes optional up/down spinner buttons (and ArrowUp/ArrowDown keys) for small-step tweaks.
 * Supports floats, scientific notation, and simple fractions (e.g. 1/3) when integer=false.
 */
export function DeferredNumberInput({
  value,
  onCommit,
  integer = false,
  step,
  min,
  max,
  showSpinners = true,
  precision = 9,
  formatValue,
  validate,
  disabled = false,
  className = '',
  inputClassName = '',
  title,
  placeholder,
  id,
  'aria-label': ariaLabel,
}: {
  value: number;
  onCommit: (next: number) => void;
  integer?: boolean;
  step?: number;
  min?: number;
  max?: number;
  showSpinners?: boolean;
  precision?: number;
  formatValue?: (value: number) => string;
  validate?: (value: number) => boolean;
  disabled?: boolean;
  className?: string;
  inputClassName?: string;
  title?: string;
  placeholder?: string;
  id?: string;
  'aria-label'?: string;
}) {
  const effectiveStep = step ?? (integer ? 1 : 0.001);
  const format = useCallback(
    (v: number) => (
      formatValue
        ? formatValue(v)
        : integer && Number.isInteger(v)
          ? String(v)
          : formatNumericValue(v, precision)
    ),
    [formatValue, integer, precision],
  );
  const [draft, setDraft] = useState<string | null>(null);
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    setDraft(null);
    setInvalid(false);
  }, [value]);

  const tryCommit = useCallback((text: string): boolean => {
    const parsed = parseNumericInput(text, { integer });
    if (parsed === null || (validate && !validate(parsed))) {
      return false;
    }
    onCommit(parsed);
    setDraft(null);
    setInvalid(false);
    return true;
  }, [integer, validate, onCommit]);

  const stepBy = useCallback((direction: 1 | -1, multiplier = 1) => {
    if (disabled) return;
    const base = draft !== null ? (parseNumericInput(draft, { integer }) ?? value) : value;
    const delta = direction * effectiveStep * multiplier;
    const cleanStep = (rawNext: number) => {
      const cleaned = integer
        ? Math.round(rawNext)
        : Math.abs(rawNext) < 1e-12 * Math.max(1, Math.abs(base))
          ? 0
          : Number(rawNext.toPrecision(12));
      if (min !== undefined && cleaned < min) return min;
      if (max !== undefined && cleaned > max) return max;
      return cleaned;
    };
    let next = cleanStep(base + delta);
    if (validate && !validate(next)) {
      const skipped = cleanStep(base + 2 * delta);
      if (!validate(skipped)) return;
      next = skipped;
    }
    onCommit(next);
    setDraft(null);
    setInvalid(false);
  }, [disabled, draft, integer, value, effectiveStep, min, max, validate, onCommit]);

  const isDirty = draft !== null;
  const displayValue = isDirty ? draft : format(value);
  const stateClasses = invalid
    ? 'border-red-400 bg-red-50/40 ring-1 ring-red-400'
    : isDirty
      ? 'border-amber-400 bg-amber-50/40'
      : '';

  const inputElement = (
    <input
      id={id}
      type="text"
      inputMode={integer ? 'numeric' : 'decimal'}
      aria-label={ariaLabel}
      aria-invalid={invalid || undefined}
      placeholder={placeholder}
      disabled={disabled}
      value={displayValue}
      title={title ?? (integer ? 'Press Enter to apply (Esc to cancel, ↑/↓ to step)' : 'Enter decimal or fraction (e.g. 1/3), press Enter to apply (Esc to cancel, ↑/↓ to step)')}
      onChange={(event) => {
        setDraft(event.target.value);
        if (invalid) setInvalid(false);
      }}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          if (draft === null) return;
          if (!tryCommit(draft)) {
            setInvalid(true);
          }
        } else if (event.key === 'Escape') {
          event.preventDefault();
          setDraft(null);
          setInvalid(false);
        } else if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
          event.preventDefault();
          stepBy(event.key === 'ArrowUp' ? 1 : -1, event.shiftKey ? 10 : 1);
        }
      }}
      onBlur={() => {
        if (draft === null) return;
        if (draft.trim() !== format(value)) {
          tryCommit(draft);
        }
        setDraft(null);
        setInvalid(false);
      }}
      className={
        showSpinners
          ? `min-w-0 flex-1 bg-transparent outline-none disabled:text-slate-500 ${inputClassName}`.trim()
          : `${className} ${inputClassName} ${stateClasses}`.trim()
      }
    />
  );

  if (!showSpinners) {
    return inputElement;
  }

  return (
    <div
      className={`inline-flex items-stretch overflow-hidden border border-slate-300 rounded-md bg-white focus-within:ring-1 focus-within:ring-blue-500 ${disabled ? 'bg-slate-100' : ''} ${className} ${stateClasses}`.trim()}
    >
      {inputElement}
      <div className="flex flex-col border-l border-slate-200 shrink-0 w-5 bg-slate-50/80">
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          aria-label={ariaLabel ? `Increase ${ariaLabel}` : 'Increase value'}
          title={`Increase by ${effectiveStep} (Shift: ×10)`}
          onMouseDown={(event) => event.preventDefault()}
          onClick={(event) => stepBy(1, event.shiftKey ? 10 : 1)}
          className="flex-1 flex items-center justify-center text-slate-500 hover:bg-slate-200/80 hover:text-slate-800 active:bg-slate-300/80 disabled:opacity-40 disabled:pointer-events-none leading-none border-b border-slate-200"
        >
          <ChevronUp size={11} strokeWidth={2.5} />
        </button>
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          aria-label={ariaLabel ? `Decrease ${ariaLabel}` : 'Decrease value'}
          title={`Decrease by ${effectiveStep} (Shift: ×10)`}
          onMouseDown={(event) => event.preventDefault()}
          onClick={(event) => stepBy(-1, event.shiftKey ? 10 : 1)}
          className="flex-1 flex items-center justify-center text-slate-500 hover:bg-slate-200/80 hover:text-slate-800 active:bg-slate-300/80 disabled:opacity-40 disabled:pointer-events-none leading-none"
        >
          <ChevronDown size={11} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  );
}

/** Prominent × delete button that asks for inline confirmation before removing an item. */
export function ConfirmDeleteButton({
  onConfirm,
  ariaLabel,
  title = 'Remove',
  confirmLabel = 'Remove',
}: {
  onConfirm: () => void;
  ariaLabel: string;
  title?: string;
  confirmLabel?: string;
}) {
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (!confirming || typeof window === 'undefined') return;
    const timer = window.setTimeout(() => setConfirming(false), 5000);
    return () => window.clearTimeout(timer);
  }, [confirming]);

  if (confirming) {
    return (
      <span
        className="inline-flex items-center gap-1.5 whitespace-nowrap"
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.preventDefault();
            setConfirming(false);
          }
        }}
      >
        <button
          type="button"
          aria-label={`Confirm ${ariaLabel.toLowerCase()}`}
          onClick={() => {
            setConfirming(false);
            onConfirm();
          }}
          className="h-9 px-2.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition-colors"
        >
          {confirmLabel}?
        </button>
        <button
          type="button"
          aria-label="Cancel removal"
          onClick={() => setConfirming(false)}
          className="h-9 px-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 text-xs font-semibold transition-colors"
        >
          Cancel
        </button>
      </span>
    );
  }

  return (
    <button
      type="button"
      aria-label={ariaLabel}
      title={title}
      onClick={() => setConfirming(true)}
      className="h-9 min-w-9 px-2.5 rounded-lg border border-red-200 bg-red-50/70 text-red-600 hover:bg-red-100 hover:border-red-300 hover:text-red-700 font-bold text-xl leading-none inline-flex items-center justify-center transition-colors"
    >
      ×
    </button>
  );
}

/** Combined label + DeferredNumberInput + range slider reused across visualizer controls. */
export function NumberSlider({
  label,
  value,
  min = 0,
  max = 1,
  step = 0.001,
  clampStep = true,
  onChange,
  integer = false,
  disabled = false,
  layout = 'inline',
  inputAriaLabel,
  sliderAriaLabel,
  inputClassName,
  rangeClassName = 'w-full accent-blue-500 disabled:opacity-50',
  rangeStyle,
}: {
  label: React.ReactNode;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  clampStep?: boolean;
  onChange: (next: number) => void;
  integer?: boolean;
  disabled?: boolean;
  layout?: 'inline' | 'stacked';
  inputAriaLabel?: string;
  sliderAriaLabel?: string;
  inputClassName?: string;
  rangeClassName?: string;
  rangeStyle?: React.CSSProperties;
}) {
  const slider = (
    <input
      type="range"
      aria-label={sliderAriaLabel}
      min={min}
      max={max}
      step={step}
      value={value}
      disabled={disabled}
      onChange={(event) => {
        const parsed = parseFloat(event.target.value);
        if (Number.isFinite(parsed)) onChange(parsed);
      }}
      className={rangeClassName}
      style={rangeStyle}
    />
  );

  if (layout === 'stacked') {
    return (
      <label className="text-xs text-slate-600 block">
        {label}
        <DeferredNumberInput
          aria-label={inputAriaLabel}
          integer={integer}
          step={step}
          min={clampStep ? min : undefined}
          max={clampStep ? max : undefined}
          value={value}
          disabled={disabled}
          onCommit={onChange}
          className={inputClassName ?? 'w-full mt-1'}
          inputClassName="px-2 py-1.5 text-sm font-mono text-slate-800"
        />
        <div className="mt-2">{slider}</div>
      </label>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center text-sm mb-1">
        <label className="font-medium text-slate-700">{label}</label>
        <DeferredNumberInput
          aria-label={inputAriaLabel ?? (typeof label === 'string' ? label : undefined)}
          integer={integer}
          step={step}
          min={clampStep ? min : undefined}
          max={clampStep ? max : undefined}
          value={value}
          disabled={disabled}
          onCommit={onChange}
          className={inputClassName ?? 'w-36 border-slate-200 rounded-lg'}
          inputClassName="px-1.5 py-0.5 text-right font-mono text-sm text-slate-700"
        />
      </div>
      {slider}
    </div>
  );
}

/** Radial tick and circle marker at a turn on a circle ring. */
export function CircleMarker({
  radius,
  turn,
  innerOffset = -12,
  outerOffset = 13,
  dotRadius = 4.5,
  hollow = true,
  ariaLabel,
}: {
  radius: number;
  turn: number;
  innerOffset?: number;
  outerOffset?: number;
  dotRadius?: number;
  hollow?: boolean;
  ariaLabel?: string;
}) {
  const inner = circlePoint(radius + innerOffset, turn);
  const outer = circlePoint(radius + outerOffset, turn);
  const marker = circlePoint(radius, turn);
  return (
    <g aria-label={ariaLabel}>
      <line x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="#0f172a" strokeWidth={2.5} />
      <circle
        cx={marker.x}
        cy={marker.y}
        r={dotRadius}
        fill={hollow ? 'white' : '#0f172a'}
        stroke="#0f172a"
        strokeWidth={hollow ? 2 : 0}
      />
    </g>
  );
}

/** Shared SVG circular arc on R/Z (0 = top, clockwise). */
export function CircleArc({
  radius,
  start,
  end,
  color,
  strokeWidth = 14,
  showZeroWidthDot = false,
  className = '',
  style,
  ...rest
}: {
  radius: number;
  start: number;
  end: number;
  color: string;
  strokeWidth?: number;
  showZeroWidthDot?: boolean;
  className?: string;
  style?: React.CSSProperties;
} & Omit<React.SVGProps<SVGElement>, 'r' | 'stroke' | 'strokeWidth' | 'fill' | 'className' | 'style'>) {
  const span = end - start;
  if (span < 0) return null;
  if (span <= 1e-12) {
    if (!showZeroWidthDot) return null;
    const p = circlePoint(radius, start);
    return <circle cx={p.x} cy={p.y} r={4} fill={color} className={className || undefined} style={style} {...(rest as React.SVGProps<SVGCircleElement>)} />;
  }
  if (span >= 1 - 1e-12) {
    return (
      <circle
        cx="0"
        cy="0"
        r={radius}
        stroke={color}
        strokeWidth={strokeWidth}
        fill="none"
        className={className || undefined}
        style={style}
        {...(rest as React.SVGProps<SVGCircleElement>)}
      />
    );
  }

  const pStart = circlePoint(radius, start);
  const pEnd = circlePoint(radius, end);
  const largeArcFlag = span > 0.5 ? '1' : '0';
  const pathData = `M ${pStart.x} ${pStart.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${pEnd.x} ${pEnd.y}`;

  return (
    <path
      d={pathData}
      stroke={color}
      strokeWidth={strokeWidth}
      fill="none"
      strokeLinecap="butt"
      className={className || undefined}
      style={style}
      {...(rest as React.SVGProps<SVGPathElement>)}
    />
  );
}

/** Cardinal axis lines and/or labels at turns 0, 0.25, 0.5, 0.75. */
export function CircleAxes({
  innerRadius,
  outerRadius,
  labelRadius,
  labels = ['0', '1/4', '1/2', '3/4'],
  showLines = true,
  labelClassName = 'text-sm font-semibold fill-slate-400',
  labelFontSize,
}: {
  innerRadius?: number;
  outerRadius?: number;
  labelRadius: number;
  labels?: [React.ReactNode, React.ReactNode, React.ReactNode, React.ReactNode];
  showLines?: boolean;
  labelClassName?: string;
  labelFontSize?: number;
}) {
  const turns = [0, 0.25, 0.5, 0.75];
  return (
    <g>
      {showLines && innerRadius !== undefined && outerRadius !== undefined && turns.map(turn => {
        const p1 = polarToCartesian(0, 0, innerRadius, turn);
        const p2 = polarToCartesian(0, 0, outerRadius, turn);
        return (
          <line
            key={`axis-${turn}`}
            x1={p1.x}
            y1={p1.y}
            x2={p2.x}
            y2={p2.y}
            stroke="#e2e8f0"
            strokeWidth="2"
            strokeDasharray="4 4"
          />
        );
      })}
      {turns.map((turn, index) => {
        const p = circlePoint(labelRadius, turn);
        return (
          <text
            key={`label-${turn}`}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={labelFontSize}
            className={labelClassName}
          >
            {labels[index]}
          </text>
        );
      })}
    </g>
  );
}

/** Compute the circle turn in [0, 1) corresponding to a pointer event on an SVG centered at (0, 0). */
export function pointerTurnFromSvg(svg: SVGSVGElement | null, clientX: number, clientY: number): number | null {
  if (!svg) return null;
  const transform = svg.getScreenCTM?.();
  if (transform) {
    const cursor = svg.createSVGPoint();
    cursor.x = clientX;
    cursor.y = clientY;
    const local = cursor.matrixTransform(transform.inverse());
    return normalizeTurn(Math.atan2(local.x, -local.y) / (2 * Math.PI));
  }
  const rect = svg.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;
  const dx = clientX - (rect.left + rect.width / 2);
  const dy = clientY - (rect.top + rect.height / 2);
  return normalizeTurn(Math.atan2(dx, -dy) / (2 * Math.PI));
}

/**
 * Reusable SVG ring-drag hook that captures the pointer on the stable <svg> element,
 * preventing loss of capture when an arc splits across turn 0.
 */
export function useCircleDrag<T>(onDragTurn: (payload: T, turn: number, startTurn: number) => void) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ payload: T; pointerId: number; startTurn: number } | null>(null);
  const [activePayload, setActivePayload] = useState<T | null>(null);
  const onDragRef = useRef(onDragTurn);
  onDragRef.current = onDragTurn;

  const finishDrag = useCallback((event?: React.PointerEvent<SVGSVGElement>) => {
    if (event && dragRef.current?.pointerId !== event.pointerId) return;
    const pointerId = dragRef.current?.pointerId;
    dragRef.current = null;
    setActivePayload(null);
    if (event && pointerId !== undefined && event.currentTarget.hasPointerCapture?.(pointerId)) {
      event.currentTarget.releasePointerCapture(pointerId);
    }
  }, []);

  const startDrag = useCallback((event: React.PointerEvent<SVGElement>, payload: T) => {
    if (event.button !== 0 || dragRef.current) return;
    const turn = pointerTurnFromSvg(svgRef.current, event.clientX, event.clientY);
    if (turn === null) return;
    event.preventDefault();
    event.stopPropagation();
    svgRef.current?.setPointerCapture?.(event.pointerId);
    dragRef.current = { payload, pointerId: event.pointerId, startTurn: turn };
    setActivePayload(payload);
  }, []);

  const moveDrag = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (event.pointerType === 'mouse' && (event.buttons & 1) === 0) {
      finishDrag(event);
      return;
    }
    const turn = pointerTurnFromSvg(svgRef.current, event.clientX, event.clientY);
    if (turn === null) return;
    onDragRef.current(drag.payload, turn, drag.startTurn);
  }, [finishDrag]);

  const clearDrag = useCallback(() => {
    dragRef.current = null;
    setActivePayload(null);
  }, []);

  const svgHandlers = {
    onPointerMove: moveDrag,
    onPointerUp: finishDrag,
    onPointerCancel: finishDrag,
    onLostPointerCapture: finishDrag,
  };

  return { svgRef, activePayload, startDrag, clearDrag, svgHandlers };
}

/** Hook for transient timed feedback (e.g. copy/import status). */
export function useTimedFlag(durationMs = 1600) {
  const [status, setStatus] = useState('idle');
  const timerRef = useRef<number | null>(null);

  const flash = useCallback((nextStatus: string, ms = durationMs) => {
    setStatus(nextStatus);
    if (typeof window === 'undefined') return;
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      setStatus('idle');
      timerRef.current = null;
    }, ms);
  }, [durationMs]);

  useEffect(() => () => {
    if (timerRef.current !== null && typeof window !== 'undefined') {
      window.clearTimeout(timerRef.current);
    }
  }, []);

  return [status, flash] as const;
}

export type HeaderAction = {
  label: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
  primary?: boolean;
};

export function VisualizerHeader({
  eyebrow,
  title,
  description,
  actions,
  shareUrl,
  copyLabel = 'Copy current state link',
  copyText = defaultCopyText,
  onCopyResult,
}: {
  eyebrow?: string;
  title: string;
  description: React.ReactNode;
  actions: HeaderAction[];
  shareUrl?: string;
  copyLabel?: string;
  copyText?: (text: string) => Promise<void>;
  onCopyResult?: (ok: boolean) => void;
}) {
  const [copyStatus, flashCopy] = useTimedFlag(1600);

  const handleCopy = useCallback(async () => {
    if (!shareUrl) return;
    try {
      await copyText(shareUrl);
      flashCopy('copied');
      onCopyResult?.(true);
    } catch {
      flashCopy('failed');
      onCopyResult?.(false);
    }
  }, [shareUrl, copyText, flashCopy, onCopyResult]);

  return (
    <header className="mb-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="max-w-2xl">
          {eyebrow && (
            <p className="text-xs uppercase tracking-widest font-semibold text-indigo-700 mb-2">
              {eyebrow}
            </p>
          )}
          <h1 className="text-3xl font-bold text-slate-900 mb-2">{title}</h1>
          <p className="text-slate-600">{description}</p>
        </div>
        <nav aria-label="Visualizer pages" className="flex flex-wrap gap-2">
          {actions.map((action, index) => (
            <button
              key={index}
              type="button"
              onClick={action.onClick}
              disabled={action.disabled}
              title={action.title}
              className={
                action.primary
                  ? 'shrink-0 bg-slate-900 hover:bg-slate-700 text-white px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50'
                  : 'shrink-0 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed'
              }
            >
              {action.label}
            </button>
          ))}
          {shareUrl !== undefined && (
            <button
              type="button"
              onClick={handleCopy}
              className="shrink-0 bg-slate-900 hover:bg-slate-700 text-white px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm font-bold"
              title="Copy shareable setup link"
            >
              {copyStatus === 'copied' ? <Check size={16} /> : <Copy size={16} />}
              {copyStatus === 'copied' ? 'Copied' : copyStatus === 'failed' ? 'Copy Failed' : copyLabel}
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}

/** Shared integer-coefficients input form used by LinearForm and PreimageConstruction visualizers. */
export function CoefficientsForm({
  id,
  label,
  value,
  onChange,
  onApply,
  onError,
  helpText,
}: {
  id: string;
  label: React.ReactNode;
  value: string;
  onChange: (text: string) => void;
  onApply: (coefficients: number[]) => void;
  onError?: (error: unknown) => void;
  helpText?: React.ReactNode;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        try {
          onApply(parseIntegerList(value));
        } catch (error) {
          onError?.(error);
        }
      }}
    >
      <label htmlFor={id} className="block text-sm font-semibold mb-2">
        {label}
      </label>
      <div className="flex gap-2">
        <input
          id={id}
          className={FIELD_CLASS}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="submit" className={BUTTON_CLASS}>
          Apply
        </button>
      </div>
      {helpText && <p className="text-xs text-slate-500 mt-2">{helpText}</p>}
    </form>
  );
}

/** Shared State JSON export/import card supporting both compact sidebar and two-column layouts. */
export function StateJsonPanel({
  title = 'State JSON',
  stateJson,
  onImport,
  copyText = defaultCopyText,
  layout = 'compact',
  exportId,
  importId,
  exportLabel = 'Current state',
  importLabel = 'Import state JSON',
  placeholder = 'Paste state JSON',
  statusMessage,
  onStatusMessage,
}: {
  title?: string;
  stateJson: string;
  onImport: (raw: unknown) => string | void;
  copyText?: (text: string) => Promise<void>;
  layout?: 'compact' | 'split';
  exportId?: string;
  importId?: string;
  exportLabel?: string;
  importLabel?: string;
  placeholder?: string;
  statusMessage?: string;
  onStatusMessage?: (message: string) => void;
}) {
  const [inputJson, setInputJson] = useState('');
  const [jsonStatus, flashStatus] = useTimedFlag(1800);

  const handleCopy = useCallback(async () => {
    try {
      await copyText(stateJson);
      flashStatus('copied');
      onStatusMessage?.('Configuration JSON copied.');
    } catch {
      flashStatus('copy-failed');
      onStatusMessage?.('Copy failed. Select and copy the state JSON below.');
    }
  }, [copyText, stateJson, flashStatus, onStatusMessage]);

  const handleImport = useCallback(() => {
    try {
      const parsed = JSON.parse(inputJson);
      const customMessage = onImport(parsed);
      flashStatus('imported', 2200);
      if (onStatusMessage) {
        onStatusMessage(typeof customMessage === 'string' ? customMessage : 'State imported.');
      }
    } catch (error) {
      flashStatus('invalid', 2200);
      onStatusMessage?.(`Import failed: ${errorMessage(error)}`);
    }
  }, [inputJson, onImport, flashStatus, onStatusMessage]);

  if (layout === 'split') {
    return (
      <section className="mt-6 bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold mb-3">{title}</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label htmlFor={exportId} className="text-sm">
              {exportLabel}
            </label>
            <textarea
              id={exportId}
              className={`${FIELD_CLASS} mt-2 font-mono text-xs`}
              rows={7}
              readOnly
              value={stateJson}
            />
            <button type="button" className={`${BUTTON_CLASS} mt-2`} onClick={handleCopy}>
              {jsonStatus === 'copied' ? 'Copied JSON' : 'Copy JSON'}
            </button>
          </div>
          <div>
            <label htmlFor={importId} className="text-sm">
              {importLabel}
            </label>
            <textarea
              id={importId}
              className={`${FIELD_CLASS} mt-2 font-mono text-xs`}
              rows={7}
              placeholder={placeholder}
              spellCheck={false}
              value={inputJson}
              onChange={(event) => setInputJson(event.target.value)}
            />
            <button
              type="button"
              className={`${BUTTON_CLASS} mt-2`}
              onClick={handleImport}
            >
              Import JSON
            </button>
          </div>
        </div>
        <p role="status" aria-live="polite" className="mt-3 text-sm text-slate-600">
          {statusMessage ?? ''}
        </p>
      </section>
    );
  }

  return (
    <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <h2 className="font-bold text-lg">{title}</h2>
        <button
          type="button"
          onClick={handleCopy}
          className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm font-bold"
        >
          {jsonStatus === 'copied' ? <Check size={16} /> : <Copy size={16} />}
          {jsonStatus === 'copied' ? 'Copied' : jsonStatus === 'copy-failed' ? 'Copy Failed' : 'Copy current JSON'}
        </button>
      </div>

      <textarea
        id={importId}
        value={inputJson}
        onChange={(event) => setInputJson(event.target.value)}
        placeholder={placeholder}
        spellCheck={false}
        className="w-full min-h-40 resize-y rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      <div className="mt-3 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={handleImport}
          disabled={!inputJson.trim()}
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
  );
}
