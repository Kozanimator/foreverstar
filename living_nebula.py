import unreal, random, traceback
p = r'E:\Projects\TMU\ARVR\ForeverStar\planet-server\matdbg.txt'
out = []
def w(s): out.append(str(s))
random.seed(3)
try:
    mel = unreal.MaterialEditingLibrary
    eal = unreal.EditorAssetLibrary
    at  = unreal.AssetToolsHelpers.get_asset_tools()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    def get_or_make(path, name):
        if eal.does_asset_exist(path):
            m = eal.load_asset(path); mel.delete_all_material_expressions(m); return m
        return at.create_asset(name, '/Game/ForeverStar/Materials', unreal.Material, unreal.MaterialFactoryNew())

    # ================= 1. ANIMATED FRACTAL NEBULA =================
    mat = get_or_make('/Game/ForeverStar/Materials/M_SkyNebula', 'M_SkyNebula')
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)

    def expr(m, cls, x, y, **props):
        e = mel.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            try: e.set_editor_property(k, v)
            except Exception as ex: w('  prop %s: %s' % (k, str(ex)[:50]))
        return e
    def noisefn(node, fname, **props):
        try: node.set_editor_property('noise_function', getattr(unreal.NoiseFunction, fname))
        except Exception as ex: w('  nf %s: %s' % (fname, str(ex)[:50]))
        for k, v in props.items():
            try: node.set_editor_property(k, v)
            except Exception: pass

    wpos = expr(mat, unreal.MaterialExpressionWorldPosition, -2200, 0)
    t    = expr(mat, unreal.MaterialExpressionTime, -2200, 300)

    # drift vectors (very slow: world units/sec at sky scale)
    d1 = expr(mat, unreal.MaterialExpressionConstant3Vector, -2200, 400, constant=unreal.LinearColor(70, 30, 12, 1))
    d2 = expr(mat, unreal.MaterialExpressionConstant3Vector, -2200, 500, constant=unreal.LinearColor(-45, 55, 20, 1))
    t1 = expr(mat, unreal.MaterialExpressionMultiply, -2000, 350)
    mel.connect_material_expressions(t, '', t1, 'A'); mel.connect_material_expressions(d1, '', t1, 'B')
    t2 = expr(mat, unreal.MaterialExpressionMultiply, -2000, 480)
    mel.connect_material_expressions(t, '', t2, 'A'); mel.connect_material_expressions(d2, '', t2, 'B')

    p1 = expr(mat, unreal.MaterialExpressionAdd, -1850, 100)
    mel.connect_material_expressions(wpos, '', p1, 'A'); mel.connect_material_expressions(t1, '', p1, 'B')

    # warp noise (low freq, drifting)
    warp = expr(mat, unreal.MaterialExpressionNoise, -1650, 100)
    noisefn(warp, 'NOISEFUNCTION_GRADIENT_ALU', scale=0.00035, levels=2, output_min=-1.0, output_max=1.0, quality=1)
    mel.connect_material_expressions(p1, '', warp, 'Position')
    wamp = expr(mat, unreal.MaterialExpressionMultiply, -1450, 100, const_b=3400.0)
    mel.connect_material_expressions(warp, '', wamp, 'A')

    p2a = expr(mat, unreal.MaterialExpressionAdd, -1300, 40)
    mel.connect_material_expressions(wpos, '', p2a, 'A'); mel.connect_material_expressions(t2, '', p2a, 'B')
    p2 = expr(mat, unreal.MaterialExpressionAdd, -1150, 60)
    mel.connect_material_expressions(p2a, '', p2, 'A'); mel.connect_material_expressions(wamp, '', p2, 'B')

    # main gas (turbulent fbm, domain-warped, drifting)
    gas = expr(mat, unreal.MaterialExpressionNoise, -950, 60)
    noisefn(gas, 'NOISEFUNCTION_GRADIENT_ALU', scale=0.00012, levels=3, turbulence=False,
            output_min=0.0, output_max=1.0, quality=1)
    mel.connect_material_expressions(p2, '', gas, 'Position')
    gpow = expr(mat, unreal.MaterialExpressionPower, -760, 60, const_exponent=2.4)
    mel.connect_material_expressions(gas, '', gpow, 'Base')

    # hue patches (independent slow drift)
    hue = expr(mat, unreal.MaterialExpressionNoise, -950, 320)
    noisefn(hue, 'NOISEFUNCTION_GRADIENT_ALU', scale=0.00028, levels=1, output_min=0.0, output_max=1.0, quality=1)
    mel.connect_material_expressions(p1, '', hue, 'Position')

    deep = expr(mat, unreal.MaterialExpressionConstant3Vector, -600, -160, constant=unreal.LinearColor(0.015, 0.05, 0.18, 1))
    cyan = expr(mat, unreal.MaterialExpressionConstant3Vector, -600, -60, constant=unreal.LinearColor(0.10, 0.55, 0.75, 1))
    purp = expr(mat, unreal.MaterialExpressionConstant3Vector, -600, 40, constant=unreal.LinearColor(0.30, 0.10, 0.55, 1))
    cA = expr(mat, unreal.MaterialExpressionLinearInterpolate, -430, -100)
    mel.connect_material_expressions(deep, '', cA, 'A'); mel.connect_material_expressions(cyan, '', cA, 'B')
    mel.connect_material_expressions(gpow, '', cA, 'Alpha')
    cB = expr(mat, unreal.MaterialExpressionLinearInterpolate, -280, -40)
    mel.connect_material_expressions(cA, '', cB, 'A'); mel.connect_material_expressions(purp, '', cB, 'B')
    hmul = expr(mat, unreal.MaterialExpressionMultiply, -430, 200, const_b=0.55)
    mel.connect_material_expressions(hue, '', hmul, 'A')
    mel.connect_material_expressions(hmul, '', cB, 'Alpha')

    nebfin = expr(mat, unreal.MaterialExpressionMultiply, -120, 0)
    mel.connect_material_expressions(cB, '', nebfin, 'A')
    mel.connect_material_expressions(gpow, '', nebfin, 'B')
    nebint = expr(mat, unreal.MaterialExpressionMultiply, 20, 0, const_b=2.0)
    mel.connect_material_expressions(nebfin, '', nebint, 'A')

    # --- horizontal band mask (angle-based, radius independent) ---
    ndir = expr(mat, unreal.MaterialExpressionNormalize, -1900, 700)
    mel.connect_material_expressions(wpos, '', ndir, '')
    zmask = expr(mat, unreal.MaterialExpressionComponentMask, -1750, 700, r=False, g=False, b=True, a=False)
    mel.connect_material_expressions(ndir, '', zmask, '')
    zabs = expr(mat, unreal.MaterialExpressionAbs, -1600, 700)
    mel.connect_material_expressions(zmask, '', zabs, '')
    zinv = expr(mat, unreal.MaterialExpressionOneMinus, -1450, 700)
    mel.connect_material_expressions(zabs, '', zinv, '')
    band = expr(mat, unreal.MaterialExpressionPower, -1300, 700, const_exponent=9.0)
    mel.connect_material_expressions(zinv, '', band, 'Base')

    # --- coverage mask: isolated cloud regions, most of the sky black ---
    cov = expr(mat, unreal.MaterialExpressionNoise, -950, 780)
    noisefn(cov, 'NOISEFUNCTION_GRADIENT_ALU', scale=0.00006, levels=1, output_min=0.0, output_max=1.0, quality=1)
    mel.connect_material_expressions(wpos, '', cov, 'Position')   # static coverage: nebula stays put, gas drifts inside it
    covp = expr(mat, unreal.MaterialExpressionPower, -780, 780, const_exponent=0.7)
    mel.connect_material_expressions(cov, '', covp, 'Base')

    mask1 = expr(mat, unreal.MaterialExpressionMultiply, -600, 740)
    mel.connect_material_expressions(band, '', mask1, 'A')
    mel.connect_material_expressions(covp, '', mask1, 'B')
    nebmasked = expr(mat, unreal.MaterialExpressionMultiply, 140, 20)
    mel.connect_material_expressions(nebint, '', nebmasked, 'A')
    mel.connect_material_expressions(mask1, '', nebmasked, 'B')
    nebint = nebmasked

    # (baked star layer removed — the instanced particle stars handle stars)

    mel.connect_material_property(nebint, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset('/Game/ForeverStar/Materials/M_SkyNebula')
    w('M_SkyNebula built (drifting domain-warped gas + stars)')

    for a in eas.get_all_level_actors():
        if a.get_actor_label() == 'StarSphere':
            a.get_component_by_class(unreal.StaticMeshComponent).set_material(0, mat)
            w('StarSphere -> M_SkyNebula')

    # ================= 2. DIGITAL SHIP TRAILS =================
    tm = get_or_make('/Game/ForeverStar/Materials/M_ShipTrail', 'M_ShipTrail')
    tm.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    tm.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    try:
        bb = expr(tm, unreal.MaterialExpressionBoundingBoxBased_0_1_UVW, -800, 0)
        msk = expr(tm, unreal.MaterialExpressionComponentMask, -650, 0, g=True, r=False, b=False, a=False)
        mel.connect_material_expressions(bb, '', msk, '')
        grad = msk
        w('trail gradient: bounding box Y')
    except Exception as ex:
        grad = expr(tm, unreal.MaterialExpressionTextureCoordinate, -650, 0)
        w('trail gradient fallback texcoord: %s' % str(ex)[:60])
    gp = expr(tm, unreal.MaterialExpressionPower, -500, 0, const_exponent=2.2)
    mel.connect_material_expressions(grad, '', gp, 'Base')
    tt = expr(tm, unreal.MaterialExpressionTime, -800, 200)
    ts = expr(tm, unreal.MaterialExpressionMultiply, -660, 200, const_b=6.0)
    mel.connect_material_expressions(tt, '', ts, 'A')
    tsin = expr(tm, unreal.MaterialExpressionSine, -520, 200)
    mel.connect_material_expressions(ts, '', tsin, '')
    tamp = expr(tm, unreal.MaterialExpressionMultiply, -380, 200, const_b=0.2)
    mel.connect_material_expressions(tsin, '', tamp, 'A')
    tbase = expr(tm, unreal.MaterialExpressionAdd, -240, 200, const_b=0.8)
    mel.connect_material_expressions(tamp, '', tbase, 'A')
    tc = expr(tm, unreal.MaterialExpressionConstant3Vector, -500, -160, constant=unreal.LinearColor(0.35, 0.9, 1.0, 1))
    tb = expr(tm, unreal.MaterialExpressionMultiply, -300, -60, const_b=30.0)
    mel.connect_material_expressions(tc, '', tb, 'A')
    e1 = expr(tm, unreal.MaterialExpressionMultiply, -140, 0)
    mel.connect_material_expressions(tb, '', e1, 'A')
    mel.connect_material_expressions(gp, '', e1, 'B')
    e2 = expr(tm, unreal.MaterialExpressionMultiply, 0, 60)
    mel.connect_material_expressions(e1, '', e2, 'A')
    mel.connect_material_expressions(tbase, '', e2, 'B')
    mel.connect_material_property(e2, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(tm)
    eal.save_asset('/Game/ForeverStar/Materials/M_ShipTrail')
    w('M_ShipTrail built (fading tail + pulse)')

    ships = 0
    for a in eas.get_all_level_actors():
        if a.get_actor_label().startswith('Ship_'):
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                if c.get_editor_property('static_mesh'):
                    c.set_material(0, tm)
                    c.set_relative_scale3d(unreal.Vector(0.10, 6.0, 0.05))  # long digital streak
            rc = a.get_component_by_class(unreal.RotatingMovementComponent)
            if rc:
                spd = random.uniform(5.0, 12.0) * random.choice([1, -1])
                rc.set_editor_property('rotation_rate', unreal.Rotator(0, spd, 0))
            ships += 1
    w('ships updated: %d (trail material, 6x length, 5-12 deg/s)' % ships)

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    w('level saved')
except Exception:
    w('EXC: %s' % traceback.format_exc()[-500:])
with open(p, 'w') as f:
    f.write('\n'.join(out))
print('LIVING NEBULA DONE')
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               