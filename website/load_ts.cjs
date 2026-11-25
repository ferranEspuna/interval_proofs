const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const cache = new Map();

function loadSource(filename) {
  const resolved = path.isAbsolute(filename) ? filename : path.join(__dirname, 'src', filename);
  if (cache.has(resolved)) return cache.get(resolved).exports;
  const loaded = new Module(resolved, module);
  loaded.paths = module.paths;
  cache.set(resolved, loaded);
  loaded.require = name => {
    if (name.endsWith('.css')) return {};
    if (!name.startsWith('./') && !name.startsWith('../')) return require(name);
    const base = path.resolve(path.dirname(resolved), name);
    const source = ['.ts', '.tsx'].map(ext => base + ext).find(fs.existsSync);
    return source ? loadSource(source) : require(name);
  };
  loaded._compile(ts.transpileModule(fs.readFileSync(resolved, 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText, resolved);
  return loaded.exports;
}

module.exports = { loadSource };
