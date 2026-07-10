# ForeverStar — cloud mode (phones join from anywhere)

Phones connect over their own data/Wi-Fi to a cloud relay; the installation
PC connects outward to the same relay. No venue firewall setup, no cert
warnings, one permanent QR code.

```
phone (anywhere) --wss--> cloud relay <--wss-- bridge.js (UE machine) --OSC--> Unreal
```

## One-time: deploy the relay (~10 min, free)

1. Put this repo on GitHub (or use Render's "Public Git repository" field).
2. On https://render.com → New → Web Service:
   - Root directory: `planet-server/cloud`
   - Build command: `npm install`
   - Start command: `node server.js`
   - Instance type: Free
   - Environment variable: `BRIDGE_KEY` = a password you pick
3. Note your URL, e.g. `https://foreverstar.onrender.com`
4. In `planet-server`, create `cloud_url.txt` containing exactly that URL.
   Then in UE run `update_qr.py` once — the in-world QR is now **permanent**.

## Every show

On the installation PC:
```
set BRIDGE_KEY=yourpassword
node bridge.js wss://foreverstar.onrender.com
```
That's it. Phones scan the wall QR and play — from any network.

## Tuning lag

In `bridge.js`:
- `LOOKAHEAD_MS` (default 100): raise to 140–160 if aim still trails.
- `SMOOTHING` (default 0.35): lower = smoother but floatier, higher = snappier but jittery.
- Pick a Render region close to the venue (Ohio/us-east for Toronto).

## Claims

Successful claims are saved to `claims.json` on the relay and re-sent to the
bridge on every connect (`CLAIMS_SNAPSHOT`) — ready for the restore-claims
Unreal event when we build it. Note: Render's free tier has an ephemeral
disk, so claims reset on redeploy. For real persistence add a Render disk
($1/mo) or point saveClaims() at a hosted DB.

## Testing without deploying

`node test_e2e.js` — spins up relay + bridge + fake phone + fake Unreal
locally and checks the whole message loop (11 assertions).

## LAN fallback (venue with no internet)

The old mode still works: `node server.js` + run `update_qr.py`
(without cloud_url.txt) to point the QR at this machine's IP.
Phones must be on the same network; expect the certificate warning.
