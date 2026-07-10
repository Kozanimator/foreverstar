import unreal, random, math, traceback
p = r'E:\Projects\TMU\ARVR\ForeverStar\planet-server\matdbg.txt'
out = []
def w(s): out.append(str(s))
random.seed(21)
try:
    eal = unreal.EditorAssetLibrary
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

    # ---------- 1. rebuild particle stars BIGGER (kills aliasing shimmer) ----------
    for a in list(eas.get_all_level_actors()):
        if a.get_actor_label() == 'ParticleStars':
            eas.destroy_actor(a)
    sphere = unreal.load_object(None, '/Engine/BasicShapes/Sphere.Sphere')
    mat = eal.load_asset('/Game/ForeverStar/Materials/M_StarParticle')
    holder = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    holder.set_actor_label('ParticleStars')
    holder.set_mobility(unreal.ComponentMobility.STATIC)
    handles = sds.k2_gather_subobject_data_for_instance(holder)
    prm = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.InstancedStaticMeshComponent)
    h2, fail = sds.add_new_subobject(prm)
    ism = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(sds.k2_find_subobject_data_from_handle(h2))
    ism.set_static_mesh(sphere)
    ism.set_material(0, mat)
    ism.set_editor_property('cast_shadow', False)
    n = 0
    for cnt, rmin, rmax, smin, smax in [(400, 4000, 6000, 8, 16),
                                        (1000, 7000, 10000, 16, 32),
                                        (1200, 11000, 15000, 26, 55)]:
        for _ in range(cnt):
            v = unreal.Vector(random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))
            L = math.sqrt(v.x*v.x + v.y*v.y + v.z*v.z) or 1.0
            r = random.uniform(rmin, rmax)
            s = random.uniform(smin, smax) / 100.0
            ism.add_instance(unreal.Transform(location=unreal.Vector(v.x/L*r, v.y/L*r, v.z/L*r),
                                              rotation=unreal.Rotator(0, 0, 0),
                                              scale=unreal.Vector(s, s, s)))
            n += 1
    w('stars rebuilt: %d, 2.5x bigger (soft dots, no shimmer)' % n)

    # ---------- 2. close ships weaving between the planets ----------
    for a in list(eas.get_all_level_actors()):
        if a.get_actor_label().startswith('ShipNear_'):
            eas.destroy_actor(a)
    cube = unreal.load_object(None, '/Engine/BasicShapes/Cube.Cube')
    trail = eal.load_asset('/Game/ForeverStar/Materials/M_ShipTrail')
    ships = 0
    for i in range(5):
        z = random.uniform(-250, 400)
        radius = random.uniform(650, 1500)
        tilt = random.uniform(-12, 12)   # tilted orbit planes so paths cross visibly
        holder2 = eas.spawn_actor_from_class(unreal.StaticMeshActor,
                                             unreal.Vector(0, 0, z),
                                             unreal.Rotator(tilt, random.uniform(0, 360), 0))
        holder2.set_actor_label('ShipNear_%d' % i)
        holder2.set_folder_path('Sky/Ships')
        holder2.set_mobility(unreal.ComponentMobility.MOVABLE)
        hh = sds.k2_gather_subobject_data_for_instance(holder2)
        prm = unreal.AddNewSubobjectParams(parent_handle=hh[0], new_class=unreal.StaticMeshComponent)
        h3, f3 = sds.add_new_subobject(prm)
        body = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(sds.k2_find_subobject_data_from_handle(h3))
        body.set_static_mesh(cube)
        body.set_material(0, trail)
        body.set_editor_property('cast_shadow', False)
        body.set_relative_location(unreal.Vector(radius, 0, 0), False, False)
        body.set_relative_scale3d(unreal.Vector(0.05, 1.6, 0.025))
        prm2 = unreal.AddNewSubobjectParams(parent_handle=hh[0], new_class=unreal.RotatingMovementComponent)
        h4, f4 = sds.add_new_subobject(prm2)
        rot = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(sds.k2_find_subobject_data_from_handle(h4))
        spd = random.uniform(9.0, 20.0) * random.choice([1, -1])
        rot.set_editor_property('rotation_rate', unreal.Rotator(0, spd, 0))
        ships += 1
    w('near ships: %d at radius 650-1500, tilted lanes, 9-20 deg/s' % ships)

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    w('level saved')
except Exception:
    w('EXC: %s' % traceback.format_exc()[-500:])
with open(p, 'w') as f:
    f.write('\n'.join(out))
print('STARS AND SHIPS DONE')
