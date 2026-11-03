const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const test = require('node:test');
const ts = require('typescript');

function loadTypeScript(name, imports = {}) {
  const filename = path.join(__dirname, 'src', name);
  const loaded = new Module(filename, module);
  loaded.paths = module.paths;
  loaded.require = name => imports[name] ?? require(name);
  loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText, filename);
  return loaded.exports;
}
const oldGeometry = loadTypeScript('linearFormGeometry.ts');
const geometry = loadTypeScript('preimageConstruction.ts', { './linearFormGeometry': oldGeometry });
const {
  applyLinearForm, containsPoint, defaultConstructionState, evaluateConstruction,
  findGuaranteedShift, findMissingPoint, groupCoefficients, intersectSets,
  normalizeConstructionState, openCircleSet, preimage, resetOptimalWidths, setMeasure,
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
