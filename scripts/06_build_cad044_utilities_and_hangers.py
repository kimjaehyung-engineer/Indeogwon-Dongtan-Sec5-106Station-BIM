import bpy
import bmesh
import os
import json
import math
from mathutils import Vector, Euler, Matrix

# ==============================================================================
# 044_01.106정거장 1차 가시설도-3th (type-9,10,11버팀보, 차수 수정) - 우각부 버팀보 수정
# & 106정거장 지장물도 / 지장물 횡단면도 (Mistrut 적용 단면 A-A, B-B) 기준:
# 1) 106정거장 통과 6대 지장물 계통 (광역상수관, 시상수관, 삼천리 도시가스관, 하수관, 통신관, 한전전력관)
# 2) 지장물 가시설 (주형보 I-700x300 하부 플랜지 직결 3단 찬넬·강봉 프레임 매달기 보호공,
#    강봉 달대 + ㄷ형강 하부 받침보 + 쐐기 받침목, 다공관 박스형 보호틀 행거) 3D BIM 완벽 구현!
# ==============================================================================

json_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\0d917c24-0c73-469d-af45-411a71b292b9\scratch\cad_044_data.json"
blend_save_path = r"C:\Users\20040178\Desktop\2영역\토스앤\1.설계변경관리\2.인덕원동탄5공구\7.정거장 구조물 원가개선\정거장 가시설도, 구조도\106정거장_가시설_전체구간_3D_BIM.blend"

with open(json_path, 'r', encoding='utf-8') as f:
    cad = json.load(f)

# ==============================================================================
# 1. 재질(Materials) 정의 — 106정거장 지장물 현황도 범례 색상 + 지장물 가시설 강재/받침목 색상
# ==============================================================================
def make_mat(name, rgba, metallic=0.45, roughness=0.35, alpha=1.0):
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

# 지장물 관로 6대 계통 재질 (106정거장 지장물 현황도 범례 컬러 일치)
mat_wide_water = make_mat("MAT_Util_WideWater_Cyan",     (0.05, 0.78, 0.92), metallic=0.50, roughness=0.30) # 광역상수도 (D900x11t, D500x11t — 밝은 시안블루)
mat_city_water = make_mat("MAT_Util_CityWater_Blue",     (0.12, 0.32, 0.88), metallic=0.50, roughness=0.32) # 시상수도 (D900, D500, D350, D150 — 코발트블루)
mat_city_gas   = make_mat("MAT_Util_CityGas_Red",        (0.92, 0.14, 0.14), metallic=0.55, roughness=0.28) # 삼천리 도시가스 (D200, D150 — 안전 적색)
mat_sewer      = make_mat("MAT_Util_Sewer_Brown",        (0.58, 0.40, 0.22), metallic=0.25, roughness=0.55) # 하수관/우수관 (D1000, D600, D450 — 콘크리트/주철 황갈색)
mat_telecom    = make_mat("MAT_Util_Telecom_Green",      (0.15, 0.78, 0.30), metallic=0.35, roughness=0.38) # 통신관 (100Øx16공 PVC, 175Ø — 선명한 초록색)
mat_kepco      = make_mat("MAT_Util_KEPCO_Yellow",       (0.98, 0.82, 0.08), metallic=0.40, roughness=0.34) # 한전 전력관 (175Øx6공, 150Øx2 — 선명한 노란색)

# 지장물 매달기 보호공 가시설 재질 (강봉 달대, 상·하부 받침 찬넬, 주형보 후크 클램프, 쐐기 받침목)
mat_hanger_stl = make_mat("MAT_Util_Hanger_ChannelSteel",(0.78, 0.82, 0.86), metallic=0.75, roughness=0.26) # 매달기 찬넬·받침보·후크클램프 (아연도금/밝은 강재)
mat_hanger_rod = make_mat("MAT_Util_Hanger_TieRod",      (0.92, 0.68, 0.15), metallic=0.80, roughness=0.24) # 고장력 강봉 달대(행거볼트 Ø25) 및 체결 핀/너트 (황동/골드강재)
mat_wedge_wood = make_mat("MAT_Util_Wedge_CradleWood",   (0.76, 0.52, 0.24), metallic=0.10, roughness=0.65) # 관 하부 삼각 쐐기 받침목 (고임목/각재 보호대)

# ==============================================================================
# 2. 3D 기하 생성 헬퍼 함수 (연속 관로, 다공관 번들, 3단 매달기 프레임, 강봉 달대, 쐐기목)
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

def add_pipe_3d_polyline(verts, faces, pts_3d, radius=0.45, n_seg=16):
    """3D 폴리라인[(x,y,z), ...]을 따라 매끄럽게 이어지는 원형 지장물 관로 생성"""
    if len(pts_3d) < 2:
        return
    rings = []
    n_pts = len(pts_3d)
    for idx, pt in enumerate(pts_3d):
        if idx == 0:
            dx = pts_3d[1][0] - pt[0]
            dy = pts_3d[1][1] - pt[1]
            dz = pts_3d[1][2] - pt[2]
        elif idx == n_pts - 1:
            dx = pt[0] - pts_3d[idx-1][0]
            dy = pt[1] - pts_3d[idx-1][1]
            dz = pt[2] - pts_3d[idx-1][2]
        else:
            dx = pts_3d[idx+1][0] - pts_3d[idx-1][0]
            dy = pts_3d[idx+1][1] - pts_3d[idx-1][1]
            dz = pts_3d[idx+1][2] - pts_3d[idx-1][2]
        L_xy = math.hypot(dx, dy)
        if L_xy < 1e-5:
            nx, ny = 0.0, 1.0
        else:
            nx, ny = -dy / L_xy, dx / L_xy
        base = len(verts)
        for k in range(n_seg):
            ang = 2.0 * math.pi * k / n_seg
            ca, sa = math.cos(ang), math.sin(ang)
            verts.append((pt[0] + nx * radius * ca, pt[1] + ny * radius * ca, pt[2] + radius * sa))
        rings.append(base)
    for r_i in range(len(rings) - 1):
        b1, b2 = rings[r_i], rings[r_i + 1]
        for k in range(n_seg):
            kn = (k + 1) % n_seg
            faces.append((b1 + k, b1 + kn, b2 + kn, b2 + k))
    faces.append(tuple(rings[0] + k for k in range(n_seg - 1, -1, -1)))
    faces.append(tuple(rings[-1] + k for k in range(n_seg)))

def add_vertical_cylinder(verts, faces, cx, cy, z_bot, z_top, radius=0.018, n_seg=8):
    """수직 강봉 달대(행거볼트 Ø25~32mm) 생성"""
    base = len(verts)
    for z_val in (z_bot, z_top):
        for k in range(n_seg):
            ang = 2.0 * math.pi * k / n_seg
            verts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang), z_val))
    for k in range(n_seg):
        kn = (k + 1) % n_seg
        faces.append((base + k, base + kn, base + n_seg + kn, base + n_seg + k))
    faces.append(tuple(base + k for k in range(n_seg - 1, -1, -1)))
    faces.append(tuple(base + n_seg + k for k in range(n_seg)))

def intersect_girder_and_polyline(g_c1, g_c2, pts_3d):
    """
    주형보 선분 g_c1(x1,y1) -> g_c2(x2,y2)와 지장물 3D 폴리라인 pts_3d의
    정확한 2D 평면 교차점 (ix, iy, iz, ux_g, uy_g) 리스트 반환!
    이를 통해 모든 매달기 가시설의 상단 후크/C-클램프가 실제 주형보(I-700x300) 하부 플랜지 중앙에 100% 정확히 체결됨!
    """
    gx1, gy1 = g_c1[0], g_c1[1]
    gx2, gy2 = g_c2[0], g_c2[1]
    gdx, gdy = gx2 - gx1, gy2 - gy1
    gL = math.hypot(gdx, gdy)
    if gL < 0.2:
        return []
    ux_g, uy_g = gdx / gL, gdy / gL
    hits = []
    for k in range(len(pts_3d) - 1):
        p1, p2 = pts_3d[k], pts_3d[k+1]
        px1, py1, pz1 = p1[0], p1[1], p1[2]
        px2, py2, pz2 = p2[0], p2[1], p2[2]
        pdx, pdy = px2 - px1, py2 - py1
        denom = gdx * pdy - gdy * pdx
        if abs(denom) < 1e-7:
            continue
        t_g = ((px1 - gx1) * pdy - (py1 - gy1) * pdx) / denom
        t_p = ((px1 - gx1) * gdy - (py1 - gy1) * gdx) / denom
        if 0.02 <= t_g <= 0.98 and -0.001 <= t_p <= 1.001:
            t_p_c = max(0.0, min(1.0, t_p))
            ix = px1 + t_p_c * pdx
            iy = py1 + t_p_c * pdy
            iz = pz1 + t_p_c * (pz2 - pz1)
            hits.append((ix, iy, iz, ux_g, uy_g))
    return hits

def add_type_a_frame_hanger(
    stl_v, stl_f, rod_v, rod_f, wood_v, wood_f,
    px, py, pz, radius, ux_g, uy_g, z_girder_bot=-0.90
):
    """
    [Type A 지장물 가시설 — 대구경 상수관·광역상수관(D900, D500) 3단 찬넬·강봉 프레임식 매달기 보호공]
    CAD 블록 CZSECM79(900Ø 상수관), CZDIMA157(900Ø*11 광역상수관), CZDIMA141(500Ø*11 광역상수관) 정밀 구현
    """
    half_w = radius + 0.20
    p_left  = (px - ux_g * half_w, py - uy_g * half_w)
    p_right = (px + ux_g * half_w, py + uy_g * half_w)

    # 1) 상부 주형보 하부 밀착 수평 걸침보 (Z = z_girder_bot - 0.09 ~ z_girder_bot)
    add_box_segment_3d(stl_v, stl_f, p_left, p_right, z_girder_bot - 0.09, z_girder_bot, 0.16)
    # 2) 중간(관 상단 직상부) 흔들림방지 수평 고정찬넬 (Z = pz + radius + 0.01 ~ pz + radius + 0.09)
    if pz + radius + 0.12 < z_girder_bot - 0.10:
        add_box_segment_3d(stl_v, stl_f, p_left, p_right, pz + radius + 0.01, pz + radius + 0.09, 0.14)
    # 3) 하부 관 받침보 (Z = pz - radius - 0.095 ~ pz - radius)
    z_cradle_bot = pz - radius - 0.095
    z_cradle_top = pz - radius
    add_box_segment_3d(stl_v, stl_f, p_left, p_right, z_cradle_bot, z_cradle_top, 0.18)

    # 4) 좌·우 수직 매달기 달대 찬넬 + 고장력 행거강봉 + 주형보 플랜지 후크 클램프
    rod_off = radius + 0.055
    for s_sign in (-1.0, 1.0):
        rx = px + s_sign * ux_g * rod_off
        ry = py + s_sign * uy_g * rod_off
        p_r1 = (rx - ux_g * 0.045, ry - uy_g * 0.045)
        p_r2 = (rx + ux_g * 0.045, ry + uy_g * 0.045)
        add_box_segment_3d(stl_v, stl_f, p_r1, p_r2, z_cradle_bot, z_girder_bot + 0.08, 0.12)
        p_hk1 = (rx - ux_g * 0.08, ry - uy_g * 0.08)
        p_hk2 = (rx + ux_g * 0.08, ry + uy_g * 0.08)
        add_box_segment_3d(rod_v, rod_f, p_hk1, p_hk2, z_girder_bot + 0.024, z_girder_bot + 0.085, 0.34)
        for z_pin in (z_cradle_bot + 0.04, pz + radius + 0.05, z_girder_bot - 0.045):
            if z_pin < z_girder_bot:
                add_box_segment_3d(rod_v, rod_f, p_r1, p_r2, z_pin - 0.025, z_pin + 0.025, 0.16)

    # 5) 관 하부 좌·우 삼각 쐐기 받침목 (고임목)
    w_off1 = radius * 0.35
    w_off2 = radius * 0.85
    for s_sign in (-1.0, 1.0):
        w1 = (px + s_sign * ux_g * w_off1, py + s_sign * uy_g * w_off1)
        w2 = (px + s_sign * ux_g * w_off2, py + s_sign * uy_g * w_off2)
        add_box_segment_3d(wood_v, wood_f, w1, w2, z_cradle_top, z_cradle_top + radius * 0.28, 0.22)

def add_type_b_rod_hanger(
    stl_v, stl_f, rod_v, rod_f, wood_v, wood_f,
    px, py, pz, radius, ux_g, uy_g, z_girder_bot=-0.90
):
    """
    [Type B 지장물 가시설 — 가스관(D200/D150)·하수관(D1000/D600/D450)·소구경 상수관(D350/D150) 강봉 달대 매달기 보호공]
    CAD 블록 CZSECM18(200Ø 가스관), CZSECM19(600Ø 하수관), CZDIMA90(1000Ø 하수관), CZNOCR2(150Ø 가스관) 정밀 구현
    """
    half_w = radius + 0.12
    p_left  = (px - ux_g * half_w, py - uy_g * half_w)
    p_right = (px + ux_g * half_w, py + uy_g * half_w)
    z_cradle_bot = pz - radius - 0.09
    z_cradle_top = pz - radius

    add_box_segment_3d(stl_v, stl_f, p_left, p_right, z_cradle_bot, z_cradle_top, 0.14)
    w_s1 = (px - ux_g * (radius * 0.75), py - uy_g * (radius * 0.75))
    w_s2 = (px + ux_g * (radius * 0.75), py + uy_g * (radius * 0.75))
    add_box_segment_3d(wood_v, wood_f, w_s1, w_s2, z_cradle_top, z_cradle_top + radius * 0.22, 0.16)

    rod_off = radius + 0.035
    for s_sign in (-1.0, 1.0):
        rx = px + s_sign * ux_g * rod_off
        ry = py + s_sign * uy_g * rod_off
        add_vertical_cylinder(rod_v, rod_f, rx, ry, z_cradle_bot - 0.03, z_girder_bot + 0.06, radius=0.018, n_seg=8)
        p_c1 = (rx - ux_g * 0.05, ry - uy_g * 0.05)
        p_c2 = (rx + ux_g * 0.05, ry + uy_g * 0.05)
        add_box_segment_3d(stl_v, stl_f, p_c1, p_c2, z_girder_bot - 0.03, z_girder_bot + 0.07, 0.33)
        add_box_segment_3d(rod_v, rod_f, p_c1, p_c2, z_cradle_bot - 0.035, z_cradle_bot + 0.015, 0.10)

def add_type_c_duct_box_hanger(
    stl_v, stl_f, rod_v, rod_f, wood_v, wood_f,
    px, py, pz, box_half_w, box_half_h, ux_g, uy_g, z_girder_bot=-0.90
):
    """
    [Type C 지장물 가시설 — 통신관(100Øx16공 PVC, 175Ø) 및 한전전력관(175Øx6공, 150Øx2) 다공관 박스형 보호틀 매달기]
    CAD 블록 CZSECM184, CZSECM141, CZDIMA143 및 지장물 횡단면도(단면 A-A, B-B) 정밀 구현
    """
    half_w = box_half_w + 0.08
    p_left  = (px - ux_g * half_w, py - uy_g * half_w)
    p_right = (px + ux_g * half_w, py + uy_g * half_w)
    z_bot = pz - box_half_h - 0.07
    z_top = pz + box_half_h + 0.05

    add_box_segment_3d(stl_v, stl_f, p_left, p_right, z_bot, z_bot + 0.07, 0.14)
    add_box_segment_3d(wood_v, wood_f, p_left, p_right, z_top - 0.05, z_top, 0.12)
    for s_sign in (-1.0, 1.0):
        rx = px + s_sign * ux_g * (box_half_w + 0.03)
        ry = py + s_sign * uy_g * (box_half_w + 0.03)
        add_vertical_cylinder(rod_v, rod_f, rx, ry, z_bot - 0.02, z_girder_bot + 0.06, radius=0.016, n_seg=8)
        p_c1 = (rx - ux_g * 0.045, ry - uy_g * 0.045)
        p_c2 = (rx + ux_g * 0.045, ry + uy_g * 0.045)
        add_box_segment_3d(stl_v, stl_f, p_c1, p_c2, z_girder_bot - 0.025, z_girder_bot + 0.065, 0.32)

# ==============================================================================
# 3. 지장물 전용 컬렉션 준비: 01U_가시설_지장물현황_및_지장물매달기보호공_상세
# ==============================================================================
root_col = bpy.data.collections.get("106_Station_BIM_CAD044")
if not root_col:
    root_col = bpy.context.scene.collection

col_util_name = "01U_가시설_지장물현황_및_지장물매달기보호공_상세"
col_util = bpy.data.collections.get(col_util_name)
if not col_util:
    col_util = bpy.data.collections.new(col_util_name)
    root_col.children.link(col_util)
col_util.hide_viewport = False
col_util.hide_render   = False

for o in list(col_util.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ==============================================================================
# 4. CAD 044_01 (TYPE-1 ~ TYPE-11) 및 106정거장 지장물도 기준 13개 지장물 노선 3D 좌표 정의
#    - 중간말뚝(center_piles) 및 내측 주형지지보(Z=-0.90~-1.30m)와 간섭이 없도록 스팬 사이 공간 통과!
# ==============================================================================
center_piles = cad.get('center_piles', [])
def adjust_pts_avoid_piles(pts, clearance=0.80):
    """중간말뚝(H-400x400) 및 내측 주형지지보(Z=-0.90~-1.30m)와의 간섭을 자동 회피"""
    out = []
    for (x, y, z) in pts:
        y_adj = y
        z_adj = min(z, -1.52) # 내측 주형지지보 하단(Z=-1.30m)보다 최소 22cm 이상 아래로 통과
        for cp in center_piles:
            cx, cy = (cp[0], cp[1]) if isinstance(cp, (list, tuple)) else (cp.get('x', 0.0), cp.get('y', 0.0))
            if abs(x - cx) < 3.5 and abs(y_adj - cy) < clearance:
                if y_adj >= cy:
                    y_adj = cy + clearance
                else:
                    y_adj = cy - clearance
        out.append((x, y_adj, z_adj))
    return out

# ① 광역상수도 (청록색: 북측 D900x11t 주간선 & 남측 D500x11t 주간선)
pts_wide_d900 = adjust_pts_avoid_piles([
    (-4.0, 19.60, -2.42), ( 8.0, 19.32, -2.45), (19.0, 18.03, -2.58),
    (30.0, 17.78, -2.61), (42.0, 17.15, -2.90), (49.0, 16.67, -2.87),
    (60.0, 16.80, -3.02), (70.0, 17.77, -2.82), (78.0, 17.64, -2.76),
    (84.0, 18.01, -2.82), (90.0, 18.67, -2.82), (98.0, 19.02, -2.82),
    (108.0, 19.05, -2.82), (121.0, 19.10, -2.80)
], clearance=0.88)

pts_wide_d500 = adjust_pts_avoid_piles([
    (-4.0,  0.35, -2.12), ( 8.0,  0.19, -2.16), (19.0, -0.55, -2.08),
    (30.0, -1.60, -2.25), (42.0, -2.05, -2.52), (49.0, -2.24, -2.45),
    (60.0, -3.31, -2.80), (70.0, -3.64, -2.93), (78.0, -2.92, -2.95),
    (84.0, -2.66, -2.93), (90.0, -2.34, -2.95), (98.0, -1.64, -2.95),
    (108.0, -1.02, -2.95), (121.0, -0.80, -2.90)
], clearance=0.72)

# ② 시상수도 (진청색: 북측 1열 D900, 북측 2열 D900 주간선 + 동측 분기 D900, 남측 D900 주간선, 중앙 대각횡단 D500, 북측 D150, 남측 D350)
pts_city_d900_n1 = adjust_pts_avoid_piles([
    (-4.0, 20.60, -2.02), ( 8.0, 20.40, -2.05), (19.0, 19.31, -2.11),
    (42.0, 18.28, -2.34), (49.0, 17.99, -1.92), (60.0, 17.13, -1.92),
    (70.0, 16.25, -1.92), (82.0, 16.17, -1.92)
], clearance=0.88)

pts_city_d900_n2 = adjust_pts_avoid_piles([
    (-4.0, 14.80, -2.45), ( 8.0, 14.47, -2.47), (19.0, 13.50, -2.60),
    (30.0, 14.65, -2.63), (42.0, 14.20, -2.92), (49.0, 13.85, -2.86),
    (60.0, 12.92, -2.77), (70.0, 13.51, -2.86), (84.0, 16.39, -2.76),
    (90.0, 16.83, -2.86), (98.0, 17.22, -2.70), (108.0, 18.03, -2.86),
    (121.0, 18.20, -2.86)
], clearance=0.88)

pts_city_d900_n2_br = adjust_pts_avoid_piles([
    (70.0, 13.51, -2.86), (98.0, 14.25, -2.86), (108.0, 14.66, -2.86), (121.0, 14.85, -2.86)
], clearance=0.88)

pts_city_d900_s = adjust_pts_avoid_piles([
    (-4.0, -3.80, -2.58), ( 8.0, -3.99, -2.62), (19.0, -4.41, -2.54),
    (30.0, -5.27, -2.68), (42.0, -5.67, -2.95), (49.0, -5.79, -2.89),
    (60.0, -8.85, -3.04), (70.0, -7.36, -2.65), (78.0, -7.16, -2.48),
    (84.0, -6.93, -2.55), (90.0, -6.62, -2.52), (98.0, -6.10, -2.48),
    (108.0, -5.37, -2.50), (121.0, -5.10, -2.50)
], clearance=0.88)

pts_city_d500_diag = adjust_pts_avoid_piles([
    (32.0, -5.60, -2.15), (40.0, -0.50, -2.15), (48.0,  5.20, -2.15),
    (56.0, 11.00, -2.15), (64.0, 16.25, -2.15)
], clearance=0.72)

pts_city_d150_n = adjust_pts_avoid_piles([
    (62.0, 14.00, -1.68), (78.0, 14.15, -1.68), (84.0, 14.09, -1.68),
    (90.0, 14.54, -1.68), (98.0, 14.86, -1.68), (108.0, 15.36, -1.68), (121.0, 15.50, -1.68)
], clearance=0.55)

pts_city_d350_s = adjust_pts_avoid_piles([
    (62.0, -11.50, -2.18), (70.0, -12.34, -2.18), (78.0, -11.93, -1.68),
    (90.0, -11.62, -1.68), (98.0, -10.99, -1.68), (108.0, -10.41, -1.68), (121.0, -10.10, -1.68)
], clearance=0.65)

# ③ 삼천리 도시가스관 (적색: 중앙~북측 D150 강관 & 남측 D200 강관)
pts_gas_d150 = adjust_pts_avoid_piles([
    (-4.0, 11.90, -1.68), ( 8.0, 11.68, -1.68), (19.0, 10.42, -1.73),
    (30.0, 10.15, -1.68), (42.0,  9.57, -1.87), (49.0,  9.32, -1.81),
    (60.0,  8.48, -1.78), (70.0,  9.02, -1.75), (84.0,  8.68, -1.91),
    (90.0,  8.22, -1.88), (98.0,  9.03, -1.88), (108.0,  9.78, -2.10),
    (121.0,  9.95, -2.10)
], clearance=0.55)

pts_gas_d200 = adjust_pts_avoid_piles([
    (-4.0,  1.95, -1.62), ( 8.0,  1.72, -1.62), (19.0,  0.77, -1.65),
    (30.0, -0.08, -1.65), (42.0, -0.53, -1.82), (49.0, -0.72, -1.76),
    (60.0, -7.25, -2.00), (70.0, -7.90, -1.72), (78.0, -7.50, -1.65),
    (84.0, -7.20, -1.65), (90.0, -7.10, -1.65), (98.0, -6.80, -1.65),
    (108.0, -6.20, -1.65), (121.0, -5.90, -1.65)
], clearance=0.58)

# ④ 하수관 — 우수/오수관 (황갈색: 북측 D1000 하수관 & 북측 D600 / 남측 D600 하수관)
pts_sewer_d1000 = adjust_pts_avoid_piles([
    (-4.0, 18.50, -1.92), ( 8.0, 18.33, -1.92), (19.0, 16.48, -1.95),
    (30.0, 16.35, -1.97), (42.0, 15.85, -2.32), (49.0, 15.48, -2.25),
    (60.0, 13.52, -2.45), (72.0, 13.40, -2.44)
], clearance=0.92)

pts_sewer_d600_n = adjust_pts_avoid_piles([
    (-4.0, 16.10, -1.88), ( 8.0, 15.88, -1.88), (19.0, 14.94, -1.92), (32.0, 14.50, -1.95)
], clearance=0.75)

pts_sewer_d600_s = adjust_pts_avoid_piles([
    (-4.0, -7.80, -2.15), ( 8.0, -7.91, -2.15), (19.0, -8.83, -2.27),
    (30.0, -9.05, -2.60), (42.0, -9.50, -2.87), (49.0, -9.69, -2.80),
    (70.0, -9.83, -1.93), (84.0, -9.45, -1.78), (98.0, -8.80, -1.78),
    (108.0, -8.20, -1.78), (121.0, -7.90, -1.78)
], clearance=0.75)

# ⑤ 통신관 (초록색: 북측 외벽 인접 100Øx16공 PVC 다공관 다발 & 중앙부 100Øx2/80Øx2 통신관)
pts_telecom_bundle_n = adjust_pts_avoid_piles([
    (-4.0, 22.10, -1.62), ( 8.0, 21.80, -1.62), (19.0, 21.92, -1.65),
    (30.0, 22.90, -1.62), (42.0, 22.46, -1.73), (49.0, 22.27, -1.67),
    (60.0, 23.37, -1.62), (70.0, 21.50, -1.62), (78.0, 20.80, -1.65),
    (84.0, 21.02, -1.68), (90.0, 21.55, -1.62), (98.0, 22.00, -1.62),
    (108.0, 22.50, -1.62), (121.0, 22.80, -1.62)
], clearance=0.65)

pts_telecom_mid = adjust_pts_avoid_piles([
    (-4.0,  7.40, -1.62), (19.0,  6.95, -1.62), (42.0,  6.40, -1.65),
    (60.0, 18.46, -1.71), (70.0, 19.24, -1.66), (84.0, 19.93, -1.70),
    (98.0, 20.50, -1.65), (121.0, 21.00, -1.65)
], clearance=0.65)

# ⑥ 한전 전력관 (노란색: 북측 150Øx2, 100Øx2 다발 & 중앙부 175Øx6공, 100Øx2, 50Øx1 다발)
pts_kepco_north = adjust_pts_avoid_piles([
    (24.0, 19.10, -1.62), (30.0, 19.02, -1.62), (42.0, 18.53, -1.65),
    (49.0, 18.31, -1.65), (60.0, 15.86, -1.65), (70.0, 16.00, -1.62),
    (78.0, 16.01, -1.62), (84.0, 16.26, -1.62), (90.0, 16.73, -1.62),
    (98.0, 17.97, -1.62), (112.0, 18.20, -1.62)
], clearance=0.68)

pts_kepco_center = adjust_pts_avoid_piles([
    (-4.0, 10.20, -1.68), (19.0,  9.40, -1.68), (42.0,  8.50, -1.68),
    (60.0,  7.20, -1.68), (78.0,  6.60, -1.68), (98.0,  6.10, -1.68),
    (121.0,  5.80, -1.68)
], clearance=0.75)

# ==============================================================================
# 5. 6대 지장물 관로 3D 메쉬 생성
# ==============================================================================
# 5-1. 광역상수도 (D900x11t, D500x11t)
v_ww900, f_ww900 = [], []
add_pipe_3d_polyline(v_ww900, f_ww900, pts_wide_d900, radius=0.450, n_seg=18)
create_mesh_obj("01A_지장물_광역상수관_D900x11t_강관_북측주간선", v_ww900, f_ww900, mat_wide_water, col_util)

v_ww500, f_ww500 = [], []
add_pipe_3d_polyline(v_ww500, f_ww500, pts_wide_d500, radius=0.250, n_seg=16)
create_mesh_obj("01B_지장물_광역상수관_D500x11t_강관_남측주간선", v_ww500, f_ww500, mat_wide_water, col_util)

# 5-2. 시상수도 (D900 3열 + D500 대각횡단 + D350 + D150)
v_cw900, f_cw900 = [], []
add_pipe_3d_polyline(v_cw900, f_cw900, pts_city_d900_n1,    radius=0.450, n_seg=18)
add_pipe_3d_polyline(v_cw900, f_cw900, pts_city_d900_n2,    radius=0.450, n_seg=18)
add_pipe_3d_polyline(v_cw900, f_cw900, pts_city_d900_n2_br, radius=0.450, n_seg=18)
add_pipe_3d_polyline(v_cw900, f_cw900, pts_city_d900_s,     radius=0.450, n_seg=18)
create_mesh_obj("02A_지장물_시상수관_D900_강관_남북주간선_4열", v_cw900, f_cw900, mat_city_water, col_util)

v_cw_sub, f_cw_sub = [], []
add_pipe_3d_polyline(v_cw_sub, f_cw_sub, pts_city_d500_diag, radius=0.250, n_seg=16)
add_pipe_3d_polyline(v_cw_sub, f_cw_sub, pts_city_d150_n,    radius=0.075, n_seg=12)
add_pipe_3d_polyline(v_cw_sub, f_cw_sub, pts_city_d350_s,    radius=0.175, n_seg=14)
create_mesh_obj("02B_지장물_시상수관_D500대각횡단_및_D350_D150", v_cw_sub, f_cw_sub, mat_city_water, col_util)

# 5-3. 삼천리 도시가스관 (D150, D200)
v_gas, f_gas = [], []
add_pipe_3d_polyline(v_gas, f_gas, pts_gas_d150, radius=0.075, n_seg=12)
add_pipe_3d_polyline(v_gas, f_gas, pts_gas_d200, radius=0.100, n_seg=14)
create_mesh_obj("03_지장물_삼천리도시가스관_D200_및_D150_강관", v_gas, f_gas, mat_city_gas, col_util)

# 5-4. 하수관 (우수/오수 D1000, D600)
v_sew, f_sew = [], []
add_pipe_3d_polyline(v_sew, f_sew, pts_sewer_d1000,  radius=0.500, n_seg=18)
add_pipe_3d_polyline(v_sew, f_sew, pts_sewer_d600_n, radius=0.300, n_seg=16)
add_pipe_3d_polyline(v_sew, f_sew, pts_sewer_d600_s, radius=0.300, n_seg=16)
create_mesh_obj("04_지장물_하수관_우수오수_D1000_및_D600", v_sew, f_sew, mat_sewer, col_util)

# 5-5. 통신관 다발 (100Øx16공 PVC 4x2 다공관 번들 + 중앙 100Øx2, 80Øx2 번들)
v_tel, f_tel = [], []
for dy_off in (-0.18, -0.06, 0.06, 0.18):
    for dz_off in (-0.06, 0.06):
        sub_pts = [(p[0], p[1] + dy_off, p[2] + dz_off) for p in pts_telecom_bundle_n]
        add_pipe_3d_polyline(v_tel, f_tel, sub_pts, radius=0.050, n_seg=8)
for dy_off, dz_off, r_t in [(-0.07, 0.04, 0.050), (0.07, 0.04, 0.050), (-0.07, -0.05, 0.040), (0.07, -0.05, 0.040)]:
    sub_pts = [(p[0], p[1] + dy_off, p[2] + dz_off) for p in pts_telecom_mid]
    add_pipe_3d_polyline(v_tel, f_tel, sub_pts, radius=r_t, n_seg=8)
create_mesh_obj("05_지장물_통신관_100x16공PVC_및_175공_다발관로", v_tel, f_tel, mat_telecom, col_util)

# 5-6. 한전 전력관 다발 (북측 150Øx2, 100Øx2 + 중앙부 175Øx6공, 100Øx2, 50Øx1 다발)
v_kep, f_kep = [], []
for dy_off, dz_off, r_k in [(-0.09, 0.05, 0.075), (0.09, 0.05, 0.075), (-0.08, -0.07, 0.050), (0.08, -0.07, 0.050)]:
    sub_pts = [(p[0], p[1] + dy_off, p[2] + dz_off) for p in pts_kepco_north]
    add_pipe_3d_polyline(v_kep, f_kep, sub_pts, radius=r_k, n_seg=10)
for dy_off in (-0.19, 0.0, 0.19):
    for dz_off in (-0.09, 0.09):
        sub_pts = [(p[0], p[1] + dy_off, p[2] + dz_off) for p in pts_kepco_center]
        add_pipe_3d_polyline(v_kep, f_kep, sub_pts, radius=0.0875, n_seg=10)
create_mesh_obj("06_지장물_한전전력관_175x6공_및_150x2공_다발관로", v_kep, f_kep, mat_kepco, col_util)

# ==============================================================================
# 6. 지장물 가시설 (지장물 매달기 및 받침보호공 상세) — 실제 주형보(main_girders, I-700x300)와의
#    정확한 2D 평면 교차점마다 100% 체결되도록 구현!
# ==============================================================================
dxf_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\0d917c24-0c73-469d-af45-411a71b292b9\scratch\cad_044.dxf"
with open(dxf_path, 'r', encoding='cp949', errors='replace') as f:
    dxf_lines = f.read().splitlines()

n_dxf = len(dxf_lines)
idx_d = 0
in_ent = False
cur_e = None
entities = []
while idx_d < n_dxf - 1:
    c_code = dxf_lines[idx_d].strip()
    c_val = dxf_lines[idx_d+1].strip()
    idx_d += 2
    if c_code == '0' and c_val == 'SECTION':
        if idx_d < n_dxf - 1 and dxf_lines[idx_d].strip() == '2':
            s_name = dxf_lines[idx_d+1].strip()
            idx_d += 2
            in_ent = (s_name == 'ENTITIES')
            continue
    elif c_code == '0' and c_val == 'ENDSEC':
        if cur_e and in_ent:
            entities.append(cur_e)
        cur_e = None
        in_ent = False
        continue
    if in_ent:
        if c_code == '0':
            if cur_e:
                entities.append(cur_e)
            cur_e = {'type': c_val, 'layer': '', 'x': [], 'y': []}
        elif cur_e is not None:
            if c_code == '8':
                cur_e['layer'] = c_val
            elif c_code in ('10', '11'):
                try:
                    cur_e['x'].append(float(c_val))
                except:
                    pass
            elif c_code in ('20', '21'):
                try:
                    cur_e['y'].append(float(c_val))
                except:
                    pass

line_segs = []
for e in entities:
    if e['layer'] == 'CE-LINE-STEL' and e['type'] in ('LWPOLYLINE', 'LINE') and len(e['x']) >= 2:
        mx, my = sum(e['x'])/len(e['x']), sum(e['y'])/len(e['y'])
        if 0 <= mx <= 205 and 20 <= my <= 100:
            pts = [(round(x - 26.8, 4), round(y - 52.0, 4)) for x, y in zip(e['x'], e['y'])]
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
        main_girders.append({'c1': c1, 'c2': c2})

typeA_stl_v,  typeA_stl_f  = [], []
typeA_rod_v,  typeA_rod_f  = [], []
typeA_wood_v, typeA_wood_f = [], []

typeB_stl_v,  typeB_stl_f  = [], []
typeB_rod_v,  typeB_rod_f  = [], []
typeB_wood_v, typeB_wood_f = [], []

typeC_stl_v,  typeC_stl_f  = [], []
typeC_rod_v,  typeC_rod_f  = [], []
typeC_wood_v, typeC_wood_f = [], []

cnt_hanger_A = 0
cnt_hanger_B = 0
cnt_hanger_C = 0

type_a_lines = [
    (pts_wide_d900,       0.450),
    (pts_wide_d500,       0.250),
    (pts_city_d900_n1,    0.450),
    (pts_city_d900_n2,    0.450),
    (pts_city_d900_n2_br, 0.450),
    (pts_city_d900_s,     0.450),
    (pts_city_d500_diag,  0.250),
]

type_b_lines = [
    (pts_gas_d150,     0.075),
    (pts_gas_d200,     0.100),
    (pts_sewer_d1000,  0.500),
    (pts_sewer_d600_n, 0.300),
    (pts_sewer_d600_s, 0.300),
    (pts_city_d150_n,  0.075),
    (pts_city_d350_s,  0.175),
]

type_c_lines = [
    (pts_telecom_bundle_n, 0.24, 0.12),
    (pts_telecom_mid,      0.14, 0.10),
    (pts_kepco_north,      0.18, 0.13),
    (pts_kepco_center,     0.29, 0.18),
]

# 모든 실제 주형보(I-700x300, main_girders) 선분과 각 지장물 노선의 교차점마다 매달기 가시설 생성!
for mg in main_girders:
    c1, c2 = mg['c1'], mg['c2']
    if math.hypot(c2[0] - c1[0], c2[1] - c1[1]) < 1.5:
        continue

    # 1) Type A 대구경 상수관/광역상수관 3단 프레임 매달기 가시설
    for pts_l, rad_l in type_a_lines:
        for (ix, iy, iz, ux_g, uy_g) in intersect_girder_and_polyline(c1, c2, pts_l):
            add_type_a_frame_hanger(
                typeA_stl_v, typeA_stl_f,
                typeA_rod_v, typeA_rod_f,
                typeA_wood_v, typeA_wood_f,
                ix, iy, iz, rad_l, ux_g, uy_g, z_girder_bot=-0.90
            )
            cnt_hanger_A += 1

    # 2) Type B 가스관·하수관·소구경 상수관 강봉 달대 + ㄷ형강 받침보 매달기 가시설
    for pts_l, rad_l in type_b_lines:
        for (ix, iy, iz, ux_g, uy_g) in intersect_girder_and_polyline(c1, c2, pts_l):
            add_type_b_rod_hanger(
                typeB_stl_v, typeB_stl_f,
                typeB_rod_v, typeB_rod_f,
                typeB_wood_v, typeB_wood_f,
                ix, iy, iz, rad_l, ux_g, uy_g, z_girder_bot=-0.90
            )
            cnt_hanger_B += 1

    # 3) Type C 통신관·한전전력관 다공관 박스형 보호틀 매달기 가시설
    for pts_l, hw, hh in type_c_lines:
        for (ix, iy, iz, ux_g, uy_g) in intersect_girder_and_polyline(c1, c2, pts_l):
            add_type_c_duct_box_hanger(
                typeC_stl_v, typeC_stl_f,
                typeC_rod_v, typeC_rod_f,
                typeC_wood_v, typeC_wood_f,
                ix, iy, iz, hw, hh, ux_g, uy_g, z_girder_bot=-0.90
            )
            cnt_hanger_C += 1

# 대구경 지장물(Type A)의 매달기 프레임을 종방향으로 서로 연결하여 흔들림을 방지하는
# '지장물 매달기 종방향 연결보(2-ㄷ100x50 / L-90x90)'도 하단에 연속 설치!
for pts_l, rad_l in [(pts_wide_d900, 0.450), (pts_wide_d500, 0.250), (pts_city_d900_n2, 0.450), (pts_city_d900_s, 0.450)]:
    for idx in range(len(pts_l) - 1):
        p1, p2 = pts_l[idx], pts_l[idx+1]
        if p1[0] >= 2.0 and p2[0] <= 116.0:
            for s_sign in (-1.0, 1.0):
                off = s_sign * (rad_l + 0.055)
                q1 = (p1[0], p1[1] + off)
                q2 = (p2[0], p2[1] + off)
                z_mid = 0.5*(p1[2] + p2[2]) - rad_l - 0.05
                add_box_segment_3d(typeA_stl_v, typeA_stl_f, q1, q2, z_mid - 0.04, z_mid + 0.04, 0.08)

create_mesh_obj(f"07A_지장물가시설_대구경상수관_3단매달기프레임_찬넬및받침보_{cnt_hanger_A}개소", typeA_stl_v, typeA_stl_f, mat_hanger_stl, col_util)
create_mesh_obj(f"07B_지장물가시설_대구경상수관_주형보후크클램프및체결핀_{cnt_hanger_A}개소", typeA_rod_v, typeA_rod_f, mat_hanger_rod, col_util)
create_mesh_obj(f"07C_지장물가시설_대구경상수관_삼각쐐기받침목_고임목_{cnt_hanger_A}개소", typeA_wood_v, typeA_wood_f, mat_wedge_wood, col_util)

create_mesh_obj(f"08A_지장물가시설_가스하수관_하부받침ㄷ형강및C클램프_{cnt_hanger_B}개소", typeB_stl_v, typeB_stl_f, mat_hanger_stl, col_util)
create_mesh_obj(f"08B_지장물가시설_가스하수관_수직강봉달대_행거볼트_{cnt_hanger_B}개소", typeB_rod_v, typeB_rod_f, mat_hanger_rod, col_util)
create_mesh_obj(f"08C_지장물가시설_가스하수관_관보호새들받침목_{cnt_hanger_B}개소", typeB_wood_v, typeB_wood_f, mat_wedge_wood, col_util)

create_mesh_obj(f"09A_지장물가시설_통신전력다공관_박스형보호틀받침찬넬_{cnt_hanger_C}개소", typeC_stl_v, typeC_stl_f, mat_hanger_stl, col_util)
create_mesh_obj(f"09B_지장물가시설_통신전력다공관_수직강봉달대_{cnt_hanger_C}개소", typeC_rod_v, typeC_rod_f, mat_hanger_rod, col_util)
create_mesh_obj(f"09C_지장물가시설_통신전력다공관_상부목재보호커버_{cnt_hanger_C}개소", typeC_wood_v, typeC_wood_f, mat_wedge_wood, col_util)

# ==============================================================================
# 7. 초기 굴착 바닥면 레벨을 Z = -3.80m (2단 버팀보 GL-3.895m 직상부)로 유지하여
#    대구경 상수관(D900) 하부 매달기 받침보(Z = -3.45m)까지 공중에 선명하게 매달린 상태 구현!
# ==============================================================================
col_exc = bpy.data.collections.get("00A_정거장_단계별굴착_원지반토사면_및_단별토류판")
if col_exc:
    for o in list(col_exc.objects):
        if "00A_초기굴착바닥" in o.name:
            for v in o.data.vertices:
                if v.co.z < -2.50:
                    v.co.z = -3.80
            o.data.update()
            o.name = "00A_초기굴착바닥_Mistrut및지장물매달기_무지보대공간_Z-3.80m"
        elif "03C_토류판" in o.name or "02_엄지말뚝" in o.name or "08_중간말뚝" in o.name:
            for v in o.data.vertices:
                if v.co.z < -3.00:
                    v.co.z = -3.80
            o.data.update()

# 컬렉션 가시성 확인 (정거장 + Mistrut + 지장물 가시설 ON)
keep_cols = {
    "106_Station_BIM_CAD044",
    "00_가시설_외벽엄지말뚝_차수_토류판",
    "00A_정거장_단계별굴착_원지반토사면_및_단별토류판",
    "01A_가시설_복공판_주형보_주형지지보_피스브라켓_상세",
    "01M_가시설_Mistrut공법_1단버팀보대체_상세",
    "01U_가시설_지장물현황_및_지장물매달기보호공_상세",
}
for c in bpy.data.collections:
    c.hide_viewport = (c.name not in keep_cols)
    c.hide_render   = (c.name not in keep_cols)

# 뷰포트 카메라를 복공 하부 주형보 스팬 사이 열린 공간(Z=-2.10m)에 배치하여
# Mistrut + 주형보 + 6대 지장물 관로 + 3종 매달기 가시설이 가림 없이 한눈에 보이도록 세팅!
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
                    r3d.view_location = Vector((36.5, 13.5, -2.10))
                    r3d.view_rotation = Euler((math.radians(85), 0.0, math.radians(-58))).to_quaternion()
                    r3d.view_distance = 6.5
                    r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=blend_save_path)
print(f"SUCCESS: Built 6 Utility Systems & 3 Types of Hanging Protection Structures (A={cnt_hanger_A}, B={cnt_hanger_B}, C={cnt_hanger_C})!")
