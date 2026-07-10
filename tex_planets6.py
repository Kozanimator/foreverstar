import unreal, traceback
p = r'E:\Projects\TMU\ARVR\ForeverStar\planet-server\matdbg.txt'
open(p, 'w').write('')
def w(s):
    with open(p, 'a') as f:
        f.write(str(s) + '\n')
try:
    mel = unreal.MaterialEditingLibrary
    eal = unreal.EditorAssetLibrary
    C = unreal.LinearColor
    MP = '/Game/ForeverStar/Materials/M_PlanetSurf'
    at = unreal.AssetToolsHelpers.get_asset_tools()
    if eal.does_asset_exist(MP):
        mat = eal.load_asset(MP); mel.delete_all_material_expressions(mat)
    else:
        mat = at.create_asset('M_PlanetSurf', '/Game/ForeverStar/Materials', unreal.Material, unreal.MaterialFactoryNew())
    w('building into fresh asset M_PlanetSurf')
    def expr(cls, x, y, **props):
        w('  + ' + cls.__name__)
        e = mel.create_material_expression(mat, cls, x, y)
        for k, v in props.items():
            try: e.set_editor_property(k, v)
            except Exception as ex: w('  prop %s: %s' % (k, str(ex)[:50]))
        return e
    def sp(name, val, x, y):
        return expr(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(val))
    def link(a, ao, b, bi): mel.connect_material_expressions(a, ao, b, bi)

    # ===== seed-driven UV offset: every planet shows a different face =====
    seed = sp('PlanetSeed', 0.0, -2700, 100)
    sm = expr(unreal.MaterialExpressionMultiply, -2560, 100, const_b=0.137)
    link(seed, '', sm, 'A')
    sfr = expr(unreal.MaterialExpressionFrac, -2430, 100)
    link(sm, '', sfr, '')
    zero = expr(unreal.MaterialExpressionConstant, -2430, 180, r=0.0)
    sap = expr(unreal.MaterialExpressionAppendVector, -2300, 100)
    link(sfr, '', sap, 'A'); link(zero, '', sap, 'B')
    uv0 = expr(unreal.MaterialExpressionTextureCoordinate, -2560, 220)
    uv = expr(unreal.MaterialExpressionAdd, -2300, 200)
    link(uv0, '', uv, 'A'); link(sap, '', uv, 'B')

    surf = expr(unreal.MaterialExpressionTextureSampleParameter2D, -2000, -200, parameter_name='SurfaceTex')
    surf.set_editor_property('texture', eal.load_asset('/Game/ForeverStar/Textures/T2_OceanWorld'))
    link(uv, '', surf, 'UVs')

    # ===== clouds: two layers + shadow =====
    t = expr(unreal.MaterialExpressionTime, -2700, 460)
    cspd = sp('CloudSpeed', 0.006, -2700, 560)
    tm = expr(unreal.MaterialExpressionMultiply, -2560, 500)
    link(t, '', tm, 'A'); link(cspd, '', tm, 'B')
    ap = expr(unreal.MaterialExpressionAppendVector, -2430, 500)
    link(tm, '', ap, 'A'); link(zero, '', ap, 'B')
    cuv1 = expr(unreal.MaterialExpressionAdd, -2300, 420)
    link(uv, '', cuv1, 'A'); link(ap, '', cuv1, 'B')
    ct1 = expr(unreal.MaterialExpressionTextureSampleParameter2D, -2150, 380, parameter_name='CloudTex')
    ct1.set_editor_property('texture', eal.load_asset('/Game/ForeverStar/Textures/T2_Clouds'))
    link(cuv1, '', ct1, 'UVs')
    uv2 = expr(unreal.MaterialExpressionMultiply, -2300, 620, const_b=2.3)
    link(uv, '', uv2, 'A')
    tm2 = expr(unreal.MaterialExpressionMultiply, -2300, 720, const_b=1.7)
    link(tm, '', tm2, 'A')
    ap2 = expr(unreal.MaterialExpressionAppendVector, -2170, 720)
    link(tm2, '', ap2, 'A'); link(zero, '', ap2, 'B')
    cuv2 = expr(unreal.MaterialExpressionAdd, -2040, 660)
    link(uv2, '', cuv2, 'A'); link(ap2, '', cuv2, 'B')
    ct2 = expr(unreal.MaterialExpressionTextureSampleParameter2D, -1900, 620, parameter_name='CloudTex2')
    ct2.set_editor_property('texture', eal.load_asset('/Game/ForeverStar/Textures/T2_Clouds'))
    link(cuv2, '', ct2, 'UVs')
    half = expr(unreal.MaterialExpressionMultiply, -1730, 660, const_b=0.5)
    link(ct2, 'R', half, 'A')
    csum = expr(unreal.MaterialExpressionAdd, -1600, 480)
    link(ct1, 'R', csum, 'A'); link(half, '', csum, 'B')
    csat = expr(unreal.MaterialExpressionSaturate, -1480, 480)
    link(csum, '', csat, '')
    camt = sp('CloudAmount', 0.5, -1480, 600)
    cmask = expr(unreal.MaterialExpressionMultiply, -1340, 500)
    link(csat, '', cmask, 'A'); link(camt, '', cmask, 'B')
    soff = expr(unreal.MaterialExpressionAdd, -2300, 860, const_b=0.008)
    link(cuv1, '', soff, 'A')
    ct3 = expr(unreal.MaterialExpressionTextureSampleParameter2D, -2150, 840, parameter_name='CloudTexS')
    ct3.set_editor_property('texture', eal.load_asset('/Game/ForeverStar/Textures/T2_Clouds'))
    link(soff, '', ct3, 'UVs')
    shm = expr(unreal.MaterialExpressionMultiply, -1980, 880)
    link(ct3, 'R', shm, 'A'); link(camt, '', shm, 'B')
    shs = expr(unreal.MaterialExpressionMultiply, -1850, 900, const_b=0.35)
    link(shm, '', shs, 'A')
    shi = expr(unreal.MaterialExpressionOneMinus, -1720, 900)
    link(shs, '', shi, '')

    # ===== per-planet tint (warm/cool by seed) =====
    tsm = expr(unreal.MaterialExpressionMultiply, -2560, 1040, const_b=0.61)
    link(seed, '', tsm, 'A')
    tfr = expr(unreal.MaterialExpressionFrac, -2430, 1040)
    link(tsm, '', tfr, '')
    cool = expr(unreal.MaterialExpressionConstant3Vector, -2300, 980, constant=C(0.90, 0.97, 1.10, 1))
    warm = expr(unreal.MaterialExpressionConstant3Vector, -2300, 1100, constant=C(1.12, 1.00, 0.86, 1))
    tint = expr(unreal.MaterialExpressionLinearInterpolate, -2150, 1040)
    link(cool, '', tint, 'A'); link(warm, '', tint, 'B'); link(tfr, '', tint, 'Alpha')

    surft = expr(unreal.MaterialExpressionMultiply, -1720, -140)
    link(surf, 'RGB', surft, 'A'); link(tint, '', surft, 'B')
    surfsh = expr(unreal.MaterialExpressionMultiply, -1560, -80)
    link(surft, '', surfsh, 'A'); link(shi, '', surfsh, 'B')

    cloudcol = expr(unreal.MaterialExpressionConstant3Vector, -1340, 320, constant=C(0.97, 0.98, 1.0, 1))
    bc0 = expr(unreal.MaterialExpressionLinearInterpolate, -1180, 0)
    link(surfsh, '', bc0, 'A'); link(cloudcol, '', bc0, 'B'); link(cmask, '', bc0, 'Alpha')

    # ===== limb darkening: edges roll away =====
    fres = expr(unreal.MaterialExpressionFresnel, -1180, 180, exponent=2.2)
    fmul = expr(unreal.MaterialExpressionMultiply, -1040, 180, const_b=0.4)
    link(fres, '', fmul, 'A')
    finv = expr(unreal.MaterialExpressionOneMinus, -910, 180)
    link(fmul, '', finv, '')
    bc = expr(unreal.MaterialExpressionMultiply, -770, 40)
    link(bc0, '', bc, 'A'); link(finv, '', bc, 'B')
    mel.connect_material_property(bc, '', unreal.MaterialProperty.MP_BASE_COLOR)

    # ===== roughness / specular / metallic =====
    rw = sp('RoughWater', 0.10, -1340, 740)
    rl = sp('RoughLand', 0.85, -1340, 840)
    r1 = expr(unreal.MaterialExpressionLinearInterpolate, -1180, 780)
    link(rl, '', r1, 'A'); link(rw, '', r1, 'B'); link(surf, 'A', r1, 'Alpha')
    r2 = expr(unreal.MaterialExpressionLinearInterpolate, -1040, 800, const_b=0.9)
    link(r1, '', r2, 'A'); link(cmask, '', r2, 'Alpha')
    mel.connect_material_property(r2, '', unreal.MaterialProperty.MP_ROUGHNESS)
    spec1 = expr(unreal.MaterialExpressionLinearInterpolate, -1180, 960, const_a=0.30, const_b=1.0)
    link(surf, 'A', spec1, 'Alpha')
    spec2 = expr(unreal.MaterialExpressionLinearInterpolate, -1040, 980, const_b=0.1)
    link(spec1, '', spec2, 'A'); link(cmask, '', spec2, 'Alpha')
    mel.connect_material_property(spec2, '', unreal.MaterialProperty.MP_SPECULAR)
    met = expr(unreal.MaterialExpressionConstant, -1040, 1080, r=0.0)
    mel.connect_material_property(met, '', unreal.MaterialProperty.MP_METALLIC)

    # ===== normal with strength boost =====
    nt = expr(unreal.MaterialExpressionTextureSampleParameter2D, -1340, 1200, parameter_name='NormalTex')
    nt.set_editor_property('texture', eal.load_asset('/Game/ForeverStar/Textures/N2_OceanWorld'))
    try: nt.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    except Exception as ex: w('sampler: %s' % str(ex)[:50])
    link(uv, '', nt, 'UVs')
    nmask = expr(unreal.MaterialExpressionComponentMask, -1180, 1200, r=True, g=True, b=False, a=False)
    link(nt, '', nmask, '')
    nstr = sp('NormalStrength', 2.2, -1180, 1320)
    nboost = expr(unreal.MaterialExpressionMultiply, -1040, 1240)
    link(nmask, '', nboost, 'A'); link(nstr, '', nboost, 'B')
    nb = expr(unreal.MaterialExpressionComponentMask, -1180, 1420, r=False, g=False, b=True, a=False)
    link(nt, '', nb, '')
    nfin = expr(unreal.MaterialExpressionAppendVector, -900, 1280)
    link(nboost, '', nfin, 'A'); link(nb, '', nfin, 'B')
    mel.connect_material_property(nfin, '', unreal.MaterialProperty.MP_NORMAL)

    # ===== emissive: cloud glow + lightning + highlight =====
    cglow = sp('CloudGlow', 0.08, -1180, 1560)
    ce = expr(unreal.MaterialExpressionMultiply, -1040, 1560)
    link(cmask, '', ce, 'A'); link(cglow, '', ce, 'B')
    f1 = expr(unreal.MaterialExpressionMultiply, -2560, 1560, const_b=7.3)
    link(t, '', f1, 'A')
    f2 = expr(unreal.MaterialExpressionMultiply, -2560, 1660, const_b=2.71)
    link(t, '', f2, 'A')
    sadd = expr(unreal.MaterialExpressionAdd, -2430, 1680)
    link(f2, '', sadd, 'A'); link(seed, '', sadd, 'B')
    s1 = expr(unreal.MaterialExpressionSine, -2300, 1560)
    link(f1, '', s1, '')
    s2 = expr(unreal.MaterialExpressionSine, -2300, 1680)
    link(sadd, '', s2, '')
    smul = expr(unreal.MaterialExpressionMultiply, -2170, 1620)
    link(s1, '', smul, 'A'); link(s2, '', smul, 'B')
    ssat = expr(unreal.MaterialExpressionSaturate, -2040, 1620)
    link(smul, '', ssat, '')
    spow = expr(unreal.MaterialExpressionPower, -1910, 1620, const_exponent=40.0)
    link(ssat, '', spow, 'Base')
    lamt = sp('LightningAmount', 0.0, -1910, 1740)
    l1 = expr(unreal.MaterialExpressionMultiply, -1780, 1660)
    link(spow, '', l1, 'A'); link(lamt, '', l1, 'B')
    cm2 = expr(unreal.MaterialExpressionMultiply, -1650, 1620)
    link(cmask, '', cm2, 'A'); link(cmask, '', cm2, 'B')
    l2 = expr(unreal.MaterialExpressionMultiply, -1520, 1640)
    link(l1, '', l2, 'A'); link(cm2, '', l2, 'B')
    lcol = expr(unreal.MaterialExpressionConstant3Vector, -1520, 1760, constant=C(4.0, 5.0, 8.0, 1))
    l3 = expr(unreal.MaterialExpressionMultiply, -1390, 1680)
    link(l2, '', l3, 'A'); link(lcol, '', l3, 'B')
    atmos = expr(unreal.MaterialExpressionVectorParameter, -1390, 1840, parameter_name='AtmosphereColor',
                 default_value=C(0.3, 0.5, 1.0, 1))
    estr = sp('EmissiveStrength', 0.0, -1390, 1980)
    he = expr(unreal.MaterialExpressionMultiply, -1250, 1900)
    link(atmos, '', he, 'A'); link(estr, '', he, 'B')
    e1 = expr(unreal.MaterialExpressionAdd, -900, 1640)
    link(ce, '', e1, 'A'); link(l3, '', e1, 'B')
    e2 = expr(unreal.MaterialExpressionAdd, -770, 1700)
    link(e1, '', e2, 'A'); link(he, '', e2, 'B')
    mel.connect_material_property(e2, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    mel.recompile_material(mat)
    eal.save_asset(MP)
    w('master built OK into M_PlanetSurf')
    # ---- reattach all instances to the fresh master in the same run ----
    clouds = eal.load_asset('/Game/ForeverStar/Textures/T2_Clouds')
    cfg = {
        'OceanWorld': (0.08, 0.75, 0.80, 0.10, 0.5, C(0.25, 0.55, 1.0, 1)),
        'Terran':     (0.10, 0.85, 0.85, 0.10, 0.8, C(0.30, 0.65, 1.0, 1)),
        'IceWorld':   (0.10, 0.20, 0.35, 0.06, 0.0, C(0.55, 0.80, 1.0, 1)),
        'GasGiant':   (0.55, 0.70, 0.25, 0.02, 1.2, C(1.0, 0.50, 0.15, 1)),
        'Desert':     (0.70, 0.90, 0.20, 0.04, 0.0, C(1.0, 0.45, 0.15, 1)),
        'Asteroid':   (0.90, 0.95, 0.00, 0.00, 0.0, C(0.35, 0.22, 0.12, 1)),
    }
    for tn, (rw2, rl2, ca2, cg2, la2, ac2) in cfg.items():
        mi = eal.load_asset('/Game/ForeverStar/Materials/MI_%s' % tn)
        mi.set_editor_property('parent', mat)
        try: mel.update_material_instance(mi)
        except Exception as ex: w('  upd %s: %s' % (tn, str(ex)[:50]))
        ok1 = mel.set_material_instance_texture_parameter_value(mi, 'SurfaceTex',
              eal.load_asset('/Game/ForeverStar/Textures/T2_%s' % tn))
        mel.set_material_instance_texture_parameter_value(mi, 'NormalTex',
              eal.load_asset('/Game/ForeverStar/Textures/N2_%s' % tn))
        for cp in ['CloudTex', 'CloudTex2', 'CloudTexS']:
            mel.set_material_instance_texture_parameter_value(mi, cp, clouds)
        for k2, v2 in [('RoughWater', rw2), ('RoughLand', rl2), ('CloudAmount', ca2),
                       ('CloudGlow', cg2), ('LightningAmount', la2)]:
            mel.set_material_instance_scalar_parameter_value(mi, k2, float(v2))
        mel.set_material_instance_vector_parameter_value(mi, 'AtmosphereColor', ac2)
        eal.save_asset('/Game/ForeverStar/Materials/MI_%s' % tn)
        w('MI_%s attached: surf=%s' % (tn, ok1))
    w('ALL COMPLETE')
except Exception:
    w('EXC: %s' % traceback.format_exc()[-400:])
print('TEX PLANETS V4 DONE')
