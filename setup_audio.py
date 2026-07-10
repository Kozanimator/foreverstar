import unreal, traceback
p = r'E:\Projects\TMU\ARVR\ForeverStar\planet-server\matdbg.txt'
open(p, 'w').write('')
def w(s):
    with open(p, 'a') as f: f.write(str(s) + '\n')
try:
    eal = unreal.EditorAssetLibrary
    at  = unreal.AssetToolsHelpers.get_asset_tools()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    src = r'E:\Projects\TMU\ARVR\ForeverStar\ForeverStarUE\Content\ForeverStar\Audio'
    tasks = []
    for fn, name in [('ForeverStar_Awakening.mp3', 'A_Ambient_Loop'),
                     ('S_Select.wav', 'A_SelectCue'),
                     ('S_PlanetBuild.wav', 'A_PlanetBuild')]:
        task = unreal.AssetImportTask()
        task.filename = src + '\\' + fn
        task.destination_path = '/Game/ForeverStar/Audio'
        task.destination_name = name
        task.automated = True; task.save = True; task.replace_existing = True
        tasks.append(task)
    at.import_asset_tasks(tasks)
    for name in ['A_Ambient_Loop', 'A_SelectCue', 'A_PlanetBuild']:
        ok = eal.does_asset_exist('/Game/ForeverStar/Audio/' + name)
        w('%s imported: %s' % (name, ok))

    music = eal.load_asset('/Game/ForeverStar/Audio/A_Ambient_Loop')
    if music:
        music.set_editor_property('looping', True)
        music.set_editor_property('volume', 0.6)
        eal.save_asset('/Game/ForeverStar/Audio/A_Ambient_Loop')
        w('music set to loop at 0.6 volume')
        for a in list(eas.get_all_level_actors()):
            if a.get_actor_label() == 'AmbientMusic':
                eas.destroy_actor(a)
        amb = eas.spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        amb.set_actor_label('AmbientMusic')
        ac = amb.get_component_by_class(unreal.AudioComponent)
        ac.set_editor_property('sound', music)
        ac.set_editor_property('allow_spatialization', False)   # 2D: same volume everywhere
        ac.set_editor_property('auto_activate', True)
        w('AmbientMusic actor placed (2D, autoplay, loops)')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    w('saved')
except Exception:
    w('EXC: %s' % traceback.format_exc()[-400:])
print('AUDIO SETUP DONE')
