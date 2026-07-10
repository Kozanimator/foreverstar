# ForeverStar — Unreal Planet Scene Guide
**Engine:** UE 5.5.1 · **Style:** Blueprint + Materials · **Planets:** 100

---

## 1. PROJECT SETUP

### New Project
- Template: **Blank**
- Quality: **Maximum**
- Raytracing: **OFF** (nDisplay doesn't support it well)
- Starter Content: **OFF**

### Enable These Plugins (Edit → Plugins)
- **OSC** — phone communication
- **Geometry Script** — name carving later
- **nDisplay** — already configured, keep enabled

### Project Settings (Edit → Project Settings → Rendering)
- Lumen Global Illumination: **Enabled**
- Lumen Reflections: **Enabled**
- Bloom: **Enabled**
- Auto Exposure: **OFF** (set fixed — consistent 360 look)
- Motion Blur: **OFF** (bad in 360 rooms)

### Folder Structure (Content Browser)
```
Content/
  ForeverStar/
    Materials/
      M_Planet_Master
      M_Atmosphere
      MI_GasGiant
      MI_OceanWorld
      MI_Terran
      MI_Asteroid
      MI_IceWorld
      MI_Desert
    Blueprints/
      BP_Planet
      BP_PlanetSpawner
      BP_OSCReceiver
      BP_Reticle
      ENUM_PlanetType
    Audio/
      A_Ambient_Loop
      A_SelectionCue
    Maps/
      ForeverStar_Main
```

---

## 2. PLANET TYPE ENUM

Create a Blueprint Enum: **ENUM_PlanetType**

Values: `GasGiant, OceanWorld, Terran, Asteroid, IceWorld, Desert`

---

## 3. MASTER PLANET MATERIAL (M_Planet_Master)

Create a new Material. Settings:
- Shading Model: **Lit**
- Two Sided: OFF

### Material Parameters to Create

| Parameter Name    | Type    | Default         |
|-------------------|---------|-----------------|
| BaseColor_A       | Vector3 | (0.2, 0.4, 0.8) |
| BaseColor_B       | Vector3 | (0.1, 0.2, 0.5) |
| BaseColor_C       | Vector3 | (0.8, 0.6, 0.2) |
| NoiseScale        | Scalar  | 3.0             |
| NoiseContrast     | Scalar  | 2.0             |
| TerrainThreshold  | Scalar  | 0.5             |
| RoughnessOcean    | Scalar  | 0.05            |
| RoughnessLand     | Scalar  | 0.8             |
| AtmosphereColor   | Vector3 | (0.3, 0.5, 1.0) |
| EmissiveStrength  | Scalar  | 0.0             |
| CloudCoverage     | Scalar  | 0.4             |
| CloudSpeed        | Scalar  | 0.02            |
| BandFrequency     | Scalar  | 8.0             |
| RotationSpeed     | Scalar  | 0.01            |
| PlanetSeed        | Scalar  | 0.0             |

### Material Graph — Build in This Order

#### A. Animated UVs (planet self-rotation)
```
[Time] × [RotationSpeed param]
  → AppendVector (X=result, Y=0)
  → Add to [TexCoord 0]
  → [RotatedUVs]   ← use this for ALL noise below
```

#### B. Terrain Noise
```
[RotatedUVs] → [Noise node]
  Function: Gradient (Perlin)
  Scale: connect to [NoiseScale param]
  Levels: 6
→ [TerrainNoise]

[TerrainNoise] × [NoiseContrast param] → Saturate → [TerrainMask]
```

#### C. Detail Noise
```
[RotatedUVs] × 4.0 → [Noise]
  Function: Voronoi, Scale: 2.0, Levels: 3
→ × 0.2 → [DetailNoise]

[TerrainMask] + [DetailNoise] → Clamp(0,1) → [FinalTerrainMask]
```

#### D. Color Blending
```
Use [If] node:
  A = FinalTerrainMask
  B = TerrainThreshold param
  A < B:  BaseColor_C param  (water/low areas)
  A >= B: Lerp(BaseColor_A, BaseColor_B, FinalTerrainMask)  (terrain)
→ [SurfaceColor]
```

#### E. Cloud Layer
```
[Time] × [CloudSpeed param] → [CloudOffset]
RotateAboutAxis(Position=WorldPos+PlanetSeed_offset, Axis=(0,0,1), Angle=CloudOffset)
  → Normalize → Multiply(0.5) → [CloudPos]

[CloudPos] → [Noise node]
  Function: Gradient - Computational
  Turbulence: OFF  ← IMPORTANT: keep OFF so output is truly in [0,1]
  Scale: 2.0
  Levels: 8 (ignored when Turbulence=OFF)
  Output Min: 0.0 / Output Max: 1.0
→ [CloudNoise]

[CloudNoise] Subtract [CloudCoverage param] → Clamp(0,1)
  → Power(Exp=0.6) → [CloudMask]

Lerp([SurfaceColor], (1,1,1), CloudMask) → [ColorWithClouds]
```

> **CloudCoverage range:** 0.0 = maximum clouds, 1.0 = no clouds (acts as a threshold:
> clouds appear where NoiseValue > CloudCoverage). Values outside [0,1] are valid —
> use 1.0+ to guarantee zero clouds. Turbulence MUST stay disabled; enabling it causes
> the noise to exceed OutputMax and makes CloudCoverage values > 1 necessary.

#### F. Roughness
```
Lerp([RoughnessOcean], [RoughnessLand], FinalTerrainMask) → [SurfaceRough]
Lerp([SurfaceRough], 0.3, CloudMask) → [FinalRoughness]
```

#### G. Emissive (city lights on dark side)
```
[SurfaceColor] → Desaturate → × [EmissiveStrength param] → [Emissive]
```

#### H. Connect to Output
```
Base Color  → ColorWithClouds
Metallic    → 0.0
Roughness   → FinalRoughness
Emissive    → Emissive
```

---

## 4. ATMOSPHERE MATERIAL (M_Atmosphere)

New Material:
- Blend Mode: **Translucent**
- Shading Model: **Unlit**
- Two Sided: **ON**

### Parameters
| Name         | Type    | Default        |
|--------------|---------|----------------|
| AtmosColor   | Vector3 | (0.3, 0.5, 1.0)|
| AtmosOpacity | Scalar  | 0.6            |
| RimPower     | Scalar  | 3.0            |

### Graph
```
[Camera Vector] → [Fresnel]
  Exponent: [RimPower param]
  BaseReflectFraction: 0.0
→ [FresnelMask]

[AtmosColor] × FresnelMask → Emissive Color output
FresnelMask × [AtmosOpacity] → Opacity output
```

---

## 5. MATERIAL INSTANCES — KEY PARAMETER VALUES

Create Material Instance from M_Planet_Master for each type:

### MI_GasGiant
```
BaseColor_A:      (0.8, 0.5, 0.2)    ← warm orange
BaseColor_B:      (0.6, 0.3, 0.1)    ← dark brown
BaseColor_C:      (0.9, 0.7, 0.4)    ← light cream
NoiseScale:       1.5
TerrainThreshold: 0.3
CloudCoverage:    0.2                 ← ~80% cloud coverage (lots of cloud bands)
RoughnessLand:    0.4
AtmosphereColor:  (1.0, 0.6, 0.2)
BandFrequency:    12.0
```

### MI_OceanWorld
```
BaseColor_A:      (0.05, 0.2, 0.6)   ← deep ocean
BaseColor_B:      (0.1, 0.5, 0.3)    ← coastal
BaseColor_C:      (0.15, 0.35, 0.7)  ← mid-ocean
NoiseScale:       4.0
TerrainThreshold: 0.75               ← 25% land only
RoughnessOcean:   0.02
CloudCoverage:    0.5
AtmosphereColor:  (0.2, 0.4, 1.0)
```

### MI_Terran
```
BaseColor_A:      (0.15, 0.35, 0.1)  ← forest
BaseColor_B:      (0.4, 0.25, 0.1)   ← rock/desert
BaseColor_C:      (0.05, 0.15, 0.5)  ← ocean
NoiseScale:       3.5
TerrainThreshold: 0.5
CloudCoverage:    0.4
AtmosphereColor:  (0.3, 0.5, 1.0)
EmissiveStrength: 0.05               ← faint city lights
```

### MI_Asteroid
```
BaseColor_A:      (0.6, 0.57, 0.53)  ← light grey rock (#999999)
BaseColor_B:      (0.33, 0.33, 0.33) ← dark grey (#555555)
BaseColor_C:      (0.42, 0.37, 0.31) ← brownish grey (#6B5E50)
NoiseScale:       6.0
NoiseContrast:    2.5
TerrainThreshold: 0.5
CloudCoverage:    1.0                 ← no clouds at all
RoughnessLand:    0.95
AtmosphereColor:  (0, 0, 0)          ← no atmosphere
EmissiveStrength: 0.0
```

### MI_IceWorld
```
BaseColor_A:      (0.8, 0.9, 1.0)    ← white ice
BaseColor_B:      (0.4, 0.6, 0.9)    ← blue cracks
BaseColor_C:      (0.6, 0.75, 0.95)  ← packed snow
NoiseScale:       5.0
TerrainThreshold: 0.3
RoughnessOcean:   0.1
CloudCoverage:    0.5                 ← ~50% cloud coverage
AtmosphereColor:  (0.5, 0.7, 1.0)
```

### MI_Desert
```
BaseColor_A:      (0.7, 0.4, 0.15)   ← sand
BaseColor_B:      (0.5, 0.25, 0.08)  ← dark rock
BaseColor_C:      (0.85, 0.55, 0.2)  ← bright sand
NoiseScale:       2.5
TerrainThreshold: 0.85               ← almost no water
CloudCoverage:    0.9                 ← very few clouds (~10% where noise peaks)
RoughnessLand:    0.9
AtmosphereColor:  (0.9, 0.4, 0.1)   ← orange atmosphere
```

---

## 6. BP_PLANET BLUEPRINT

New Actor Blueprint.

### Components
```
DefaultSceneRoot
  PlanetMesh (Static Mesh)    — Engine/BasicShapes/Sphere
  AtmosphereMesh (Static Mesh)— same sphere, scale (1.08,1.08,1.08), M_Atmosphere
  SelectionAudio (Audio)
  NameDecal (Decal)           — hidden initially
```

### Variables
```
PlanetType       ENUM_PlanetType   Terran
PlanetName       String            "Unknown"
PlanetSizeScale  Float             1.0
OrbitRadius      Float             800.0
OrbitSpeed       Float             5.0        ← degrees/minute
OrbitAxisTilt    Vector            (0,0,1)
OrbitAngle       Float             0.0
SelfRotationSpeed Float            15.0       ← degrees/minute
bIsHighlighted   Bool              false
bIsSelected      Bool              false
DynMaterial      Mat. Dyn. Inst.   —
SelectionCueSound Sound Base       —
```

### Event BeginPlay
```
1. Switch on PlanetType → get material (MI_GasGiant etc.)
2. Create Dynamic Material Instance from that material → DynMaterial
3. Set DynMaterial on PlanetMesh
4. Set "PlanetSeed" scalar param = Random Float (0, 100)
5. Set Actor Scale = (PlanetSizeScale, PlanetSizeScale, PlanetSizeScale)
6. Create Dynamic MI from M_Atmosphere → set on AtmosphereMesh
7. Set AtmosColor param from PlanetType lookup table
```

### Event Tick — Orbit
```
1. OrbitAngle += OrbitSpeed × DeltaSeconds ÷ 60
2. OrbitAngle = Fmod(OrbitAngle, 360)

3. RotateVectorAroundAxis:
     InVector: (OrbitRadius, 0, 0)
     Axis: OrbitAxisTilt (normalized)
     Angle: OrbitAngle
   → NewPosition

4. SetActorLocation(NewPosition)

5. AddActorLocalRotation(Yaw: SelfRotationSpeed × DeltaSeconds ÷ 60)
```

### Custom Events
```
OnHighlighted(PlayerID int, Color LinearColor):
  bIsHighlighted = true
  Set DynMaterial EmissiveStrength = 0.3
  Set DynMaterial AtmosphereColor = Color

OnDeselect():
  bIsHighlighted = false
  Restore original EmissiveStrength, AtmosphereColor

OnSelected(PlayerName string):
  bIsSelected = true
  Play SelectionAudio
  Set DynMaterial EmissiveStrength = 0.8
  Delay 0.2s → show name decal (see Section 9)
```

---

## 7. BP_PLANETSPAWNER BLUEPRINT

Actor Blueprint, place at (0,0,0) in level.

### Variables
```
PlanetCount    Int    100
MinOrbitRadius Float  500.0
MaxOrbitRadius Float  1800.0
MinPlanetSize  Float  0.3
MaxPlanetSize  Float  1.2
SpawnedPlanets Array<BP_Planet>
```

### Event BeginPlay — Fibonacci Sphere Spawn Loop

```
For Index 0 to 99:

  // Fibonacci sphere distribution (even coverage of 360° sphere)
  GoldenAngle  = 137.508°
  AzimuthAngle = Index × GoldenAngle
  PolarFraction= (Index + 0.5) / 100.0
  PolarAngle   = acos(1.0 - 2.0 × PolarFraction)  [convert to degrees: × 57.2958]

  OrbitAxis.X  = sin(PolarAngle°) × cos(AzimuthAngle°)
  OrbitAxis.Y  = sin(PolarAngle°) × sin(AzimuthAngle°)
  OrbitAxis.Z  = cos(PolarAngle°)
  OrbitAxis    = Normalize(OrbitAxis)

  // Random variation per planet
  OrbitRadius  = RandRange(500.0, 1800.0)
  PlanetSize   = RandRange(0.3, 1.2)
  StartAngle   = RandRange(0.0, 360.0)
  Speed        = RandRange(1.0, 8.0)      // degrees/minute
  SelfSpin     = RandRange(5.0, 30.0)
  PlanetType   = GetPlanetType(Index)     // see distribution below
  IsAsteroid   = (PlanetType == Asteroid)

  // Spawn
  Ref = SpawnActor(BP_Planet, Location=(0,0,0))
  Set all variables on Ref
  Ref.PlanetSizeScale = PlanetSize × (IsAsteroid ? 0.4 : 1.0)
  Ref.PlanetName = PlanetNames[Index]
  Ref.SelectionCueSound = A_SelectionCue
  SpawnedPlanets.Add(Ref)
```

### Planet Type Distribution
```
Index 0–24   (25) → Terran
Index 25–44  (20) → Desert
Index 45–62  (18) → GasGiant
Index 63–77  (15) → OceanWorld
Index 78–89  (12) → IceWorld
Index 90–99  (10) → Asteroid
```

### 100 Planet Names Array
```
VELORIA, NEXORIA PRIME, ZYNTHARA, THALVOR IX, ORIONIS, KETHARA, DRAVON,
SOLMARA, PRYTHEON, CYGARA, VELTHOS, MYRIDAN, AETHON, DRACOS IV, LUMINAE,
PYRAXIS, ORYNDAL, THESSIA, NOVARIS, KELDRATH, VOXARA, RYZAN, TETHEON,
CROMDAR, SYLVARA, FENRATH, OBERON V, CRESTHOS, VELDRIS, AZKARA, SOLIAN,
DETHARA, MYTHAR, KYRZIAN, OPALUS, GRYTHAR, VELMOOR, CYRAXIS, ATHERON,
DRAVIAN, LUMOTHOS, TETHARIS, XANDAR IV, VORDIAN, SOLMAAR, PYRION,
ETHARON, KALYDON, VELDRION, CORTHOS, MYTHARA, ZYTHIAN, KRETHON, DRAVOS,
SOLVARIS, NYTHEON, OKARIA, TEKHARA, VOLDRIS, MYTHOS V, CRYDAR, HELION,
DARVON, SOLMARIS, VELTRON, KETHARON, XERAXIS, DRAKON, PRYTHIAN, VOLVARA,
MYRATHON, CRESTON, SYLDAR, ORVION, TETHARIS II, KRONDAR, LUMAXIS,
SOLKRATH, VELMARIS, CYDRION, AETHAR, DRAVAN, NEXORIA II, VELIONAS,
MYRION, CORTHAR, KELDRIOS, SYNTHARA, DRAVONIS, PRYTHON, HELINDRA,
OKARAN, VELDHOS, SOLARAN, KYRTHAR, ETHARIUS, DRAVIAN II, VELMOAR,
TETHROS, LUMARAN, NEXORIAN
```

---

## 8. LEVEL SETUP (ForeverStar_Main)

### Actors to Place
```
1. Directional Light
   Intensity: 3.0 lux
   Color: (1.0, 0.95, 0.9) — warm sunlight
   Angle: 45° down

2. Sky Sphere (inverted sphere, Scale: 10000)
   Material: M_StarField (unlit, emissive stars)
   Star material graph:
     TexCoord × 200 → Voronoi Noise → threshold at 0.98 → (1,1,1) emissive

3. Nebula Sphere (inverted sphere, Scale: 9900)
   Material: Unlit, Translucent, opacity 0.3
   Scrolling cloud noise in purple/blue

4. BP_PlanetSpawner at (0,0,0)

5. BP_OSCReceiver at (0,0,0)

6. Post Process Volume (infinite extent):
   Bloom Intensity: 1.5
   Bloom Threshold: 0.5
   Chromatic Aberration: 0.5
   Vignette: 0.4
   Auto Exposure Min/Max: both 0 (fixed)
   Color Grading: slight blue-teal shift
```

---

## 9. OSC RECEIVER (BP_OSCReceiver)

### BeginPlay
```
Create OSC Server → IP "0.0.0.0", Port 8001, Start Listening
→ OSCServer variable
Bind OnOSCMessageReceived → HandleMessage
```

### HandleMessage
```
"/aim"  → PlayerID, Yaw, Pitch → UpdateReticle(PlayerID, Yaw, Pitch)
"/tap"  → PlayerID → HandleTap(PlayerID)
"/player/join"  → PlayerID, ColorHex → RegisterPlayer
"/player/leave" → PlayerID → UnregisterPlayer
```

### UpdateReticle(PlayerID, Yaw, Pitch)
```
YawRad   = Yaw × (π/180)
PitchRad = Pitch × (π/180)

Dir.X = cos(PitchRad) × cos(YawRad)
Dir.Y = cos(PitchRad) × sin(YawRad)
Dir.Z = sin(PitchRad)

LineTrace from (0,0,0) along Dir × 5000
→ Move Reticle[PlayerID] to hit location

For each planet in SpawnedPlanets:
  if Distance(planet, HitLocation) < 150:
    planet.OnHighlighted(PlayerID, PlayerColor)
  else:
    planet.OnDeselect()
```

### HandleTap(PlayerID)
```
Find closest planet to Reticle[PlayerID] within 200 units
If found:
  planet.OnSelected(PlayerNames[PlayerID])
  SendOSC to Node "/score" [PlayerID, 10]
```

### Score OSC back to Node
```
Create OSC Client → IP "127.0.0.1", Port 8002
On hit: send message address "/score", args [PlayerID int, Points int]
```

---

## 10. RETICLE (BP_Reticle)

Actor Blueprint with:
- **RingMesh** (SM_Torus or thin cylinder ring)
- Material: Unlit, emissive in player color, translucent

### Tick
```
Billboard: face camera
Pulse: Scale = 0.5 + sin(Time × 4) × 0.05
```

---

## 11. AMBIENT AUDIO

Level Blueprint BeginPlay:
```
Spawn Sound at Location
  Sound: A_Ambient_Loop
  Location: (0,0,0)
  Volume: 0.7
```
On the sound asset itself: set **Looping = true**

---

## 12. BUILD ORDER

Do in this exact order — test after each step:

1. Create M_Planet_Master, apply to one sphere in viewport
2. Create all 6 Material Instances, check they look visually distinct
3. Create ENUM_PlanetType
4. Create BP_Planet — orbit only first, no OSC yet
5. Manually place 5 BP_Planets, confirm orbiting works
6. Create BP_PlanetSpawner, spawn 10 planets
7. Increase to 100 planets, tune radii/sizes for room scale
8. Add star field + nebula + post process
9. Create BP_OSCReceiver — test with phone streaming aim
10. Create BP_Reticle — confirm it moves with phone
11. Wire tap → planet selection → audio
12. nDisplay pass — test on actual room

---

## KEY NUMBERS REFERENCE

| Value              | Setting        |
|--------------------|----------------|
| Room center        | (0, 0, 0)      |
| Min orbit radius   | 500 cm         |
| Max orbit radius   | 1800 cm        |
| Planet size range  | 0.3× – 1.2×    |
| Orbit speed        | 1–8 deg/min    |
| Self-rotation      | 5–30 deg/min   |
| Highlight radius   | 150 cm         |
| Select radius      | 200 cm         |
| OSC in port        | 8001           |
| OSC out port       | 8002           |
| Node server port   | 3000           |
