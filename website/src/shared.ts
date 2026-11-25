/** Shared constants, math/formatting helpers, URL state encoding, and clipboard utilities. */

export const BASE_COLORS = [
  '#ef4444',
  '#3b82f6',
  '#f59e0b',
  '#10b981',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
];

export const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/i;

export function fallbackColor(index: number): string {
  const safeIndex = ((index % BASE_COLORS.length) + BASE_COLORS.length) % BASE_COLORS.length;
  return BASE_COLORS[safeIndex];
}

export function normalizeColor(value: unknown, index: number): string {
  return typeof value === 'string' && HEX_COLOR_PATTERN.test(value)
    ? value
    : fallbackColor(index);
}

/** Convert circle turn coordinates (0 = top, 0.25 = right, clockwise) to SVG Cartesian coordinates. */
export function polarToCartesian(cx: number, cy: number, radius: number, angleInTurns: number) {
  const angleInRadians = 2 * Math.PI * angleInTurns;
  return {
    x: cx + radius * Math.sin(angleInRadians),
    y: cy - radius * Math.cos(angleInRadians),
  };
}

export function circlePoint(radius: number, turn: number) {
  return polarToCartesian(0, 0, radius, turn);
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Parse a user-entered float (including fractions like 1/3) or strict safe integer. */
export function parseNumericInput(
  raw: string,
  options: { integer?: boolean } = {},
): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  if (options.integer) {
    if (!/^[+-]?\d+$/.test(trimmed)) return null;
    const parsed = Number(trimmed);
    return Number.isSafeInteger(parsed) ? parsed : null;
  }

  const fractionMatch = trimmed.match(/^([+-]?(?:\d+\.?\d*|\.\d+))\s*\/\s*([+-]?(?:\d+\.?\d*|\.\d+))$/);
  if (fractionMatch) {
    const numerator = Number(fractionMatch[1]);
    const denominator = Number(fractionMatch[2]);
    if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator === 0) {
      return null;
    }
    const quotient = numerator / denominator;
    return Number.isFinite(quotient) ? quotient : null;
  }

  if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(trimmed)) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatNumericValue(value: number, precision = 9): string {
  if (!Number.isFinite(value)) return '—';
  if (Object.is(value, -0) || Math.abs(value) === 0) return '0';
  return Number(value.toPrecision(precision)).toString();
}

export function parseIntegerList(text: string): number[] {
  const trimmed = text.trim();
  const tokens = trimmed.split(/[\s,]+/);
  if (!trimmed || tokens.some(token => !/^[+-]?\d+$/.test(token))) {
    throw new Error('Use integer coefficients separated by spaces or commas.');
  }
  const values = tokens.map(Number);
  if (!values.every(Number.isSafeInteger)) {
    throw new Error('Coefficients must lie within the JavaScript safe integer range.');
  }
  return values;
}

export function encodeShareState(state: unknown): string {
  const json = JSON.stringify(state);
  const bytes = encodeURIComponent(json).replace(/%([0-9A-F]{2})/g, (_, hex) => (
    String.fromCharCode(parseInt(hex, 16))
  ));

  return btoa(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

export function decodeShareState(value: string): unknown {
  const padded = value
    .replace(/-/g, '+')
    .replace(/_/g, '/')
    .padEnd(Math.ceil(value.length / 4) * 4, '=');
  const bytes = atob(padded);
  const escaped = Array.from(bytes, char => (
    `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`
  )).join('');

  return JSON.parse(decodeURIComponent(escaped));
}

export function readSharedStateFromUrl(): unknown {
  if (typeof window === 'undefined') return undefined;

  const rawState = new URLSearchParams(window.location.search).get('state');
  if (!rawState) return undefined;

  try {
    return decodeShareState(rawState);
  } catch {
    return undefined;
  }
}

export function buildShareUrl(state: unknown): string {
  if (typeof window === 'undefined') return '';

  const url = new URL(window.location.href);
  url.search = '';
  url.searchParams.set('state', encodeShareState(state));
  return url.toString();
}

export async function copyText(text: string): Promise<void> {
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
