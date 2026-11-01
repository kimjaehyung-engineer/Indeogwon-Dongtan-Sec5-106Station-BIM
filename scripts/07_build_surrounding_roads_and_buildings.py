import bpy
import bmesh
import os
import json
import math
from mathutils import Vector, Euler, Matrix

# ==============================================================================
# 106정거장 주변 도로 현황 (왕복 8차선 간선도로, 사거리 교차로, 남·북 이면도로,
# 차선 도색, 횡단보도, 보도블록, 화강석 경계석, 가로수, 지상 맨홀 178개소, 공사장 가설방음벽/PE방호벽)
# 및 인접 현황 건물 15개 단지/빌딩 (국가전문행정연수원(B1), 경기도자료관(B1), 아이파크 101·102동(B1),
# 유카(B1), 송정각(B1), 1125(B1), 대영빌딩(B1), 뉴서울주유소(B1), 아주한방병원(B1) 등 지상층 + 지하B1층)
# CAD 원본 블록(CZDIMA125, 8,848 entities) 1:1 좌표 연동 3D BIM 구현 스크립트
# ==============================================================================

dxf_site_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\719438c6-31b4-4b93-b6b5-93042eba0916\scratch\site_dwg_3.dxf"
json_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\0d917c24-0c73-469d-af45-411a71b292b9\scratch\cad_044_data.json"
blend_save_path = r"C:\Users\20040178\Desktop\2영역\토스앤\1.설계변경관리\2.인덕원동탄5공구\7.정거장 구조물 원가개선\정거장 가시설도, 구조도\106정거장_가시설_전체구간_3D_BIM.blend"

with open(json_path, 'r', encoding='utf-8') as f:
    cad = json.load(f)

ow_loop = cad['outer_wale_loop']

# ==============================================================================
# 1. 재질(Materials) 정의 — 아스팔트 도로, 차선, 보도블록, 경계석, 가로수, 방음벽, 인접건물(지상/지하B1)
# ==============================================================================
def make_mat(name, rgba, metallic=0.15, roughness=0.65, alpha=1.0):
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
    if alpha < 0.999:
        if hasattr(m, "blend_method"):
            m.blend_method = 'BLEND'
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = 'BLENDED'
    m.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    return m

mat_asphalt     = make_mat("MAT_Site_Road_Asphalt",       (0.16, 0.17, 0.19), metallic=0.05, roughness=0.82) # 아스팔트 차도 포장
mat_sidewalk    = make_mat("MAT_Site_Sidewalk_Paver",     (0.68, 0.64, 0.58), metallic=0.05, roughness=0.75) # 보도블록 포장
mat_curb_stone  = make_mat("MAT_Site_Granite_Curb",       (0.80, 0.80, 0.78), metallic=0.10, roughness=0.60) # 화강석 도로경계석
mat_lane_white  = make_mat("MAT_Site_Lane_White",         (0.95, 0.96, 0.96), metallic=0.10, roughness=0.40) # 백색 차선 / 횡단보도 / 정지선
mat_lane_yellow = make_mat("MAT_Site_Lane_Yellow",        (0.96, 0.76, 0.08), metallic=0.15, roughness=0.40) # 황색 복선 중앙선
mat_lane_bus    = make_mat("MAT_Site_Lane_BusBlue",       (0.15, 0.52, 0.92), metallic=0.15, roughness=0.40) # 청색 버스전용차로선
mat_cad_line    = make_mat("MAT_Site_CAD_TopoLine",       (0.42, 0.46, 0.50), metallic=0.20, roughness=0.50) # CAD 지형도 원본 선형
mat_manhole_top = make_mat("MAT_Site_Manhole_CastIron",   (0.28, 0.30, 0.33), metallic=0.75, roughness=0.35) # 지상 맨홀 뚜껑 (우/오/E/T/가스)
mat_tree_trunk  = make_mat("MAT_Site_Tree_Trunk",         (0.38, 0.25, 0.14), metallic=0.05, roughness=0.85) # 가로수 수간
mat_tree_leaf   = make_mat("MAT_Site_Tree_Canopy",        (0.22, 0.56, 0.24), metallic=0.05, roughness=0.75) # 가로수 수관
mat_fence_panel = make_mat("MAT_Site_RPP_SoundWall",      (0.86, 0.90, 0.94), metallic=0.25, roughness=0.35, alpha=0.72) # 공사장 RPP 가설방음벽
mat_pe_barrier  = make_mat("MAT_Site_PE_Barrier_Orange",  (0.95, 0.36, 0.08), metallic=0.15, roughness=0.45) # PE 방호벽 / 차선규제봉
mat_bldg_apt    = make_mat("MAT_Site_Bldg_IPARK_Apt",     (0.84, 0.86, 0.89), metallic=0.20, roughness=0.45, alpha=0.78) # 아이파크 아파트 단지 (반투명)
mat_bldg_pub    = make_mat("MAT_Site_Bldg_PublicInst",    (0.74, 0.80, 0.86), metallic=0.25, roughness=0.42, alpha=0.78) # 경기도자료관 / 국가전문행정연수원
mat_bldg_comm   = make_mat("MAT_Site_Bldg_Commercial",    (0.86, 0.80, 0.72), metallic=0.20, roughness=0.48, alpha=0.78) # 남측 인접 상가·빌딩(유카/송정각/1125/대영빌딩)
mat_bldg_slab   = make_mat("MAT_Site_Bldg_FloorSlabLine", (0.35, 0.40, 0.46), metallic=0.45, roughness=0.35) # 건물 층간 슬래브 띠 & 옥상 파라펫
mat_bldg_b1     = make_mat("MAT_Site_Bldg_Basement_B1",   (0.90, 0.28, 0.22), metallic=0.25, roughness=0.45, alpha=0.58) # 지하 1층(B1) 근접기초 (리스크 검토용 반투명 적색)
mat_label_text  = make_mat("MAT_Site_Bldg_LabelGold",     (1.00, 0.88, 0.22), metallic=0.55, roughness=0.25) # 건물명 3D 라벨

# ==============================================================================
# 2. 기하 생성 헬퍼 함수
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

def add_cylinder_3d(verts, faces, cx, cy, z_bot, z_top, radius, n_seg=12):
    base = len(verts)
    for zv in (z_bot, z_top):
        for k in range(n_seg):
            ang = 2.0 * math.pi * k / n_seg
            verts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang), zv))
    for k in range(n_seg):
        kn = (k + 1) % n_seg
        faces.append((base + k, base + kn, base + n_seg + kn, base + n_seg + k))
    faces.append(tuple(base + k for k in range(n_seg - 1, -1, -1)))
    faces.append(tuple(base + n_seg + k for k in range(n_seg)))

def add_building_with_floors(
    bldg_v, bldg_f, slab_v, slab_f, b1_v, b1_f,
    poly_2d, n_floors_above=3, floor_h=3.4, b1_depth=4.5
):
    """
    인접 현황 건물 3D 매스 생성:
    - 지상층(Z = 0.0 ~ n_floors_above * floor_h): 외벽 매스 + 층간 슬래브 라인 + 옥상 파라펫(높이 1.1m)
    - 지하층(b1_depth > 0 인 경우 Z = -b1_depth ~ 0.0): 지하 1층(B1) 기초 및 지하 외벽 매스
    """
    z_roof = n_floors_above * floor_h
    add_polygon_slab_bm(bldg_v, bldg_f, poly_2d, 0.0, z_roof)
    # 층간 슬래브 띠 & 옥상 파라펫 테두리
    n_p = len(poly_2d)
    for fl in range(1, n_floors_above + 1):
        zf = fl * floor_h
        for k in range(n_p):
            p1, p2 = poly_2d[k], poly_2d[(k + 1) % n_p]
            add_box_segment_3d(slab_v, slab_f, p1, p2, zf - 0.18, zf + 0.05, 0.35)
    # 옥상 난간/파라펫 벽체
    for k in range(n_p):
        p1, p2 = poly_2d[k], poly_2d[(k + 1) % n_p]
        add_box_segment_3d(slab_v, slab_f, p1, p2, z_roof, z_roof + 1.05, 0.28)
    # 지하 1층(B1) 구조물 매스 및 기초 슬래브
    if b1_depth > 0.1:
        add_polygon_slab_bm(b1_v, b1_f, poly_2d, -b1_depth, -0.05)
        for k in range(n_p):
            p1, p2 = poly_2d[k], poly_2d[(k + 1) % n_p]
            add_box_segment_3d(slab_v, slab_f, p1, p2, -b1_depth - 0.30, -b1_depth, 0.45)

# ==============================================================================
# 3. 주변 도로 및 인접 현황 전용 컬렉션 준비
# ==============================================================================
root_col = bpy.data.collections.get("106_Station_BIM_CAD044")
if not root_col:
    root_col = bpy.context.scene.collection

col_site_name = "02S_주변도로현황_교차로_보도_가설방음벽_및_인접건물현황_상세"
col_site = bpy.data.collections.get(col_site_name)
if not col_site:
    col_site = bpy.data.collections.new(col_site_name)
    root_col.children.link(col_site)
col_site.hide_viewport = False
col_site.hide_render   = False

for o in list(col_site.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ==============================================================================
# 4. CAD 원본 지형 블록(CZDIMA125)에서 도로 경계·지적선·지상 맨홀(178개소) 추출 및 3D 구현
# ==============================================================================
cz_segs = []
ce_segs = []
ce_circles = []

if os.path.exists(dxf_site_path):
    with open(dxf_site_path, 'r', encoding='cp949', errors='replace') as f:
        lines = f.read().splitlines()
    n = len(lines)
    i = 0
    in_blocks = False
    cur_b = None
    cur_e = None
    while i < n - 1:
        c = lines[i].strip()
        v = lines[i+1].strip()
        i += 2
        if c == '0' and v == 'SECTION':
            if i < n - 1 and lines[i].strip() == '2':
                sn = lines[i+1].strip()
                i += 2
                in_blocks = (sn == 'BLOCKS')
                continue
        elif c == '0' and v == 'ENDSEC':
            in_blocks = False
            continue
        if in_blocks:
            if c == '0' and v == 'BLOCK':
                cur_b = ''
                while i < n - 1:
                    bc = lines[i].strip()
                    bv = lines[i+1].strip()
                    i += 2
                    if bc == '2': cur_b = bv
                    elif bc == '0':
                        i -= 2
                        break
            elif c == '0' and v == 'ENDBLK':
                cur_b = None
                cur_e = None
            elif cur_b == 'CZDIMA125':
                if c == '0':
                    if cur_e:
                        if cur_e['type'] == 'LINE' and len(cur_e['x']) >= 2:
                            p1 = (cur_e['x'][0] + 69.7914, cur_e['y'][0] + 6.8534)
                            p2 = (cur_e['x'][1] + 69.7914, cur_e['y'][1] + 6.8534)
                            if (-85 <= p1[0] <= 215 and -68 <= p1[1] <= 82) or (-85 <= p2[0] <= 215 and -68 <= p2[1] <= 82):
                                if cur_e['layer'] == 'CZ-BASE':
                                    cz_segs.append((p1, p2))
                                else:
                                    ce_segs.append((p1, p2))
                        elif cur_e['type'] == 'CIRCLE' and cur_e['x']:
                            cx = cur_e['x'][0] + 69.7914
                            cy = cur_e['y'][0] + 6.8534
                            if -85 <= cx <= 215 and -68 <= cy <= 82 and 0.15 <= cur_e['r'] <= 2.5:
                                ce_circles.append((cx, cy, cur_e['r']))
                    cur_e = {'type': v, 'layer': '', 'x': [], 'y': [], 'r': 0.0}
                elif cur_e is not None:
                    if c == '8': cur_e['layer'] = v
                    elif c == '40':
                        try: cur_e['r'] = float(v)
                        except: pass
                    elif c in ('10', '11'):
                        try: cur_e['x'].append(float(v))
                        except: pass
                    elif c in ('20', '21'):
                        try: cur_e['y'].append(float(v))
                        except: pass

# CAD 원본 지형/도로/지적선 3D 입체 기준선 생성
topo_v, topo_f = [], []
for p1, p2 in ce_segs:
    add_box_segment_3d(topo_v, topo_f, p1, p2, 0.01, 0.04, 0.08)
for p1, p2 in cz_segs:
    add_box_segment_3d(topo_v, topo_f, p1, p2, 0.01, 0.05, 0.10)
create_mesh_obj(f"06_CAD원본_주변도로경계_및_인접건물지적선_{len(ce_segs)+len(cz_segs)}SEG", topo_v, topo_f, mat_cad_line, col_site)

# ==============================================================================
# 5. 주변 도로 현황 (왕복 8차선 간선도로 + 서측 사거리 교차로 + 남·북 이면도로 아스팔트 포장)
#    * 주의: 정거장 개착구간(X = 1.1m ~ 117.1m, Y = -6.5m ~ +22.5m)은 복공판 및 하부 굴착부가
#      선명히 보이도록 차도 메쉬에서 정확히 개구(Cutout) 처리하여 복공판과 매끄럽게 연결!
# ==============================================================================
road_v, road_f = [], []

# 5-1. 서측 간선도로 (인덕원 방면: X = -85m ~ +1.2m, Y = -8.0m ~ +27.5m)
poly_road_west = [
    (-85.0, -5.5), (-35.0, -6.5), (1.2, -7.2),
    (4.1, 25.7), (-35.0, 26.8), (-85.0, 28.5)
]
add_polygon_slab_bm(road_v, road_f, poly_road_west, -0.12, -0.01)

# 5-2. 동측 간선도로 (동탄 방면: X = 116.5m ~ +215.0m, Y = -6.5m ~ +29.5m)
poly_road_east = [
    (116.5, -5.8), (160.0, -3.5), (215.0, 1.5),
    (215.0, 32.5), (160.0, 28.5), (114.5, 27.8)
]
add_polygon_slab_bm(road_v, road_f, poly_road_east, -0.12, -0.01)

# 5-3. 서측 사거리 교차로 남·북 직교 도로 (X = -62m ~ -34m, Y = -65m ~ +75m)
poly_cross_west_s = [(-62.0, -65.0), (-34.0, -65.0), (-34.0, -5.5), (-62.0, -5.0)]
poly_cross_west_n = [(-62.0, 26.5), (-34.0, 26.0), (-30.0, 75.0), (-58.0, 75.0)]
add_polygon_slab_bm(road_v, road_f, poly_cross_west_s, -0.12, -0.01)
add_polygon_slab_bm(road_v, road_f, poly_cross_west_n, -0.12, -0.01)

# 5-4. 정거장 중앙 남측 이면도로 (유카(B1) ~ 송정각(B1) 사이 도로: X = 42m ~ 59m, Y = -65m ~ -7.5m)
poly_branch_south = [(41.5, -65.0), (59.5, -65.0), (59.5, -7.8), (41.5, -7.8)]
add_polygon_slab_bm(road_v, road_f, poly_branch_south, -0.12, -0.01)

# 5-5. 정거장 북측 진입 이면도로 2개소 (행정연수원~경기도자료관 사이 X=16~29m, 경기도자료관~아이파크 사이 X=76~88m)
poly_branch_north1 = [(16.0, 24.5), (29.0, 24.0), (31.0, 75.0), (18.0, 75.0)]
poly_branch_north2 = [(75.0, 27.5), (87.0, 28.0), (92.0, 75.0), (80.0, 75.0)]
add_polygon_slab_bm(road_v, road_f, poly_branch_north1, -0.12, -0.01)
add_polygon_slab_bm(road_v, road_f, poly_branch_north2, -0.12, -0.01)

# 5-6. 동측 교차 이면도로 (뉴서울주유소 ~ 강남면옥 사이: X = 152m ~ 164m, Y = -65m ~ -2.5m)
poly_branch_east_s = [(151.0, -65.0), (163.0, -65.0), (163.0, -2.5), (151.0, -3.5)]
add_polygon_slab_bm(road_v, road_f, poly_branch_east_s, -0.12, -0.01)

create_mesh_obj("01_주변도로_왕복8차선간선도로_사거리교차로_및_이면도로_아스팔트포장", road_v, road_f, mat_asphalt, col_site)

# ==============================================================================
# 6. 차선 도색 (중앙선 황색 복선, 왕복 8차선 백색 차선, 버스전용차로, 정지선, 횡단보도 4개소)
# ==============================================================================
yel_v, yel_f = [], []
wht_v, wht_f = [], []
bus_v, bus_f = [], []

def road_center_y(x):
    # 도로 중심선 Y(x) 선형
    if x < 0.0:
        return 9.5 - 0.02 * x
    elif x <= 60.0:
        return 9.5 - 0.035 * x
    elif x <= 120.0:
        return 7.4 + 0.055 * (x - 60.0)
    else:
        return 10.7 + 0.065 * (x - 120.0)

# 서측 구간(X = -82m ~ -2m) 및 동측 구간(X = 118m ~ 210m) 본선 차선 도색
for x_start, x_end in [(-82.0, -35.0), (-32.0, 0.5), (117.5, 210.0)]:
    steps = int((x_end - x_start) / 4.0)
    for s in range(steps):
        x1 = x_start + s * 4.0
        x2 = x1 + 4.0
        yc1, yc2 = road_center_y(x1), road_center_y(x2)
        # 1) 중앙선 황색 복선
        for dy_c in (-0.18, 0.18):
            add_box_segment_3d(yel_v, yel_f, (x1, yc1 + dy_c), (x2, yc2 + dy_c), -0.005, 0.015, 0.15)
        # 2) 상·하행 일반 차선 (백색 점선: 3.2m 간격 4차선)
        for lane_idx in (1, 2, 3):
            for sign_l in (-1.0, 1.0):
                ly1 = yc1 + sign_l * (lane_idx * 3.35)
                ly2 = yc2 + sign_l * (lane_idx * 3.35)
                xm = x1 + 2.2
                ym = yc1 + (yc2 - yc1) * 0.55 + sign_l * (lane_idx * 3.35)
                add_box_segment_3d(wht_v, wht_f, (x1, ly1), (xm, ym), -0.005, 0.015, 0.15)
        # 3) 버스전용차로 청색 실선 (가장 바깥 차로 안쪽 ±10.05m)
        for sign_l in (-1.0, 1.0):
            by1 = yc1 + sign_l * 10.05
            by2 = yc2 + sign_l * 10.05
            add_box_segment_3d(bus_v, bus_f, (x1, by1), (x2, by2), -0.005, 0.015, 0.22)
        # 4) 길가장자리 백색 실선 (±13.4m)
        for sign_l in (-1.0, 1.0):
            ey1 = yc1 + sign_l * 13.40
            ey2 = yc2 + sign_l * 13.40
            add_box_segment_3d(wht_v, wht_f, (x1, ey1), (x2, ey2), -0.005, 0.015, 0.18)

# 횡단보도 (Zebra Crosswalks — CAD 도면 사거리 및 이면도로 교차부 4개소!)
# ① 서측 사거리 동측 횡단보도 (X = -31.0m ~ -26.0m, Y = -5.5m ~ +25.5m)
for y_st in range(-5, 25):
    if y_st % 1 == 0:
        add_box_segment_3d(wht_v, wht_f, (-31.0, float(y_st)), (-26.0, float(y_st)), -0.004, 0.018, 0.45)
add_box_segment_3d(wht_v, wht_f, (-24.0, -5.5), (-24.0, 9.5), -0.004, 0.018, 0.45) # 정지선

# ② 동측 정거장 종점부 횡단보도 (X = 120.0m ~ 125.0m, Y = -5.0m ~ +27.0m)
for y_st in range(-4, 27):
    add_box_segment_3d(wht_v, wht_f, (120.0, float(y_st)), (125.0, float(y_st)), -0.004, 0.018, 0.45)
add_box_segment_3d(wht_v, wht_f, (118.2, 10.5), (118.2, 27.0), -0.004, 0.018, 0.45) # 정지선

# ③ 중앙 남측 이면도로 횡단보도 (X = 42.5m ~ 58.5m, Y = -11.5m ~ -8.5m)
for x_st in range(43, 59):
    add_box_segment_3d(wht_v, wht_f, (float(x_st), -11.8), (float(x_st), -8.2), -0.004, 0.018, 0.45)

# ④ 북측 진입도로 횡단보도 (X = 17.0m ~ 28.0m, Y = 24.8m ~ 28.0m 및 X = 76.0m ~ 86.0m, Y = 28.2m ~ 31.4m)
for x_st in range(17, 29):
    add_box_segment_3d(wht_v, wht_f, (float(x_st), 25.0), (float(x_st), 28.2), -0.004, 0.018, 0.42)
for x_st in range(76, 87):
    add_box_segment_3d(wht_v, wht_f, (float(x_st), 28.2), (float(x_st), 31.4), -0.004, 0.018, 0.42)

create_mesh_obj("02A_도로차선_횡단보도_정지선_백색도색", wht_v, wht_f, mat_lane_white, col_site)
create_mesh_obj("02B_도로차선_중앙선_황색복선도색", yel_v, yel_f, mat_lane_yellow, col_site)
create_mesh_obj("02C_도로차선_버스전용차로_청색도색", bus_v, bus_f, mat_lane_bus, col_site)

# ==============================================================================
# 7. 양측 보도(Sidewalk) 블록 및 화강석 도로경계석(Curb)
# ==============================================================================
sw_v, sw_f = [], []
curb_v, curb_f = [], []

# 북측 보도 구간 3블록 (교차로/이면도로 사이 보도 구간)
north_sw_blocks = [
    [(-33.5, 26.5), (15.5, 24.8), (15.5, 31.5), (-33.5, 33.0)],
    [(29.5, 22.8), (54.0, 22.8), (62.5, 28.0), (74.5, 28.0), (74.5, 34.0), (29.5, 33.5)],
    [(87.5, 28.8), (145.0, 28.8), (210.0, 32.8), (210.0, 38.5), (145.0, 35.0), (87.5, 35.0)],
]
# 남측 보도 구간 3블록 (외벽 남측 ~ 인접 상가/빌딩 전면 보도)
south_sw_blocks = [
    [(-33.5, -13.0), (41.0, -13.0), (41.0, -8.2), (-33.5, -6.5)],
    [(60.0, -15.0), (150.5, -12.0), (150.5, -6.2), (60.0, -9.2)],
    [(163.5, -10.0), (210.0, -5.0), (210.0, 0.5), (163.5, -3.5)],
]

for blk in north_sw_blocks + south_sw_blocks:
    add_polygon_slab_bm(sw_v, sw_f, blk, 0.0, 0.16)
    for k in range(len(blk)):
        p1, p2 = blk[k], blk[(k + 1) % len(blk)]
        add_box_segment_3d(curb_v, curb_f, p1, p2, 0.0, 0.20, 0.22)

create_mesh_obj("03A_양측보도_보행자보도블록_포장", sw_v, sw_f, mat_sidewalk, col_site)
create_mesh_obj("03B_양측보도_화강석도로경계석_연석", curb_v, curb_f, mat_curb_stone, col_site)

# ==============================================================================
# 8. 지상 맨홀 뚜껑 178개소 (CAD CZDIMA125 실제 좌표) 및 가로수 (보도 식수대)
# ==============================================================================
mh_v, mh_f = [], []
for (cx, cy, r_c) in ce_circles:
    # 정거장 내부 굴착 구역 밖의 지상 맨홀 및 복공판 위 맨홀 표시
    add_cylinder_3d(mh_v, mh_f, cx, cy, 0.01, 0.06, max(0.35, min(0.75, r_c)), n_seg=12)
create_mesh_obj(f"04A_지상맨홀_우수오수한전통신가스_및_교통신호제어기_{len(ce_circles)}개소", mh_v, mh_f, mat_manhole_top, col_site)

trunk_v, trunk_f = [], []
leaf_v, leaf_f   = [], []
tree_positions = []
# 북측 보도 가로수 열
for xt in range(-28, 200, 14):
    if 14 <= xt <= 31 or 55 <= xt <= 88:
        continue
    yt = 29.8 if xt < 60 else 32.2
    tree_positions.append((float(xt), yt))
# 남측 보도 가로수 열
for xt in range(-28, 200, 14):
    if 38 <= xt <= 64 or 148 <= xt <= 166:
        continue
    yt = -10.8 if xt < 60 else -11.2
    tree_positions.append((float(xt), yt))

for (tx, ty) in tree_positions:
    add_cylinder_3d(trunk_v, trunk_f, tx, ty, 0.16, 2.60, 0.16, n_seg=8)
    add_cylinder_3d(leaf_v, leaf_f,   tx, ty, 2.20, 4.80, 1.45, n_seg=10)
    add_cylinder_3d(leaf_v, leaf_f,   tx, ty, 4.20, 5.80, 0.95, n_seg=10)

create_mesh_obj(f"04B_가로수_수간_및_보호틀_{len(tree_positions)}주", trunk_v, trunk_f, mat_tree_trunk, col_site)
create_mesh_obj(f"04C_가로수_수관_녹지대_{len(tree_positions)}주", leaf_v, leaf_f, mat_tree_leaf, col_site)

# ==============================================================================
# 9. 공사구간 단계별 교통처리 안전시설 — 가설방음벽(RPP H=3.0m) 및 PE 방호벽
#    - 정거장 외벽 테두리(보도 인접 구간)를 따라 가설방음펜스 및 PE 방호블록 설치
# ==============================================================================
fence_v, fence_f = [], []
pe_v, pe_f       = [], []

for k in range(len(ow_loop) - 1):
    p1, p2 = ow_loop[k], ow_loop[k+1]
    L_seg = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if L_seg < 1.0:
        continue
    # 서측/동측 본선 차량 통행 방향(남북 횡단 변: X≈2m 또는 X≈116m)은 차량이 복공판으로 진입하므로 방음벽 제외!
    if abs(p2[0] - p1[0]) < 3.5 and L_seg > 15.0:
        continue
    # 남·북 외벽 보도 경계선을 따라 PE 방호벽(높이 0.85m) + 상부 RPP 가설방음판(높이 2.8m) 설치
    add_box_segment_3d(pe_v, pe_f,       p1, p2, 0.0, 0.85, 0.45)
    add_box_segment_3d(fence_v, fence_f, p1, p2, 0.85, 3.00, 0.12)

create_mesh_obj("05A_공사구간_단계별교통처리_RPP가설방음벽_H3.0m", fence_v, fence_f, mat_fence_panel, col_site)
create_mesh_obj("05B_공사구간_단계별교통처리_PE방호벽_안전펜스", pe_v, pe_f, mat_pe_barrier, col_site)

# ==============================================================================
# 10. 인접 현황 건물 15개 단지/빌딩 (CAD CZDIMA125 및 106정거장 일반도 기준)
#     - 지상 건축 매스 + 층간 슬래브 라인 + 지하 1층(B1) 근접기초 구조물 + 3D 건물명 라벨!
# ==============================================================================
apt_v,  apt_f  = [], []
pub_v,  pub_f  = [], []
comm_v, comm_f = [], []
slab_v, slab_f = [], []
b1_v,   b1_f   = [], []

# 10-1. 북측 인접 현황 건물군 (국가전문행정연수원(B1), 경기도자료관(B1), 유리세차장, 아이파크 101동/102동(B1))
north_buildings = [
    # (건물명, 폴리곤 좌표, 지상층수, 층고, 지하층깊이 B1, 분류)
    ("국가전문행정연수원(B1)", [(-48.0, 36.0), (11.0, 34.0), (11.0, 66.0), (-48.0, 68.0)], 5, 3.6, 4.5, "PUB"),
    ("경기도자료관(B1)",       [(33.0, 35.5), (73.5, 35.0), (73.5, 66.0), (33.0, 66.5)], 4, 3.8, 4.5, "PUB"),
    ("유리세차장(북측)",       [(86.5, 35.5), (101.0, 35.5), (101.0, 46.5), (86.5, 46.5)], 2, 3.5, 0.0, "COMM"),
    ("아이파크 101동(B1)",     [(108.0, 37.5), (164.0, 39.5), (163.0, 56.5), (107.0, 54.5)], 15, 3.1, 6.0, "APT"),
    ("아이파크 102동(B1)",     [(172.0, 41.0), (212.0, 44.0), (210.5, 62.0), (170.5, 59.0)], 15, 3.1, 6.0, "APT"),
]

# 10-2. 남측 인접 현황 건물군 (정거장 굴착 외벽 및 외부출입구#2/환기구와 초근접한 B1 보유 빌딩/상가!)
south_buildings = [
    ("제일자동차매매센타",     [(-78.0, -45.0), (-63.5, -45.0), (-63.5, -14.0), (-78.0, -14.0)], 3, 3.6, 0.0, "COMM"),
    ("수원북부교회(B1)",       [(-59.0, -48.0), (-36.0, -48.0), (-36.0, -24.0), (-59.0, -24.0)], 4, 3.6, 4.2, "PUB"),
    ("유카(B1) / 신세계카센타",[(-14.0, -39.5), (38.5, -39.5), (38.5, -14.2), (-14.0, -14.2)], 3, 3.6, 4.5, "COMM"),
    ("송정각(B1)",             [(62.0, -35.5), (78.5, -35.5), (78.5, -16.0), (62.0, -16.0)], 4, 3.5, 4.5, "COMM"),
    ("수원하천네트워크(B1)",   [(62.0, -56.0), (78.5, -56.0), (78.5, -38.0), (62.0, -38.0)], 3, 3.4, 4.2, "COMM"),
    ("1125(B1) 빌딩",          [(80.2, -35.1), (93.5, -35.1), (93.5, -15.5), (80.2, -15.5)], 5, 3.5, 4.5, "COMM"),
    ("대영빌딩(B1)",           [(95.0, -34.9), (114.2, -34.9), (114.2, -16.2), (95.0, -16.2)], 6, 3.5, 5.0, "COMM"),
    ("(주)미루 / 삼일빌라(B1)",[(82.0, -58.0), (112.0, -58.0), (112.0, -39.0), (82.0, -39.0)], 4, 3.3, 4.0, "COMM"),
    ("뉴서울주유소(B1)",       [(116.5, -31.8), (149.5, -30.5), (149.5, -13.5), (116.5, -14.8)], 2, 4.2, 4.5, "COMM"),
    ("강남면옥(1S)",           [(164.5, -45.0), (189.5, -45.0), (189.5, -24.0), (164.5, -24.0)], 2, 3.8, 0.0, "COMM"),
    ("아주한방병원(B1)",       [(191.5, -38.0), (222.0, -36.0), (222.0, -10.0), (191.5, -12.0)], 6, 3.6, 5.0, "PUB"),
]

all_buildings = north_buildings + south_buildings

for b_name, poly, n_fl, fl_h, b1_d, b_cat in all_buildings:
    if b_cat == "APT":
        add_building_with_floors(apt_v, apt_f, slab_v, slab_f, b1_v, b1_f, poly, n_fl, fl_h, b1_d)
    elif b_cat == "PUB":
        add_building_with_floors(pub_v, pub_f, slab_v, slab_f, b1_v, b1_f, poly, n_fl, fl_h, b1_d)
    else:
        add_building_with_floors(comm_v, comm_f, slab_v, slab_f, b1_v, b1_f, poly, n_fl, fl_h, b1_d)

create_mesh_obj("07A_인접현황건물_북측아파트단지_아이파크_101동_102동_지상15층", apt_v, apt_f, mat_bldg_apt, col_site)
create_mesh_obj("07B_인접현황건물_공공기관_국가전문행정연수원_경기도자료관_아주한방병원", pub_v, pub_f, mat_bldg_pub, col_site)
create_mesh_obj("08_인접현황건물_남측근접상가빌딩_유카_송정각_1125_대영빌딩_뉴서울주유소", comm_v, comm_f, mat_bldg_comm, col_site)
create_mesh_obj("09A_인접현황건물_층간슬래브라인_및_옥상파라펫", slab_v, slab_f, mat_bldg_slab, col_site)
create_mesh_obj("09B_인접현황건물_지하1층_B1_기초및지하외벽_근접시공리스크검토용", b1_v, b1_f, mat_bldg_b1, col_site)

# 10-3. 각 인접 건물 옥상 상부에 한글 3D 텍스트 라벨 생성 (한글 폰트 malgun.ttf 자동 연동)
font_path = r"C:\Windows\Fonts\malgunbd.ttf"
if not os.path.exists(font_path):
    font_path = r"C:\Windows\Fonts\malgun.ttf"
kr_font = bpy.data.fonts.load(font_path) if os.path.exists(font_path) else None

for idx_b, (b_name, poly, n_fl, fl_h, b1_d, b_cat) in enumerate(all_buildings):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    cz = n_fl * fl_h + 2.2
    t_name = f"10_인접건물라벨_{idx_b+1:02d}_{b_name.split('/')[0].strip()}"
    old_t = bpy.data.objects.get(t_name)
    if old_t:
        bpy.data.objects.remove(old_t, do_unlink=True)
    t_curve = bpy.data.curves.new(name=t_name + "_Curve", type='FONT')
    t_curve.body = b_name
    t_curve.size = 2.8 if b_cat != "APT" else 3.6
    t_curve.extrude = 0.25
    t_curve.align_x = 'CENTER'
    t_curve.align_y = 'CENTER'
    if kr_font:
        t_curve.font = kr_font
    t_obj = bpy.data.objects.new(t_name, t_curve)
    t_obj.location = (cx, cy, cz)
    t_obj.rotation_euler = (math.radians(35), 0.0, 0.0)
    t_obj.data.materials.append(mat_label_text)
    col_site.objects.link(t_obj)

# ==============================================================================
# 11. 컬렉션 가시성 유지 및 전체 주변 도로·인접 건물 현황이 한눈에 보이는 조감 뷰 세팅
# ==============================================================================
keep_cols = {
    "106_Station_BIM_CAD044",
    "00_가시설_외벽엄지말뚝_차수_토류판",
    "00A_정거장_단계별굴착_원지반토사면_및_단별토류판",
    "01A_가시설_복공판_주형보_주형지지보_피스브라켓_상세",
    "01M_가시설_Mistrut공법_1단버팀보대체_상세",
    "01U_가시설_지장물현황_및_지장물매달기보호공_상세",
    "02S_주변도로현황_교차로_보도_가설방음벽_및_인접건물현황_상세",
}
for c in bpy.data.collections:
    c.hide_viewport = (c.name not in keep_cols)
    c.hide_render   = (c.name not in keep_cols)

bpy.ops.object.select_all(action='DESELECT')

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
                    r3d.view_location = Vector((62.0, 5.0, 2.0))
                    r3d.view_rotation = Euler((math.radians(54), 0.0, math.radians(-32))).to_quaternion()
                    r3d.view_distance = 175.0
                    r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=blend_save_path)
print("SUCCESS: Built Surrounding Roads, Intersections, Sidewalks, Sound Walls & 16 Adjacent Buildings (with B1 Basements)!")
