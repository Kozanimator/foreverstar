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
    master = eal.load_asset('/Game/ForeverStar/Materials/M_Planet_Tex')
    cfg = {
        'OceanWorld': (0.08, 0.75, 0.80, 0.10, 0.5, C(0.25, 0.55, 1.0, 1)),
        'Terran':     (0.10, 0.85, 0.85, 0.10, 0.8, C(0.30, 0.65, 1.0, 1)),
        'IceWorld':   (0.10, 0.20, 0.35, 0.06, 0.0, C(0.55, 0.80, 1.0, 1)),
        'GasGiant':   (0.55, 0.70, 0.25, 0.02, 1.2, C(1.0, 0.50, 0.15, 1)),
        'Desert':     (0.70, 0.90, 0.20, 0.04, 0.0, C(1.0, 0.45, 0.15, 1)),
        'Asteroid':   (0.90, 0.95, 0.00, 0.00, 0.0, C(0.35, 0.22, 0.12, 1)),
    }
    clouds = eal.load_asset('/Game/ForeverStar/Textures/T2_Clouds')
    for t, (rw, rl, ca, cg, la, ac) in cfg.items():
        mi = eal.load_asset('/Game/ForeverStar/Materials/MI_%s' % t)
        mi.set_editor_property('parent', master)
        try: mel.update_material_instance(mi)
        except Exception as ex: w('  update: %s' % str(ex)[:60])
        ok1 = mel.set_material_instance_texture_parameter_value(mi, 'SurfaceTex',
              eal.load_asset('/Game/ForeverStar/Textures/T2_%s' % t))
        ok2 = mel.set_material_instance_texture_parameter_value(mi, 'NormalTex',
              eal.load_asset('/Game/ForeverStar/Textures/N2_%s' % t))
        for cp in ['CloudTex', 'CloudTex2', 'CloudTexS']:
            mel.set_material_instance_texture_parameter_value(mi, cp, clouds)
        for k, v in [('RoughWater', rw), ('RoughLand', rl), ('CloudAmount', ca),
                     ('CloudGlow', cg), ('LightningAmount', la)]:
            mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
        mel.set_material_instance_vector_parameter_value(mi, 'AtmosphereColor', ac)
        eal.save_asset('/Game/ForeverStar/Materials/MI_%s' % t)
        w('MI_%-11s parent=M_Planet_Tex surf=%s norm=%s' % (t, ok1, ok2))
    w('ALL REATTACHED')
except Exception:
    w('EXC: %s' % traceback.format_exc()[-500:])
print('REATTACH DONE')
