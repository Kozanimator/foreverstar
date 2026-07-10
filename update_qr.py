import unreal, traceback, os, sys, socket, zlib, struct
p = r'E:\Projects\TMU\ARVR\ForeverStar\planet-server\matdbg.txt'
open(p, 'w').write('')
def w(s):
    with open(p, 'a') as f: f.write(str(s) + '\n')

BASE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else r'E:\Projects\TMU\ARVR\ForeverStar\planet-server'
PORT = 3000  # must match HTTPS_PORT in server.js

def local_ip():
    s = socket.socket(socket.SOCK_DGRAM if False else socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))  # no traffic sent; just picks the outbound interface
        return s.getsockname()[0]
    finally:
        s.close()

def write_png(path, matrix, scale=16):
    n = len(matrix)
    size = n * scale
    rows = []
    for my in range(n):
        line = bytearray()
        for mx in range(n):
            v = b'\x00' if matrix[my][mx] else b'\xff'   # black modules on white
            line += v * scale
        for _ in range(scale):
            rows.append(b'\x00' + bytes(line))
    raw = zlib.compress(b''.join(rows), 9)
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 0, 0, 0, 0)  # 8-bit grayscale
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', raw) + chunk(b'IEND', b''))
    return size

try:
    # if cloud_url.txt exists, the QR points at the permanent cloud relay instead of this machine
    cloud_file = os.path.join(BASE, 'cloud_url.txt')
    if os.path.exists(cloud_file):
        url = open(cloud_file).read().strip()
        ip = 'cloud'
        w('using permanent cloud URL from cloud_url.txt')
    else:
        ip = local_ip()
        url = 'https://%s:%d' % (ip, PORT)
        w('machine IP: %s' % ip)
    w('QR url: %s' % url)

    sys.path.insert(0, os.path.join(BASE, 'pylibs'))
    import qrcode
    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    png = os.path.join(BASE, 'textures', 'T_JoinQR_live.png')
    size = write_png(png, qr.get_matrix())
    w('png written: %dpx' % size)

    mel = unreal.MaterialEditingLibrary
    eal = unreal.EditorAssetLibrary
    at  = unreal.AssetToolsHelpers.get_asset_tools()

    # fresh asset name per IP (replace_existing is unreliable on referenced assets)
    asset_name = 'T_JoinQR_%s' % ip.replace('.', '_')
    asset_path = '/Game/ForeverStar/Textures/%s' % asset_name
    if not eal.does_asset_exist(asset_path):
        task = unreal.AssetImportTask()
        task.filename = png
        task.destination_path = '/Game/ForeverStar/Textures'
        task.destination_name = asset_name
        task.automated = True; task.save = True; task.replace_existing = True
        at.import_asset_tasks([task])
    tex = eal.load_asset(asset_path)
    w('texture %s: %s' % (asset_name, bool(tex)))

    mat = eal.load_asset('/Game/ForeverStar/Materials/M_JoinCard')
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    ts = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -500, 0)
    ts.set_editor_property('texture', tex)
    br = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -500, 200)
    br.set_editor_property('parameter_name', 'CardBrightness')
    br.set_editor_property('default_value', 0.9)
    m = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -250, 60)
    mel.connect_material_expressions(ts, 'RGB', m, 'A')
    mel.connect_material_expressions(br, '', m, 'B')
    mel.connect_material_property(m, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset('/Game/ForeverStar/Materials/M_JoinCard')
    w('M_JoinCard now points at %s' % asset_name)
    w('DONE - QR encodes %s' % url)
except Exception:
    w('EXC: %s' % traceback.format_exc()[-400:])
print('QR UPDATE DONE')
