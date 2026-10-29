/** Shared interval editing rules used by both circle visualizer modes. */
export const EPSILON = 1e-9;

// Splits an interval [s, e] into segments strictly within [0, 1].
export function getWrappedSegments(s, e) {
  let segments = [];
  if (s > e) {
    let temp = s; s = e; e = temp;
  }
  let L = e - s;
  if (L <= 0) return [];

  let startInt = Math.floor(s);
  let endInt = Math.floor(e);

  if (startInt === endInt) {
    segments.push([s - startInt, e - startInt]);
  } else {
    segments.push([s - startInt, 1]);
    for (let i = startInt + 1; i < endInt; i++) {
      segments.push([0, 1]);
    }
    if (e - endInt > EPSILON) {
      segments.push([0, e - endInt]);
    }
  }
  return segments;
}

export function normalizeTurn(value) {
  return ((value % 1) + 1) % 1;
}

export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export function circularDistance(a, b) {
  const diff = Math.abs(normalizeTurn(a) - normalizeTurn(b));
  return Math.min(diff, 1 - diff);
}

export function signedCircularDelta(value, origin) {
  let delta = normalizeTurn(value) - normalizeTurn(origin);
  if (delta > 0.5) delta -= 1;
  if (delta < -0.5) delta += 1;
  return delta;
}

export function intervalSegments(start, width) {
  if (width <= EPSILON) return [];
  return getWrappedSegments(start, start + Math.min(width, 1));
}

export function intervalsOverlapOnCircle(startA, widthA, startB, widthB) {
  if (widthA <= EPSILON || widthB <= EPSILON) return false;

  const segmentsA = intervalSegments(startA, widthA);
  const segmentsB = intervalSegments(startB, widthB);
  return segmentsA.some(a => (
    segmentsB.some(b => Math.max(a[0], b[0]) < Math.min(a[1], b[1]) - EPSILON)
  ));
}

export function isStartAllowed(start, width, otherIntervals) {
  return !otherIntervals.some(other => (
    intervalsOverlapOnCircle(start, width, other.start, other.width)
  ));
}

export function getForbiddenStartSegments(width, otherIntervals) {
  if (width <= EPSILON) return [];

  const rawSegments = [];
  for (const other of otherIntervals) {
    if (other.width <= EPSILON) continue;

    const forbiddenLength = width + other.width;
    if (forbiddenLength >= 1 - EPSILON) {
      return [{ start: 0, end: 1 }];
    }

    const start = normalizeTurn(other.start - width);
    const end = start + forbiddenLength;
    if (end <= 1 + EPSILON) {
      rawSegments.push({ start, end: Math.min(end, 1) });
    } else {
      rawSegments.push({ start, end: 1 });
      rawSegments.push({ start: 0, end: end - 1 });
    }
  }

  if (rawSegments.length === 0) return [];

  const sorted = rawSegments.sort((a, b) => a.start - b.start);
  const merged = [];
  let current = { ...sorted[0] };
  for (let i = 1; i < sorted.length; i++) {
    const segment = sorted[i];
    if (segment.start <= current.end + EPSILON) {
      current.end = Math.max(current.end, segment.end);
    } else {
      merged.push(current);
      current = { ...segment };
    }
  }
  merged.push(current);
  return merged;
}

export function forbiddenStartBackground(forbiddenSegments) {
  const allowedColor = '#dbeafe';
  const forbiddenColor = 'rgba(248, 113, 113, 0.5)';

  if (!forbiddenSegments || forbiddenSegments.length === 0) return allowedColor;
  if (forbiddenSegments.length === 1 && forbiddenSegments[0].start <= EPSILON && forbiddenSegments[0].end >= 1 - EPSILON) {
    return forbiddenColor;
  }

  const stops = [];
  let cursor = 0;
  forbiddenSegments.forEach(segment => {
    const start = clamp(segment.start, 0, 1);
    const end = clamp(segment.end, 0, 1);
    if (start > cursor + EPSILON) {
      stops.push(`${allowedColor} ${cursor * 100}%`, `${allowedColor} ${start * 100}%`);
    }
    stops.push(`${forbiddenColor} ${start * 100}%`, `${forbiddenColor} ${end * 100}%`);
    cursor = Math.max(cursor, end);
  });

  if (cursor < 1 - EPSILON) {
    stops.push(`${allowedColor} ${cursor * 100}%`, `${allowedColor} 100%`);
  }

  return `linear-gradient(to right, ${stops.join(', ')})`;
}

export function maxValueBackground(maxValue) {
  const allowedColor = '#dbeafe';
  const forbiddenColor = 'rgba(248, 113, 113, 0.5)';
  const cutoff = clamp(maxValue, 0, 1) * 100;

  if (cutoff >= 100 - EPSILON) return allowedColor;
  if (cutoff <= EPSILON) return forbiddenColor;
  return `linear-gradient(to right, ${allowedColor} 0%, ${allowedColor} ${cutoff}%, ${forbiddenColor} ${cutoff}%, ${forbiddenColor} 100%)`;
}

export function snapStartToAllowed(desiredStart, width, otherIntervals, fallbackStart) {
  const desired = normalizeTurn(desiredStart);
  if (width <= EPSILON || isStartAllowed(desired, width, otherIntervals)) return desired;
  if (width + otherIntervals.reduce((sum, interval) => sum + interval.width, 0) > 1 + EPSILON) {
    return normalizeTurn(fallbackStart);
  }

  const candidates = [];
  otherIntervals.forEach(other => {
    candidates.push(normalizeTurn(other.start + other.width));
    candidates.push(normalizeTurn(other.start - width));
  });

  let bestStart = normalizeTurn(fallbackStart);
  let bestDistance = Infinity;
  candidates.forEach(candidate => {
    if (!isStartAllowed(candidate, width, otherIntervals)) return;
    const distance = circularDistance(candidate, desired);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestStart = candidate;
    }
  });

  return bestStart;
}

export function getClockwiseOrderFromAnchor(intervals, anchorId = intervals[0]?.id) {
  const anchor = intervals.find(interval => interval.id === anchorId) || intervals[0];
  if (!anchor) return [];

  const anchorStart = normalizeTurn(anchor.start);
  return [...intervals].sort((a, b) => {
    if (a.id === anchor.id) return -1;
    if (b.id === anchor.id) return 1;
    return normalizeTurn(a.start - anchorStart) - normalizeTurn(b.start - anchorStart);
  });
}

export function packIntervalsConsecutively(intervals, anchorId = intervals[0]?.id) {
  const ordered = getClockwiseOrderFromAnchor(intervals, anchorId);
  if (ordered.length === 0) return intervals;

  const packedById = new Map();
  let currentStart = normalizeTurn(ordered[0].start);
  ordered.forEach(interval => {
    packedById.set(interval.id, { ...interval, start: normalizeTurn(currentStart) });
    currentStart += interval.width;
  });

  return intervals.map(interval => packedById.get(interval.id) || interval);
}

export function packIntervalsClockwise(intervals, anchorId = intervals[0]?.id) {
  if (intervals.length <= 1) {
    return intervals.map(interval => ({ ...interval, start: normalizeTurn(interval.start) }));
  }

  const totalWidth = intervals.reduce((sum, interval) => sum + interval.width, 0);
  if (totalWidth > 1 + EPSILON) return intervals;

  const anchor = intervals.find(interval => interval.id === anchorId) || intervals[0];
  const anchorStart = normalizeTurn(anchor.start);
  const ordered = getClockwiseOrderFromAnchor(intervals, anchorId);

  const packedById = new Map();
  let currentEnd = anchorStart;
  ordered.forEach((interval, index) => {
    let liftedStart = index === 0 ? anchorStart : anchorStart + normalizeTurn(interval.start - anchorStart);
    if (index > 0 && liftedStart < currentEnd - EPSILON) {
      liftedStart = currentEnd;
    }

    packedById.set(interval.id, { ...interval, start: normalizeTurn(liftedStart) });
    currentEnd = liftedStart + interval.width;
  });

  if (currentEnd > anchorStart + 1 + EPSILON) {
    return packIntervalsConsecutively(intervals, anchorId);
  }

  return intervals.map(interval => packedById.get(interval.id) || interval);
}

export function scaleIntervalsToTotal(intervals, targetTotal) {
  if (intervals.length === 0) return intervals;

  const total = intervals.reduce((sum, interval) => sum + interval.width, 0);
  if (targetTotal <= EPSILON) {
    return intervals.map(interval => ({ ...interval, width: 0 }));
  }

  if (total <= EPSILON) {
    const equalWidth = targetTotal / intervals.length;
    return intervals.map(interval => ({ ...interval, width: equalWidth }));
  }

  const scale = targetTotal / total;
  return intervals.map(interval => ({ ...interval, width: interval.width * scale }));
}

export function balanceWidthsToTarget(intervals, targetTotal, preferredIndex = 0) {
  if (intervals.length === 0) return intervals;

  const balanced = intervals.map(interval => ({ ...interval, width: Math.max(0, interval.width) }));
  let diff = targetTotal - balanced.reduce((sum, interval) => sum + interval.width, 0);
  const preferred = ((preferredIndex % balanced.length) + balanced.length) % balanced.length;

  if (diff > EPSILON) {
    balanced[preferred].width += diff;
  } else if (diff < -EPSILON) {
    let remaining = -diff;
    for (let step = 0; step < balanced.length && remaining > EPSILON; step++) {
      const index = (preferred + step) % balanced.length;
      const reduction = Math.min(balanced[index].width, remaining);
      balanced[index].width -= reduction;
      remaining -= reduction;
    }
  }

  return balanced;
}

export function resizeWithFixedTotal(intervals, intervalIndex, requestedWidth, targetTotal) {
  if (intervals.length === 0) return intervals;

  const next = intervals.map(interval => ({ ...interval }));
  const index = ((intervalIndex % next.length) + next.length) % next.length;
  const nextIndex = (index + 1) % next.length;

  if (next.length === 1) {
    next[index].width = targetTotal;
    return next;
  }

  const currentWidth = next[index].width;
  const desiredWidth = clamp(requestedWidth, 0, targetTotal);
  let delta = desiredWidth - currentWidth;
  next[index].width = desiredWidth;

  if (delta > EPSILON) {
    let remaining = delta;
    for (let step = 1; step < next.length && remaining > EPSILON; step++) {
      const donorIndex = (index + step) % next.length;
      const reduction = Math.min(next[donorIndex].width, remaining);
      next[donorIndex].width -= reduction;
      remaining -= reduction;
    }

    if (remaining > EPSILON) {
      next[index].width = Math.max(0, next[index].width - remaining);
    }
  } else if (delta < -EPSILON) {
    next[nextIndex].width += -delta;
  }

  return balanceWidthsToTarget(next, targetTotal, nextIndex);
}

export function resizeWithinMaxTotal(intervals, intervalIndex, requestedWidth, maxTotal = 1) {
  if (intervals.length === 0) return intervals;

  const next = intervals.map(interval => ({ ...interval }));
  const index = ((intervalIndex % next.length) + next.length) % next.length;
  const desiredWidth = clamp(requestedWidth, 0, maxTotal);
  const otherWidth = next.reduce((sum, interval, i) => i === index ? sum : sum + interval.width, 0);
  let overflow = desiredWidth + otherWidth - maxTotal;

  next[index].width = desiredWidth;

  if (overflow > EPSILON) {
    for (let step = 1; step < next.length && overflow > EPSILON; step++) {
      const donorIndex = (index + step) % next.length;
      const reduction = Math.min(next[donorIndex].width, overflow);
      next[donorIndex].width -= reduction;
      overflow -= reduction;
    }

    if (overflow > EPSILON) {
      next[index].width = Math.max(0, next[index].width - overflow);
    }
  }

  return next;
}

export function moveIntervalStart(intervals, id, requestedStart) {
  const interval = intervals.find(item => item.id === id);
  if (!interval) return intervals;

  const others = intervals.filter(item => item.id !== id);
  const snappedStart = snapStartToAllowed(requestedStart, interval.width, others, interval.start);
  return intervals.map(item => item.id === id ? { ...item, start: snappedStart } : item);
}

export function changeIntervalWidth(intervals, id, requestedWidth, fixTotalLength = false, targetTotal = 1) {
  const intervalIndex = intervals.findIndex(item => item.id === id);
  if (intervalIndex === -1) return intervals;

  const requested = clamp(requestedWidth, 0, 1);
  const next = fixTotalLength
    ? resizeWithFixedTotal(intervals, intervalIndex, requested, targetTotal)
    : resizeWithinMaxTotal(intervals, intervalIndex, requested, 1);
  return packIntervalsClockwise(next, id);
}

export function appendInterval(intervals, newInterval, fixTotalLength = false) {
  const usedLength = intervals.reduce((sum, interval) => sum + interval.width, 0);
  const width = fixTotalLength ? 0 : Math.min(0.1, Math.max(0, 1 - usedLength));
  const added = { ...newInterval, width };
  added.start = snapStartToAllowed(added.start, added.width, intervals, 0);
  return packIntervalsClockwise([...intervals, added], added.id);
}
