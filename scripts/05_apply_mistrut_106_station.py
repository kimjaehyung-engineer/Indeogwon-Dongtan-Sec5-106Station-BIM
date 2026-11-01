import bpy
import bmesh
import os
import json
import math
from mathutils import Vector, Euler, Matrix

# ==============================================================================
# 인덕원~동탄 5공구 106정거장 가시설 원가·시공성 개선 설계변경:
# [당초] 1단 강관버팀보(S1, Ø406.4) + 1단 띠장(H-300x305) + 1단 전도방지 ㄷ형강 + 스크류잭/화타 삭제!
# [변경] Mistrut(버팀화부재, 건설신기술 제614호 / 철도신기술 2011-0005호) 적용:
#        주형보(I-700x300x13x24) 하부에 Mistrut(MS50/MS80) + 수평 스크류잭 + 전단키 플레이트를 장착하여
#        주형보를 1단 버팀보로 겸용하고, 복공 하단 3.0m 이상의 광활한 무지보 작업공간 확보!
# ==============================================================================

json_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\0d917c24-0c73-469d-af45-411a71b292b9\scratch\cad_044_data.json"
blend_save_path = r"C:\Users\20040178\Desktop\2영역\토스앤\1.설계변경관리\2.인덕원동탄5공구\7.정거장 구조물 원가개선\정거장 가시설도, 구조도\106정거장_가시설_전체구간_3D_BIM.blend"

with open(json_path, 'r', encoding='utf-8') as f:
    cad = json.load(f)

# ==============================================================================
# 1. 재질(Materials) 정의 — Mistrut 핵심 부재별 고시인성 엔지니어링 컬러
# ==============================================================================
def make_mat(name, rgba, metallic=0.55, roughness=0.32, alpha=1.0):
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

mat_ms_body      = make_mat("MAT_Mistrut_Body_MS80_OrangeRed",  (0.96, 0.26, 0.08), metallic=0.65, roughness=0.28) # Mistrut 주강 본체 (선명한 안전 오렌지레드)
mat_ms_plate     = make_mat("MAT_Mistrut_ShearPlate_Gold",      (0.95, 0.76, 0.12), metallic=0.70, roughness=0.26) # 설치 플레이트(L-428x300x14) + 전단키 + M22 볼트
mat_ms_jack      = make_mat("MAT_Mistrut_ScrewJack_Chrome",     (0.88, 0.90, 0.94), metallic=0.85, roughness=0.20) # 수평 스크류잭 (고강도 크롬/강재)
mat_ms_reinf_w   = make_mat("MAT_Mistrut_ReinfWale_CyanBlue",   (0.10, 0.72, 0.88), metallic=0.58, roughness=0.32) # 외측/작업구 보강띠장 (H-300x305x15x15)
mat_ms_angle     = make_mat("MAT_Mistrut_BraceAngle_LimeGreen", (0.22, 0.85, 0.38), metallic=0.55, roughness=0.34) # 내측 주형지지보 보강앵글 (L-100x100x10) 및 보강빔
mat_ms_stiff     = make_mat("MAT_Mistrut_WebStiffener_Yellow",  (0.98, 0.84, 0.15), metallic=0.62, roughness=0.30) # 주형보/띠장 웨브 보강 스티프너

# ==============================================================================
# 2. 1단 버팀보(S1)·1단 띠장·1단 ㄷ형강·1단 화타·1단 스크류잭·띠장보걸이 완벽 삭제(숨김) 처리
#    - Mistrut 공법 적용으로 불필요해진 1단 가시설 부재 일체 제거!
# ==============================================================================
col_tiers = bpy.data.collections.get("01_가시설_단별해체_버팀보_띠장_ㄷ형강")
removed_s1_names = []
if col_tiers:
    for o in list(col_tiers.objects):
        o.animation_data_clear()
        # 1단(S1) 및 2~11단 모두 초기 굴착 + Mistrut 상태에서는 비표시 (1단은 Mistrut로 완전 대체됨!)
        o.hide_viewport = True
        o.hide_render   = True
        if "01단_S1" in o.name:
            removed_s1_names.append(o.name)
    col_tiers.hide_viewport = True
    col_tiers.hide_render   = True

col_decking = bpy.data.collections.get("01A_가시설_복공판_주형보_주형지지보_피스브라켓_상세")
if col_decking:
    for o in list(col_decking.objects):
        # 당초 1단 띠장 지지용 삼각피스브라켓(03C) 및 1단 ㄷ형강 지지브라켓(03D)도 1단 버팀보 삭제로 불필요하므로 숨김!
        if o.name.startswith("03C_띠장보걸이") or o.name.startswith("03D_중간말뚝_ㄷ형강지지브라켓"):
            o.hide_viewport = True
            o.hide_render   = True
            removed_s1_names.append(o.name)

# ==============================================================================
# 3. 3D 형상 생성 헬퍼 함수 (Mistrut 본체, 전단키 설치판, 수평 스크류잭, 웨브 스티프너, 보강띠장, 보강앵글)
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

def add_h_beam_horizontal(verts, faces, p1, p2, z_bot, z_top, B=0.305, tf=0.015, tw=0.015):
    add_box_segment_3d(verts, faces, p1, p2, z_bot, z_bot + tf, B)
    add_box_segment_3d(verts, faces, p1, p2, z_top - tf, z_top, B)
    if z_top - z_bot > 2.0 * tf + 0.005:
        add_box_segment_3d(verts, faces, p1, p2, z_bot + tf, z_top - tf, tw)

def add_pipe_segment_3d(verts, faces, p1, p2, z_lvl, radius=0.065, n_seg=10):
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

def add_mistrut_unit_3d(
    body_v, body_f,
    plate_v, plate_f,
    jack_v, jack_f,
    stiff_v, stiff_f,
    cx, cy, ux, uy,
    z_girder_bot=-0.90,
    z_girder_top=-0.20,
    plate_len=0.428,
    plate_wid=0.300,
    jack_len=0.22,
    add_stiffener=True
):
    """
    2.2 Mistrut 설치 상세도 (MW2/MW3, MM2/MMW2) 기준 정밀 3D 어셈블리 생성:
    - (cx, cy): Mistrut 전면(스크류잭이 띠장/주형지지보와 맞닿는 기준점)에서 후방(-ux, -uy)으로 Mistrut 본체 배치,
                전방(+ux, +uy)으로 수평 스크류잭(Screw Jack) 배치!
    - 1) 설치 플레이트 (L-428x300x14 또는 L-288x300x14) + 하부 전단키(Shear Key) + M22x80 고장력볼트 4EA
    - 2) Mistrut 주강 본체 (MS50/MS80: 상부 플랜지판 + 전면 수직 반력판 + 좌/우/중앙 삼각 리브 + 잭 하우징)
    - 3) 수평 스크류잭 (Screw Jack: 나사 실린더 + 조절 너트 칼라 + 지압 베이스플레이트)
    - 4) 주형보(I-700x300x13x24) 복부 웨브 수직 보강 스티프너 (양측 2매)
    """
    nx, ny = -uy, ux  # 주형보 폭 방향 단위벡터

    # 1. 설치 플레이트 (Mounting Plate: Z = z_girder_bot - 0.018 ~ z_girder_bot)
    p_pl_front = (cx + ux * 0.04, cy + uy * 0.04)
    p_pl_back  = (cx - ux * (plate_len - 0.04), cy - uy * (plate_len - 0.04))
    add_box_segment_3d(plate_v, plate_f, p_pl_back, p_pl_front, z_girder_bot - 0.018, z_girder_bot, plate_wid)
    # 전단키 (Shear Key: 설치 플레이트 하면 후방에 용접된 전단 저항 각재)
    p_sk1 = (cx - ux * (plate_len - 0.08), cy - uy * (plate_len - 0.08))
    p_sk2 = (cx - ux * (plate_len - 0.03), cy - uy * (plate_len - 0.03))
    add_box_segment_3d(plate_v, plate_f, p_sk1, p_sk2, z_girder_bot - 0.052, z_girder_bot - 0.018, plate_wid * 0.85)

    # 2. Mistrut 주강 본체 (MS50/MS80 Casting Body: Z = z_girder_bot - 0.31 ~ z_girder_bot - 0.018)
    z_ms_top = z_girder_bot - 0.018
    z_ms_bot = z_girder_bot - 0.310
    body_len = 0.300
    body_wid = 0.250
    p_bd_front = (cx, cy)
    p_bd_back  = (cx - ux * body_len, cy - uy * body_len)
    # 2-a) 본체 상부 볼트 체결 플랜지 (M22x70 4EA 체결판)
    add_box_segment_3d(body_v, body_f, p_bd_back, p_bd_front, z_ms_top - 0.024, z_ms_top, body_wid)
    # 2-b) 본체 전면 수직 지압판 (Front Thrust Face)
    p_face_back = (cx - ux * 0.035, cy - uy * 0.035)
    add_box_segment_3d(body_v, body_f, p_face_back, p_bd_front, z_ms_bot, z_ms_top - 0.024, body_wid)
    # 2-c) 본체 좌·우·중앙 3열 고강성 삼각 리브 (Triangular Gusset Ribs)
    for off_w, rib_t in [(-body_wid*0.38, 0.022), (0.0, 0.026), (body_wid*0.38, 0.022)]:
        ox, oy = nx * off_w, ny * off_w
        tx, ty = nx * (rib_t * 0.5), ny * (rib_t * 0.5)
        b = len(body_v)
        body_v.extend([
            (p_bd_front[0] + ox - tx, p_bd_front[1] + oy - ty, z_ms_bot),
            (p_bd_front[0] + ox + tx, p_bd_front[1] + oy + ty, z_ms_bot),
            (p_bd_front[0] + ox + tx, p_bd_front[1] + oy + ty, z_ms_top - 0.024),
            (p_bd_front[0] + ox - tx, p_bd_front[1] + oy - ty, z_ms_top - 0.024),
            (p_bd_back[0]  + ox - tx, p_bd_back[1]  + oy - ty, z_ms_top - 0.065),
            (p_bd_back[0]  + ox + tx, p_bd_back[1]  + oy + ty, z_ms_top - 0.065),
            (p_bd_back[0]  + ox + tx, p_bd_back[1]  + oy + ty, z_ms_top - 0.024),
            (p_bd_back[0]  + ox - tx, p_bd_back[1]  + oy - ty, z_ms_top - 0.024),
        ])
        body_f.extend([
            (b+0, b+1, b+2, b+3),
            (b+4, b+7, b+6, b+5),
            (b+0, b+4, b+5, b+1),
            (b+1, b+5, b+6, b+2),
            (b+2, b+6, b+7, b+3),
            (b+3, b+7, b+4, b+0),
        ])

    # 3. 수평 스크류잭 (Horizontal Screw Jack: cx,cy에서 +ux,+uy 방향으로 jack_len만큼 전진하여 띠장/지지보 가압!)
    z_jack = 0.5 * (z_ms_top + z_ms_bot) - 0.01
    p_jk_end = (cx + ux * jack_len, cy + uy * jack_len)
    p_jk_mid1 = (cx + ux * (jack_len * 0.25), cy + uy * (jack_len * 0.25))
    p_jk_mid2 = (cx + ux * (jack_len * 0.65), cy + uy * (jack_len * 0.65))
    p_jk_pad  = (cx + ux * (jack_len - 0.025), cy + uy * (jack_len - 0.025))
    # 잭 실린더 축 (Ø110mm) + 육각 조절 너트 칼라 (Ø170mm) + 선단 지압판 (220x220x25t)
    add_pipe_segment_3d(jack_v, jack_f, p_bd_front, p_jk_end, z_jack, radius=0.055, n_seg=10)
    add_pipe_segment_3d(jack_v, jack_f, p_jk_mid1, p_jk_mid2, z_jack, radius=0.088, n_seg=8)
    add_box_segment_3d(jack_v, jack_f, p_jk_pad, p_jk_end, z_jack - 0.11, z_jack + 0.11, 0.22)

    # 4. 주형보(I-700x300x13x24) 복부 웨브 보강 스티프너 (주형보 플랜지 폭 0.30m 내부에 깔끔하게 수납: 폭 0.27m, 두께 16mm)
    if add_stiffener:
        p_st1 = (cx - ux * 0.08, cy - uy * 0.08)
        p_st2 = (cx - ux * 0.062, cy - uy * 0.062)
        add_box_segment_3d(stiff_v, stiff_f, p_st1, p_st2, z_girder_bot + 0.024, z_girder_top - 0.024, 0.27)

# ==============================================================================
# 4. Mistrut 전용 컬렉션 생성: 01M_가시설_Mistrut공법_1단버팀보대체_상세
# ==============================================================================
root_col = bpy.data.collections.get("106_Station_BIM_CAD044")
if not root_col:
    root_col = bpy.context.scene.collection

col_ms_name = "01M_가시설_Mistrut공법_1단버팀보대체_상세"
col_ms = bpy.data.collections.get(col_ms_name)
if not col_ms:
    col_ms = bpy.data.collections.new(col_ms_name)
    root_col.children.link(col_ms)
col_ms.hide_viewport = False
col_ms.hide_render   = False

for o in list(col_ms.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ==============================================================================
# 5. 주형보(I-700x300x13x24) 및 내·외측 주형지지보 위치에서 Mistrut 정밀 배치
# ==============================================================================
# 5-1. 기존 생성된 주형보 및 내측주형지지보 기하 데이터 복원 (dxf 재파싱 없이 빠르고 정확하게 추출)
dxf_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\0d917c24-0c73-469d-af45-411a71b292b9\scratch\cad_044.dxf"
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
            cur_ent = {'type': val, 'layer': '', 'x': [], 'y': [], 'closed': 0}
        elif cur_ent is not None:
            if code == '8':
                cur_ent['layer'] = val
            elif code == '70':
                try:
                    cur_ent['closed'] = int(val)
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

def to_loc_deck(x, y):
    return (round(x - 26.8, 4), round(y - 52.0, 4))

line_segs = []
base_segs = []
work_opening_polys = []

for e in entities:
    if e['type'] in ('LWPOLYLINE', 'LINE') and len(e['x']) >= 2:
        mx, my = sum(e['x'])/len(e['x']), sum(e['y'])/len(e['y'])
        if 0 <= mx <= 205 and 20 <= my <= 100:
            pts = [to_loc_deck(x, y) for x, y in zip(e['x'], e['y'])]
            if e['layer'] == 'CE-LINE-STEL':
                for k in range(len(pts) - 1):
                    p1, p2 = pts[k], pts[k+1]
                    if p1[1] > p2[1] or (abs(p1[1] - p2[1]) < 0.2 and p1[0] > p2[0]):
                        p1, p2 = p2, p1
                    line_segs.append((p1, p2))
            elif e['layer'] == 'CE-BASE-STEL':
                is_closed = (e['closed'] == 1) or (len(pts) >= 4 and math.hypot(pts[0][0]-pts[-1][0], pts[0][1]-pts[-1][1]) < 0.05)
                if is_closed or len(pts) >= 4:
                    dx_p = max(p[0] for p in pts) - min(p[0] for p in pts)
                    dy_p = max(p[1] for p in pts) - min(p[1] for p in pts)
                    if len(pts) in (4, 5) and 3.6 <= dx_p <= 4.5 and 3.6 <= dy_p <= 4.5:
                        work_opening_polys.append(pts[:4])
                else:
                    p1, p2 = pts[0], pts[-1]
                    if p1[0] > p2[0]:
                        p1, p2 = p2, p1
                    base_segs.append((p1, p2))

if len(work_opening_polys) < 3:
    work_opening_polys.append([(102.8, 4.8), (106.8, 5.1), (106.5, 9.1), (102.5, 8.8)])

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

# ==============================================================================
# 5-2. 외측파일부 Mistrut (MW2-TYPE / MW3-TYPE) + 외측 보강띠장 (H-300x305x15x15)
#      - 본선 주형보(I-700x300x13x24)의 외벽 측 단부마다 Mistrut + Screw Jack + 전단키 플레이트 + 주형보 웨브 스티프너 설치!
#      - 외측 주형지지보(H-300x305x15x15) 내측면에 맞닿아 약축을 보강하는 '외측 보강띠장(H-300x305x15x15)' 및 띠장 스티프너 설치!
# ==============================================================================
outer_loop = cad['outer_wale_loop']

out_ms_body_v,  out_ms_body_f  = [], []
out_ms_plate_v, out_ms_plate_f = [], []
out_ms_jack_v,  out_ms_jack_f  = [], []
out_ms_stiff_v, out_ms_stiff_f = [], []

mid_ms_body_v,  mid_ms_body_f  = [], []
mid_ms_plate_v, mid_ms_plate_f = [], []
mid_ms_jack_v,  mid_ms_jack_f  = [], []

cnt_outer_ms = 0
cnt_mid_ms   = 0

def dist_to_outer_loop(pt):
    px, py = pt
    best_d = 999.0
    for k in range(len(outer_loop) - 1):
        x1, y1 = outer_loop[k]
        x2, y2 = outer_loop[k+1]
        ddx, ddy = x2 - x1, y2 - y1
        l2 = ddx*ddx + ddy*ddy
        t = max(0.0, min(1.0, ((px - x1)*ddx + (py - y1)*ddy) / (l2 if l2 > 1e-8 else 1.0)))
        d = math.hypot(x1 + t*ddx - px, y1 + t*ddy - py)
        if d < best_d:
            best_d = d
    return best_d

def seg_intersect_2d(p1, p2, q1, q2):
    """선분 p1-p2와 q1-q2의 교점 (ix, iy, t_p) 반환 (교차하지 않으면 None)"""
    rx, ry = p2[0] - p1[0], p2[1] - p1[1]
    sx, sy = q2[0] - q1[0], q2[1] - q1[1]
    rxs = rx * sy - ry * sx
    if abs(rxs) < 1e-8:
        return None
    qpx, qpy = q1[0] - p1[0], q1[1] - p1[1]
    t = (qpx * sy - qpy * sx) / rxs
    u = (qpx * ry - qpy * rx) / rxs
    if -0.05 <= t <= 1.05 and -0.02 <= u <= 1.02:
        return (p1[0] + t * rx, p1[1] + t * ry, t)
    return None

for c1, c2 in main_girders:
    mx, my = 0.5*(c1[0]+c2[0]), 0.5*(c1[1]+c2[1])
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    L = math.hypot(dx, dy)
    # 진입부 H-440 단경간 제외, 본선 주형보(I-700x300x13x24) 대상
    if (mx < 16.0 and my > 21.0) or mx > 113.5 or L < 3.5:
        continue
    ux, uy = dx / L, dy / L  # c1 -> c2 방향 단위벡터

    # (A) 주형보 양단(c1, c2) 중 외벽(outer_loop)과 만나는 외측파일부(MW2/MW3-TYPE) 판별
    d1 = dist_to_outer_loop(c1)
    d2 = dist_to_outer_loop(c2)
    if d1 < 1.8:
        # c1이 외측벽(남측벽 등)에 인접 -> 스크류잭은 -ux,-uy(외벽 보강띠장 쪽)를 향해 밀어줌!
        cx_o = c1[0] + ux * 0.58
        cy_o = c1[1] + uy * 0.58
        add_mistrut_unit_3d(
            out_ms_body_v, out_ms_body_f,
            out_ms_plate_v, out_ms_plate_f,
            out_ms_jack_v, out_ms_jack_f,
            out_ms_stiff_v, out_ms_stiff_f,
            cx_o, cy_o, -ux, -uy,
            z_girder_bot=-0.90, z_girder_top=-0.20,
            plate_len=0.288, plate_wid=0.300, jack_len=0.24, add_stiffener=True
        )
        cnt_outer_ms += 1

    if d2 < 1.8:
        # c2가 외측벽(북측벽 등)에 인접 -> 스크류잭은 +ux,+uy(외벽 보강띠장 쪽)를 향해 밀어줌!
        cx_o = c2[0] - ux * 0.58
        cy_o = c2[1] - uy * 0.58
        add_mistrut_unit_3d(
            out_ms_body_v, out_ms_body_f,
            out_ms_plate_v, out_ms_plate_f,
            out_ms_jack_v, out_ms_jack_f,
            out_ms_stiff_v, out_ms_stiff_f,
            cx_o, cy_o, ux, uy,
            z_girder_bot=-0.90, z_girder_top=-0.20,
            plate_len=0.288, plate_wid=0.300, jack_len=0.24, add_stiffener=True
        )
        cnt_outer_ms += 1

    # (B) 주형보(c1-c2)가 내측 주형지지보(2열 H-440x300x11x18)와 교차하는 중간파일부(MM2/MMW2-TYPE) 판별
    hits_t = []
    for q1, q2 in inner_support_beams:
        res = seg_intersect_2d(c1, c2, q1, q2)
        if res is not None:
            hits_t.append(res[2])
    if hits_t:
        hits_t.sort()
        # 근접한 2열 내측 주형지지보(간격 약 0.6~0.8m)를 클러스터링하여 2열 중심점(t_mid) 도출
        clusters = []
        for t_val in hits_t:
            if not clusters or (t_val - clusters[-1][-1]) * L > 1.3:
                clusters.append([t_val])
            else:
                clusters[-1].append(t_val)
        for cl in clusters:
            t_mid = sum(cl) / len(cl)
            ix = c1[0] + t_mid * dx
            iy = c1[1] + t_mid * dy
            # 2열 내측 주형지지보의 외측면(중심에서 ±0.45m) 바깥쪽(±0.68m)에 양측 대칭 Mistrut + Jack 배치!
            # 단, 중앙 내측주형지지보 상부에서 남·북 주형보가 서로 엇배치(Lap-Splice)로 끝나는 경우,
            # 실제 주형보 플랜지가 존재하는 쪽(단부 여유 >= 0.75m)에만 Mistrut와 스티프너를 장착하여 공중 돌출 방지!
            if t_mid * L >= 0.75:
                # 1) 남측(-ux,-uy 측)에서 +ux,+uy 방향으로 내측주형지지보를 가압하는 Mistrut
                add_mistrut_unit_3d(
                    mid_ms_body_v, mid_ms_body_f,
                    mid_ms_plate_v, mid_ms_plate_f,
                    mid_ms_jack_v, mid_ms_jack_f,
                    out_ms_stiff_v, out_ms_stiff_f,
                    ix - ux * 0.68, iy - uy * 0.68, ux, uy,
                    z_girder_bot=-0.90, z_girder_top=-0.20,
                    plate_len=0.428, plate_wid=0.300, jack_len=0.22, add_stiffener=True
                )
                cnt_mid_ms += 1
            if (1.0 - t_mid) * L >= 0.75:
                # 2) 북측(+ux,+uy 측)에서 -ux,-uy 방향으로 내측주형지지보를 가압하는 Mistrut
                add_mistrut_unit_3d(
                    mid_ms_body_v, mid_ms_body_f,
                    mid_ms_plate_v, mid_ms_plate_f,
                    mid_ms_jack_v, mid_ms_jack_f,
                    out_ms_stiff_v, out_ms_stiff_f,
                    ix + ux * 0.68, iy + uy * 0.68, -ux, -uy,
                    z_girder_bot=-0.90, z_girder_top=-0.20,
                    plate_len=0.428, plate_wid=0.300, jack_len=0.22, add_stiffener=True
                )
                cnt_mid_ms += 1

# 5-3. 외측 보강띠장 (MW2/MW3-TYPE: 외측 주형지지보 내측면에 H-300x305x15x15 보강띠장 + 띠장 웨브 스티프너 + L-65x65x6 보걸이)
reinf_wale_v, reinf_wale_f = [], []
for k in range(len(outer_loop) - 1):
    p1, p2 = outer_loop[k], outer_loop[k+1]
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 0.2:
        continue
    # 정거장 내측 중심(58.0, 12.0) 방향으로 0.31m 오프셋하여 외측 주형지지보와 나란히 밀착 배치!
    nx, ny = -dy / L, dx / L
    mx, my = 0.5*(p1[0]+p2[0]), 0.5*(p1[1]+p2[1])
    if nx*(58.0 - mx) + ny*(12.0 - my) < 0:
        nx, ny = -nx, -ny
    q1 = (p1[0] + nx * 0.31, p1[1] + ny * 0.31)
    q2 = (p2[0] + nx * 0.31, p2[1] + ny * 0.31)
    add_h_beam_horizontal(reinf_wale_v, reinf_wale_f, q1, q2, -1.20, -0.90, B=0.305, tf=0.015, tw=0.015)
    # 2.0m 간격 띠장용 웨브 스티프너 (300x305x15x15 띠장용 스티프너)
    n_st = int(L / 2.0)
    ux, uy = dx / L, dy / L
    for s_idx in range(1, n_st + 1):
        dist_s = s_idx * 2.0
        if dist_s < L - 0.3:
            sp1 = (q1[0] + ux*(dist_s - 0.008), q1[1] + uy*(dist_s - 0.008))
            sp2 = (q1[0] + ux*(dist_s + 0.008), q1[1] + uy*(dist_s + 0.008))
            add_box_segment_3d(out_ms_stiff_v, out_ms_stiff_f, sp1, sp2, -1.185, -0.915, 0.295)

# ==============================================================================
# 5-4. 중간파일부 2열 내측 주형지지보(2-H440x300x11x18) 간 보강앵글(L-100x100x10) 및 보강빔(H-300x305)
#      - 2.2 Mistrut 설치 상세도 '단면 A-A' 및 '상세 "A"' 완벽 반영!
#      - 2열의 내측 주형지지보(간격 600~800mm) 상·하부 플랜지를 2.0m 간격으로 연결하는 L-100x100x10 보강앵글과
#        횡방향 다이어프램 보강빔을 설치하여, 1단 버팀보 축력 전달 시 비틀림·횡좌굴 완벽 방지!
# ==============================================================================
angle_v, angle_f = [], []
# inner_support_beams에서 서로 마주보는 2열 쌍(Pair)을 찾아 2.0m 간격으로 상·하부 보강앵글 및 대각 브레이싱 생성
used_pair = [False] * len(inner_support_beams)
for i1 in range(len(inner_support_beams)):
    if used_pair[i1]:
        continue
    a1, a2 = inner_support_beams[i1]
    mxa, mya = 0.5*(a1[0]+a2[0]), 0.5*(a1[1]+a2[1])
    best_i2, best_dist = None, 999.0
    for i2 in range(i1 + 1, len(inner_support_beams)):
        if used_pair[i2]:
            continue
        b1, b2 = inner_support_beams[i2]
        mxb, myb = 0.5*(b1[0]+b2[0]), 0.5*(b1[1]+b2[1])
        d = math.hypot(mxa - mxb, mya - myb)
        if 0.40 <= d <= 1.25 and abs(mxa - mxb) < 1.5:
            if d < best_dist:
                best_dist = d
                best_i2 = i2
    if best_i2 is not None:
        used_pair[i1] = True
        used_pair[best_i2] = True
        b1, b2 = inner_support_beams[best_i2]
        L_seg = math.hypot(a2[0]-a1[0], a2[1]-a1[1])
        n_bays = max(1, int(L_seg / 2.0))
        for k in range(n_bays + 1):
            t = k / float(n_bays)
            pa = (a1[0]*(1-t) + a2[0]*t, a1[1]*(1-t) + a2[1]*t)
            pb = (b1[0]*(1-t) + b2[0]*t, b1[1]*(1-t) + b2[1]*t)
            # 상부 수평 보강앵글 (L-100x100x10, Z = -0.94m ~ -0.90m)
            add_box_segment_3d(angle_v, angle_f, pa, pb, -0.95, -0.90, 0.10)
            # 하부 수평 보강앵글 (L-100x100x10, Z = -1.34m ~ -1.29m)
            add_box_segment_3d(angle_v, angle_f, pa, pb, -1.34, -1.29, 0.10)
            # 복부 다이어프램 보강빔 (H-300x305, 4.0m 간격마다 배치)
            if k % 2 == 0:
                add_box_segment_3d(angle_v, angle_f, pa, pb, -1.27, -0.97, 0.15)
            # 평면 대각 브레이싱 앵글 (L-100x100x10)
            if k < n_bays:
                t_next = (k + 1) / float(n_bays)
                pb_next = (b1[0]*(1-t_next) + b2[0]*t_next, b1[1]*(1-t_next) + b2[1]*t_next)
                add_box_segment_3d(angle_v, angle_f, pa, pb_next, -0.95, -0.91, 0.08)

# ==============================================================================
# 5-5. 작업구(4.0m x 4.0m, 3개소) 구간 Mistrut 및 작업구 보강띠장 (2.3 Mistrut 작업구 설치 상세도 반영)
#      - 작업구 개구부로 인해 주형보가 단절되는 구간에는 내측 주형지지보 외측면에 '작업구 보강띠장(H-300x305x15x15)'을 추가 설치하고,
#        절단된 주형보 단부 및 인접 주형보에 작업구 전용 Mistrut + Screw Jack 설치!
# ==============================================================================
wo_ms_v, wo_ms_f = [], []
for op_poly in work_opening_polys:
    cx_op = sum(p[0] for p in op_poly) / len(op_poly)
    cy_op = sum(p[1] for p in op_poly) / len(op_poly)
    # 개구부 종방향(X축 방향, 길이 6.0m)으로 남·북 테두리에 작업구 보강띠장(H-300x305x15x15, Z=-1.20~-0.90m) 배치
    ang_rad = math.radians(-4.2)
    ux_w, uy_w = math.cos(ang_rad), math.sin(ang_rad)
    nx_w, ny_w = -uy_w, ux_w
    for side_s in (-1.0, 1.0):
        p_w1 = (cx_op - ux_w*3.0 + nx_w*side_s*2.25, cy_op - uy_w*3.0 + ny_w*side_s*2.25)
        p_w2 = (cx_op + ux_w*3.0 + nx_w*side_s*2.25, cy_op + uy_w*3.0 + ny_w*side_s*2.25)
        add_h_beam_horizontal(wo_ms_v, wo_ms_f, p_w1, p_w2, -1.20, -0.90, B=0.305, tf=0.015, tw=0.015)
        # 작업구 보강띠장 양단 및 중앙에 Mistrut + Screw Jack 3세트씩 추가 장착!
        for s_off in (-1.8, 0.0, 1.8):
            mx_s = cx_op + ux_w*s_off + nx_w*side_s*2.65
            my_s = cy_op + uy_w*s_off + ny_w*side_s*2.65
            add_mistrut_unit_3d(
                mid_ms_body_v, mid_ms_body_f,
                mid_ms_plate_v, mid_ms_plate_f,
                mid_ms_jack_v, mid_ms_jack_f,
                out_ms_stiff_v, out_ms_stiff_f,
                mx_s, my_s, -nx_w*side_s, -ny_w*side_s,
                z_girder_bot=-0.90, z_girder_top=-0.20,
                plate_len=0.428, plate_wid=0.300, jack_len=0.24, add_stiffener=True
            )

# ==============================================================================
# 6. Mistrut 3D 오브젝트 생성 및 컬렉션 등록
# ==============================================================================
create_mesh_obj(f"01_Mistrut_외측파일부_MW2_MW3_주강본체_{cnt_outer_ms}EA", out_ms_body_v, out_ms_body_f, mat_ms_body, col_ms)
create_mesh_obj(f"02_Mistrut_외측파일부_설치플레이트및전단키_{cnt_outer_ms}EA", out_ms_plate_v, out_ms_plate_f, mat_ms_plate, col_ms)
create_mesh_obj(f"03_Mistrut_외측파일부_수평스크류잭_{cnt_outer_ms}EA", out_ms_jack_v, out_ms_jack_f, mat_ms_jack, col_ms)
create_mesh_obj("04_Mistrut_외측보강띠장_H300x305x15x15_약축보강", reinf_wale_v, reinf_wale_f, mat_ms_reinf_w, col_ms)

create_mesh_obj(f"05_Mistrut_중간파일부_MM2_MMW2_양측주강본체_{cnt_mid_ms}EA", mid_ms_body_v, mid_ms_body_f, mat_ms_body, col_ms)
create_mesh_obj(f"06_Mistrut_중간파일부_설치플레이트및전단키_{cnt_mid_ms}EA", mid_ms_plate_v, mid_ms_plate_f, mat_ms_plate, col_ms)
create_mesh_obj(f"07_Mistrut_중간파일부_양측수평스크류잭_{cnt_mid_ms}EA", mid_ms_jack_v, mid_ms_jack_f, mat_ms_jack, col_ms)
create_mesh_obj("08_Mistrut_내측주형지지보_보강앵글_L100x100x10_및_다이어프램", angle_v, angle_f, mat_ms_angle, col_ms)
create_mesh_obj("09_Mistrut_작업구구간_4x4m_3개소_외측보강띠장_H300x305", wo_ms_v, wo_ms_f, mat_ms_reinf_w, col_ms)
create_mesh_obj("10_Mistrut_주형보및보강띠장_웨브보강스티프너", out_ms_stiff_v, out_ms_stiff_f, mat_ms_stiff, col_ms)

# ==============================================================================
# 7. 1단 버팀보 삭제로 확보된 복공 하부 대공간(GL -0.90m ~ 굴착면 Z = -3.20m) 정합성 업데이트
#    - Mistrut(시방서 및 시티기술단 도면 15p) 핵심 장점:
#      1단 버팀보(S1) 삭제로 복공판 및 주형보 하부에 높이 3.0m 이상의 넓은 무지보 작업공간 확보!
# ==============================================================================
col_exc = bpy.data.collections.get("00A_정거장_단계별굴착_원지반토사면_및_단별토류판")
if col_exc:
    for o in list(col_exc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    z_exc_floor = -3.20  # Mistrut 적용 후 2단 버팀보(GL-3.895m) 설치 전 광활한 1차 굴착 작업공간 레벨!
    ow_loop = cad['outer_wall_loop']

    def add_polygon_slab_bm(verts, faces, poly_2d, z_bot, z_top):
        import bmesh as _bm
        if len(poly_2d) < 3:
            return
        bm = _bm.new()
        b_verts = [bm.verts.new((pt[0], pt[1], z_bot)) for pt in poly_2d]
        try:
            f_bot = bm.faces.new(b_verts)
        except:
            bm.free()
            return
        _bm.ops.triangulate(bm, faces=[f_bot])
        res = _bm.ops.extrude_face_region(bm, geom=bm.faces[:])
        ext_verts = [g for g in res['geom'] if isinstance(g, _bm.types.BMVert)]
        _bm.ops.translate(bm, verts=ext_verts, vec=(0.0, 0.0, z_top - z_bot))
        _bm.ops.recalc_face_normals(bm, faces=bm.faces[:])
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

    def add_h_beam_vertical(verts, faces, cx, cy, rot_deg, z_bot, z_top, B=0.30, H=0.30, tf=0.015, tw=0.012):
        import math as _m
        rad = _m.radians(rot_deg)
        ux, uy = _m.cos(rad), _m.sin(rad)
        vx, vy = -uy, ux
        def pt(lx, ly):
            return (cx + lx * ux + ly * vx, cy + lx * uy + ly * vy)
        add_box_segment_3d(verts, faces, pt(-H*0.5, -B*0.5), pt(-H*0.5, B*0.5), z_bot, z_top, tf)
        add_box_segment_3d(verts, faces, pt( H*0.5, -B*0.5), pt( H*0.5, B*0.5), z_bot, z_top, tf)
        add_box_segment_3d(verts, faces, pt(-H*0.5 + tf*0.5, 0.0), pt(H*0.5 - tf*0.5, 0.0), z_bot, z_top, tw)

    # 7-1. 굴착 바닥면 (Z = -3.20m: 1단 버팀보 없이 굴착 장비가 자유롭게 주행하는 공간)
    mat_soil_exc = bpy.data.materials.get("MAT_106_Excavated_Soil_Floor")
    sv_e, sf_e = [], []
    add_polygon_slab_bm(sv_e, sf_e, ow_loop[:-1], z_exc_floor - 0.35, z_exc_floor)
    create_mesh_obj("00A_초기굴착바닥_Mistrut무지보대공간_Z-3.20m", sv_e, sf_e, mat_soil_exc, col_exc)

    # 7-2. 주변 원지반 지표면 (GL 0.0m)
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
    to_del = [f for f in bm_g.faces if point_in_poly_2d(f.calc_center_median().x, f.calc_center_median().y, ow_loop[:-1])]
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

    # 7-3. 토류판 노출 구간 (Z = -3.20m ~ -0.20m)
    mat_lag = bpy.data.materials.get("MAT_CAD044_Lagging")
    lv, lf = [], []
    for k in range(len(ow_loop) - 1):
        add_box_segment_3d(lv, lf, ow_loop[k], ow_loop[k+1], z_exc_floor, -0.20, 0.08)
    create_mesh_obj("03C_토류판_초기굴착구간_GL0_to_Z-3.20m", lv, lf, mat_lag, col_exc)

    # 7-4. 외벽 엄지말뚝 노출 구간 (Z = -3.20m ~ -0.90m)
    mat_hp = bpy.data.materials.get("MAT_CAD044_HPile_Blue")
    hpv, hpf = [], []
    for wp in cad['wall_piles']:
        if wp['group'] == 'OUTER':
            add_h_beam_vertical(hpv, hpf, wp['x'], wp['y'], wp['rot'], z_exc_floor, -0.90, B=0.305, H=0.300)
    create_mesh_obj("02_엄지말뚝_초기굴착노출부_GL0_to_Z-3.20m", hpv, hpf, mat_hp, col_exc)

    # 7-5. 중간말뚝 노출 구간 (Z = -3.20m ~ -0.90m)
    mat_cp = bpy.data.materials.get("MAT_CAD044_CPile_Upper_Removable")
    cpv, cpf = [], []
    for cp in cad['center_piles']:
        add_h_beam_vertical(cpv, cpf, cp['x'], cp['y'], cp['rot'], z_exc_floor, -0.90, B=0.300, H=0.300)
    create_mesh_obj("08_중간말뚝_초기굴착노출부_122EA_GL0_to_Z-3.20m", cpv, cpf, mat_cp, col_exc)

# ==============================================================================
# 8. 컬렉션 가시성 정리 (1단 버팀보 컬렉션은 OFF, Mistrut 컬렉션은 ON!)
# ==============================================================================
keep_cols = {
    "106_Station_BIM_CAD044",
    "00_가시설_외벽엄지말뚝_차수_토류판",
    "00A_정거장_단계별굴착_원지반토사면_및_단별토류판",
    "01A_가시설_복공판_주형보_주형지지보_피스브라켓_상세",
    "01M_가시설_Mistrut공법_1단버팀보대체_상세",
}
for c in bpy.data.collections:
    c.hide_viewport = (c.name not in keep_cols)
    c.hide_render   = (c.name not in keep_cols)

# 절개구간 주형보(01A_주형보_하부지지보투시창_절개구간_ON_OFF용)는 켜서 주형보 하단에 달린 Mistrut가 그대로 보이게 하고,
# 복공판 중앙 투시창(04B)만 숨겨서 위에서도 Mistrut와 주형보의 결합 구조가 한눈에 보이도록 설정!
obj_mg_cut = bpy.data.objects.get("01A_주형보_하부지지보투시창_절개구간_ON_OFF용")
if obj_mg_cut:
    obj_mg_cut.hide_viewport = False
    obj_mg_cut.hide_render   = False

obj_deck_cut = bpy.data.objects.get("04B_복공판_중앙하부투시창_절개구간_ON_OFF용")
if obj_deck_cut:
    obj_deck_cut.hide_viewport = True
    obj_deck_cut.hide_render   = True

# 뷰포트 카메라를 주형보 하단의 Mistrut + 수평 스크류잭 + 내·외측 주형지지보 + 1단 버팀보가 삭제된 넓은 하부 작업공간이
# 가장 입체적으로 잘 보이는 각도로 세팅!
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
                    r3d.view_location = Vector((29.5, 9.2, -1.25))
                    r3d.view_rotation = Euler((math.radians(78), 0.0, math.radians(-36))).to_quaternion()
                    r3d.view_distance = 7.2
                    r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=blend_save_path)
print(f"SUCCESS: Removed S1 ({len(removed_s1_names)} objs) & Applied Mistrut (Outer={cnt_outer_ms}EA, Mid={cnt_mid_ms}EA)!")
