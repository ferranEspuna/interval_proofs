const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { loadSource } = require('./load_ts.cjs');

const Page = loadSource('PreimageConstructionVisualizer.tsx').default;
const shared = loadSource('shared.ts');
const preimageGeometry = loadSource('preimageConstruction.ts');
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

const App = loadSource('App.tsx').default;
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

test('construction page renders editable multiplier and multi-interval union controls', () => {
  const html = renderToStaticMarkup(React.createElement(Page, {
    ...props,
    initialState: {
      mode: 'preimage-construction',
      coefficients: [1, 1, -3],
      targets: [
        { coefficient: 5, intervals: [{ start: 0.1, width: 0.15 }, { start: 0.6, width: 0.15 }] },
        { coefficient: -2, start: 0.2, width: 0.3 },
      ],
    },
  }));
  assert.match(html, /data-target-coefficient="5"/);
  assert.match(html, /data-target-coefficient="-2"/);
  assert.match(html, /aria-label="Multiplier of preimage 1"/);
  assert.match(html, /Interval 1 of 2/);
  assert.match(html, /Interval 2 of 2/);
  assert.match(html, /Add preimage/);
  assert.match(html, /Custom multipliers or multi-interval target unions are active/);
  assert.doesNotMatch(html, /role="alert"/);
});

test('floating point inputs render as deferred text inputs with spinner buttons', () => {
  const html = renderToStaticMarkup(React.createElement(Page, props));
  assert.match(html, /aria-label="Start of target 10"/);
  assert.match(html, /aria-label="Increase Start of target 10"/);
  assert.match(html, /aria-label="Decrease Start of target 10"/);
  assert.match(html, /aria-label="Increase Multiplier of preimage 1"/);
  assert.match(html, /aria-label="Decrease Multiplier of preimage 1"/);
  assert.match(html, /aria-label="Remove preimage 1"/);
  assert.match(html, /inputMode="decimal"|inputmode="decimal"/);
  assert.doesNotMatch(html, /type="number"/);
});

test('all existing VISUALIZER_LINKS.md links and legacy URLs decode, render, and round-trip cleanly', () => {
  const linksDoc = fs.readFileSync(path.join(__dirname, '..', 'VISUALIZER_LINKS.md'), 'utf8');
  const matches = [...linksDoc.matchAll(/https:\/\/ferranespuna\.github\.io\/interval_proofs\/(\?state=[A-Za-z0-9_-]+)/g)];
  assert.ok(matches.length >= 40, `Expected at least 40 catalog links, found ${matches.length}`);

  const oldWindow = global.window;
  try {
    for (const [, search] of matches) {
      const encoded = new URLSearchParams(search).get('state');
      const decoded = shared.decodeShareState(encoded);
      assert.deepEqual(shared.decodeShareState(shared.encodeShareState(decoded)), decoded);

      global.window = { location: { search, href: 'https://example.test/' + search } };
      const html = renderToStaticMarkup(React.createElement(App));
      assert.doesNotMatch(html, /role="alert"/);
      if (decoded.mode === 'candela') {
        assert.match(html, /Candela Construction Visualizer/);
      } else {
        assert.match(html, /Circle Group Visualizer/);
      }
    }

    // Legacy interval link without explicit mode and using `lambda` instead of `m`.
    const legacyState = { v: 1, lambda: 5, intervals: [{ id: 1, start: 0.2, width: 0.1, color: '#ef4444' }] };
    const legacySearch = '?state=' + shared.encodeShareState(legacyState);
    global.window = { location: { search: legacySearch, href: 'https://example.test/' + legacySearch } };
    const legacyHtml = renderToStaticMarkup(React.createElement(App));
    assert.match(legacyHtml, /Circle Group Visualizer/);
    assert.match(legacyHtml, /5A\./);
    assert.doesNotMatch(legacyHtml, /role="alert"/);

    // Custom multiplier + multi-interval preimage construction link round-trip.
    const customConstruction = preimageGeometry.serializeConstructionState(
      preimageGeometry.normalizeConstructionState({
        mode: 'preimage-construction',
        coefficients: [10, 10, -19],
        targets: [
          { coefficient: 5, intervals: [{ start: 0.1, width: 0.2 }, { start: 0.6, width: 0.15 }], color: '#ef4444' },
          { coefficient: -19, start: 0.25, width: 0.3, color: '#3b82f6' },
        ],
      }),
    );
    const customUrl = shared.buildShareUrl(customConstruction);
    const customSearch = new URL(customUrl).search;
    global.window = { location: { search: customSearch, href: customUrl } };
    const customHtml = renderToStaticMarkup(React.createElement(App));
    assert.match(customHtml, /Preimage intersection construction/);
    assert.match(customHtml, /data-target-coefficient="5"/);
    assert.match(customHtml, /data-target-coefficient="-19"/);
    assert.match(customHtml, /Interval 2 of 2/);
    assert.doesNotMatch(customHtml, /role="alert"/);
  } finally {
    if (oldWindow === undefined) delete global.window;
    else global.window = oldWindow;
  }
});
