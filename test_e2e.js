// End-to-end protocol test: fake phone -> cloud relay -> bridge -> fake Unreal (OSC) and back.
// Run: node test_e2e.js   (exits 0 on pass)
const { spawn } = require('child_process');
const WebSocket = require('ws');
const osc = require('osc');

let failures = 0;
const ok = (cond, label) => { console.log((cond ? 'PASS ' : 'FAIL ') + label); if (!cond) failures++; };

// fake Unreal: OSC in on 8001, replies out to bridge on 8002
const ue = new osc.UDPPort({ localAddress: '127.0.0.1', localPort: 8001, metadata: true });
const ueOut = new osc.UDPPort({ localAddress: '0.0.0.0', localPort: 0, remoteAddress: '127.0.0.1', remotePort: 8002, metadata: true });
const got = { aim: [], tap: 0, claim: null, join: 0 };
ue.on('message', (m) => {
  if (m.address === '/aim') got.aim.push(m.args.map(a => a.value));
  if (m.address === '/tap') {
    got.tap++;
    ueOut.send({ address: '/target', args: [
      { type: 'i', value: m.args[0].value }, { type: 's', value: 'KEPLER' }, { type: 'i', value: 0 }] });
  }
  if (m.address === '/claim') {
    got.claim = m.args.map(a => a.value);
    ueOut.send({ address: '/claimresult', args: [
      { type: 'i', value: m.args[0].value }, { type: 'i', value: 1 }] });
  }
  if (m.address === '/player/join') got.join++;
});
ue.open(); ueOut.open();

const relay = spawn('node', ['cloud/server.js'], { env: { ...process.env, PORT: '3100' }, stdio: 'inherit' });
let bridge;
setTimeout(() => { bridge = spawn('node', ['bridge.js', 'ws://localhost:3100'], { stdio: 'inherit' }); }, 500);

setTimeout(() => {
  const phone = new WebSocket('ws://localhost:3100');
  const rx = {};
  phone.on('open', () => phone.send(JSON.stringify({ type: 'HELLO' })));
  phone.on('message', (raw) => {
    const m = JSON.parse(raw);
    rx[m.type] = m;
    if (m.type === 'ASSIGN') {
      // stream AIM at 20Hz with constant velocity: yaw 100->, 40 deg/s
      let yaw = 100; const iv = setInterval(() => {
        yaw += 2; phone.send(JSON.stringify({ type: 'AIM', yaw, pitch: 5, vyaw: 40, vpitch: 0 }));
      }, 50);
      setTimeout(() => { clearInterval(iv); phone.send(JSON.stringify({ type: 'TAP' })); }, 1200);
      setTimeout(() => phone.send(JSON.stringify({ type: 'CLAIM', name: 'kozak', tier: 'forever' })), 1700);
    }
  });

  setTimeout(() => {
    ok(rx.ASSIGN && rx.ASSIGN.playerId === 1, 'phone got ASSIGN playerId=1');
    ok(rx.ROOM && rx.ROOM.online === true, 'phone told room online');
    ok(got.join >= 1, 'UE got /player/join');
    ok(got.aim.length > 30, `UE receiving /aim stream (${got.aim.length} packets)`);
    if (got.aim.length) {
      const last = got.aim[got.aim.length - 1];
      // phone was at ~yaw+velocity; prediction should be AHEAD of raw sent yaw
      console.log('  last /aim:', JSON.stringify(last));
      ok(last[1] > 100 && last[1] < 360, 'aim yaw in range and advancing');
      ok(Math.abs(last[2] - 5) < 1.5, 'pitch tracked');
    }
    ok(got.tap === 1, 'UE got /tap');
    ok(rx.TARGET && rx.TARGET.name === 'KEPLER', 'phone got TARGET name back from UE');
    ok(got.claim && got.claim[1] === 'KOZAK' && got.claim[2] === 1, 'UE got /claim KOZAK forever');
    ok(rx.CLAIM_RESULT && rx.CLAIM_RESULT.success === true, 'phone got CLAIM_RESULT success');
    const claims = JSON.parse(require('fs').readFileSync('cloud/claims.json', 'utf8'));
    ok(claims.length >= 1 && claims[claims.length - 1].name === 'KOZAK', 'claim persisted to claims.json');
    console.log(failures === 0 ? '\nALL TESTS PASSED' : `\n${failures} FAILURES`);
    relay.kill(); if (bridge) bridge.kill();
    process.exit(failures === 0 ? 0 : 1);
  }, 2600);
}, 1200);
