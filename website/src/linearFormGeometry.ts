/** Circle-set arithmetic for the arbitrary linear-form visualizer. */
export type Segment = [number, number];
export type Interval = { id: number; start: number; width: number; color: string };

export const normalizeTurn = (value: number) => ((value % 1) + 1) % 1;

export function wrappedSegments(left: number, right: number): Segment[] {
  const width = Math.max(0, right - left);
  if (width >= 1) return [[0, 1]];
  const start = normalizeTurn(left);
  const end = start + width;
  return end <= 1 ? [[start, end]] : [[start, 1], [0, end - 1]];
}

export function mergeSegments(segments: Segment[]): Segment[] {
  const ordered = [...segments].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: Segment[] = [];
  for (const [start, end] of ordered) {
    const previous = merged[merged.length - 1];
    if (previous && start <= previous[1] + 1e-12) {
      previous[1] = Math.max(previous[1], end);
    } else {
      merged.push([start, end]);
    }
  }
  return merged;
}

export function intervalSegments(intervals: Interval[]): Segment[] {
  return mergeSegments(intervals.flatMap(({ start, width }) => wrappedSegments(start, start + width)));
}

export function measure(segments: Segment[]): number {
  return mergeSegments(segments).reduce((total, [start, end]) => total + end - start, 0);
}

export function linearFormSegments(intervals: Interval[], coefficients: number[], budget = 250000): Segment[] {
  if (!intervals.length) return [];
  // Each term is a dilation c*A, not a sum of |c| independent copies of A.
  // Merging between Minkowski sums avoids enumerating every interval tuple.
  let result: Segment[] = [[0, 0]];
  let operations = 0;
  for (const coefficient of coefficients) {
    if (coefficient === 0) continue;
    const term = mergeSegments(intervals.flatMap(({ start, width }) => (
      coefficient > 0
        ? wrappedSegments(coefficient * start, coefficient * (start + width))
        : wrappedSegments(coefficient * (start + width), coefficient * start)
    )));
    const sums: Segment[] = [];
    for (const [left, right] of result) {
      for (const [termLeft, termRight] of term) {
        operations += 1;
        if (operations > budget) {
          throw new Error('This configuration is too large to draw the full image interactively. The intervals and saved solver result remain available.');
        }
        if (right - left + termRight - termLeft >= 1) return [[0, 1]];
        sums.push(...wrappedSegments(left + termLeft, right + termRight));
      }
    }
    result = mergeSegments(sums);
    if (result.length === 1 && result[0][0] === 0 && result[0][1] === 1) return result;
  }
  return result;
}
