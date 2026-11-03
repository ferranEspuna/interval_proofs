const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const test = require('node:test');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

const cache = new Map();
function loadSource(filename) {
  if (cache.has(filename)) return cache.get(filename).exports;
  const loaded = new Module(filename, module);
  loaded.paths = module.paths;
  cache.set(filename, loaded);
  loaded.require = name => {
    if (name.endsWith('.css')) return {};
    if (!name.startsWith('./')) return require(name);
    const base = path.resolve(path.dirname(filename), name);
    const source = ['.ts', '.tsx'].map(ext => base + ext).find(fs.existsSync);
    return source ? loadSource(source) : require(name);
  };
  loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
    },
  }).outputText, filename);
  return loaded.exports;
}

const Page = loadSource(path.join(__dirname, 'src', 'PreimageConstructionVisualizer.tsx')).default;
const props = {
  buildShareUrl: state => 'https://example.test/?state=' + Buffer.from(JSON.stringify(state)).toString('base64url'),
  copyText: async () => {}, onSwitchToLinearForm: () => {}, onSwitchToIntervals: () => {},
};

test('construction page renders target/preimage pairs, A, image and controls', () => {
  const html = renderToStaticMarkup(React.createElement(Page, props));
  assert.match(html, /Preimage intersection construction/);
  assert.match(html, /data-target-coefficient="10"/);
  assert.match(html, /data-target-coefficient="19"/);
  assert.match(html, /Next to outer ring: A/);
  assert.match(html, /Outermost: L\(A\)/);
  assert.match(html, /Reset optimal widths/);
  assert.match(html, /Find guaranteed shift/);
  assert.match(html, /id="construction-export"/);
  assert.match(html, /mode&quot;: &quot;preimage-construction/);
  assert.doesNotMatch(html, /role="alert"/);
});

test('navigation from a linear form retains coefficients and initializes its targets', () => {
  const html = renderToStaticMarkup(React.createElement(Page, { ...props, initialState: { coefficients: [2, -2, 0] } }));
  assert.match(html, /data-target-coefficient="2"/);
  assert.doesNotMatch(html, /data-target-coefficient="10"/);
  assert.doesNotMatch(html, /role="alert"/);
});

test('zero form and full image have honest missing-point states', () => {
  const zero = renderToStaticMarkup(React.createElement(Page, { ...props, initialState: { coefficients: [0, 0] } }));
  assert.match(zero, /single point 0/);
  assert.doesNotMatch(zero, /data-target-coefficient=/);
  const full = renderToStaticMarkup(React.createElement(Page, { ...props, initialState: {
    coefficients: [1, 1], targets: [{ coefficient: 1, start: 0, width: 0.75 }],
  } }));
  assert.match(full, /There is no missing point/);
  assert.doesNotMatch(full, /aria-label="Missing point /);
});

test('invalid construction links report an error rather than silently substituting', () => {
  for (const initialState of [[], { coefficients: [1.5], targets: [] }, { coefficients: [1], targets: [] }]) {
    const html = renderToStaticMarkup(React.createElement(Page, { ...props, initialState }));
    assert.match(html, /role="alert"/);
    assert.match(html, /Could not load the construction/);
  }
});

const App = loadSource(path.join(__dirname, 'src', 'App.tsx')).default;
test('shared URLs still select each existing page and the new construction page', () => {
  const oldWindow = global.window;
  try {
    for (const [state, expected] of [
      [null, /Candela Construction Visualizer/],
      [{ mode: 'interval', m: 3, intervals: [] }, /Circle Group Visualizer/],
      [{ mode: 'linear-form', coefficients: [1, -3], intervals: [] }, /Linear Form Visualizer/],
      [{ mode: 'preimage-construction', coefficients: [0], targets: [] }, /Preimage intersection construction/],
    ]) {
      const search = state ? '?state=' + Buffer.from(JSON.stringify(state)).toString('base64url') : '';
      global.window = { location: { search, href: 'https://example.test/' + search } };
      const html = renderToStaticMarkup(React.createElement(App));
      assert.match(html, expected);
      assert.doesNotMatch(html, /role="alert"/);
    }
  } finally {
    if (oldWindow === undefined) delete global.window;
    else global.window = oldWindow;
  }
});
