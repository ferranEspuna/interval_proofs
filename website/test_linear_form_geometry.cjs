const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const test = require('node:test');
const ts = require('typescript');

const filename = path.join(__dirname, 'src', 'linearFormGeometry.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const geometry = new Module(filename, module);
geometry._compile(compiled.outputText, filename);
const { linearFormSegments, mergeSegments, measure, wrappedSegments } = geometry.exports;

const interval = (start, width, id = 1) => ({ id, start, width, color: '#ef4444' });
function close(actual, expected) {
  assert.equal(actual.length, expected.length, JSON.stringify({ actual, expected }));
  actual.forEach((segment, i) => segment.forEach((value, j) => {
    assert.ok(Math.abs(value - expected[i][j]) < 1e-10, JSON.stringify({ actual, expected }));
  }));
}

test('dilation is not a repeated independent sum', () => {
  const intervals = [interval(0, 0.05), interval(0.25, 0.05, 2)];
  close(linearFormSegments(intervals, [2]), [[0, 0.1], [0.5, 0.6]]);
  close(linearFormSegments(intervals, [1, 1]), [[0, 0.1], [0.25, 0.35], [0.5, 0.6]]);
});

test('negative dilations, wrapping, and degenerate points', () => {
  close(linearFormSegments([interval(0.2, 0.1)], [-2]), [[0.4, 0.6]]);
  close(wrappedSegments(0.9, 1.1), [[0.9, 1], [0, 0.1]]);
  close(linearFormSegments([interval(0.25, 0)], [1, -2]), [[0.75, 0.75]]);
  close(linearFormSegments([interval(0.7, 0.1)], [0, 0]), [[0, 0]]);
  close(linearFormSegments([], [0]), []);
});

test('merge and density retain gaps and point intervals', () => {
  close(mergeSegments([[0.2, 0.3], [0.1, 0.25], [0.5, 0.5], [0.7, 0.9]]), [[0.1, 0.3], [0.5, 0.5], [0.7, 0.9]]);
  assert.ok(Math.abs(measure([[0.1, 0.4], [0.3, 0.6]]) - 0.5) < 1e-12);
});

test('long forms cover the circle without enumerating all tuples', () => {
  close(linearFormSegments([interval(0, 0.02), interval(0.2, 0.03)], Array(100).fill(1)), [[0, 1]]);
});

test('image agrees with exhaustive independent tuple endpoints', () => {
  const intervals = [interval(0.03, 0.012), interval(0.24, 0.025, 2), interval(0.7, 0, 3)];
  for (const coefficients of [[1], [-3], [1, 1, -3], [1, -2, 0, 1], [2, -3, 4], [0, 0], [-2, -2, 1, 1]]) {
    const segments = [];
    function visit(slot, left, right) {
      if (slot === coefficients.length) {
        if (right - left >= 1) { segments.push([0, 1]); return; }
        for (let shift = Math.floor(left); shift <= Math.floor(right); shift += 1) {
          segments.push([Math.max(left, shift) - shift, Math.min(right, shift + 1) - shift]);
        }
        return;
      }
      const coefficient = coefficients[slot];
      for (const item of intervals) {
        const a = coefficient * item.start;
        const b = coefficient * (item.start + item.width);
        visit(slot + 1, left + Math.min(a, b), right + Math.max(a, b));
      }
    }
    visit(0, 0, 0);
    close(linearFormSegments(intervals, coefficients), mergeSegments(segments));
  }
});

test('work limit reports an error instead of silently returning partial images', () => {
  assert.throws(() => linearFormSegments([interval(0.1, 0.01), interval(0.4, 0.01, 2)], [1, 1], 1), /too large/);
});

const componentFilename = path.join(__dirname, 'src', 'LinearFormVisualizer.tsx');
const component = new Module(componentFilename, module);
component.paths = module.paths;
component.require = name => name === './linearFormGeometry' ? geometry.exports : require(name);
component._compile(ts.transpileModule(fs.readFileSync(componentFilename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText, componentFilename);
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

test('import preserves wrapping intervals and rejects invalid coefficients', () => {
  const raw = { coefficients: [1, -2, 0, 3], missingPoint: 0.25, intervals: [interval(0.95, 0.1), interval(0.5, 0, 2)] };
  const restored = component.exports.normalizeLinearFormState(raw);
  assert.deepEqual(restored.coefficients, raw.coefficients);
  assert.equal(restored.intervals[0].width, 0.1);
  assert.ok(Math.abs(restored.intervals[0].start - 0.95) < 1e-12);
  assert.equal(restored.missingPoint, 0.25);
  assert.throws(() => component.exports.normalizeLinearFormState({ ...raw, coefficients: [1.5] }), /integer coefficients/);
});

test('invalid shared state has an explicit alert instead of a silent example', () => {
  const markup = renderToStaticMarkup(React.createElement(component.exports.default, {
    initialState: { coefficients: [0.5], intervals: [] },
    buildShareUrl: () => 'http://localhost/', copyText: async () => {}, onSwitchToIntervals: () => {},
  }));
  assert.match(markup, /role="alert"/);
  assert.match(markup, /Could not load the shared configuration/);
});
