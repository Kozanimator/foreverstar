const https = require('https');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const osc = require('osc');

// --- Config ---
const LOCAL_IP = '192.168.2.98';
const HTTPS_PORT = 3000;
const UNREAL_IP = '127.0.0.1';         // Unreal on same machine; change if separate PC
const UNREAL_OSC_PORT = 8001;          // must match Unreal OSC Server port
const MAX_PLAYERS = 2;
const PLAYER_COLORS = ['#a855f7', '#f43f5e'];  // purple, red

// --- HTTPS server (serves the phone app) ---
const sslOptions = {
  key:  fs.readFileSync(path.join(__dirname, '192.168.2.98-key.pem')),
  cert: fs.readFileSync(path.join(__dirname, '192.168.2.98.pem')),
};

const httpsServer = https.createServer(sslOptions, (req, res) => {
  if (req.method === 'GET') {
    const html = fs.readFileSync(path.join(__dirname, 'phone-app.html'), 'utf8');
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  }
});

// --- WebSocket server ---
const wss = new WebSocket.Server({ server: httpsServer });

const players = {};
let nextPlayerId = 1;

wss.on('connection', (ws) => {
  const existingIds = Object.keys(players).map(Number);
  if (existingIds.length >= MAX_PLAYERS) {
    ws.send(JSON.stringify({ type: 'FULL' }));
    ws.close();
    return;
  }

  const playerId = nextPlayerId++;
  players[playerId] = ws;
  const color = PLAYER_COLORS[(playerId - 1) % PLAYER_COLORS.length];

  console.log(`Player ${playerId} connected (${color})`);
  ws.send(JSON.stringify({ type: 'ASSIGN', playerId, color }));

  sendOSC('/player/join', [
    { type: 'i', value: playerId },
    { type: 's', value: color },
  ]);

  players[playerId].smoothYaw   = 0;
  players[playerId].smoothPitch = 0;

  ws.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    if (msg.type === 'AIM') {
      const SMOOTHING = 0.25;
      players[playerId].smoothYaw   = lerp(players[playerId].smoothYaw,   msg.yaw,   SMOOTHING);
      players[playerId].smoothPitch = lerp(players[playerId].smoothPitch, msg.pitch, SMOOTHING);
      sendOSC('/aim', [
        { type: 'i', value: playerId },
        { type: 'f', value: players[playerId].smoothYaw },
        { type: 'f', value: players[playerId].smoothPitch },
      ]);
    }

    if (msg.type === 'TAP') {
      sendOSC('/tap', [{ type: 'i', value: playerId }]);
    }

    if (msg.type === 'CLAIM') {
      const name = String(msg.name || '').trim().toUpperCase().slice(0, 8);
      const tier = msg.tier === 'forever' ? 1 : 0;   // 1 = Forever, 0 = Once
      if (name.length === 0) return;
      sendOSC('/claim', [
        { type: 'i', value: playerId },
        { type: 's', value: name },
        { type: 'i', value: tier },
      ]);
    }

    if (msg.type === 'CANCEL') {
      sendOSC('/cancel', [{ type: 'i', value: playerId }]);
    }
  });

  ws.on('close', () => {
    console.log(`Player ${playerId} disconnected`);
    delete players[playerId];
    sendOSC('/player/leave', [{ type: 'i', value: playerId }]);
  });
});

// --- OSC out to Unreal ---
const udpPort = new osc.UDPPort({
  localAddress: '0.0.0.0',
  localPort: 0,
  remoteAddress: UNREAL_IP,
  remotePort: UNREAL_OSC_PORT,
  metadata: true,
});
udpPort.open();

function sendOSC(address, args) {
  udpPort.send({ address, args });
}

function lerp(a, b, t) { return a + (b - a) * t; }

// --- OSC in from Unreal (target + claim results) ---
const inboundPort = new osc.UDPPort({
  localAddress: '0.0.0.0',
  localPort: 8002,
  metadata: true,
});

inboundPort.on('message', (oscMsg) => {
  const playerId = oscMsg.args[0] && oscMsg.args[0].value;
  const ws = players[playerId];
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  if (oscMsg.address === '/target') {
    const name    = oscMsg.args[1] ? oscMsg.args[1].value : '';
    const claimed = oscMsg.args[2] ? !!oscMsg.args[2].value : false;
    ws.send(JSON.stringify({ type: 'TARGET', name, claimed }));
  }

  if (oscMsg.address === '/claimresult') {
    const success = oscMsg.args[1] ? !!oscMsg.args[1].value : false;
    ws.send(JSON.stringify({ type: 'CLAIM_RESULT', success }));
  }
});
inboundPort.open();

// --- Start + print QR ---
const qrcode = require('qrcode');
const url = `https://${LOCAL_IP}:${HTTPS_PORT}`;

httpsServer.listen(HTTPS_PORT, () => {
  console.log(`\nForeverStar server running at ${url}\n`);
  qrcode.toString(url, { type: 'terminal', small: true }, (err, code) => {
    if (!err) console.log(code);
    console.log(`Scan the QR code above with your iPhone.\n`);
    console.log(`Waiting for players...\n`);
  });
});
