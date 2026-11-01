import bpy
import bmesh
import ezdxf
import os
import math
from mathutils import Vector, Euler, Matrix

# ==============================================================================
# 106정거장 공사중 단계별 교통처리계획 (1단계 ~ 8단계) 3D BIM 구축 스크립트
# - 원본 CAD: 1. 단계별 교통처리계획.dwg (traffic_plan.dxf, 15,594 entities)
# - 기준 블록: 각 단계 내 106정거장 가시설 블록(A$C940b6d1d)과 CAD044 정거장 좌표계 1:1 정밀 매칭
# - 기본 표시 단계: 7단계 (7단계 - 106정거장 복공설치(해체) 공사)
# ==============================================================================

dxf_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\719438c6-31b4-4b93-b6b5-93042eba0916\scratch\traffic_plan.dxf"
blend_save_path = r"C:\Users\20040178\Desktop\2영역\토스앤\1.설계변경관리\2.인덕원동탄5공구\7.정거장 구조물 원가개선\정거장 가시설도, 구조도\106정거장_가시설_전체구간_3D_BIM.blend"

# ==============================================================================
# 1. 재질(Materials) 정의
# ==============================================================================
def make_mat(name, rgba, metallic=0.15, roughness=0.55, alpha=1.0, emission_strength=0.0):
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
        if emission_strength > 0.0 and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (rgba[0], rgba[1], rgba[2], 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 0.999:
        if hasattr(m, "blend_method"):
            m.blend_method = 'BLEND'
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = 'BLENDED'
    m.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    return m

mat_asphalt_base = make_mat("MAT_Traf_Road_Asphalt",      (0.15, 0.16, 0.18), metallic=0.05, roughness=0.85)
mat_deck_done    = make_mat("MAT_Traf_Deck_Completed",    (0.24, 0.33, 0.44), metallic=0.65, roughness=0.38, alpha=0.82) # 기설치 복공판 (지-철판)
mat_deck_grid    = make_mat("MAT_Traf_Deck_JointLine",    (0.14, 0.20, 0.28), metallic=0.75, roughness=0.32)             # 복공판 줄눈/리브
mat_deck_active  = make_mat("MAT_Traf_Deck_ActiveWork",   (0.05, 0.78, 0.85), metallic=0.45, roughness=0.30, alpha=0.78, emission_strength=0.25) # 금회 시공/해체 복공판 (CE-LINE-LIN3)
mat_work_floor   = make_mat("MAT_Traf_WorkZone_Floor",    (0.95, 0.42, 0.08), metallic=0.10, roughness=0.50, alpha=0.48) # 점용 작업구간 바닥
mat_pe_orange    = make_mat("MAT_Traf_PE_Barrier_Orange", (0.98, 0.33, 0.05), metallic=0.15, roughness=0.40)             # PE 방호벽 (주황)
mat_pe_white     = make_mat("MAT_Traf_PE_Barrier_White",  (0.95, 0.96, 0.98), metallic=0.15, roughness=0.40)             # PE 방호벽 (백색 교차)
mat_safety_fence = make_mat("MAT_Traf_SafetyFence_Wing",  (0.85, 0.92, 0.98), metallic=0.30, roughness=0.35, alpha=0.72) # 가설안전휀스+윙카 상부 패널
mat_cone_red     = make_mat("MAT_Traf_RubberCone_Red",    (0.96, 0.14, 0.08), metallic=0.10, roughness=0.35, emission_strength=0.15) # 라바콘/차선규제봉
mat_beacon_led   = make_mat("MAT_Traf_Beacon_LED_Red",    (1.00, 0.18, 0.05), metallic=0.20, roughness=0.20, emission_strength=1.20) # 점멸 경광등
mat_lane_chg_yel = make_mat("MAT_Traf_Lane_Changed_Yel",  (1.00, 0.82, 0.04), metallic=0.15, roughness=0.32, emission_strength=0.25) # 차선도색(변경) - 시인성 강화 황색
mat_lane_chg_wht = make_mat("MAT_Traf_Lane_Changed_Wht",  (0.98, 0.98, 1.00), metallic=0.15, roughness=0.32, emission_strength=0.20) # 차선도색(변경) - 백색 우회차선
mat_lane_orig    = make_mat("MAT_Traf_Lane_Orig_White",   (0.82, 0.85, 0.88), metallic=0.10, roughness=0.45)             # 현황/당초 차선 및 횡단보도
mat_lane_center  = make_mat("MAT_Traf_Lane_Center_Yel",   (0.95, 0.68, 0.05), metallic=0.15, roughness=0.38)             # 중앙선 황색 실선
mat_lane_guide   = make_mat("MAT_Traf_Lane_Guide_Cyan",   (0.25, 0.75, 0.98), metallic=0.15, roughness=0.38)             # 유도선-파선
mat_flow_arrow   = make_mat("MAT_Traf_Flow_Arrow_Green",  (0.15, 0.92, 0.42), metallic=0.20, roughness=0.30, emission_strength=0.35) # 차량 주행동선 화살표
mat_sign_board   = make_mat("MAT_Traf_SignBoard_Yellow",  (0.98, 0.78, 0.08), metallic=0.25, roughness=0.35)             # 공사안내 표지판
mat_sec_line     = make_mat("MAT_Traf_SectionLine_Mag",   (0.98, 0.22, 0.65), metallic=0.25, roughness=0.30, emission_strength=0.40) # 단면 A-A', B-B' 기준선
mat_banner_gold  = make_mat("MAT_Traf_Banner_TextGold",   (1.00, 0.90, 0.20), metallic=0.45, roughness=0.25, emission_strength=0.35) # 3D 단계 배너 텍스트
mat_banner_bg    = make_mat("MAT_Traf_Banner_BoardDark",  (0.08, 0.12, 0.18), metallic=0.35, roughness=0.45, alpha=0.88) # 3D 배너 배경판

# ==============================================================================
# 2. 기하 생성 헬퍼 함수
# ==============================================================================
def create_mesh_obj(name, verts, faces, mat, col):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    if not verts or not faces:
        return None
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
    # 중복 연속점 제거
    clean_pts = []
    for pt in poly_2d:
        if not clean_pts or math.hypot(pt[0] - clean_pts[-1][0], pt[1] - clean_pts[-1][1]) > 0.02:
            clean_pts.append(pt)
    if len(clean_pts) >= 2 and math.hypot(clean_pts[0][0] - clean_pts[-1][0], clean_pts[0][1] - clean_pts[-1][1]) <= 0.02:
        clean_pts.pop()
    if len(clean_pts) < 3:
        return
    bm = bmesh.new()
    b_verts = [bm.verts.new((pt[0], pt[1], z_bot)) for pt in clean_pts]
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

def add_cone_3d(verts, faces, cx, cy, z_bot, z_top, r_bot, r_top, n_seg=8):
    base = len(verts)
    for k in range(n_seg):
        ang = 2.0 * math.pi * k / n_seg
        verts.append((cx + r_bot * math.cos(ang), cy + r_bot * math.sin(ang), z_bot))
    for k in range(n_seg):
        ang = 2.0 * math.pi * k / n_seg
        verts.append((cx + r_top * math.cos(ang), cy + r_top * math.sin(ang), z_top))
    for k in range(n_seg):
        kn = (k + 1) % n_seg
        faces.append((base + k, base + kn, base + n_seg + kn, base + n_seg + k))
    faces.append(tuple(base + k for k in range(n_seg - 1, -1, -1)))
    faces.append(tuple(base + n_seg + k for k in range(n_seg)))

def add_arrow_3d(verts, faces, cx, cy, angle_deg, z_bot=0.04, z_top=0.12, scale=1.0):
    rad = math.radians(angle_deg)
    cr, sr = math.cos(rad), math.sin(rad)
    local_pts = [
        (-2.2 * scale, -0.35 * scale),
        ( 0.6 * scale, -0.35 * scale),
        ( 0.6 * scale, -0.95 * scale),
        ( 2.4 * scale,  0.00 * scale),
        ( 0.6 * scale,  0.95 * scale),
        ( 0.6 * scale,  0.35 * scale),
        (-2.2 * scale,  0.35 * scale),
    ]
    w_pts = [(cx + px * cr - py * sr, cy + px * sr + py * cr) for px, py in local_pts]
    add_polygon_slab_bm(verts, faces, w_pts, z_bot, z_top)

# 한글 폰트 로드
font_path = r"C:\Windows\Fonts\malgunbd.ttf"
if not os.path.exists(font_path):
    font_path = r"C:\Windows\Fonts\malgun.ttf"
kr_font = bpy.data.fonts.load(font_path) if os.path.exists(font_path) else None

def create_3d_text(name, body, loc, size, rot_euler, mat, col, align_x='CENTER', extrude=0.05):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cu = bpy.data.curves.new(name + "_Curve", type='FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align_x
    cu.align_y = 'CENTER'
    if kr_font:
        cu.font = kr_font
    obj = bpy.data.objects.new(name, cu)
    obj.location = loc
    obj.rotation_euler = Euler(rot_euler, 'XYZ')
    if mat:
        obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj

# ==============================================================================
# 3. 컬렉션 준비 및 기존 정적 도로 차선/방음벽 가시성 정리
# ==============================================================================
root_col = bpy.data.collections.get("106_Station_BIM_CAD044")
if not root_col:
    root_col = bpy.context.scene.collection

# 기존 주변도로 컬렉션에서 정적 차선/정적 방음벽은 단계별 교통처리계획과 겹치지 않도록 숨김 처리하고,
# 정거장 개착구간 주변 도로 바닥은 단계별 교통처리에서 완벽히 제어!
col_site = bpy.data.collections.get("02S_주변도로현황_교차로_보도_가설방음벽_및_인접건물현황_상세")
if col_site:
    for o in col_site.objects:
        if any(k in o.name for k in ("02A_도로차선", "02B_도로차선", "02C_도로차선", "05A_공사구간", "05B_공사구간")):
            o.hide_viewport = True
            o.hide_render = True

parent_col_name = "03T_단계별교통처리계획_1단계_8단계_전체"
parent_col = bpy.data.collections.get(parent_col_name)
if not parent_col:
    parent_col = bpy.data.collections.new(parent_col_name)
    root_col.children.link(parent_col)
parent_col.hide_viewport = False
parent_col.hide_render   = False

# 단계별 메타데이터 (1단계 ~ 8단계)
STAGE_META = {
    1: (
        "03T_1단계_교통처리계획_보도축소_지장물이설_및_남측복공1차",
        "1단계 : 보도 축소·지장물 이설 및 남측 가시설/복공 1차 시공",
        "기설치 복공 0구역 | 금회 복공설치 2구역(남측 좌·우) | 남측 보도측 점용 및 PE방호벽·가설휀스 설치"
    ),
    2: (
        "03T_2단계_교통처리계획_남측하위차로점용_및_남측중앙복공2차",
        "2단계(2-1단계) : 남측 하위 차로 점용 및 남측 중앙부 복공 2차 시공",
        "금회 복공설치 2구역(남측 중앙 교차부·돌출부) | 남측 하위 차로 가설안전휀스·라바콘 점용(4개 구역)"
    ),
    3: (
        "03T_3단계_교통처리계획_남측복공통행전환_및_중앙차로점용복공3차",
        "3단계 : 남측 복공판(4구역) 통행 전환 및 도로 중앙부 복공 3차 시공",
        "기설치 복공 4구역(남측 완료) | 금회 복공설치 2구역(중앙 서·동측) | 중앙 차로 점용 및 우회차선 운영"
    ),
    4: (
        "03T_4단계_교통처리계획_중앙교차부점용_및_중앙복공4차",
        "4단계 : 남측+중앙서측 복공(5구역) 통행 및 중앙 교차부 복공 4차 시공",
        "기설치 복공 5구역 | 금회 복공설치 3구역(중앙 교차부 포함) | 중앙 차로 및 남측 출입구 점용(4개 구역)"
    ),
    5: (
        "03T_5단계_교통처리계획_북측중앙차로점용_복공5차_당초삭제단계",
        "5단계(당초/삭제검토) : 남측+중앙 전구간 복공(7구역) 완료 및 북측 중앙차로 복공 시공",
        "기설치 복공 7구역(남측·중앙 완료) | 금회 복공설치 2구역(북측 중앙차로) | 북측 차로 점용(3개 구역)"
    ),
    6: (
        "03T_6단계_교통처리계획_북측하위차로점용_및_북측전구간복공6차",
        "6단계 : 남측+중앙+북측내측 복공(9구역) 완료 및 북측 최외측 복공 5개 구역 시공",
        "기설치 복공 9구역 | 금회 복공설치 5구역(북측 외측·보도측 전구간) | 북측 최외측 차로 점용(3개 구역)"
    ),
    7: (
        "03T_7단계_교통처리계획_복공설치해체공사_중앙남측작업구간_핵심단계",
        "7단계 : 본선 복공판(14구역) 완료 + 남서측 복공(1구역) 및 중앙·남측 작업구간(8개소) 운영",
        "A-A'단면(46.9m): 북측3차로(9.0m)+중앙공사구간(8.4m)+남측3차로(9.0m)+남측공사구간(8.6m) | B-B'단면(45.0m): 북측4차로(12.0m)+중앙공사구간(12.3m)+남측3차로(9.0m)+남측공사구간(5.1m)"
    ),
    8: (
        "03T_8단계_교통처리계획_전구간복공완료_및_중앙작업구설치_본체굴착",
        "8단계 : 전 구간 복공판(15구역) 100% 설치 완료 및 도로 중앙 작업구(4개소) 설치",
        "기설치 복공 15구역(전구간 완료) | 중앙 서측·동측 대형 작업구 및 남측 출입구 작업구 가설휀스 운영 (지하 본체·Mistrut 시공)"
    ),
}

# ==============================================================================
# 4. DXF 로드 및 단계별 기준점(A$C940b6d1d) 추출
# ==============================================================================
doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

stage_blk_ins = {}
for e in msp.query('INSERT'):
    if e.dxf.name == 'A$C940b6d1d':
        ins = e.dxf.insert
        for s in range(1, 9):
            yc = 516008.1 - (s - 1) * 707.9735
            if abs(ins.y - yc) < 300.0:
                stage_blk_ins[s] = (ins.x, ins.y, e.dxf.rotation)

# ==============================================================================
# 5. 1단계 ~ 8단계 전체 3D 교통처리계획 생성 루프
# ==============================================================================
ACTIVE_STAGE = 7  # 사용자 요청: 7단계 교통처리단계 표시!

for s in range(1, 9):
    col_name, title_kr, desc_kr = STAGE_META[s]
    s_col = bpy.data.collections.get(col_name)
    if not s_col:
        s_col = bpy.data.collections.new(col_name)
        parent_col.children.link(s_col)
    for o in list(s_col.objects):
        bpy.data.objects.remove(o, do_unlink=True)

    # 현재 활성 단계(7단계)만 표시, 나머지 1~6, 8단계는 즉시 전환 가능하도록 숨김 설정
    is_active = (s == ACTIVE_STAGE)
    s_col.hide_viewport = not is_active
    s_col.hide_render   = not is_active

    ix, iy, rot_deg = stage_blk_ins.get(s, (205063.3415, 515836.4914 - (s - 1) * 707.9735, 0.9533))
    rad = -math.radians(rot_deg)
    cr, sr = math.cos(rad), math.sin(rad)

    def to_b(x, y):
        dx, dy = x - ix, y - iy
        return (dx * cr - dy * sr + 79.704, dx * sr + dy * cr - 16.160)

    def in_stage_roi(pt_b):
        return (-110.0 <= pt_b[0] <= 220.0) and (-72.0 <= pt_b[1] <= 75.0)

    # 메쉬 버퍼 초기화
    deck_done_v,   deck_done_f   = [], []
    deck_grid_v,   deck_grid_f   = [], []
    deck_active_v, deck_active_f = [], []
    work_floor_v,  work_floor_f  = [], []
    pe_org_v,      pe_org_f      = [], []
    pe_wht_v,      pe_wht_f      = [], []
    fence_v,       fence_f       = [], []
    cone_v,        cone_f        = [], []
    beacon_v,      beacon_f      = [], []
    lane_cy_v,     lane_cy_f     = [], []
    lane_cw_v,     lane_cw_f     = [], []
    lane_ow_v,     lane_ow_f     = [], []
    lane_oy_v,     lane_oy_f     = [], []
    lane_gd_v,     lane_gd_f     = [], []
    arrow_v,       arrow_f       = [], []
    sign_v,        sign_f        = [], []
    sec_v,         sec_f         = [], []

    # --------------------------------------------------------------------------
    # 5-1. LWPOLYLINE 처리 (복공판, 금회시공 복공판, 안전휀스/라바콘 작업구간, 변경차선, 당초차선, 단면선)
    # --------------------------------------------------------------------------
    for e in msp.query('LWPOLYLINE'):
        pts_raw = list(e.get_points())
        if not pts_raw or abs(pts_raw[0][1] - iy) > 260.0:
            continue
        bpts = [to_b(p[0], p[1]) for p in pts_raw]
        if not any(in_stage_roi(p) for p in bpts):
            continue

        lay = e.dxf.layer
        is_closed = bool(e.closed)
        cw = getattr(e.dxf, 'const_width', 0.0) or 0.0

        # (A) 기설치 완료 복공판 구역 (지-철판)
        if lay == '지-철판':
            add_polygon_slab_bm(deck_done_v, deck_done_f, bpts, -0.02, 0.045)
            # 테두리 및 내부 2.0m 간격 복공판 조인트 리브 표현
            n_b = len(bpts)
            for k in range(n_b):
                p1, p2 = bpts[k], bpts[(k + 1) % n_b]
                add_box_segment_3d(deck_grid_v, deck_grid_f, p1, p2, -0.01, 0.055, 0.14)
            xs_p = [p[0] for p in bpts]
            ys_p = [p[1] for p in bpts]
            y_mid_L = 0.5 * (min(ys_p) + max(ys_p))
            for x_rib in range(int(min(xs_p)) + 2, int(max(xs_p)), 3):
                # 폴리곤을 가로지르는 폭 방향 복공판 줄눈
                add_box_segment_3d(deck_grid_v, deck_grid_f, (float(x_rib), min(ys_p) + 0.4), (float(x_rib), max(ys_p) - 0.4), 0.04, 0.052, 0.06)

        # (B) 금회 단계 복공판 설치/해체 시공 구역 (CE-LINE-LIN3)
        elif lay == 'CE-LINE-LIN3' and len(bpts) >= 4:
            add_polygon_slab_bm(deck_active_v, deck_active_f, bpts, -0.01, 0.075)
            n_b = len(bpts)
            for k in range(n_b):
                p1, p2 = bpts[k], bpts[(k + 1) % n_b]
                add_box_segment_3d(pe_org_v, pe_org_f, p1, p2, 0.0, 0.35, 0.25)

        # (C) 공사 점용구역 및 가설안전휀스/라바콘/PE방호벽 (지-안전휀스 라바콘-개선, 지-공사중, PE방호벽, 가설휀스, 지-안전휀스-현황)
        elif lay in ('지-안전휀스 라바콘-개선', '지-공사중', 'PE방호벽', '가설휀스', '지-안전휀스-현황'):
            if is_closed and len(bpts) >= 3:
                add_polygon_slab_bm(work_floor_v, work_floor_f, bpts, 0.005, 0.055)
            elif lay == '지-공사중' and len(bpts) >= 4:
                add_polygon_slab_bm(work_floor_v, work_floor_f, bpts, 0.005, 0.055)

            seg_count = len(bpts) if is_closed else (len(bpts) - 1)
            for k in range(seg_count):
                p1, p2 = bpts[k], bpts[(k + 1) % len(bpts)]
                L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if L < 0.2:
                    continue
                # 2.0m 단위 교차 색상(주황/백색) PE 방호벽 (H=0.85m) + 상부 가설안전휀스/윙카 (H=0.85~1.65m)
                n_div = max(1, int(round(L / 2.0)))
                for d_i in range(n_div):
                    t0 = d_i / n_div
                    t1 = (d_i + 1) / n_div
                    q1 = (p1[0] + (p2[0] - p1[0]) * t0, p1[1] + (p2[1] - p1[1]) * t0)
                    q2 = (p1[0] + (p2[0] - p1[0]) * t1, p1[1] + (p2[1] - p1[1]) * t1)
                    if d_i % 2 == 0:
                        add_box_segment_3d(pe_org_v, pe_org_f, q1, q2, 0.0, 0.85, 0.42)
                    else:
                        add_box_segment_3d(pe_wht_v, pe_wht_f, q1, q2, 0.0, 0.85, 0.42)
                add_box_segment_3d(fence_v, fence_f, p1, p2, 0.85, 1.65, 0.10)

                # 테두리 외측을 따라 2.5m 간격으로 3D 라바콘(Rubber Cone) 배치!
                dx_s, dy_s = (p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L
                nx_s, ny_s = -dy_s * 0.55, dx_s * 0.55
                n_cones = max(1, int(L / 2.5))
                for c_i in range(n_cones + 1):
                    tc = min(1.0, c_i / max(1, n_cones))
                    cx_c = p1[0] + (p2[0] - p1[0]) * tc + nx_s
                    cy_c = p1[1] + (p2[1] - p1[1]) * tc + ny_s
                    add_cone_3d(cone_v, cone_f, cx_c, cy_c, 0.0, 0.72, 0.20, 0.05, n_seg=8)

        # (D) 변경 차선 도색 (차선도색(변경), 마킹선-차로) -> 황색/백색 입체 우회차선
        elif lay in ('차선도색(변경)', '마킹선-차로'):
            w_line = max(0.18, min(0.55, cw if cw > 0.05 else 0.18))
            seg_count = len(bpts) if is_closed else (len(bpts) - 1)
            for k in range(seg_count):
                p1, p2 = bpts[k], bpts[(k + 1) % len(bpts)]
                if cw >= 0.40:
                    # 변경 횡단보도 / 변경 정지선 (백색 강조)
                    add_box_segment_3d(lane_cw_v, lane_cw_f, p1, p2, 0.015, 0.060, w_line)
                else:
                    # 변경 우회차선 (황색 강조)
                    add_box_segment_3d(lane_cy_v, lane_cy_f, p1, p2, 0.015, 0.065, w_line)

        # (E) 유도선-파선-현황
        elif lay in ('유도선-파선-현황', '유턴-파선-현황'):
            seg_count = len(bpts) if is_closed else (len(bpts) - 1)
            for k in range(seg_count):
                p1, p2 = bpts[k], bpts[(k + 1) % len(bpts)]
                add_box_segment_3d(lane_gd_v, lane_gd_f, p1, p2, 0.012, 0.052, 0.18)

        # (F) 중앙선-실선-현황 / 진로변경제한선
        elif lay in ('중앙선-실선-현황', '진로변경제한선-실선-현황'):
            seg_count = len(bpts) if is_closed else (len(bpts) - 1)
            for k in range(seg_count):
                p1, p2 = bpts[k], bpts[(k + 1) % len(bpts)]
                add_box_segment_3d(lane_oy_v, lane_oy_f, p1, p2, 0.010, 0.048, 0.16)

        # (G) 당초/현황 차선, 횡단보도, 정지선
        elif lay in ('차선도색(당초)', '차선-파선-현황', '정지선-현황', '지-횡단보도-현황', '지-자전거횡단도-현황'):
            w_line = max(0.15, min(0.55, cw if cw > 0.05 else (0.42 if '횡단' in lay or '정지' in lay else 0.15)))
            seg_count = len(bpts) if is_closed else (len(bpts) - 1)
            for k in range(seg_count):
                p1, p2 = bpts[k], bpts[(k + 1) % len(bpts)]
                add_box_segment_3d(lane_ow_v, lane_ow_f, p1, p2, 0.008, 0.042, w_line)

        # (H) 횡단면도 기준선 (지-단면: 단면 A-A', 단면 B-B')
        elif lay == '지-단면':
            seg_count = len(bpts) if is_closed else (len(bpts) - 1)
            for k in range(seg_count):
                p1, p2 = bpts[k], bpts[(k + 1) % len(bpts)]
                add_box_segment_3d(sec_v, sec_f, p1, p2, 0.02, 0.18, max(0.28, cw if cw > 0.1 else 0.28))

    # --------------------------------------------------------------------------
    # 5-2. INSERT 블록 처리 (차로규제봉, 점멸경광등, 공사표지판, 주행동선 화살표, 신호수/공사차량)
    # --------------------------------------------------------------------------
    for e in msp.query('INSERT'):
        ins = e.dxf.insert
        if abs(ins.y - iy) > 260.0:
            continue
        bx, by = to_b(ins.x, ins.y)
        if not in_stage_roi((bx, by)):
            continue
        lay = e.dxf.layer
        rot_b = e.dxf.rotation - rot_deg

        if lay == '지-차로규제봉-현황':
            add_cone_3d(cone_v, cone_f, bx, by, 0.0, 0.85, 0.12, 0.08, n_seg=8)
        elif lay == '지-경광등':
            # 경광등 받침대 + 상부 적색 LED 발광 비콘
            add_cone_3d(pe_org_v, pe_org_f, bx, by, 0.0, 1.25, 0.25, 0.15, n_seg=10)
            add_cone_3d(beacon_v, beacon_f, bx, by, 1.25, 1.75, 0.28, 0.22, n_seg=12)
        elif lay == '공사표지판':
            # 입체 공사안내 표지판 (지주 + 황색 표지판 보드)
            add_cone_3d(deck_grid_v, deck_grid_f, bx, by, 0.0, 2.20, 0.10, 0.08, n_seg=8)
            rad_s = math.radians(rot_b)
            p_s1 = (bx - 1.1 * math.sin(rad_s), by + 1.1 * math.cos(rad_s))
            p_s2 = (bx + 1.1 * math.sin(rad_s), by - 1.1 * math.cos(rad_s))
            add_box_segment_3d(sign_v, sign_f, p_s1, p_s2, 1.00, 2.40, 0.18)
        elif lay in ('지-동선-개선', '지-화살표', '지-노면표시-현황', '지-유출입-현황'):
            add_arrow_3d(arrow_v, arrow_f, bx, by, rot_b, z_bot=0.03, z_top=0.10, scale=0.95 if '노면' in lay else 1.35)
        elif lay == '지-통제수 및 차량-개선':
            # 공사차량 / 신호수 배치 위치 입체 표시
            add_box_segment_3d(sign_v, sign_f, (bx - 2.2, by), (bx + 2.2, by), 0.10, 1.85, 2.10)
            add_cone_3d(beacon_v, beacon_f, bx, by, 1.85, 2.35, 0.35, 0.20, n_seg=10)

    # 본선 차량 통행방향(서->동 동탄방면, 동->서 인덕원방면) 주행 유도 화살표 추가 (시각적 흐름 강화)
    for x_arr in (-20.0, 18.0, 62.0, 102.0, 138.0):
        # 인덕원 방향(상행 북측 차로, 서쪽 진행 angle=180 deg)
        add_arrow_3d(arrow_v, arrow_f, x_arr, 21.2, 180.0, z_bot=0.04, z_top=0.11, scale=1.25)
        # 동탄 방향(하행 남측 차로, 동쪽 진행 angle=0 deg)
        add_arrow_3d(arrow_v, arrow_f, x_arr, -2.5 if s < 7 else 0.8, 0.0, z_bot=0.04, z_top=0.11, scale=1.25)

    # --------------------------------------------------------------------------
    # 5-3. 메쉬 오브젝트 생성 및 단계별 컬렉션 등록
    # --------------------------------------------------------------------------
    create_mesh_obj(f"S{s}_01A_기설치완료_복공판구역_지철판",           deck_done_v,   deck_done_f,   mat_deck_done,    s_col)
    create_mesh_obj(f"S{s}_01B_기설치완료_복공판줄눈리브",             deck_grid_v,   deck_grid_f,   mat_deck_grid,    s_col)
    create_mesh_obj(f"S{s}_02_금회시공중_복공판설치해체구역_CELINE",    deck_active_v, deck_active_f, mat_deck_active,  s_col)
    create_mesh_obj(f"S{s}_03_공사점용작업구간_바닥안전영역",           work_floor_v,  work_floor_f,  mat_work_floor,   s_col)
    create_mesh_obj(f"S{s}_04A_가설PE방호벽_주황블록_H0.85m",          pe_org_v,      pe_org_f,      mat_pe_orange,    s_col)
    create_mesh_obj(f"S{s}_04B_가설PE방호벽_백색블록_H0.85m",          pe_wht_v,      pe_wht_f,      mat_pe_white,     s_col)
    create_mesh_obj(f"S{s}_04C_가설안전휀스_및_윙카패널_H1.65m",        fence_v,       fence_f,       mat_safety_fence, s_col)
    create_mesh_obj(f"S{s}_05A_라바콘_및_차선규제봉_안전유도시설",      cone_v,        cone_f,        mat_cone_red,     s_col)
    create_mesh_obj(f"S{s}_05B_점멸경광등_LED적색경고등",               beacon_v,      beacon_f,      mat_beacon_led,   s_col)
    create_mesh_obj(f"S{s}_06A_차선도색_변경우회차선_황색강조",         lane_cy_v,     lane_cy_f,     mat_lane_chg_yel, s_col)
    create_mesh_obj(f"S{s}_06B_차선도색_변경횡단보도정지선_백색",       lane_cw_v,     lane_cw_f,     mat_lane_chg_wht, s_col)
    create_mesh_obj(f"S{s}_06C_현황및당초차선_횡단보도_백색도색",       lane_ow_v,     lane_ow_f,     mat_lane_orig,    s_col)
    create_mesh_obj(f"S{s}_06D_중앙선_및_진로변경제한선_황색실선",      lane_oy_v,     lane_oy_f,     mat_lane_center,  s_col)
    create_mesh_obj(f"S{s}_06E_교차로유도선_파선도색",                 lane_gd_v,     lane_gd_f,     mat_lane_guide,   s_col)
    create_mesh_obj(f"S{s}_07A_차량주행동선_노면방향화살표",            arrow_v,       arrow_f,       mat_flow_arrow,   s_col)
    create_mesh_obj(f"S{s}_07B_공사안내표지판_및_통제차량",             sign_v,        sign_f,        mat_sign_board,   s_col)
    create_mesh_obj(f"S{s}_08A_횡단면도기준선_단면AA_단면BB",           sec_v,         sec_f,         mat_sec_line,     s_col)

    # --------------------------------------------------------------------------
    # 5-4. 단계별 3D 타이틀 배너 및 단면 A-A' / B-B' 3D 라벨 생성
    # --------------------------------------------------------------------------
    # 상단 배너 배경 보드 (정거장 북측 상공 Y=45m, Z=14m~21m)
    bg_v, bg_f = [], []
    add_box_segment_3d(bg_v, bg_f, (10.0, 44.5), (108.0, 44.5), 13.5, 22.0, 0.45)
    create_mesh_obj(f"S{s}_08B_단계별교통처리_3D배너보드", bg_v, bg_f, mat_banner_bg, s_col)

    create_3d_text(
        f"S{s}_08C_단계타이틀_{s}단계",
        f"[{title_kr}]",
        (59.0, 44.1, 19.3),
        2.35,
        (math.radians(78.0), 0.0, 0.0),
        mat_banner_gold,
        s_col,
        align_x='CENTER',
        extrude=0.08
    )
    create_3d_text(
        f"S{s}_08D_단계상세설명_{s}단계",
        desc_kr,
        (59.0, 44.1, 15.8),
        1.25,
        (math.radians(78.0), 0.0, 0.0),
        mat_lane_chg_wht,
        s_col,
        align_x='CENTER',
        extrude=0.05
    )

    # 단면 A-A' (X≈2.0m) 및 단면 B-B' (X≈99.0m) 3D 마커 텍스트
    create_3d_text(
        f"S{s}_08E_단면AA_마커",
        f"단면 A-A' ({s}단계)",
        (2.0, 31.5, 1.8),
        1.55,
        (math.radians(60.0), 0.0, 0.0),
        mat_sec_line,
        s_col,
        align_x='CENTER',
        extrude=0.06
    )
    create_3d_text(
        f"S{s}_08F_단면BB_마커",
        f"단면 B-B' ({s}단계)",
        (99.0, 34.5, 1.8),
        1.55,
        (math.radians(60.0), 0.0, 0.0),
        mat_sec_line,
        s_col,
        align_x='CENTER',
        extrude=0.06
    )

    # 7단계(핵심 요청 단계)에는 각 작업구간 및 차로 위에 직관적인 3D 구역 라벨 추가!
    if s == 7:
        stage7_callouts = [
            ("S7_09A_라벨_중앙서측작업구간", "7단계 중앙 작업구간(서측 B=8.4m)\n안전휀스+라바콘+윙카 설치", (12.0, 10.5, 2.2), 1.35, mat_banner_gold),
            ("S7_09B_라벨_중앙동측작업구간", "7단계 중앙 작업구간(동측 B=12.3m)\n복공 설치(해체) 및 안전휀스", (112.0, 11.5, 2.2), 1.35, mat_banner_gold),
            ("S7_09C_라벨_남측서부작업구간", "7단계 남측 작업구간(서측 B=8.6m)\n보도축소·안전휀스·신호수배치", (8.0, -9.5, 2.2), 1.25, mat_pe_orange),
            ("S7_09D_라벨_남측동부작업구간", "7단계 남측 작업구간(동측 B=5.1m)\n출입구·환기구 가시설 점용", (105.0, -8.5, 2.2), 1.25, mat_pe_orange),
            ("S7_09E_라벨_금회복공시공구역", "금회 복공설치 구역\n(남서측 시점부)", (5.5, -5.8, 1.5), 1.15, mat_deck_active),
            ("S7_09F_라벨_상행우회차로",     "◀ 인덕원 방면 우회차로 (3~4차로 확보: 기설치 복공판 통행)", (55.0, 21.5, 1.2), 1.30, mat_flow_arrow),
            ("S7_09G_라벨_하행우회차로",     "동탄 방면 우회차로 (3차로 확보: 기설치 복공판 통행) ▶",     (55.0, 1.2, 1.2),  1.30, mat_flow_arrow),
        ]
        for c_name, c_txt, c_loc, c_sz, c_mat in stage7_callouts:
            create_3d_text(c_name, c_txt, c_loc, c_sz, (math.radians(58.0), 0.0, 0.0), c_mat, s_col, align_x='CENTER', extrude=0.05)

# ==============================================================================
# 6. 7단계 교통처리계획이 한눈에 보이도록 뷰포트 카메라 정렬 및 파일 저장
# ==============================================================================
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'
                    space.shading.show_xray = False
                    space.overlay.show_overlays = True
                    r3d = space.region_3d
                    # 정거장 및 7단계 교통처리구간 전체가 남측 상공에서 입체적으로 한눈에 보이는 조감 뷰
                    r3d.view_perspective = 'PERSP'
                    r3d.view_location = Vector((58.0, 8.0, 0.0))
                    r3d.view_distance = 165.0
                    r3d.view_rotation = Euler((math.radians(52.0), 0.0, math.radians(-12.0)), 'XYZ').to_quaternion()

bpy.ops.wm.save_as_mainfile(filepath=blend_save_path)
print("Successfully built 8-stage traffic control plan and activated Stage 7!")
