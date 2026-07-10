// ForeverStar cloud relay
// Phones connect here from ANY network (cellular or wifi).
// The installation PC runs bridge.js, which also connects here (outbound),
// so the venue needs no firewall rules, port forwarding, or fixed IP.
//
// Deploy: Render / Railway / Fly (root dir = planet-server/cloud, `node server.js`)
// TLS is terminated by the host, so this is plain HTTP internally.

const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const PORT = process.env.PORT || 3100;
const BRIDGE_KEY = process.env.BRIDGE_KEY || 'foreverstar';
const MAX_PLAYERS = 2;
const PLAYER_COLORS = ['#a855f7', '#f43f5e'];
const CLAIMS_FILE = path.join(__dirname, 'claims.json');

// --- claims persistence ---
let claims = [];
try { claims = JSON.parse(fs.readFileSync(CLAIMS_FILE, 'utf8')); } catch { /* first run */ }
function saveClaims() {
  fs.writeFile(CLAIMS_FILE, JSON.stringify(claims, null, 2), () => {});
}

// --- http: serve the phone app ---
const server = http.createServer((req, res) => {
  if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) {
    const html = fs.readFileSync(path.join(__dirname, 'phone-app.html'), 'utf8');
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  } else if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, bridgeOnline: !!bridge, players: Object.keys(players).length }));
  } else if (req.method === 'GET' && req.url === '/cards.json') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'max-age=300' });
    res.end(fs.readFileSync(path.join(__dirname, 'cards.json')));
  } else if (req.method === 'GET' && /^\/cards\/\d+\.jpg$/.test(req.url)) {
    const f = path.join(__dirname, req.url);
    if (fs.existsSync(f)) {
      res.writeHead(200, { 'Content-Type': 'image/jpeg', 'Cache-Control': 'max-age=86400' });
      res.end(fs.readFileSync(f));
    } else { res.writeHead(404); res.end(); }
  } else {
    res.writeHead(404); res.end();
  }
});

const wss = new WebSocket.Server({ server });

let bridge = null;              // the installation PC (one at a time)
const players = {};             // playerId -> phone ws
const pendingClaims = {};       // playerId -> {name, tier} awaiting UE verdict

// always hand out the lowest free slot (1..MAX_PLAYERS) so Unreal's
// per-player selectors keep working across phone reloads
function freePlayerId() {
  for (let i = 1; i <= MAX_PLAYERS; i++) if (!players[i]) return i;
  return null;
}

function toBridge(obj) {
  if (bridge && bridge.readyState === WebSocket.OPEN) bridge.send(JSON.stringify(obj));
}
function toPlayer(id, obj) {
  const ws = players[id];
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}
function broadcastRoomState() {
  const online = !!bridge;
  for (const id of Object.keys(players)) toPlayer(id, { type: 'ROOM', online });
}

wss.on('connection', (ws) => {
  let role = 'phone';
  let playerId = null;
  let joined = false;

  ws.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    // --- bridge handshake ---
    if (msg.type === 'BRIDGE') {
      if (msg.key !== BRIDGE_KEY) { ws.close(); return; }
      if (bridge) try { bridge.close(); } catch {}
      role = 'bridge';
      bridge = ws;
      console.log('Bridge (installation) connected');
      // replay active players + stored claims so the venue can restore state
      for (const id of Object.keys(players)) {
        toBridge({ type: 'PLAYER_JOIN', playerId: Number(id), color: PLAYER_COLORS[(id - 1) % PLAYER_COLORS.length] });
      }
      toBridge({ type: 'CLAIMS_SNAPSHOT', claims });
      broadcastRoomState();
      return;
    }

    if (role === 'bridge') {
      // --- messages coming UP from the installation ---
      if (msg.type === 'TARGET') toPlayer(msg.playerId, { type: 'TARGET', name: msg.name, claimed: msg.claimed, cardId: msg.cardId || 0 });
      if (msg.type === 'CLAIM_RESULT') {
        toPlayer(msg.playerId, { type: 'CLAIM_RESULT', success: msg.success });
        const pc = pendingClaims[msg.playerId];
        if (msg.success && pc) {
          claims.push({ ...pc, ts: Date.now() });
          saveClaims();
          console.log(`Claim saved: ${pc.name} (${pc.tier})`);
        }
        delete pendingClaims[msg.playerId];
      }
      return;
    }

    // --- phone messages ---
    if (!joined) {
      // first message from a phone joins it
      playerId = freePlayerId();
      if (playerId === null) {
        ws.send(JSON.stringify({ type: 'FULL' })); ws.close(); return;
      }
      players[playerId] = ws;
      joined = true;
      const color = PLAYER_COLORS[(playerId - 1) % PLAYER_COLORS.length];
      console.log(`Player ${playerId} connected (${color})`);
      ws.send(JSON.stringify({ type: 'ASSIGN', playerId, color }));
      ws.send(JSON.stringify({ type: 'ROOM', online: !!bridge }));
      toBridge({ type: 'PLAYER_JOIN', playerId, color });
      if (msg.type === 'HELLO') return; // pure handshake, nothing to forward
    }

    if (msg.type === 'AIM') {
      toBridge({ type: 'AIM', playerId, yaw: msg.yaw, pitch: msg.pitch,
                 vyaw: msg.vyaw || 0, vpitch: msg.vpitch || 0, t: Date.now() });
    }
    if (msg.type === 'TAP') toBridge({ type: 'TAP', playerId });
    if (msg.type === 'CLAIM') {
      const name = String(msg.name || '').trim().toUpperCase().slice(0, 8);
      if (!name) return;
      const tier = msg.tier === 'forever' ? 'forever' : 'once';
      pendingClaims[playerId] = { name, tier, playerId };
      toBridge({ type: 'CLAIM', playerId, name, tier: tier === 'forever' ? 1 : 0 });
    }
    if (msg.type === 'CANCEL') toBridge({ type: 'CANCEL', playerId });
  });

  ws.on('close', () => {
    if (role === 'bridge') {
      if (bridge === ws) bridge = null;
      console.log('Bridge disconnected');
      broadcastRoomState();
    } else if (playerId !== null) {
      console.log(`Player ${playerId} disconnected`);
      delete players[playerId];
      delete pendingClaims[playerId];
      toBridge({ type: 'PLAYER_LEAVE', playerId });
    }
  });
});

server.listen(PORT, () => console.log(`ForeverStar relay listening on :${PORT}`));
