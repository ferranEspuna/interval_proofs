/** Open-set geometry for intersections of multiplication preimages.
 *
 * The original visualizers intentionally draw closed segments. This module
 * retains open endpoints, including the single hole in an arc of width one.
 * Each preimage factor uses an arbitrary nonzero integer multiplier and a
 * finite union of open target intervals; numbers here are for interactive
 * display while Python provides exact arithmetic.
 */
import { normalizeTurn, wrappedSegments } from './linearFormGeometry';
import type { Interval, Segment } from './linearFormGeometry';
import { BASE_COLORS, normalizeColor } from './shared';

export type OpenArc = { start: number; width: number };
export type OpenCircleSet = { arcs: OpenArc[]; full: boolean; points: number[] };
export type ConstructionTarget = OpenArc & {
  coefficient: number;
  color: string;
  /** Present when the target is a union of 0 or 2+ open intervals; omitted for a single interval. */
  intervals?: OpenArc[];
};
export type ConstructionState = { coefficients: number[]; targets: ConstructionTarget[] };
export type CoefficientGroup = { coefficient: number; multiplicity: number };
export type ConstructionEvaluation = {
  targetSets: OpenCircleSet[];
  preimages: OpenCircleSet[];
  a: OpenCircleSet;
  image: OpenCircleSet;
  intervals: Interval[];
  density: number;
  imageMeasure: number;
  missingPoint: number | null;
  boundWidth: number | null;
  boundWitness: number | null;
  guaranteedDensity: number;
  widthGuarantee: boolean;
  isCanonical: boolean;
};

export const CONSTRUCTION_COLORS = BASE_COLORS;
export const MAX_PREIMAGE_ARCS = 5000;
const TOLERANCE = 1e-12;
const MAX_OPERATIONS = 250000;
const precisionError = () => new Error('This configuration is too close to an endpoint or too narrow to resolve at browser precision. Use the exact Python construction to verify it.');
const emptySet = (): OpenCircleSet => ({ arcs: [], full: false, points: [] });
const fullSet = (): OpenCircleSet => ({ arcs: [], full: true, points: [] });
const samePoint = (a: number, b: number) => Math.min(normalizeTurn(a - b), normalizeTurn(b - a)) <= TOLERANCE;
const isEmpty = (set: OpenCircleSet) => !set.full && !set.arcs.length && !set.points.length;

function validateCoefficients(coefficients: unknown): asserts coefficients is number[] {
  if (!Array.isArray(coefficients) || !coefficients.length || !coefficients.every(Number.isSafeInteger)) {
    throw new Error('Provide a nonempty list of integer coefficients within the JavaScript safe integer range.');
  }
}

function normalizeArc(raw: unknown): OpenArc {
  const arc = raw as Partial<OpenArc> | null | undefined;
  if (!arc || typeof arc !== 'object' || !Number.isFinite(arc.start) || !Number.isFinite(arc.width) || arc.width! < 0 || arc.width! > 1) {
    throw new Error('Target starts must be finite and widths must lie between zero and one.');
  }
  const start = arc.start! >= 0 && arc.start! < 1 ? arc.start! : normalizeTurn(arc.start!);
  return { start, width: arc.width! };
}

export function getTargetIntervals(target: ConstructionTarget): OpenArc[] {
  return Array.isArray(target.intervals)
    ? target.intervals
    : [{ start: target.start, width: target.width }];
}

export function makeConstructionTarget(
  coefficient: number,
  intervals: OpenArc[],
  color: string,
): ConstructionTarget {
  if (intervals.length === 1) {
    return {
      coefficient,
      start: intervals[0].start,
      width: intervals[0].width,
      color,
    };
  }
  return {
    coefficient,
    start: intervals[0]?.start ?? 0,
    width: intervals[0]?.width ?? 0,
    intervals: intervals.map(arc => ({ start: arc.start, width: arc.width })),
    color,
  };
}

export function groupCoefficients(coefficients: number[]): CoefficientGroup[] {
  validateCoefficients(coefficients);
  const counts = new Map<number, number>();
  for (const c of coefficients) if (c !== 0) counts.set(Math.abs(c), (counts.get(Math.abs(c)) ?? 0) + 1);
  return [...counts].sort(([a], [b]) => a - b).map(([coefficient, multiplicity]) => ({ coefficient, multiplicity }));
}

export function isCanonicalRuzsaTargets(groups: CoefficientGroup[], targets: ConstructionTarget[]): boolean {
  if (targets.length !== groups.length) return false;
  return groups.every((group, index) => (
    targets[index].coefficient === group.coefficient && getTargetIntervals(targets[index]).length === 1
  ));
}

export function containsPoint(set: OpenCircleSet, point: number): boolean {
  if (set.full || set.points.some(value => samePoint(point, value))) return true;
  return set.arcs.some(arc => {
    const offset = normalizeTurn(point - arc.start);
    return offset > TOLERANCE && offset < arc.width - TOLERANCE;
  });
}

export function openCircleSet(arcs: OpenArc[], points: number[] = []): OpenCircleSet {
  if (arcs.some(arc => arc.width > 1 + TOLERANCE)) return fullSet();
  if (arcs.some(arc => arc.width > 0 && arc.width <= TOLERANCE)) throw precisionError();
  const lifted: Segment[] = [];
  for (const arc of arcs) {
    if (arc.width <= TOLERANCE) continue;
    const start = normalizeTurn(arc.start);
    const width = Math.min(1, arc.width);
    for (const shift of [-1, 0, 1]) lifted.push([start + shift, start + shift + width]);
  }
  lifted.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: Segment[] = [];
  for (const [start, end] of lifted) {
    const previous = merged[merged.length - 1];
    if (previous && start < previous[1] - TOLERANCE) previous[1] = Math.max(previous[1], end);
    else merged.push([start, end]);
  }
  if (merged.some(([start, end]) => end - start > 1 + TOLERANCE)) return fullSet();
  const result: OpenCircleSet = {
    arcs: merged.filter(([start]) => start >= 0 && start < 1)
      .map(([start, end]) => ({ start, width: Math.min(1, end - start) })),
    full: false,
    points: [],
  };
  for (const point of points) if (!containsPoint(result, point)) result.points.push(normalizeTurn(point));
  return result;
}

export function setMeasure(set: OpenCircleSet): number {
  return set.full ? 1 : Math.min(1, set.arcs.reduce((sum, arc) => sum + arc.width, 0));
}

/** Drawing segments do not carry endpoint inclusion; use containsPoint for membership. */
export function setSegments(set: OpenCircleSet): Segment[] {
  if (set.full) return [[0, 1]];
  return set.arcs.flatMap(arc => wrappedSegments(arc.start, arc.start + arc.width));
}

export function intersectSets(left: OpenCircleSet, right: OpenCircleSet): OpenCircleSet {
  if (left.full) return right;
  if (right.full) return left;
  if (left.arcs.length * right.arcs.length > MAX_OPERATIONS) {
    throw new Error('This intersection is too large for an interactive display. Use fewer or smaller coefficients.');
  }
  const arcs: OpenArc[] = [];
  for (const first of left.arcs) for (const second of right.arcs) for (const shift of [-1, 0, 1]) {
    const start = Math.max(first.start, second.start + shift);
    const end = Math.min(first.start + first.width, second.start + second.width + shift);
    if (end - start > TOLERANCE) arcs.push({ start, width: end - start });
  }
  const points = [...left.points.filter(point => containsPoint(right, point)), ...right.points.filter(point => containsPoint(left, point))];
  return openCircleSet(arcs, points);
}

function singleArcPreimageArcs(target: OpenArc, coefficient: number): OpenArc[] {
  const normalized = normalizeArc(target);
  if (normalized.width === 0) return [];
  const absCoeff = Math.abs(coefficient);
  const width = normalized.width / absCoeff;
  if (width <= TOLERANCE) throw precisionError();
  const start = coefficient > 0
    ? normalized.start
    : normalizeTurn(-(normalized.start + normalized.width));
  // These arcs are already sorted and disjoint. Reconstructing every width
  // from lifted endpoints loses precision which later dilation amplifies.
  return Array.from({ length: absCoeff }, (_, k) => ({
    start: (start + k) / absCoeff,
    width,
  }));
}

export function preimage(target: OpenArc | OpenArc[], coefficient: number): OpenCircleSet {
  if (!Number.isSafeInteger(coefficient) || coefficient === 0) {
    throw new Error('Preimage multipliers must be nonzero integers.');
  }
  const absCoeff = Math.abs(coefficient);
  if (absCoeff > MAX_PREIMAGE_ARCS) {
    throw new Error(`At most ${MAX_PREIMAGE_ARCS} preimage arcs can be displayed per coefficient.`);
  }
  if (!Array.isArray(target)) {
    const arcs = singleArcPreimageArcs(target, coefficient);
    return arcs.length ? { arcs, full: false, points: [] } : emptySet();
  }
  const normalizedArcs = target.map(normalizeArc);
  if (normalizedArcs.length === 0) return emptySet();
  if (normalizedArcs.length === 1) {
    const arcs = singleArcPreimageArcs(normalizedArcs[0], coefficient);
    return arcs.length ? { arcs, full: false, points: [] } : emptySet();
  }
  const union = openCircleSet(normalizedArcs);
  if (union.full) return fullSet();
  if (!union.arcs.length) return emptySet();
  if (union.arcs.length * absCoeff > MAX_PREIMAGE_ARCS) {
    throw new Error(`At most ${MAX_PREIMAGE_ARCS} preimage arcs can be displayed per coefficient.`);
  }
  const arcs = union.arcs
    .flatMap(arc => singleArcPreimageArcs(arc, coefficient))
    .sort((a, b) => a.start - b.start);
  return { arcs, full: false, points: [] };
}

function dilate(set: OpenCircleSet, coefficient: number): OpenCircleSet {
  if (isEmpty(set)) return emptySet();
  if (coefficient === 0) return openCircleSet([], [0]);
  if (set.full) return fullSet();
  return openCircleSet(set.arcs.map(arc => ({
    start: coefficient > 0 ? coefficient * arc.start : coefficient * (arc.start + arc.width),
    width: Math.abs(coefficient) * arc.width,
  })), set.points.map(point => coefficient * point));
}

function addSets(left: OpenCircleSet, right: OpenCircleSet, budget: { operations: number }): OpenCircleSet {
  if (isEmpty(left) || isEmpty(right)) return emptySet();
  if (left.full || right.full) return fullSet();
  budget.operations += (left.arcs.length + left.points.length) * (right.arcs.length + right.points.length);
  if (budget.operations > MAX_OPERATIONS) throw new Error('The linear-form image is too large to compute interactively. Use fewer or smaller coefficients.');
  const arcs: OpenArc[] = [];
  for (const first of left.arcs) for (const second of right.arcs) {
    const width = first.width + second.width;
    if (width > 1 + TOLERANCE) return fullSet();
    arcs.push({ start: first.start + second.start, width });
  }
  for (const arc of left.arcs) for (const point of right.points) arcs.push({ start: arc.start + point, width: arc.width });
  for (const point of left.points) for (const arc of right.arcs) arcs.push({ start: point + arc.start, width: arc.width });
  const points = left.points.flatMap(first => right.points.map(second => first + second));
  return openCircleSet(arcs, points);
}

export function applyLinearForm(set: OpenCircleSet, coefficients: number[]): OpenCircleSet {
  validateCoefficients(coefficients);
  if (isEmpty(set)) return emptySet();
  let result = openCircleSet([], [0]);
  const budget = { operations: 0 };
  for (const coefficient of coefficients) {
    if (coefficient === 0) continue;
    result = addSets(result, dilate(set, coefficient), budget);
    if (result.full) return result;
  }
  return result;
}

export function findMissingPoint(set: OpenCircleSet): number | null {
  if (set.full) return null;
  if (isEmpty(set)) return 0;
  const boundaries = [...set.arcs.flatMap(arc => [arc.start, normalizeTurn(arc.start + arc.width)]), ...set.points]
    .sort((a, b) => a - b);
  // Prefer an interior gap so rounding cannot move a marker onto an endpoint.
  let candidate: number | null = null;
  let widest = 0;
  for (let i = 0; i < boundaries.length; i += 1) {
    const start = boundaries[i];
    const end = i + 1 < boundaries.length ? boundaries[i + 1] : boundaries[0] + 1;
    if (end - start <= widest + TOLERANCE) continue;
    const point = normalizeTurn((start + end) / 2);
    if (!containsPoint(set, point)) { candidate = point; widest = end - start; }
  }
  if (candidate !== null) return candidate;
  return boundaries.find(point => !containsPoint(set, point)) ?? null;
}

/** Suggest a visible non-overlapping open interval in the widest gap of existing target intervals. */
export function suggestNewInterval(existing: OpenArc[]): OpenArc {
  const valid = existing.filter(arc => Number.isFinite(arc.start) && Number.isFinite(arc.width) && arc.width > TOLERANCE);
  if (!valid.length) return { start: 0, width: 0.25 };
  let union: OpenCircleSet;
  try {
    union = openCircleSet(valid);
  } catch {
    return { start: 0, width: 0.1 };
  }
  if (union.full || !union.arcs.length) return { start: 0, width: 0.1 };

  const boundaries = union.arcs
    .flatMap(arc => [arc.start, normalizeTurn(arc.start + arc.width)])
    .sort((a, b) => a - b);
  let bestStart = 0;
  let widest = 0;
  for (let i = 0; i < boundaries.length; i += 1) {
    const start = boundaries[i];
    const end = i + 1 < boundaries.length ? boundaries[i + 1] : boundaries[0] + 1;
    const gap = end - start;
    if (gap <= widest + TOLERANCE) continue;
    const mid = normalizeTurn((start + end) / 2);
    if (!containsPoint(union, mid)) {
      bestStart = start;
      widest = gap;
    }
  }
  if (widest <= 1e-4) return { start: 0, width: 0.1 };
  const width = Number(Math.min(0.2, widest * 0.5).toFixed(6));
  const start = Number(normalizeTurn(bestStart + (widest - width) / 2).toFixed(6));
  return { start, width };
}

/** Suggest a sensible positive integer multiplier for a newly added preimage factor. */
export function suggestNewMultiplier(targets: ConstructionTarget[], coefficients: number[]): number {
  const used = new Set(targets.map(target => Math.abs(target.coefficient)));
  for (const group of groupCoefficients(coefficients)) {
    if (!used.has(group.coefficient)) return group.coefficient;
  }
  let candidate = 1;
  while (used.has(candidate)) candidate += 1;
  return candidate;
}

export function normalizeConstructionState(raw: unknown): ConstructionState {
  const state = raw as Partial<ConstructionState>;
  if (!state || typeof state !== 'object' || Array.isArray(state)) {
    throw new Error('Provide a construction state object.');
  }
  validateCoefficients(state.coefficients);
  const groups = groupCoefficients(state.coefficients);
  if (!Array.isArray(state.targets)) {
    throw new Error('Provide one target interval for each distinct nonzero absolute coefficient.');
  }
  if (groups.length > 0 && state.targets.length === 0) {
    throw new Error('Provide at least one target interval when the linear form has nonzero coefficients.');
  }

  const parsedTargets = state.targets.map((rawTarget, index) => {
    if (!rawTarget || typeof rawTarget !== 'object' || Array.isArray(rawTarget)) {
      throw new Error('Each target must be an object with a multiplier and interval(s).');
    }
    const coefficient = rawTarget.coefficient;
    if (!Number.isSafeInteger(coefficient) || coefficient === 0) {
      throw new Error('Preimage multipliers must be nonzero integers.');
    }
    const intervals = Array.isArray(rawTarget.intervals)
      ? rawTarget.intervals.map(normalizeArc)
      : [normalizeArc(rawTarget)];
    return {
      target: makeConstructionTarget(coefficient, intervals, normalizeColor(rawTarget.color, index)),
      hasExplicitColor: typeof rawTarget.color === 'string' && /^#[0-9a-f]{6}$/i.test(rawTarget.color),
    };
  });

  // If the targets match the canonical Ruzsa coefficient groups 1-to-1,
  // normalize them into canonical sorted coefficient order (preserving Python-link ordering).
  const matchesCanonicalCoefficients = parsedTargets.length === groups.length
    && groups.every(group => parsedTargets.filter(item => item.target.coefficient === group.coefficient).length === 1);

  if (matchesCanonicalCoefficients) {
    const ordered = groups.map((group, index) => {
      const entry = parsedTargets.find(item => item.target.coefficient === group.coefficient)!;
      return entry.hasExplicitColor
        ? entry.target
        : { ...entry.target, color: CONSTRUCTION_COLORS[index % CONSTRUCTION_COLORS.length] };
    });
    return { coefficients: [...state.coefficients], targets: ordered };
  }

  return {
    coefficients: [...state.coefficients],
    targets: parsedTargets.map(entry => entry.target),
  };
}

export function serializeConstructionState(state: ConstructionState) {
  return {
    v: 1,
    mode: 'preimage-construction' as const,
    coefficients: [...state.coefficients],
    targets: state.targets.map(target => {
      const intervals = getTargetIntervals(target);
      if (intervals.length === 1) {
        return {
          coefficient: target.coefficient,
          start: intervals[0].start,
          width: intervals[0].width,
          color: target.color,
        };
      }
      return {
        coefficient: target.coefficient,
        intervals: intervals.map(arc => ({ start: arc.start, width: arc.width })),
        color: target.color,
      };
    }),
  };
}

export function resetOptimalWidths(state: ConstructionState): ConstructionState {
  const normalized = normalizeConstructionState(state);
  const groups = groupCoefficients(normalized.coefficients);
  return {
    coefficients: [...normalized.coefficients],
    targets: groups.map((group, index) => {
      const existing = normalized.targets.find(target => target.coefficient === group.coefficient)
        ?? normalized.targets.find(target => Math.abs(target.coefficient) === group.coefficient);
      const firstArc = existing ? getTargetIntervals(existing)[0] : undefined;
      return {
        coefficient: group.coefficient,
        start: firstArc?.start ?? 0,
        width: 1 / (groups.length * group.multiplicity),
        color: existing?.color ?? CONSTRUCTION_COLORS[index % CONSTRUCTION_COLORS.length],
      };
    }),
  };
}

/** Pick a partition cell attaining the pigeonhole bound in a one-dimensional sweep. */
export function findGuaranteedShift(state: ConstructionState): ConstructionState {
  const reset = resetOptimalWidths(state);
  const groups = groupCoefficients(reset.coefficients);
  if (!groups.length) return reset;
  const partitionCounts = groups.map(group => groups.length * group.multiplicity);
  const denominators = groups.map((group, index) => group.coefficient * partitionCounts[index]);
  if (denominators.some(value => !Number.isSafeInteger(value)) || denominators.reduce((a, b) => a + b, 0) > 100000) {
    throw new Error('The guaranteed-shift search is too large for the browser. Use fewer or smaller coefficients.');
  }
  const boundaries = [0, 1];
  for (const denominator of denominators) for (let k = 1; k < denominator; k += 1) boundaries.push(k / denominator);
  boundaries.sort((a, b) => a - b);
  const cells = new Map<string, { indices: number[]; measure: number }>();
  for (let i = 1; i < boundaries.length; i += 1) {
    const left = boundaries[i - 1];
    const right = boundaries[i];
    if (right - left <= TOLERANCE) continue;
    const midpoint = (left + right) / 2;
    const indices = groups.map((group, index) => Math.min(partitionCounts[index] - 1,
      Math.floor(normalizeTurn(group.coefficient * midpoint) * partitionCounts[index])));
    const key = indices.join(',');
    const cell = cells.get(key);
    if (cell) cell.measure += right - left;
    else cells.set(key, { indices, measure: right - left });
  }
  let best: { indices: number[]; measure: number } | undefined;
  for (const cell of cells.values()) if (!best || cell.measure > best.measure + TOLERANCE) best = cell;
  if (!best) throw new Error('No partition cell could be resolved at browser precision.');
  return { ...reset, targets: reset.targets.map((target, index) => ({
    ...target, start: best!.indices[index] / partitionCounts[index],
  })) };
}

export function defaultConstructionState(coefficients: number[] = [10, 10, -19]): ConstructionState {
  const groups = groupCoefficients(coefficients);
  return findGuaranteedShift({ coefficients, targets: groups.map((group, index) => ({
    coefficient: group.coefficient, start: 0, width: 1 / (groups.length * group.multiplicity),
    color: CONSTRUCTION_COLORS[index % CONSTRUCTION_COLORS.length],
  })) });
}

export function evaluateConstruction(state: ConstructionState): ConstructionEvaluation {
  const normalized = normalizeConstructionState(state);
  const groups = groupCoefficients(normalized.coefficients);
  const targetSets = normalized.targets.map(target => openCircleSet(getTargetIntervals(target)));
  const preimages = normalized.targets.map(target => preimage(getTargetIntervals(target), target.coefficient));
  const a = preimages.reduce(intersectSets, fullSet());
  const isCanonical = isCanonicalRuzsaTargets(groups, normalized.targets);
  const guaranteedDensity = groups.reduce((product, group) => product / (groups.length * group.multiplicity), 1);

  let boundWidth: number | null = null;
  let widthGuarantee = false;
  let boundWitness: number | null = null;
  let image: OpenCircleSet;

  if (isCanonical) {
    let lower = 0;
    let widthSum = 0;
    let compensation = 0;
    for (let index = 0; index < groups.length; index += 1) {
      const group = groups[index];
      const target = normalized.targets[index];
      const negative = normalized.coefficients.filter(coefficient => coefficient === -group.coefficient).length;
      lower += (group.multiplicity - 2 * negative) * target.start - negative * target.width;
      // Sum each multiplicity once, with compensation, so repeated fractions
      // at the optimal widths do not accumulate an artificial excess over one.
      const weighted = group.multiplicity * target.width - compensation;
      const next = widthSum + weighted;
      compensation = (next - widthSum) - weighted;
      widthSum = next;
    }
    boundWidth = widthSum;
    // With one group, d(A) is exactly its target I. The image is the signed
    // independent sum of copies of I; no large-coefficient floating dilation
    // is needed to recover it from thousands of tiny preimage components.
    image = groups.length === 1
      ? isEmpty(a) ? emptySet() : widthSum > 1 ? fullSet() : openCircleSet([{ start: lower, width: widthSum }])
      : applyLinearForm(a, normalized.coefficients);
    widthGuarantee = widthSum <= 1;
    boundWitness = widthGuarantee
      ? normalizeTurn(widthSum === 1 ? lower : lower + widthSum + (1 - widthSum) / 2)
      : null;
    if (boundWitness !== null && containsPoint(image, boundWitness)) throw precisionError();
  } else if (normalized.targets.length === 1
      && normalized.coefficients.every(coefficient => coefficient % normalized.targets[0].coefficient === 0)) {
    // With a single preimage A = d^{-1}(U), surjectivity gives d(A) = U, so any
    // linear form with coefficients divisible by d evaluates directly on U.
    const d = normalized.targets[0].coefficient;
    image = isEmpty(a) ? emptySet() : applyLinearForm(targetSets[0], normalized.coefficients.map(c => c / d));
  } else {
    image = applyLinearForm(a, normalized.coefficients);
  }

  const missingPoint = boundWitness ?? findMissingPoint(image);
  // Outside the width guarantee, an almost-touching overlap can be hidden
  // by floating tolerance. Do not certify an isolated hole at that scale.
  if (isCanonical && !widthGuarantee && boundWidth !== null && boundWidth - 1 <= TOLERANCE && missingPoint !== null
      && (containsPoint(image, missingPoint - 4 * TOLERANCE) || containsPoint(image, missingPoint + 4 * TOLERANCE))) {
    throw precisionError();
  }
  const intervals: Interval[] = (a.full ? [{ start: 0, width: 1 }] : a.arcs).map((arc, index) => ({
    ...arc, id: index + 1, color: '#0f766e',
  }));
  return {
    targetSets, preimages, a, image, intervals,
    density: setMeasure(a), imageMeasure: setMeasure(image),
    missingPoint,
    boundWidth, boundWitness, widthGuarantee,
    guaranteedDensity,
    isCanonical,
  };
}
