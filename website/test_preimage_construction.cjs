const assert = require('node:assert/strict');
const test = require('node:test');
const { loadSource } = require('./load_ts.cjs');

const shared = loadSource('shared.ts');
const geometry = loadSource('preimageConstruction.ts');
const {
  applyLinearForm, containsPoint, defaultConstructionState, evaluateConstruction,
  findGuaranteedShift, findMissingPoint, getTargetIntervals, groupCoefficients,
  intersectSets, normalizeConstructionState, openCircleSet, preimage,
  resetOptimalWidths, serializeConstructionState, setMeasure, suggestNewInterval,
  suggestNewMultiplier,
} = geometry;
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-10, `${actual} != ${expected}`);
const arc = (start, width) => openCircleSet([{ start, width }]);

test('open arcs retain punctures, touching holes, and wrapping interiors', () => {
  const punctured = arc(0.25, 1);
  assert.equal(punctured.full, false);
  assert.equal(containsPoint(punctured, 0.25), false);
  assert.equal(containsPoint(punctured, 0), true);
  close(setMeasure(punctured), 1);
  close(findMissingPoint(punctured), 0.25);
  const touching = openCircleSet([{ start: 0, width: 0.5 }, { start: 0.5, width: 0.5 }]);
  assert.equal(touching.full, false);
  assert.equal(containsPoint(touching, 0), false);
  assert.equal(containsPoint(touching, 0.5), false);
  const wrapped = openCircleSet([{ start: 0.75, width: 0.4 }, { start: 0, width: 0.25 }]);
  close(setMeasure(wrapped), 0.5);
  assert.equal(containsPoint(wrapped, 0), true);
  assert.equal(containsPoint(wrapped, 0.75), false);
});

test('preimages agree with multiplication at endpoints and intermediate points', () => {
  for (const start of [0, 0.25, 0.5, 0.75]) for (const width of [0, 0.25, 0.5, 0.75, 1]) {
    const target = arc(start, width);
    for (let coefficient = 1; coefficient <= 6; coefficient += 1) {
      const set = preimage({ start, width }, coefficient);
      close(setMeasure(set), width);
      for (let numerator = 0; numerator < 8 * coefficient; numerator += 1) {
        const point = numerator / (8 * coefficient);
        assert.equal(containsPoint(set, point), containsPoint(target, coefficient * point),
          JSON.stringify({ start, width, coefficient, point }));
      }
    }
  }
});

test('intersection respects open endpoints and wrapping', () => {
  const left = arc(0.75, 0.5);
  const right = arc(0.125, 0.75);
  const intersection = intersectSets(left, right);
  close(setMeasure(intersection), 0.25);
  assert.equal(intersection.arcs.length, 2);
  for (let i = 0; i < 32; i += 1) {
    const point = i / 32;
    assert.equal(containsPoint(intersection, point), containsPoint(left, point) && containsPoint(right, point));
  }
});

test('linear forms distinguish signed dilation from independent sums', () => {
  const set = openCircleSet([{ start: 0, width: 0.05 }, { start: 0.25, width: 0.05 }]);
  const dilation = applyLinearForm(set, [2]);
  const sum = applyLinearForm(set, [1, 1]);
  assert.equal(containsPoint(dilation, 0.3), false);
  assert.equal(containsPoint(sum, 0.3), true);
  const negative = applyLinearForm(arc(0.2, 0.1), [-2]);
  close(negative.arcs[0].start, 0.4);
  close(negative.arcs[0].width, 0.2);
  const punctured = applyLinearForm(arc(0, 0.5), [1, 1]);
  assert.equal(punctured.full, false);
  assert.equal(containsPoint(punctured, 0), false);
  close(setMeasure(punctured), 1);
  assert.equal(applyLinearForm(arc(0, 0.5), [1, 1, 1]).full, true);
});

test('zero forms and empty input have distinct exact meanings', () => {
  const singleton = applyLinearForm(arc(0.1, 0.2), [0, 0]);
  assert.deepEqual(singleton.points, [0]);
  assert.equal(containsPoint(singleton, 0), true);
  assert.equal(containsPoint(singleton, 0.5), false);
  close(findMissingPoint(singleton), 0.5);
  assert.deepEqual(applyLinearForm(openCircleSet([]), [0]), openCircleSet([]));
  const zeroConstruction = evaluateConstruction(defaultConstructionState([0, 0]));
  assert.equal(zeroConstruction.a.full, true);
  assert.deepEqual(zeroConstruction.image.points, [0]);
  close(zeroConstruction.density, 1);
  close(zeroConstruction.guaranteedDensity, 1);
  close(zeroConstruction.missingPoint, 0.5);
});

test('groups share one target for opposite signs and repeated absolute coefficients', () => {
  assert.deepEqual(groupCoefficients([10, -10, 0, -19, 10]), [
    { coefficient: 10, multiplicity: 3 }, { coefficient: 19, multiplicity: 1 },
  ]);
  const state = defaultConstructionState([10, -10, 0, -19, 10]);
  close(state.targets[0].width, 1 / 6);
  close(state.targets[1].width, 1 / 2);
  close(evaluateConstruction(state).guaranteedDensity, 1 / 12);
});

test('guaranteed partition search attains the pigeonhole density bound', () => {
  for (const coefficients of [[10, 10, -19], [1, 1, -3], [1, -1], [2, 0, -3, 4], [-5], [2, -2, 2]]) {
    const state = defaultConstructionState(coefficients);
    const result = evaluateConstruction(state);
    close(result.boundWidth, 1);
    assert.equal(result.widthGuarantee, true);
    assert.ok(result.density >= result.guaranteedDensity - 1e-10, JSON.stringify({ coefficients, result }));
    assert.notEqual(result.missingPoint, null);
    assert.equal(containsPoint(result.image, result.missingPoint), false);
    assert.deepEqual(findGuaranteedShift(state), state);
  }
});

test('every shift at guaranteed widths keeps the signed bounding witness missing', () => {
  for (const coefficients of [[10, 10, -19], [1, 1, -3], [1, -1], [2, 0, -3, 4]]) {
    const original = defaultConstructionState(coefficients);
    for (let k = 0; k < 11; k += 1) {
      const state = { ...original, targets: original.targets.map((target, i) => ({ ...target, start: ((i + 2) * k % 11) / 11 })) };
      const result = evaluateConstruction(state);
      assert.equal(result.widthGuarantee, true);
      assert.notEqual(result.missingPoint, null);
      assert.equal(containsPoint(result.image, result.missingPoint), false, JSON.stringify({ coefficients, state, result }));
    }
  }
});

test('width reset preserves shifts and colors and does not mutate state', () => {
  const original = defaultConstructionState([10, 10, -19]);
  const changed = { ...original, targets: original.targets.map((target, i) => ({ ...target, start: (i + 1) / 7, width: 0.8, color: '#112233' })) };
  const snapshot = JSON.stringify(changed);
  const reset = resetOptimalWidths(changed);
  assert.equal(JSON.stringify(changed), snapshot);
  assert.deepEqual(reset.targets.map(target => target.start), changed.targets.map(target => target.start));
  assert.deepEqual(reset.targets.map(target => target.color), ['#112233', '#112233']);
  close(reset.targets[0].width, 0.25);
  close(reset.targets[1].width, 0.5);
});

test('wide targets can cover the circle and report no missing point', () => {
  const state = normalizeConstructionState({ coefficients: [1, 1], targets: [{ coefficient: 1, start: 0.1, width: 0.75 }] });
  const result = evaluateConstruction(state);
  assert.equal(result.widthGuarantee, false);
  assert.equal(result.image.full, true);
  assert.equal(result.missingPoint, null);
  assert.equal(result.boundWitness, null);
});

test('state import accepts a Python-style schema and rejects malformed data', () => {
  const raw = { mode: 'preimage-construction', coefficients: [10, 10, -19], targets: [
    { coefficient: 19, start: -0.25, width: 0.5 }, { coefficient: 10, start: 1.5, width: 0.25 },
  ] };
  const state = normalizeConstructionState(raw);
  assert.equal(state.targets[0].coefficient, 10);
  close(state.targets[0].start, 0.5);
  close(state.targets[1].start, 0.75);
  assert.throws(() => normalizeConstructionState({ ...raw, coefficients: [] }), /nonempty/);
  assert.throws(() => normalizeConstructionState({ ...raw, coefficients: [1.5] }), /integer/);
  assert.throws(() => normalizeConstructionState({ ...raw, targets: [] }), /one target/);
  assert.throws(() => normalizeConstructionState({ ...raw, targets: raw.targets.map(target => ({ ...target, width: 2 })) }), /widths/);
  assert.throws(() => normalizeConstructionState({ ...raw, targets: raw.targets.map(target => ({ ...target, start: Infinity })) }), /finite/);
});

test('interactive work limits reject unresolved computations instead of returning partial sets', () => {
  assert.throws(() => preimage({ start: 0, width: 0.25 }, 5001), /preimage arcs/);
  assert.throws(() => defaultConstructionState([100000, 100001]), /too large/);
});

test('a large single coefficient preserves the target puncture in its image', () => {
  const result = evaluateConstruction({ coefficients: [5000], targets: [
    { coefficient: 5000, start: 0, width: 1 },
  ] });
  assert.equal(result.image.full, false);
  assert.equal(containsPoint(result.image, 0), false);
  assert.equal(containsPoint(result.image, 0.5), true);
  assert.equal(containsPoint(result.image, result.missingPoint), false);
});

test('positive widths below display precision are rejected instead of shown as empty', () => {
  assert.throws(() => evaluateConstruction({ coefficients: [1], targets: [
    { coefficient: 1, start: 0, width: 1e-13 },
  ] }), /browser precision/);
  assert.throws(() => preimage({ start: 0, width: 1e-10 }, 1000), /browser precision/);
});

test('an actual excess over unit width is not granted an endpoint certificate', () => {
  const result = evaluateConstruction({ coefficients: [1, 1], targets: [
    { coefficient: 1, start: 0, width: 0.5000000000002 },
  ] });
  assert.equal(result.widthGuarantee, false);
  assert.equal(result.image.full, true);
  assert.equal(result.missingPoint, null);
});

test('preimage of a union of intervals agrees with multiplication for positive and negative multipliers', () => {
  const intervals = [{ start: 0.1, width: 0.15 }, { start: 0.55, width: 0.2 }, { start: 0.9, width: 0.15 }];
  const union = openCircleSet(intervals);
  for (const multiplier of [-4, -2, -1, 1, 2, 3, 5]) {
    const set = preimage(intervals, multiplier);
    close(setMeasure(set), setMeasure(union));
    const denom = 16 * Math.abs(multiplier);
    for (let k = 0; k < denom; k += 1) {
      const point = k / denom;
      assert.equal(
        containsPoint(set, point),
        containsPoint(union, multiplier * point),
        JSON.stringify({ multiplier, point }),
      );
    }
  }
  const fullPreimage = preimage([{ start: 0, width: 0.7 }, { start: 0.5, width: 0.7 }], 3);
  assert.equal(fullPreimage.full, true);
  assert.throws(() => preimage(intervals, 0), /nonzero/);
});

test('custom multipliers and multi-interval targets evaluate, serialize, and reset cleanly', () => {
  const custom = normalizeConstructionState({
    mode: 'preimage-construction',
    coefficients: [1, 1, -3],
    targets: [
      { coefficient: 2, intervals: [{ start: 0, width: 0.2 }, { start: 0.5, width: 0.2 }], color: '#ef4444' },
      { coefficient: -3, start: 0.1, width: 0.25, color: '#3b82f6' },
    ],
  });
  assert.equal(custom.targets.length, 2);
  assert.equal(custom.targets[0].coefficient, 2);
  assert.equal(getTargetIntervals(custom.targets[0]).length, 2);
  assert.equal(custom.targets[1].coefficient, -3);

  const evaluated = evaluateConstruction(custom);
  assert.equal(evaluated.isCanonical, false);
  assert.equal(evaluated.boundWidth, null);
  assert.equal(evaluated.widthGuarantee, false);
  assert.ok(evaluated.density > 0);
  if (evaluated.missingPoint !== null) {
    assert.equal(containsPoint(evaluated.image, evaluated.missingPoint), false);
  }

  // Round-trip through serialized JSON preserves multi-interval & custom multipliers.
  const serialized = serializeConstructionState(custom);
  assert.ok(Array.isArray(serialized.targets[0].intervals));
  assert.equal(serialized.targets[0].intervals.length, 2);
  assert.equal('intervals' in serialized.targets[1], false);
  const reloaded = normalizeConstructionState(serialized);
  assert.deepEqual(reloaded, custom);

  // Resetting restores canonical Ruzsa targets for [1, 1, -3] (multipliers 1 and 3).
  const reset = resetOptimalWidths(custom);
  assert.deepEqual(reset.targets.map(t => t.coefficient), [1, 3]);
  assert.equal(evaluateConstruction(reset).isCanonical, true);
});

test('single-target multi-interval shortcut matches direct linear-form evaluation', () => {
  const state = normalizeConstructionState({
    coefficients: [4, -6],
    targets: [{ coefficient: 2, intervals: [{ start: 0, width: 0.1 }, { start: 0.5, width: 0.1 }] }],
  });
  const result = evaluateConstruction(state);
  const direct = applyLinearForm(result.a, state.coefficients);
  close(setMeasure(result.image), setMeasure(direct));
  for (let k = 0; k < 64; k += 1) {
    assert.equal(containsPoint(result.image, k / 64), containsPoint(direct, k / 64));
  }
});

test('helper suggestions place new intervals in gaps and pick fresh multipliers', () => {
  const existing = [{ start: 0, width: 0.5 }];
  const added = suggestNewInterval(existing);
  assert.ok(added.width > 0);
  assert.equal(containsPoint(openCircleSet(existing), added.start + added.width / 2), false);

  const state = defaultConstructionState([1, 1, -3]);
  assert.equal(suggestNewMultiplier(state.targets, state.coefficients), 2);
});

test('numeric input parser handles floats, scientific notation, fractions, and strict integers', () => {
  const { parseNumericInput } = shared;
  close(parseNumericInput('0.25'), 0.25);
  close(parseNumericInput('.5'), 0.5);
  close(parseNumericInput(' -1.25e-2 '), -0.0125);
  close(parseNumericInput('1/3'), 1 / 3);
  close(parseNumericInput('-2 / 7'), -2 / 7);
  assert.equal(parseNumericInput('1/0'), null);
  assert.equal(parseNumericInput(''), null);
  assert.equal(parseNumericInput('0.2.3'), null);
  assert.equal(parseNumericInput('10', { integer: true }), 10);
  assert.equal(parseNumericInput('-19', { integer: true }), -19);
  assert.equal(parseNumericInput('1.5', { integer: true }), null);
  assert.equal(parseNumericInput('1/2', { integer: true }), null);
});
