import bpy
import bmesh
import os
import json
import math
from mathutils import Vector, Euler, Matrix

# ==============================================================================
# 044_01.106정거장 1차 가시설도-3th (type-9,10,11버팀보, 차수 수정) - 우각부 버팀보 수정
# 정밀 복공판(Steel Deck Plate), 주형보(Main Girder), 주형지지보(내측/외측 주형받침보),
# 피스브라켓(외측/내측/띠장 보걸이 브라켓), 띠장(H-300x305 실단면), 우각부 버팀보 및 대각 ㄷ형강 구현
# ==============================================================================

dxf_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\0d917c24-0c73-469d-af45-411a71b292b9\scratch\cad_044.dxf"
json_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\0d917c24-0c73-469d-af45-411a71b292b9\scratch\cad_044_data.json"
blend_save_path = r"C:\Users\20040178\Desktop\2영역\토스앤\1.설계변경관리\2.인덕원동탄5공구\7.정거장 구조물 원가개선\정거장 가시설도, 구조도\106정거장_가시설_전체구간_3D_BIM.blend"

with open(json_path, 'r', encoding='utf-8') as f:
    cad = json.load(f)

with open(dxf_path, 'r', encoding='cp949', errors='replace') as f:
    lines = f.read().splitlines()

n = len(lines)
i = 0
in_entities = False
cur_ent = None
entities = []
while i < n - 1:
    code = lines[i].strip()
    val = lines[i+1].strip()
    i += 2
    if code == '0' and val == 'SECTION':
        if i < n - 1 and lines[i].strip() == '2':
            sec_name = lines[i+1].strip()
            i += 2
            in_entities = (sec_name == 'ENTITIES')
            continue
    elif code == '0' and val == 'ENDSEC':
        if cur_ent and in_entities:
            entities.append(cur_ent)
        cur_ent = None
        in_entities = False
        continue
    if in_entities:
        if code == '0':
            if cur_ent:
                entities.append(cur_ent)
            cur_ent = {'type': val, 'layer': '', 'x': [], 'y': [], 'text': '', 'name': '', 'rot': 0.0, 'closed': 0}
        elif cur_ent is not None:
            if code == '8':
                cur_ent['layer'] = val
            elif code == '2':
                cur_ent['name'] = val
            elif code == '70':
                try:
                    cur_ent['closed'] = int(val)
                except:
                    pass
            elif code == '50':
                try:
                    cur_ent['rot'] = float(val)
                except:
                    pass
            elif code in ('10', '11'):
                try:
                    cur_ent['x'].append(float(val))
                except:
                    pass
            elif code in ('20', '21'):
                try:
                    cur_ent['y'].append(float(val))
                except:
                    pass
            elif code in ('1', '3'):
                cur_ent['text'] += val

def to_loc_deck(x, y):
    # 복공평면도 (X: 0..205, Y: 20..100) -> Blender Local (X = x + 208.2 - 235.0 = x - 26.8, Y = y - 52.0)
    return (round(x - 26.8, 4), round(y - 52.0, 4))

def to_loc_b1b3(x, y):
    return (round(x - 235.0, 4), round(y - 52.0, 4))

# ==============================================================================
# 1. 재질(Materials) 정의 (부재별 명확한 색상 구분으로 시각적 가독성 극대화)
# ==============================================================================
def make_mat(name, rgba, metallic=0.45, roughness=0.40, alpha=1.0):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgba[0], rgba[1], rgba[2], alpha)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
    m.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    return m

mat_deck_plate   = make_mat("MAT_CAD044_DeckPlate_H200",     (0.32, 0.37, 0.43), metallic=0.65, roughness=0.45)
mat_deck_custom  = make_mat("MAT_CAD044_DeckPlate_CustomA",  (0.26, 0.42, 0.48), metallic=0.60, roughness=0.42)
mat_main_girder  = make_mat("MAT_CAD044_MainGirder_H700",    (0.82, 0.22, 0.16), metallic=0.55, roughness=0.35) # 진적갈색(광명단 방청도장 H-700x300)
mat_ramp_girder  = make_mat("MAT_CAD044_RampGirder_H440",    (0.88, 0.42, 0.15), metallic=0.55, roughness=0.35) # 진입부 주형보 H-440x300
mat_inner_sup    = make_mat("MAT_CAD044_InnerSupport_H440",  (0.14, 0.52, 0.85), metallic=0.55, roughness=0.35) # 청색(내측 주형지지보 2-H440x300)
mat_outer_sup    = make_mat("MAT_CAD044_OuterSupport_H300",  (0.12, 0.68, 0.58), metallic=0.55, roughness=0.35) # 청록색(외측 주형지지보 H-300x305)
mat_piece_brk_o  = make_mat("MAT_CAD044_PieceBracket_Outer", (0.95, 0.72, 0.10), metallic=0.65, roughness=0.30) # 황금색(외측 피스브라켓 H-300x305x400)
mat_piece_brk_i  = make_mat("MAT_CAD044_PieceBracket_Inner", (1.00, 0.50, 0.08), metallic=0.65, roughness=0.30) # 주황황금색(내측 피스브라켓 H-300x305x500)
mat_wale_brk     = make_mat("MAT_CAD044_WaleBracket_CZ128",  (0.92, 0.82, 0.18), metallic=0.65, roughness=0.32) # 띠장 보걸이 삼각 피스브라켓
mat_girder_brace = make_mat("MAT_CAD044_GirderBracing_L90",  (0.75, 0.78, 0.82), metallic=0.60, roughness=0.38) # 주형보 전도방지 L-90x90 브레이싱 & U볼트
mat_work_opening = make_mat("MAT_CAD044_WorkOpening_Rail",   (0.98, 0.82, 0.05), metallic=0.35, roughness=0.40) # 작업구(4.0x4.0) 안전난간 및 보강틀
mat_wale_h300    = make_mat("MAT_CAD044_Wale_RealH300",      (0.76, 0.49, 0.12), metallic=0.58, roughness=0.35) # 띠장 H-300x305x15x15 실단면
mat_strut_s1     = make_mat("MAT_CAD044_Strut_Pipe406",      (0.88, 0.68, 0.14), metallic=0.55, roughness=0.35) # 강관버팀보 Ø406.4
mat_screw_jack   = make_mat("MAT_CAD044_ScrewJack_Hardware", (0.92, 0.25, 0.18), metallic=0.70, roughness=0.28) # 스크류잭/선행하중잭 및 화타
mat_channel_380  = make_mat("MAT_CAD044_Channel_C380",       (0.20, 0.76, 0.42), metallic=0.50, roughness=0.38) # 전도방지 2-ㄷ380x100x10.5x16

# ==============================================================================
# 2. 3D 형상 생성 헬퍼 함수 (실제 H형강 단면, 삼각 피스브라켓, 복공판, 테셀레이션)
# ==============================================================================
def create_mesh_obj(name, verts, faces, mat, col):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    if mat:
        obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj

def add_box_segment_3d(verts, faces, p1, p2, z_bot, z_top, width):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 1e-4:
        return
    nx, ny = -dy / L * (width * 0.5), dx / L * (width * 0.5)
    base = len(verts)
    verts.extend([
        (p1[0] - nx, p1[1] - ny, z_bot),
        (p1[0] + nx, p1[1] + ny, z_bot),
        (p1[0] + nx, p1[1] + ny, z_top),
        (p1[0] - nx, p1[1] - ny, z_top),
        (p2[0] - nx, p2[1] - ny, z_bot),
        (p2[0] + nx, p2[1] + ny, z_bot),
        (p2[0] + nx, p2[1] + ny, z_top),
        (p2[0] - nx, p2[1] - ny, z_top),
    ])
    faces.extend([
        (base+0, base+1, base+2, base+3),
        (base+4, base+7, base+6, base+5),
        (base+0, base+4, base+5, base+1),
        (base+1, base+5, base+6, base+2),
        (base+2, base+6, base+7, base+3),
        (base+3, base+7, base+4, base+0),
    ])

def add_h_beam_horizontal(verts, faces, p1, p2, z_bot, z_top, B=0.30, tf=0.024, tw=0.014):
    """수평 H형강(주형보 H-700x300, 내측주형지지보 H-440x300, 외측주형지지보/띠장 H-300x305) 실단면 생성"""
    # 하부 플랜지 (Bottom Flange)
    add_box_segment_3d(verts, faces, p1, p2, z_bot, z_bot + tf, B)
    # 상부 플랜지 (Top Flange)
    add_box_segment_3d(verts, faces, p1, p2, z_top - tf, z_top, B)
    # 복부 웨브 (Web)
    if z_top - z_bot > 2.0 * tf + 0.005:
        add_box_segment_3d(verts, faces, p1, p2, z_bot + tf, z_top - tf, tw)

def add_h_beam_vertical(verts, faces, cx, cy, rot_deg, z_bot, z_top, B=0.30, H=0.30, tf=0.015, tw=0.012):
    """수직 H형강(엄지말뚝 및 중간말뚝) 실단면 생성"""
    rad = math.radians(rot_deg)
    ux, uy = math.cos(rad), math.sin(rad)
    vx, vy = -uy, ux
    def pt(lx, ly):
        return (cx + lx * ux + ly * vx, cy + lx * uy + ly * vy)
    # 좌/우 플랜지 + 중앙 웨브
    add_box_segment_3d(verts, faces, pt(-H*0.5, -B*0.5), pt(-H*0.5, B*0.5), z_bot, z_top, tf)
    add_box_segment_3d(verts, faces, pt( H*0.5, -B*0.5), pt( H*0.5, B*0.5), z_bot, z_top, tf)
    add_box_segment_3d(verts, faces, pt(-H*0.5 + tf*0.5, 0.0), pt(H*0.5 - tf*0.5, 0.0), z_bot, z_top, tw)

def add_piece_bracket_3d(verts, faces, px, py, dir_x, dir_y, z_bot, z_top, length=0.40, width=0.30):
    """
    엄지말뚝/중간말뚝 부착형 피스브라켓 (H-300x305x15x15 브라켓 + 삼각 보강 스티프너 + 배면 볼트판):
    - (px, py)에서 (dir_x, dir_y) 방향으로 length만큼 돌출
    - 상단 수평 받침 플랜지 + 배면 수직 접합판 + 중앙 사선 삼각 웨브 + 좌우 사선 리브
    """
    p_start = (px, py)
    p_end   = (px + dir_x * length, py + dir_y * length)
    tf = 0.022
    # 1) 상단 수평 받침 플랜지 판 (Top Bearing Plate)
    add_box_segment_3d(verts, faces, p_start, p_end, z_top - tf, z_top, width)
    # 2) 배면 기둥 밀착 수직 엔드플레이트 (Back Endplate with Bolt Margin)
    p_back = (px + dir_x * 0.025, py + dir_y * 0.025)
    add_box_segment_3d(verts, faces, p_start, p_back, z_bot, z_top, width)
    # 3) 삼각 헌치 웨브 & 좌우 보강 스티프너 (Triangular Web Haunch)
    nx, ny = -dir_y * (width * 0.42), dir_x * (width * 0.42)
    for off_x, off_y, thk in [(0.0, 0.0, 0.018), (-nx, -ny, 0.014), (nx, ny, 0.014)]:
        tx, ty = -dir_y * (thk * 0.5), dir_x * (thk * 0.5)
        b = len(verts)
        verts.extend([
            (px + off_x - tx, py + off_y - ty, z_bot),
            (px + off_x + tx, py + off_y + ty, z_bot),
            (px + off_x + tx, py + off_y + ty, z_top - tf),
            (px + off_x - tx, py + off_y - ty, z_top - tf),
            (p_end[0] + off_x - tx, p_end[1] + off_y - ty, z_top - tf - 0.05),
            (p_end[0] + off_x + tx, p_end[1] + off_y + ty, z_top - tf - 0.05),
            (p_end[0] + off_x + tx, p_end[1] + off_y + ty, z_top - tf),
            (p_end[0] + off_x - tx, p_end[1] + off_y - ty, z_top - tf),
        ])
        faces.extend([
            (b+0, b+1, b+2, b+3),
            (b+4, b+7, b+6, b+5),
            (b+0, b+4, b+5, b+1),
            (b+1, b+5, b+6, b+2),
            (b+2, b+6, b+7, b+3),
            (b+3, b+7, b+4, b+0),
        ])

def add_pipe_segment_3d(verts, faces, p1, p2, z_lvl, radius=0.2032, n_seg=12):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 1e-4:
        return
    nx, ny = -dy / L, dx / L
    base = len(verts)
    for end_pt in (p1, p2):
        for k in range(n_seg):
            ang = 2.0 * math.pi * k / n_seg
            ca, sa = math.cos(ang), math.sin(ang)
            verts.append((end_pt[0] + nx * radius * ca, end_pt[1] + ny * radius * ca, z_lvl + radius * sa))
    for k in range(n_seg):
        k_next = (k + 1) % n_seg
        faces.append((base + k, base + k_next, base + n_seg + k_next, base + n_seg + k))
    faces.append(tuple(base + k for k in range(n_seg - 1, -1, -1)))
    faces.append(tuple(base + n_seg + k for k in range(n_seg)))

def add_polygon_slab_bm(verts, faces, poly_2d, z_bot, z_top):
    if len(poly_2d) < 3:
        return
    bm = bmesh.new()
    b_verts = [bm.verts.new((pt[0], pt[1], z_bot)) for pt in poly_2d]
    try:
        f_bot = bm.faces.new(b_verts)
    except:
        bm.free()
        return
    bmesh.ops.triangulate(bm, faces=[f_bot])
    res = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    ext_verts = [g for g in res['geom'] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=ext_verts, vec=(0.0, 0.0, z_top - z_bot))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    base = len(verts)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        verts.append((v.co.x, v.co.y, v.co.z))
    for f in bm.faces:
        faces.append(tuple(base + v.index for v in f.verts))
    bm.free()

def point_in_poly_2d(px, py, poly):
    inside = False
    n_p = len(poly)
    j = n_p - 1
    for k in range(n_p):
        xi, yi = poly[k][0], poly[k][1]
        xj, yj = poly[j][0], poly[j][1]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = k
    return inside

# ==============================================================================
# 3. 컬렉션 준비: 01A_가시설_복공판_주형보_주형지지보_피스브라켓_상세 (106_Station_BIM_CAD044 산하)
# ==============================================================================
root_col = bpy.data.collections.get("106_Station_BIM_CAD044")
if not root_col:
    root_col = bpy.context.scene.collection

col_decking_name = "01A_가시설_복공판_주형보_주형지지보_피스브라켓_상세"
col_decking = bpy.data.collections.get(col_decking_name)
if not col_decking:
    col_decking = bpy.data.collections.new(col_decking_name)
    root_col.children.link(col_decking)
col_decking.hide_viewport = False
col_decking.hide_render = False

for o in list(col_decking.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ==============================================================================
# 4. CAD 복공평면도(X: 0..205, Y: 20..100)에서 주형보·주형지지보·제작복공·작업구 정밀 추출
# ==============================================================================

# 4-1. 주형보 (Main Deck Girders: CE-LINE-STEL 513 segments -> 254 girders)
line_segs = []
for e in entities:
    if e['layer'] == 'CE-LINE-STEL' and e['type'] in ('LWPOLYLINE', 'LINE') and len(e['x']) >= 2:
        mx, my = sum(e['x'])/len(e['x']), sum(e['y'])/len(e['y'])
        if 0 <= mx <= 205 and 20 <= my <= 100:
            pts = [to_loc_deck(x, y) for x, y in zip(e['x'], e['y'])]
            for k in range(len(pts) - 1):
                p1, p2 = pts[k], pts[k+1]
                if p1[1] > p2[1] or (abs(p1[1] - p2[1]) < 0.2 and p1[0] > p2[0]):
                    p1, p2 = p2, p1
                line_segs.append((p1, p2))

line_segs.sort(key=lambda s: (round(0.5*(s[0][1]+s[1][1]), 0), 0.5*(s[0][0]+s[1][0])))
used_l = [False] * len(line_segs)
main_girders = []

for idx1 in range(len(line_segs)):
    if used_l[idx1]:
        continue
    p1a, p2a = line_segs[idx1]
    mxa, mya = 0.5*(p1a[0]+p2a[0]), 0.5*(p1a[1]+p2a[1])
    la = math.hypot(p2a[0]-p1a[0], p2a[1]-p1a[1])
    best_j, best_d = None, 999.0
    for idx2 in range(idx1 + 1, len(line_segs)):
        if used_l[idx2]:
            continue
        p1b, p2b = line_segs[idx2]
        mxb, myb = 0.5*(p1b[0]+p2b[0]), 0.5*(p1b[1]+p2b[1])
        lb = math.hypot(p2b[0]-p1b[0], p2b[1]-p1b[1])
        d_mid = math.hypot(mxa - mxb, mya - myb)
        if 0.20 <= d_mid <= 0.45 and abs(la - lb) < 4.5:
            if d_mid < best_d:
                best_d = d_mid
                best_j = idx2
    if best_j is not None:
        used_l[idx1] = True
        used_l[best_j] = True
        p1b, p2b = line_segs[best_j]
        c1 = (0.5*(p1a[0]+p1b[0]), 0.5*(p1a[1]+p1b[1]))
        c2 = (0.5*(p2a[0]+p2b[0]), 0.5*(p2a[1]+p2b[1]))
        main_girders.append((c1, c2))

mg_h700_v, mg_h700_f = [], []
mg_cut_v, mg_cut_f = [], []
mg_h440_v, mg_h440_f = [], []
brace_v, brace_f = [], []

for c1, c2 in main_girders:
    mx, my = 0.5*(c1[0]+c2[0]), 0.5*(c1[1]+c2[1])
    L = math.hypot(c2[0]-c1[0], c2[1]-c1[1])
    # 진입부 복공(서북측 X<16 & Y>21 또는 동남측 X>112)은 H-440x300x11x18, 본선 복공은 H-700x300x13x24
    if (mx < 16.0 and my > 21.0) or mx > 113.5 or L < 3.5:
        add_h_beam_horizontal(mg_h440_v, mg_h440_f, c1, c2, -0.64, -0.20, B=0.30, tf=0.018, tw=0.011)
    elif (25.5 <= mx <= 36.5) or (mx < 11.0 and my < 4.5):
        # 계단식 절개 투시창(Stepped Cutaway): X=25.5~36.5m 및 서남측 우각부 코너는 하부 주형지지보·피스브라켓·띠장·우각부버팀보가 바로 보이도록 분리!
        add_h_beam_horizontal(mg_cut_v, mg_cut_f, c1, c2, -0.90, -0.20, B=0.30, tf=0.024, tw=0.013)
    else:
        add_h_beam_horizontal(mg_h700_v, mg_h700_f, c1, c2, -0.90, -0.20, B=0.30, tf=0.024, tw=0.013)

# 주형보 간 전도방지 브레이싱 (보강재 L-90x90x10 / 수평연결재, Z=-0.55m, 3.0m 간격 종방향 라인)
mg_sorted = sorted([g for g in main_girders if math.hypot(g[1][0]-g[0][0], g[1][1]-g[0][1]) > 5.0], key=lambda g: (round(0.5*(g[0][1]+g[1][1])/8.0), 0.5*(g[0][0]+g[1][0])))
for k in range(len(mg_sorted) - 1):
    g1, g2 = mg_sorted[k], mg_sorted[k+1]
    for t_frac in (0.25, 0.50, 0.75):
        q1 = (g1[0][0]*(1-t_frac) + g1[1][0]*t_frac, g1[0][1]*(1-t_frac) + g1[1][1]*t_frac)
        q2 = (g2[0][0]*(1-t_frac) + g2[1][0]*t_frac, g2[0][1]*(1-t_frac) + g2[1][1]*t_frac)
        mx_q = 0.5 * (q1[0] + q2[0])
        if 25.0 <= mx_q <= 37.0:
            continue
        dist_q = math.hypot(q2[0]-q1[0], q2[1]-q1[1])
        if 1.5 <= dist_q <= 2.4 and abs(q2[1]-q1[1]) < 0.6:
            add_box_segment_3d(brace_v, brace_f, q1, q2, -0.60, -0.51, 0.09)

create_mesh_obj(f"01A_주형보_본선구간_H700x300x13x24_{len(main_girders)}EA", mg_h700_v, mg_h700_f, mat_main_girder, col_decking)
obj_mg_cut = create_mesh_obj("01A_주형보_하부지지보투시창_절개구간_ON_OFF용", mg_cut_v, mg_cut_f, mat_main_girder, col_decking)
obj_mg_cut.hide_viewport = True
create_mesh_obj("01B_주형보_진입부복공_H440x300x11x18", mg_h440_v, mg_h440_f, mat_ramp_girder, col_decking)
create_mesh_obj("01C_주형보_전도방지보강재_L90x90x10_브레이싱", brace_v, brace_f, mat_girder_brace, col_decking)

# 4-2. 내측 주형지지보 (Inner Girder Support Beams: 2열 x H-440x300x11x18, Z=-1.34m ~ -0.90m)
#      및 제작복공(A1~A17) / 작업구(4.0x4.0m, 3개소) 추출
base_segs = []
custom_deck_polys = []
work_opening_polys = []

for e in entities:
    if e['layer'] == 'CE-BASE-STEL' and e['type'] in ('LWPOLYLINE', 'LINE') and len(e['x']) >= 2:
        mx, my = sum(e['x'])/len(e['x']), sum(e['y'])/len(e['y'])
        if 0 <= mx <= 205 and 20 <= my <= 100:
            pts = [to_loc_deck(x, y) for x, y in zip(e['x'], e['y'])]
            is_closed = (e['closed'] == 1) or (len(pts) >= 4 and math.hypot(pts[0][0]-pts[-1][0], pts[0][1]-pts[-1][1]) < 0.05)
            if is_closed or len(pts) >= 4:
                dx_p = max(p[0] for p in pts) - min(p[0] for p in pts)
                dy_p = max(p[1] for p in pts) - min(p[1] for p in pts)
                if len(pts) in (4, 5) and 3.6 <= dx_p <= 4.5 and 3.6 <= dy_p <= 4.5:
                    work_opening_polys.append(pts[:4])
                else:
                    custom_deck_polys.append(pts)
            else:
                p1, p2 = pts[0], pts[-1]
                if p1[0] > p2[0]:
                    p1, p2 = p2, p1
                base_segs.append((p1, p2))

# 동측 작업구(X=131.6-26.8=104.8, Y=58.4-52.0=6.4)도 4.0x4.0m 추가 확인
if len(work_opening_polys) < 3:
    work_opening_polys.append([(102.8, 4.8), (106.8, 5.1), (106.5, 9.1), (102.5, 8.8)])

base_segs.sort(key=lambda s: (round(0.5*(s[0][0]+s[1][0]), 0), 0.5*(s[0][1]+s[1][1])))
used_b = [False] * len(base_segs)
inner_support_beams = []

for idx1 in range(len(base_segs)):
    if used_b[idx1]:
        continue
    p1a, p2a = base_segs[idx1]
    mxa, mya = 0.5*(p1a[0]+p2a[0]), 0.5*(p1a[1]+p2a[1])
    la = math.hypot(p2a[0]-p1a[0], p2a[1]-p1a[1])
    best_j, best_d = None, 999.0
    for idx2 in range(idx1 + 1, len(base_segs)):
        if used_b[idx2]:
            continue
        p1b, p2b = base_segs[idx2]
        mxb, myb = 0.5*(p1b[0]+p2b[0]), 0.5*(p1b[1]+p2b[1])
        lb = math.hypot(p2b[0]-p1b[0], p2b[1]-p1b[1])
        d_mid = math.hypot(mxa - mxb, mya - myb)
        if 0.20 <= d_mid <= 0.40 and abs(la - lb) < 1.5:
            if d_mid < best_d:
                best_d = d_mid
                best_j = idx2
    if best_j is not None:
        used_b[idx1] = True
        used_b[best_j] = True
        p1b, p2b = base_segs[best_j]
        c1 = (0.5*(p1a[0]+p1b[0]), 0.5*(p1a[1]+p1b[1]))
        c2 = (0.5*(p2a[0]+p2b[0]), 0.5*(p2a[1]+p2b[1]))
        inner_support_beams.append((c1, c2))

in_sup_v, in_sup_f = [], []
for c1, c2 in inner_support_beams:
    add_h_beam_horizontal(in_sup_v, in_sup_f, c1, c2, -1.34, -0.90, B=0.30, tf=0.018, tw=0.011)

create_mesh_obj(f"02A_내측주형지지보_2열_H440x300x11x18_{len(inner_support_beams)}구간", in_sup_v, in_sup_f, mat_inner_sup, col_decking)

# 4-3. 외측 주형지지보 (Outer Girder Support Beam: H-300x305x15x15, Z=-1.20m ~ -0.90m)
#      복공평면도의 CE-SYMB-STEL 외곽 루프(`outer_wale_loop`와 동일 평면 궤적)를 따라 엄지말뚝 내측 피스브라켓 상부에 안착
outer_loop = cad['outer_wale_loop']
out_sup_v, out_sup_f = [], []
for k in range(len(outer_loop) - 1):
    p1, p2 = outer_loop[k], outer_loop[k+1]
    add_h_beam_horizontal(out_sup_v, out_sup_f, p1, p2, -1.20, -0.90, B=0.305, tf=0.015, tw=0.015)

create_mesh_obj("02B_외측주형지지보_엄지말뚝상부_H300x305x15x15", out_sup_v, out_sup_f, mat_outer_sup, col_decking)

# ==============================================================================
# 5. 피스브라켓 (Piece Brackets) 3종 정밀 구현:
#    - 03A_외측피스브라켓: 외벽 엄지말뚝 243본 내측면 부착 (H-300x305x15x15 x L=400mm, Z=-1.60m ~ -1.20m)
#    - 03B_내측피스브라켓: 중간말뚝 122본 좌·우 양측 부착 (H-300x305x15x15 x L=500mm, 244EA, Z=-1.84m ~ -1.34m)
#    - 03C_띠장지지_보걸이피스브라켓: 외벽 엄지말뚝 243본 1단 띠장 직하부 삼각 브라켓 (CZSECM128, Z=-2.70m ~ -2.10m)
# ==============================================================================
pbrk_out_v, pbrk_out_f = [], []
pbrk_wale_v, pbrk_wale_f = [], []

# 정거장 중심선(Y ≈ 12.0m, X ≈ 58.0m) 방향으로 돌출되도록 각 엄지말뚝의 내측 법선 벡터 산정
for wp in cad['wall_piles']:
    if wp['group'] != 'OUTER':
        continue
    wx, wy = wp['x'], wp['y']
    # 가장 가까운 outer_wale_loop 선분까지의 방향을 내측 방향으로 사용
    best_dx, best_dy, best_d = 0.0, 1.0, 999.0
    for k in range(len(outer_loop) - 1):
        x1, y1 = outer_loop[k]
        x2, y2 = outer_loop[k+1]
        ddx, ddy = x2 - x1, y2 - y1
        l2 = ddx*ddx + ddy*ddy
        t = max(0.0, min(1.0, ((wx - x1)*ddx + (wy - y1)*ddy) / (l2 if l2 > 1e-8 else 1.0)))
        qx, qy = x1 + t*ddx, y1 + t*ddy
        d = math.hypot(qx - wx, qy - wy)
        if d < best_d:
            best_d = d
            if d > 1e-4:
                best_dx, best_dy = (qx - wx)/d, (qy - wy)/d
            else:
                # 정거장 내부(58, 12)를 향하는 법선
                nx, ny = -ddy / math.sqrt(l2), ddx / math.sqrt(l2)
                if nx*(58.0 - wx) + ny*(12.0 - wy) < 0:
                    nx, ny = -nx, -ny
                best_dx, best_dy = nx, ny
    # 1) 외측 주형지지보 받침용 외측피스브라켓 (Z=-1.60m ~ -1.20m, L=0.40m)
    add_piece_bracket_3d(pbrk_out_v, pbrk_out_f, wx, wy, best_dx, best_dy, -1.60, -1.20, length=0.42, width=0.30)
    # 2) 1단 띠장(Z=-1.95m, 하단 Z=-2.10m) 받침용 보걸이 삼각 피스브라켓 (Z=-2.65m ~ -2.10m, L=0.42m)
    add_piece_bracket_3d(pbrk_wale_v, pbrk_wale_f, wx, wy, best_dx, best_dy, -2.65, -2.10, length=0.42, width=0.28)

pbrk_in_v, pbrk_in_f = [], []
cp_clamp_v, cp_clamp_f = [], []

for cp in cad['center_piles']:
    cx, cy = cp['x'], cp['y']
    # 중간말뚝 열은 종방향(X축 약 -4도 기울기)으로 배열되므로, 횡방향(남·북 양측, Y축 방향)으로 내측피스브라켓 2개씩 돌출!
    ang_rad = math.radians(-4.2)
    dir_nx, dir_ny = -math.sin(ang_rad), math.cos(ang_rad)
    # 북측(+dir_n) 및 남측(-dir_n) 양측에 내측피스브라켓(H-300x305x15x15 x L=500mm, Z=-1.84m ~ -1.34m) 장착
    add_piece_bracket_3d(pbrk_in_v, pbrk_in_f, cx + dir_nx*0.14, cy + dir_ny*0.14,  dir_nx,  dir_ny, -1.84, -1.34, length=0.46, width=0.30)
    add_piece_bracket_3d(pbrk_in_v, pbrk_in_f, cx - dir_nx*0.14, cy - dir_ny*0.14, -dir_nx, -dir_ny, -1.84, -1.34, length=0.46, width=0.30)
    # 1단 전도방지 ㄷ형강(Z=-2.23m) 지지용 브라켓 및 U-볼트 클램프 (CZNOCR70)
    add_piece_bracket_3d(cp_clamp_v, cp_clamp_f, cx + dir_nx*0.14, cy + dir_ny*0.14,  dir_nx,  dir_ny, -2.72, -2.42, length=0.28, width=0.24)
    add_piece_bracket_3d(cp_clamp_v, cp_clamp_f, cx - dir_nx*0.14, cy - dir_ny*0.14, -dir_nx, -dir_ny, -2.72, -2.42, length=0.28, width=0.24)

create_mesh_obj("03A_외측피스브라켓_외측주형지지보용_H300x305x400_243EA", pbrk_out_v, pbrk_out_f, mat_piece_brk_o, col_decking)
create_mesh_obj("03B_내측피스브라켓_내측주형지지보용_H300x305x500_244EA", pbrk_in_v, pbrk_in_f, mat_piece_brk_i, col_decking)
create_mesh_obj("03C_띠장보걸이_삼각피스브라켓_CZSECM128_243EA", pbrk_wale_v, pbrk_wale_f, mat_wale_brk, col_decking)
create_mesh_obj("03D_중간말뚝_ㄷ형강지지브라켓_CZNOCR70_244EA", cp_clamp_v, cp_clamp_f, mat_girder_brace, col_decking)

# ==============================================================================
# 6. 복공판 (Steel Deck Plates: H형 2,000 x 1,000 x 200mm, Z=-0.20m ~ 0.00m)
#    + 제작복공 (A1 ~ A17) + 작업구 (4.0m x 4.0m, 3개소 + 안전난간)
#    ※ 하부 주형보·주형지지보·피스브라켓·띠장이 한눈에 보이도록:
#       - 04A_복공판_H형_2000x1000x200_설치구간 (서측·동측·북측·작업구 주변 실제 개별 패널 그리드 표시)
#       - 04B_복공판_중앙투시개방구간_ON_OFF용 (중앙부 절개 구간 복공판 — 기본 숨김 처리하여 내부 부재 투시!)
# ==============================================================================
deck_vis_v, deck_vis_f = [], []
deck_cut_v, deck_cut_f = [], []

# 각 주형보(main_girders, 2.0m 간격) 스팬을 따라 폭 1.0m x 길이 2.0m x 두께 0.20m 개별 복공판 배치!
for c1, c2 in main_girders:
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    L = math.hypot(dx, dy)
    if L < 2.0:
        continue
    ux, uy = dx / L, dy / L           # 주형보 길이 방향 (1.0m 단위 분할)
    nx, ny = -uy, ux                  # 주형보 직각 방향 (패널 길이 2.0m = ±0.985m)
    n_panels = int(L / 1.00)
    for k in range(n_panels):
        s0 = k * 1.00 + 0.015
        s1 = (k + 1) * 1.00 - 0.015
        if s1 > L:
            break
        q1 = (c1[0] + ux * s0, c1[1] + uy * s0)
        q2 = (c1[0] + ux * s1, c1[1] + uy * s1)
        px_mid, py_mid = 0.5*(q1[0]+q2[0]), 0.5*(q1[1]+q2[1])
        # 작업구(4.0x4.0m) 3개소 내부는 복공판 개구부로 비워둠!
        in_opening = False
        for op_poly in work_opening_polys:
            if point_in_poly_2d(px_mid, py_mid, op_poly):
                in_opening = True
                break
        if in_opening:
            continue
        # 전폭 절개 투시창(X=14.5 ~ 43.5m 및 X=54.0 ~ 78.0m 전폭 + 서남측 우각부 X<14.5 & Y<4.5m)을 열어
        # 외벽 엄지말뚝·외측주형지지보·외측피스브라켓·1단띠장·보걸이브라켓·우각부버팀보·내측주형지지보가 한눈에 보이도록 구성!
        is_cutaway = (14.5 <= px_mid <= 43.5) or (54.0 <= px_mid <= 78.0) or (px_mid < 14.5 and py_mid < 4.5)
        if is_cutaway:
            add_box_segment_3d(deck_cut_v, deck_cut_f, q1, q2, -0.20, 0.00, 1.96)
        else:
            add_box_segment_3d(deck_vis_v, deck_vis_f, q1, q2, -0.20, 0.00, 1.96)

# 제작복공 (A1 ~ A17 이형 복공판 구간)도 투시창 구간은 절개 오브젝트에 분리!
cust_v, cust_f = [], []
for cpoly in custom_deck_polys:
    cx_p = sum(p[0] for p in cpoly) / len(cpoly)
    cy_p = sum(p[1] for p in cpoly) / len(cpoly)
    if (14.5 <= cx_p <= 43.5) or (54.0 <= cx_p <= 78.0) or (cx_p < 14.5 and cy_p < 4.5):
        add_polygon_slab_bm(deck_cut_v, deck_cut_f, cpoly, -0.20, 0.00)
    else:
        add_polygon_slab_bm(cust_v, cust_f, cpoly, -0.20, 0.00)

obj_deck_vis = create_mesh_obj("04A_복공판_H형_2000x1000x200_개별패널", deck_vis_v, deck_vis_f, mat_deck_plate, col_decking)
obj_deck_cut = create_mesh_obj("04B_복공판_중앙하부투시창_절개구간_ON_OFF용", deck_cut_v, deck_cut_f, mat_deck_plate, col_decking)
obj_deck_cut.hide_viewport = True  # 기본 상태에서 하부 주형보·주형지지보·피스브라켓·띠장·1단버팀보가 선명하게 보이도록 절개창 오픈!
create_mesh_obj(f"04C_제작복공판_이형접합부_A1_to_A17_{len(custom_deck_polys)}개소", cust_v, cust_f, mat_deck_custom, col_decking)

# 작업구 (4.0m x 4.0m, 3개소) 테두리 보강보 및 지상 안전난간 (Note 1 & 4 반영)
wo_v, wo_f = [], []
for op_poly in work_opening_polys:
    n_p = len(op_poly)
    for k in range(n_p):
        p1, p2 = op_poly[k], op_poly[(k + 1) % n_p]
        # 개구부 하부 주형보 보강 테두리 H형강 (-0.90m ~ 0.05m)
        add_box_segment_3d(wo_v, wo_f, p1, p2, -0.90, 0.05, 0.25)
        # 지상 안전난간 상부/중간 난간대 (Z=+0.55m, +1.10m) 및 코너 기둥
        add_box_segment_3d(wo_v, wo_f, p1, p2, 0.52, 0.58, 0.06)
        add_box_segment_3d(wo_v, wo_f, p1, p2, 1.05, 1.12, 0.06)
        add_box_segment_3d(wo_v, wo_f, p1, (p1[0]+0.08, p1[1]+0.08), 0.00, 1.15, 0.08)

create_mesh_obj("04D_복공작업구_4x4m_3개소_보강틀및안전난간", wo_v, wo_f, mat_work_opening, col_decking)

# ==============================================================================
# 7. 1단 띠장(Wale, H-300x305x15x15 실단면), 1단 버팀보(S1), 스크류잭/화타, 우각부 대각 ㄷ형강 정밀 업그레이드
#    - 복공판(-0.20~0.00m) -> 주형보(-0.90~-0.20m) -> 주형지지보(-1.34~-0.90m) -> 피스브라켓(-1.84~-1.20m)
#      직하부인 Z = -1.95m에 1단 띠장·버팀보·스크류잭·화타·우각부 대각 ㄷ형강 배치!
#    - 01_가시설_단별해체_버팀보_띠장_ㄷ형강 내 모든 오브젝트의 애니메이션 키프레임을 제거하여
#      2단~11단이 절대 저절로 켜지지 않도록 완벽 고정!
# ==============================================================================
col_tiers = bpy.data.collections.get("01_가시설_단별해체_버팀보_띠장_ㄷ형강")
if col_tiers:
    for o in col_tiers.objects:
        o.animation_data_clear()
        is_tier1 = ("01단_S1" in o.name)
        o.hide_viewport = not is_tier1
        o.hide_render   = not is_tier1

# CAD 평면도(B1~B3)의 우각부 대각 ㄷ형강(CE-BASE-STEL 대각 4선 번들 5개소) 추가 추출
corner_channels_b1b3 = [
    [(106.53, 21.11), (109.71, 24.93)],
    [(113.12,  6.05), (110.97,  7.84)],
    [(106.98, -1.33), (104.83,  0.46)],
    [(  5.28, -1.61), (  8.85,  1.38)],
    [(  6.58, 18.90), (  9.73, 15.14)],
]

z_s1 = -1.95
pv_b1b3 = cad['plan_views']['B1_B3']

# 7-1. 1단 띠장 (H-300x305x15x15 실단면, Z = -2.10m ~ -1.80m)
wv1, wf1 = [], []
for w_poly in pv_b1b3['wales']:
    for k in range(len(w_poly) - 1):
        add_h_beam_horizontal(wv1, wf1, w_poly[k], w_poly[k+1], z_s1 - 0.15, z_s1 + 0.15, B=0.305, tf=0.015, tw=0.015)

# 7-2. 1단 버팀보 (Ø406.4x7t 강관버팀보 & 우각부 코너강관버팀보 & Y-Strut, Z = -1.95m)
sv1, sf1 = [], []
jv1, jf1 = [], [] # 버팀보 양단 스크류잭(CZDIMA98) 및 플랜지 조인트
for s in pv_b1b3['struts']:
    p1, p2 = s['p1'], s['p2']
    if s['kind'] == 'Y_TIE':
        add_h_beam_horizontal(sv1, sf1, p1, p2, z_s1 - 0.125, z_s1 + 0.125, B=0.25, tf=0.014, tw=0.012)
    else:
        add_pipe_segment_3d(sv1, sf1, p1, p2, z_s1, radius=0.2032, n_seg=12)
        # 양단 스크류잭/선행하중잭 칼라 (직경 0.48m 플랜지 링)
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        L = math.hypot(dx, dy)
        if L > 1.2:
            ux, uy = dx / L, dy / L
            add_pipe_segment_3d(jv1, jf1, p1, (p1[0]+ux*0.45, p1[1]+uy*0.45), z_s1, radius=0.24, n_seg=12)
            add_pipe_segment_3d(jv1, jf1, (p2[0]-ux*0.45, p2[1]-uy*0.45), p2, z_s1, radius=0.24, n_seg=12)

# 7-3. 1단 화타 (우각부 사각 버팀보 받침 브라켓 CZSECM120 / CZDIMA24 / CZDIMA40)
bv1, bf1 = [], []
for b in pv_b1b3['brackets']:
    rad = math.radians(b['rot'])
    ux, uy = math.cos(rad), math.sin(rad)
    vx, vy = -uy, ux
    add_piece_bracket_3d(bv1, bf1, b['x'], b['y'], -vx, -vy, z_s1 - 0.18, z_s1 + 0.18, length=0.42, width=0.44)

# 7-4. 1단 전도방지 ㄷ형강 (2-ㄷ380x100x10.5x16, 종방향 + 우각부 대각 보강 5개소, Z = -2.42m ~ -2.04m)
cv1, cf1 = [], []
all_channels_s1 = list(pv_b1b3['channels']) + corner_channels_b1b3
for c_poly in all_channels_s1:
    for k in range(len(c_poly) - 1):
        p1, p2 = c_poly[k], c_poly[k+1]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        L = math.hypot(dx, dy)
        if L < 1e-4:
            continue
        nx, ny = -dy / L * 0.21, dx / L * 0.21
        add_box_segment_3d(cv1, cf1, (p1[0]-nx, p1[1]-ny), (p2[0]-nx, p2[1]-ny), z_s1 - 0.48, z_s1 - 0.10, 0.10)
        add_box_segment_3d(cv1, cf1, (p1[0]+nx, p1[1]+ny), (p2[0]+nx, p2[1]+ny), z_s1 - 0.48, z_s1 - 0.10, 0.10)

if col_tiers:
    create_mesh_obj("버팀보_01단_S1_Z-0.5m_복공하부", sv1, sf1, mat_strut_s1, col_tiers)
    create_mesh_obj("띠장_01단_S1_Z-0.5m_복공하부",   wv1, wf1, mat_wale_h300, col_tiers)
    create_mesh_obj("화타_01단_S1_Z-0.5m_복공하부",   bv1, bf1, mat_screw_jack, col_tiers)
    create_mesh_obj("ㄷ형강_01단_S1_Z-0.5m_복공하부", cv1, cf1, mat_channel_380, col_tiers)
    create_mesh_obj("스크류잭_01단_S1_버팀보단부_134EA", jv1, jf1, mat_screw_jack, col_tiers)

# ==============================================================================
# 8. 초기 1단 굴착 상태(00A_정거장_단계별굴착_원지반토사면_및_단별토류판) 레벨 정합성 업데이트:
#    - 굴착 바닥면: Z = -2.65m (1단 띠장·버팀보·전도방지 ㄷ형강 및 보걸이 피스브라켓 직하부까지 굴착 완료 상태)
#    - 엄지말뚝: Z = -2.65m ~ -0.90m (외측 주형지지보 하단까지 정확히 연결)
#    - 중간말뚝: Z = -2.65m ~ -0.90m (주형보 하단 및 내측 주형지지보 사이에 정확히 맞물림)
#    - 토류판: Z = -2.65m ~ -0.20m (복공판 하단부터 굴착 바닥면까지 흙막이 판 설치)
# ==============================================================================
col_exc = bpy.data.collections.get("00A_정거장_단계별굴착_원지반토사면_및_단별토류판")
if col_exc:
    for o in list(col_exc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    z_exc_floor = -2.65
    ow_loop = cad['outer_wall_loop']
    
    # 8-1. 굴착 바닥면 (Z = -2.65m)
    mat_soil_exc = bpy.data.materials.get("MAT_106_Excavated_Soil_Floor")
    sv_e, sf_e = [], []
    add_polygon_slab_bm(sv_e, sf_e, ow_loop[:-1], z_exc_floor - 0.35, z_exc_floor)
    create_mesh_obj("00A_초기굴착바닥_원지반토사면_Z-2.65m", sv_e, sf_e, mat_soil_exc, col_exc)
    
    # 8-2. 주변 원지반 지표면 (GL 0.0m, 정거장 개착부 중공)
    mat_ground_gl = bpy.data.materials.get("MAT_106_Surrounding_Ground_GL")
    bm_g = bmesh.new()
    outer_box = [(-18.0, -24.0), (134.0, -24.0), (134.0, 44.0), (-18.0, 44.0)]
    v_out = [bm_g.verts.new((p[0], p[1], -0.25)) for p in outer_box]
    v_in  = [bm_g.verts.new((p[0], p[1], -0.25)) for p in ow_loop[:-1]]
    for k in range(4):
        bm_g.edges.new((v_out[k], v_out[(k+1)%4]))
    n_in = len(v_in)
    for k in range(n_in):
        bm_g.edges.new((v_in[k], v_in[(k+1)%n_in]))
    bmesh.ops.triangle_fill(bm_g, use_beauty=True, use_dissolve=False, edges=bm_g.edges[:])
    to_del = []
    for f in bm_g.faces:
        c = f.calc_center_median()
        if point_in_poly_2d(c.x, c.y, ow_loop[:-1]):
            to_del.append(f)
    bmesh.ops.delete(bm_g, geom=to_del, context='FACES_ONLY')
    res_g = bmesh.ops.extrude_face_region(bm_g, geom=bm_g.faces[:])
    ext_vg = [g for g in res_g['geom'] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm_g, verts=ext_vg, vec=(0.0, 0.0, 0.25))
    bmesh.ops.recalc_face_normals(bm_g, faces=bm_g.faces[:])
    gv, gf = [], []
    bm_g.verts.ensure_lookup_table()
    for v in bm_g.verts:
        gv.append((v.co.x, v.co.y, v.co.z))
    for f in bm_g.faces:
        gf.append(tuple(v.index for v in f.verts))
    bm_g.free()
    create_mesh_obj("00B_주변원지반_지표면_GL0.0m", gv, gf, mat_ground_gl, col_exc)
    
    # 8-3. 초기 굴착 노출 구간 토류판 (Z = -2.65m ~ -0.20m)
    mat_lag = bpy.data.materials.get("MAT_CAD044_Lagging")
    lv, lf = [], []
    for k in range(len(ow_loop) - 1):
        add_box_segment_3d(lv, lf, ow_loop[k], ow_loop[k+1], z_exc_floor, -0.20, 0.08)
    create_mesh_obj("03C_토류판_초기굴착구간_GL0_to_Z-2.65m", lv, lf, mat_lag, col_exc)
    
    # 8-4. 외벽 엄지말뚝 노출 구간 (H-300x305x15x15, Z = -2.65m ~ -0.90m)
    mat_hp = bpy.data.materials.get("MAT_CAD044_HPile_Blue")
    hpv, hpf = [], []
    for wp in cad['wall_piles']:
        if wp['group'] == 'OUTER':
            add_h_beam_vertical(hpv, hpf, wp['x'], wp['y'], wp['rot'], z_exc_floor, -0.90, B=0.305, H=0.300)
    create_mesh_obj("02_엄지말뚝_초기굴착노출부_GL0_to_Z-2.65m", hpv, hpf, mat_hp, col_exc)
    
    # 8-5. 중간말뚝 노출 구간 (H-300x300x10x15, 122EA, Z = -2.65m ~ -0.90m 주형보 하단 밀착!)
    mat_cp = bpy.data.materials.get("MAT_CAD044_CPile_Upper_Removable")
    cpv, cpf = [], []
    for cp in cad['center_piles']:
        add_h_beam_vertical(cpv, cpf, cp['x'], cp['y'], cp['rot'], z_exc_floor, -0.90, B=0.300, H=0.300)
    create_mesh_obj("08_중간말뚝_초기굴착노출부_122EA_GL0_to_Z-2.65m", cpv, cpf, mat_cp, col_exc)

# 다른 모든 비-정거장/하부공정 컬렉션 숨김 유지 확인
keep_cols = {
    "106_Station_BIM_CAD044",
    "00_가시설_외벽엄지말뚝_차수_토류판",
    "00A_정거장_단계별굴착_원지반토사면_및_단별토류판",
    "01_가시설_단별해체_버팀보_띠장_ㄷ형강",
    "01A_가시설_복공판_주형보_주형지지보_피스브라켓_상세",
}
for c in bpy.data.collections:
    c.hide_viewport = (c.name not in keep_cols)
    c.hide_render   = (c.name not in keep_cols)

# 카메라 뷰포트를 복공판·주형보·주형지지보·피스브라켓·띠장·1단버팀보가 입체적으로 한눈에 보이는 클로즈업 앵글로 세팅
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'
                    space.shading.show_cavity = True
                    space.shading.cavity_type = 'BOTH'
                    space.shading.show_xray = False
                    r3d = space.region_3d
                    r3d.view_location = Vector((36.0, 8.5, -1.2))
                    r3d.view_rotation = Euler((math.radians(60), 0.0, math.radians(-35))).to_quaternion()
                    r3d.view_distance = 38.0
                    r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=blend_save_path)
print("SUCCESS: Built exact CAD 044_01 3th Deck Plates, Main Girders, Support Beams, Piece Brackets, Wales & Corner Struts!")
