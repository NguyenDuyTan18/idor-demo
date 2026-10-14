// Tests the actual topology policy body in the supplied frontend source.
// No Angular installation or server interaction is required.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2], 'utf8');
const marker = 'private updateTopologyAllowed(runInfo: AccessTrainingRunInfo)';
const start = source.indexOf(marker);
assert.ok(start >= 0, 'Compatible updateTopologyAllowed method is required');
const open = source.indexOf('{', start);
let depth = 1, end = open + 1;
for (; end < source.length && depth; end++) {
  if (source[end] === '{') depth++;
  if (source[end] === '}') depth--;
}
const body = source.slice(open + 1, end - 1);
const types = { Info: 0, Training: 1, Access: 2, Assessment: 3 };
const cases = [
  [types.Info, 'IDOR Free Lab', false, true],
  [types.Info, 'Other information', false, false],
  [types.Training, 'Any training', false, true],
  [types.Access, 'Any access', false, true],
  [types.Assessment, 'Any assessment', false, false],
  ...Object.values(types).map(type => [type, 'IDOR Free Lab', true, false]),
];
for (const [type, title, localEnvironment, expected] of cases) {
  const result = {};
  const target = {
    topologyAllowed: { set: value => result.allowed = value },
    topologyService: { setTopologyCollapsed: value => result.collapsed = value },
  };
  vm.runInNewContext(`(function(runInfo) { ${body} }).call(target, runInfo)`, {
    AbstractLevelTypeEnum: types, target,
    runInfo: { displayedLevel: {type, title}, localEnvironment },
  }, {timeout: 1000});
  assert.equal(result.allowed, expected, `${title}: allowed`);
  assert.equal(result.collapsed, !expected, `${title}: collapsed`);
}
console.log(`${cases.length} topology policy cases passed`);
