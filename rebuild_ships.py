import unreal, random, math, traceback
p = r'E:\Projects\TMU\ARVR\ForeverStar\planet-server\matdbg.txt'
out = []
def w(s): out.append(str(s))
random.seed(31)
TRAIL_SIGN = -1   # if trails ever lead instead of follow, change to +1 and rerun
try:
    mel = unreal.MaterialEditingLibrary
    eal = unreal.EditorAssetLibrary
    at  = unreal.AssetToolsHelpers.get_asset_tools()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

    # --- ship dot material: white core with cyan glow ---
    MP = '/Game/ForeverStar/Materials/M_ShipDot'
    if eal.does_asset_exist(MP):
        mat = eal.load_asset(MP); mel.delete_all_material_expressions(mat)
    else:
        mat = at.create_asset('M_ShipDot', '/Game/ForeverStar/Materials',
                              unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property('constant', unreal.LinearColor(0.55, 0.95, 1.0, 1))
    gp = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -300, 150)
    gp.set_editor_property('parameter_name', 'Glow')
    gp.set_editor_property('default_value', 35.0)
    m = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -100, 0)
    mel.connect_material_expressions(c, '', m, 'A')
    mel.connect_material_expressions(gp, '', m, 'B')
    mel.connect_material_property(m, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset(MP)

    # fading glow steps for the trail (shared across all ships)
    fades = []
    for fi in range(8):
        fp = '/Game/ForeverStar/Materials/MI_ShipDot_%d' % fi
        if eal.does_asset_exist(fp):
            mi = eal.load_asset(fp)
        else:
            mi = at.create_asset('MI_ShipDot_%d' % fi, '/Game/ForeverStar/Materials',
                                 unreal.MaterialInstanceConstant,
                                 unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property('parent', mat)
        glow = 30.0 * (1.0 - fi / 8.0) ** 2.4 + 0.15
        mel.set_material_instance_scalar_parameter_value(mi, 'Glow', glow)
        eal.save_asset(fp)
        fades.append(mi)

    # --- clear all old ships ---
    for a in list(eas.get_all_level_actors()):
        if a.get_actor_label().startswith(('Ship_', 'ShipNear_')):
            eas.destroy_actor(a)

    sphere = unreal.load_object(None, '/Engine/BasicShapes/Sphere.Sphere')

    def add_sphere(handles, world_pos, scale, material=None):
        prm = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.StaticMeshComponent)
        h, f = sds.add_new_subobject(prm)
        cpt = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(sds.k2_find_subobject_data_from_handle(h))
        cpt.set_static_mesh(sphere)
        cpt.set_material(0, material or mat)
        cpt.set_editor_property('cast_shadow', False)
        cpt.set_world_location(world_pos, False, False)   # absolute placement: immune to parenting quirks
        cpt.set_world_scale3d(unreal.Vector(scale, scale, scale))
        return cpt

    def fleet(label, count, rmin, rmax, zmin, zmax, body, dot0, ddeg, ndots, smin, smax):
        made = 0
        for i in range(count):
            z = random.uniform(zmin, zmax)
            radius = random.uniform(rmin, rmax)
            holder = eas.spawn_actor_from_class(unreal.StaticMeshActor,
                                                unreal.Vector(0, 0, z),
                                                unreal.Rotator(0, 0, 0))
            holder.set_actor_label('%s%d' % (label, i))
            holder.set_folder_path('Sky/Ships')
            holder.set_mobility(unreal.ComponentMobility.MOVABLE)
            hh = sds.k2_gather_subobject_data_for_instance(holder)
            sgn = random.choice([1, -1])
            th0 = random.uniform(0, 360)   # stagger ships around the circle
            # body: star-sized dot, placed in world space on the orbit circle
            a0 = math.radians(th0)
            add_sphere(hh, unreal.Vector(radius * math.cos(a0), radius * math.sin(a0), z), body)
            # trail: shrinking dots along the same circle, behind the travel direction
            for k in range(1, ndots + 1):
                ang = math.radians(th0 + TRAIL_SIGN * sgn * k * ddeg)
                pos = unreal.Vector(radius * math.cos(ang), radius * math.sin(ang), z)
                s = body * (1.0 - k / float(ndots + 2)) * (dot0 / body)
                fade_mat = fades[min(int(k * 8 / (ndots + 1)), 7)]
                add_sphere(hh, pos, max(s, 0.008), fade_mat)
            prm2 = unreal.AddNewSubobjectParams(parent_handle=hh[0], new_class=unreal.RotatingMovementComponent)
            h2, f2 = sds.add_new_subobject(prm2)
            rot = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(sds.k2_find_subobject_data_from_handle(h2))
            rot.set_editor_property('rotation_rate',
                                    unreal.Rotator(roll=0.0, pitch=0.0, yaw=sgn * random.uniform(smin, smax)))
            made += 1
        w('%s: %d ships, %d trail dots each' % (label, made, ndots))

    # near fleet: weaving between planets, clearly visible motion
    fleet('ShipNear_', 5, 650, 1500, -250, 400, body=0.14, dot0=0.06, ddeg=0.8, ndots=60, smin=9, smax=18)
    # far fleet: ambient background traffic
    fleet('Ship_', 6, 8500, 13000, -1500, 2500, body=0.55, dot0=0.22, ndots=52, ddeg=0.35, smin=3, smax=7)

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    w('level saved')
except Exception:
    w('EXC: %s' % traceback.format_exc()[-500:])
with open(p, 'w') as f:
    f.write('\n'.join(out))
print('SHIPS REBUILT')
