// ForeverStar local bridge — runs on the installation PC next to Unreal.
// Connects OUT to the cloud relay (works on any venue network),
// extrapolates phone aim ~100ms ahead to hide network lag,
// and speaks OSC to Unreal exactly like the old LAN server did.
//
// Usage:  node bridge.js wss://your-app.onrender.com
//    or:  set CLOUD_URL and run  node bridge.js

const WebSocket = require('ws');
const osc = require('osc');

const CLOUD_URL = process.argv[2] || process.env.CLOUD_URL || 'ws://localhost:3100';
const BRIDGE_KEY = process.env.BRIDGE_KEY || 'foreverstar';
const UNREAL_IP = '127.0.0.1';
const UNREAL_OSC_PORT = 8001;   // must match Unreal OSC server
const OSC_IN_PORT = 8002;       // /target + /claimresult from Unreal

const LOOKAHEAD_MS = 100;       // aim prediction horizon (raise if still laggy)
const SMOOTHING = 0.35;         // per-packet lerp toward predicted aim
const OSC_HZ = 50;              // rate we feed Unreal

// --- OSC out to Unreal ---
const udpPort = new osc.UDPPort({
  localAddress: '0.0.0.0', localPort: 0,
  remoteAddress: UNREAL_IP, remotePort: UNREAL_OSC_PORT, metadata: true,
});
udpPort.open();
const sendOSC = (address, args) => udpPort.send({ address, args });

// --- per-player aim state (continuous/unwrapped yaw) ---
const aim = {}; // playerId -> {yaw, pitch, vyaw, vpitch, smoothYaw, smoothPitch, lastRx}

function unwrapYaw(prev, next) {
  // keep yaw continuous across the 0/360 seam
  let d = ((next - prev) % 360 + 540) % 360 - 180;
  return prev + d;
}

function onAim(m) {
  let a = aim[m.playerId];
  if (!a) a = aim[m.playerId] = { yaw: m.yaw, pitch: m.pitch, vyaw: 0, vpitch: 0,
                                  smoothYaw: m.yaw, smoothPitch: m.pitch, lastRx: Date.now() };
  a.yaw = unwrapYaw(a.yaw, m.yaw);
  a.pitch = m.pitch;
  a.vyaw = m.vyaw || 0;      // deg/s from the phone gyro
  a.vpitch = m.vpitch || 0;
  a.lastRx = Date.now();
}

// steady 50Hz feed to Unreal: predict LOOKAHEAD ms ahead of last packet
setInterval(() => {
  const now = Date.now();
  for (const [id, a] of Object.entries(aim)) {
    const age = Math.min(now - a.lastRx, 250);            // cap: never predict off stale data
    const aheadS = (age + LOOKAHEAD_MS) / 1000;
    const predYaw = a.yaw + a.vyaw * aheadS;
    const predPitch = a.pitch + a.vpitch * aheadS;
    a.smoothYaw += (predYaw - a.smoothYaw) * SMOOTHING;
    a.smoothPitch += (predPitch - a.smoothPitch) * SMOOTHING;
    sendOSC('/aim', [
      { type: 'i', value: Number(id) },
      { type: 'f', value: ((a.smoothYaw % 360) + 360) % 360 },
      { type: 'f', value: a.smoothPitch },
    ]);
  }
}, 1000 / OSC_HZ);

// --- OSC in from Unreal -> up to the cloud ---
let ws = null;
const up = (obj) => { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); };

const inbound = new osc.UDPPort({ localAddress: '0.0.0.0', localPort: OSC_IN_PORT, metadata: true });
inbound.on('message', (m) => {
  const playerId = m.args[0] && m.args[0].value;
  if (m.address === '/target') {
    up({ type: 'TARGET', playerId,
         name: m.args[1] ? m.args[1].value : '',
         claimed: m.args[2] ? !!m.args[2].value : false });
  }
  if (m.address === '/claimresult') {
    up({ type: 'CLAIM_RESULT', playerId, success: m.args[1] ? !!m.args[1].value : false });
  }
});
inbound.open();

// --- cloud connection (auto-reconnect) ---
function connect() {
  console.log(`Connecting to relay: ${CLOUD_URL}`);
  ws = new WebSocket(CLOUD_URL);

  ws.on('open', () => {
    ws.send(JSON.stringify({ type: 'BRIDGE', key: BRIDGE_KEY }));
    console.log('Bridge online — phones can join from anywhere.');
  });

  ws.on('message', (raw) => {
    let m; try { m = JSON.parse(raw); } catch { return; }
    switch (m.type) {
      case 'AIM': onAim(m); break;
      case 'TAP': sendOSC('/tap', [{ type: 'i', value: m.playerId }]); break;
      case 'CLAIM':
        sendOSC('/claim', [
          { type: 'i', value: m.playerId },
          { type: 's', value: m.name },
          { type: 'i', value: m.tier },
        ]); break;
      case 'CANCEL': sendOSC('/cancel', [{ type: 'i', value: m.playerId }]); break;
      case 'PLAYER_JOIN':
        sendOSC('/player/join', [{ type: 'i', value: m.playerId }, { type: 's', value: m.color }]);
        console.log(`Player ${m.playerId} joined`); break;
      case 'PLAYER_LEAVE':
        delete aim[m.playerId];
        sendOSC('/player/leave', [{ type: 'i', value: m.playerId }]);
        console.log(`Player ${m.playerId} left`); break;
      case 'CLAIMS_SNAPSHOT':
        console.log(`Relay holds ${m.claims.length} saved claim(s).`);
        // future: forward to UE as /restoreclaim once BP_OSCReceiver supports it
        break;
    }
  });

  ws.on('close', () => { console.log('Relay connection lost — retrying in 3s'); setTimeout(connect, 3000); });
  ws.on('error', () => {});
}
connect();
