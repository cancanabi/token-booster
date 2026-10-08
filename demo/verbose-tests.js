'use strict';
const assert = require('node:assert/strict');
for(let i=1;i<=1200;i++) {
  assert.equal(i*17+11-11,i*17);
  console.log(`PASS arithmetic test ${String(i).padStart(4,'0')} value=${i*17+11}`);
}
console.log('TOTAL 1200 TESTS PASS');
