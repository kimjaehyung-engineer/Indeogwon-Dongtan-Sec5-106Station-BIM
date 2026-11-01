import bpy
import bmesh
import ezdxf
import os
import math
import random
from mathutils import Vector, Euler, Matrix

# ==============================================================================
# 106정거장 주변 경수대로 실사형 조경·도로시설물 고도화 스크립트
# 1. 실사형 다중 분지 가로수 (주철 가로수보호판 + 테이퍼드 수간 + 3단계 분지 가지 + 3톤 다층 유기적 수관 클러스터)
# 2. 실사형 한국 도심 아치형 LED 가로등 (플랜지 기초 + 점검구 + 테이퍼 강관주 + 유선형 붐암 + 다이캐스트 LED 등기구)
# 3. CAD 원본(지-신호등-현황) 1:1 교통신호등 갠트리 (지주 + 캔틸레버 암 + 4구/3구 차양막 신호등기구 + 보행자신호등 + 제어기함)
# ==============================================================================

dxf_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\719438c6-31b4-4b93-b6b5-93042eba0916\scratch\traffic_plan.dxf"
blend_save_path = r"C:\Users\20040178\Desktop\2영역\토스앤\1.설계변경관리\2.인덕원동탄5공구\7.정거장 구조물 원가개선\정거장 가시설도, 구조도\106정거장_가시설_전체구간_3D_BIM.blend"
repo_blend_path = r"C:\Users\20040178\Desktop\2영역\토스앤\1.설계변경관리\2.인덕원동탄5공구\7.정거장 구조물 원가개선\GitHub_인덕원동탄5공구_106정거장_BIM성과물\models\106정거장_가시설_전체구간_3D_BIM.blend"

# ==============================================================================
# 1. 실사형 PBR 재질(Materials) 정의
# ==============================================================================
def make_mat(name, rgba, metallic=0.1, roughness=0.6, emission_strength=0.0):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgba[0], rgba[1], rgba[2], 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission_strength > 0.0 and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (rgba[0], rgba[1], rgba[2], 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    m.diffuse_color = (rgba[0], rgba[1], rgba[2], 1.0)
    return m

# 가로수 재질 (수피 + 3톤 자연 수관 + 주철 보호판)
mat_bark         = make_mat("MAT_RealTree_Bark_Wood",      (0.26, 0.19, 0.13), metallic=0.02, roughness=0.92)
mat_leaf_sun     = make_mat("MAT_RealTree_Leaf_Sunlit",    (0.28, 0.58, 0.18), metallic=0.02, roughness=0.68)
mat_leaf_mid     = make_mat("MAT_RealTree_Leaf_MidGreen",  (0.18, 0.44, 0.15), metallic=0.02, roughness=0.72)
mat_leaf_deep    = make_mat("MAT_RealTree_Leaf_DeepShade", (0.11, 0.31, 0.12), metallic=0.02, roughness=0.78)
mat_tree_grate   = make_mat("MAT_RealTree_CastIron_Grate", (0.20, 0.22, 0.24), metallic=0.80, roughness=0.42)

# 가로등 & 교통신호등 재질
mat_pole_dark    = make_mat("MAT_Street_Pole_Charcoal",    (0.18, 0.21, 0.24), metallic=0.82, roughness=0.32)
mat_pole_silver  = make_mat("MAT_Street_Pole_GalvSteel",   (0.62, 0.66, 0.70), metallic=0.85, roughness=0.28)
mat_led_emit     = make_mat("MAT_Street_Lamp_LED_Warm",    (1.00, 0.96, 0.84), metallic=0.10, roughness=0.15, emission_strength=2.50)
mat_sig_body     = make_mat("MAT_Traffic_Signal_Black",    (0.07, 0.08, 0.09), metallic=0.45, roughness=0.35)
mat_sig_red      = make_mat("MAT_Traffic_Light_Red",       (1.00, 0.10, 0.06), metallic=0.10, roughness=0.15, emission_strength=2.80)
mat_sig_yellow   = make_mat("MAT_Traffic_Light_Amber",     (1.00, 0.72, 0.04), metallic=0.10, roughness=0.15, emission_strength=2.20)
mat_sig_green    = make_mat("MAT_Traffic_Light_Green",     (0.08, 0.96, 0.38), metallic=0.10, roughness=0.15, emission_strength=2.80)

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
    # 부드러운 음영(Smooth Shading) 적용으로 유기적 조형감 극대화
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    if mat:
        obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj

def add_tapered_tube_3d(verts, faces, p1, p2, r1, r2, n_seg=8):
    v1 = Vector(p1)
    v2 = Vector(p2)
    dv = v2 - v1
    L = dv.length
    if L < 1e-4:
        return
    z_axis = dv.normalized()
    up = Vector((0, 0, 1)) if abs(z_axis.z) < 0.95 else Vector((1, 0, 0))
    x_axis = z_axis.cross(up).normalized()
    y_axis = z_axis.cross(x_axis).normalized()

    base = len(verts)
    for k in range(n_seg):
        ang = 2.0 * math.pi * k / n_seg
        offset = (x_axis * math.cos(ang) + y_axis * math.sin(ang)) * r1
        pt = v1 + offset
        verts.append((pt.x, pt.y, pt.z))
    for k in range(n_seg):
        ang = 2.0 * math.pi * k / n_seg
        offset = (x_axis * math.cos(ang) + y_axis * math.sin(ang)) * r2
        pt = v2 + offset
        verts.append((pt.x, pt.y, pt.z))
    for k in range(n_seg):
        kn = (k + 1) % n_seg
        faces.append((base + k, base + kn, base + n_seg + kn, base + n_seg + k))
    faces.append(tuple(base + n_seg + k for k in range(n_seg)))

def add_organic_foliage_cluster(verts, faces, center, rx, ry, rz, seed_val=0):
    """
    단순 원기둥이 아닌, 자연스러운 굴곡을 가진 다면체 수관 클러스터(Leaf Sub-crown) 생성
    """
    rng = random.Random(seed_val)
    cx, cy, cz = center
    # 위도 4단 x 경도 8분할 유기적 구형 메쉬
    n_lat = 4
    n_lon = 8
    base = len(verts)
    # 하단 극점 & 상단 극점
    verts.append((cx, cy, cz - rz * 0.85))
    verts.append((cx, cy, cz + rz * 0.95))
    for i_lat in range(1, n_lat):
        theta = math.pi * i_lat / n_lat
        st, ct = math.sin(theta), math.cos(theta)
        for i_lon in range(n_lon):
            phi = 2.0 * math.pi * i_lon / n_lon
            # 자연스러운 수관 요철 변위 (0.82 ~ 1.18)
            jit = 1.0 + 0.18 * math.sin(3 * phi + seed_val) * math.cos(2 * theta) + rng.uniform(-0.10, 0.12)
            px = cx + rx * st * math.cos(phi) * jit
            py = cy + ry * st * math.sin(phi) * jit
            pz = cz + rz * ct * (0.92 + 0.12 * jit)
            verts.append((px, py, pz))

    # 하단 캡 연결 (ring 0: index base+2 .. base+2+n_lon-1)
    r_last = base + 2 + (n_lat - 2) * n_lon
    for k in range(n_lon):
        kn = (k + 1) % n_lon
        # 상단 극점(base+1) -> 첫 번째 링(theta 작은 쪽)
        faces.append((base + 1, base + 2 + k, base + 2 + kn))
        # 하단 극점(base+0) -> 마지막 링
        faces.append((base + 0, r_last + kn, r_last + k))

    # 중간 링 사각형 면 연결
    for i_lat in range(n_lat - 2):
        r1 = base + 2 + i_lat * n_lon
        r2 = r1 + n_lon
        for k in range(n_lon):
            kn = (k + 1) % n_lon
            faces.append((r1 + k, r2 + k, r2 + kn, r1 + kn))

def add_box_3d(verts, faces, p1, p2, z_bot, z_top, width):
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

# ==============================================================================
# 3. 대상 컬렉션(02S_주변도로현황...) 정리 및 기존 단순 원기둥 나무 제거
# ==============================================================================
col_site = bpy.data.collections.get("02S_주변도로현황_교차로_보도_가설방음벽_및_인접건물현황_상세")
if not col_site:
    col_site = bpy.context.scene.collection

# 기존 유치한 원기둥 가로수 메쉬(04B_가로수..., 04C_가로수...) 삭제
for o in list(col_site.objects):
    if any(k in o.name for k in ("04B_가로수", "04C_가로수", "04D_실사형", "04E_실사형", "04F_실사형")):
        bpy.data.objects.remove(o, do_unlink=True)

# ==============================================================================
# 4. 실사형 다중 분지 가로수 (느티나무/은행나무 수형 — 3단계 분지 + 3톤 다층 수관 + 주철 보호틀)
# ==============================================================================
bark_v,  bark_f  = [], []
sun_v,   sun_f   = [], []
mid_v,   mid_f   = [], []
deep_v,  deep_f  = [], []
grate_v, grate_f = [], []

tree_positions = []
# 북측 보도 가로수 열
for xt in range(-30, 205, 13):
    if 14 <= xt <= 31 or 54 <= xt <= 88:
        continue
    yt = 29.8 if xt < 60 else (32.0 + 0.04 * (xt - 88) if xt > 88 else 32.0)
    tree_positions.append((float(xt), yt))
# 남측 보도 가로수 열
for xt in range(-30, 205, 13):
    if 38 <= xt <= 64 or 148 <= xt <= 166:
        continue
    yt = -10.8 if xt < 60 else (-11.2 + 0.03 * max(0, xt - 115))
    tree_positions.append((float(xt), yt))

for idx_t, (tx, ty) in enumerate(tree_positions):
    rng = random.Random(1000 + idx_t * 37)
    scale_t = rng.uniform(0.88, 1.18)
    rot_z0  = rng.uniform(0.0, 2.0 * math.pi)

    # 1) 보도면 주철 가로수 보호판 (1.35m x 1.35m 격자 프레임)
    z_g = 0.16
    add_box_3d(grate_v, grate_f, (tx - 0.68, ty - 0.58), (tx + 0.68, ty - 0.58), z_g, z_g + 0.04, 0.18)
    add_box_3d(grate_v, grate_f, (tx - 0.68, ty + 0.58), (tx + 0.68, ty + 0.58), z_g, z_g + 0.04, 0.18)
    add_box_3d(grate_v, grate_f, (tx - 0.58, ty - 0.68), (tx - 0.58, ty + 0.68), z_g, z_g + 0.04, 0.18)
    add_box_3d(grate_v, grate_f, (tx + 0.58, ty - 0.68), (tx + 0.58, ty + 0.68), z_g, z_g + 0.04, 0.18)

    # 2) 뿌리 플레어(Root Flare) + 3단 굴곡 주간(Main Trunk)
    p0 = (tx, ty, z_g)
    p1 = (tx + rng.uniform(-0.06, 0.06), ty + rng.uniform(-0.06, 0.06), z_g + 0.85 * scale_t)
    p2 = (p1[0] + rng.uniform(-0.10, 0.10), p1[1] + rng.uniform(-0.10, 0.10), z_g + 1.85 * scale_t)
    p3 = (p2[0] + rng.uniform(-0.08, 0.08), p2[1] + rng.uniform(-0.08, 0.08), z_g + 2.65 * scale_t)
    add_tapered_tube_3d(bark_v, bark_f, p0, p1, 0.24 * scale_t, 0.17 * scale_t, n_seg=8)
    add_tapered_tube_3d(bark_v, bark_f, p1, p2, 0.17 * scale_t, 0.14 * scale_t, n_seg=8)
    add_tapered_tube_3d(bark_v, bark_f, p2, p3, 0.14 * scale_t, 0.11 * scale_t, n_seg=7)

    # 3) 1차 주가지 (Primary Branches: 5~6개 방사상 분지) -> 2차 부가지 (Secondary Branches: 각 3개) -> 다층 수관 클러스터
    n_b1 = rng.choice([5, 6])
    for b1 in range(n_b1):
        az1 = rot_z0 + (2.0 * math.pi * b1 / n_b1) + rng.uniform(-0.22, 0.22)
        el1 = math.radians(rng.uniform(34.0, 52.0))
        L1  = rng.uniform(1.55, 2.05) * scale_t
        # 일부 가지는 p2에서, 일부는 p3에서 분지하여 자연스러운 수형 형성
        start_b1 = p2 if (b1 % 2 == 0) else p3
        end_b1 = (
            start_b1[0] + L1 * math.cos(el1) * math.cos(az1),
            start_b1[1] + L1 * math.cos(el1) * math.sin(az1),
            start_b1[2] + L1 * math.sin(el1)
        )
        add_tapered_tube_3d(bark_v, bark_f, start_b1, end_b1, 0.085 * scale_t, 0.048 * scale_t, n_seg=6)

        # 1차 가지 중간 하부 그늘 수관 클러스터 (Deep Shade Foliage)
        mid_b1 = (
            0.35 * start_b1[0] + 0.65 * end_b1[0],
            0.35 * start_b1[1] + 0.65 * end_b1[1],
            0.35 * start_b1[2] + 0.65 * end_b1[2] + 0.15
        )
        add_organic_foliage_cluster(
            deep_v, deep_f, mid_b1,
            rx=rng.uniform(0.85, 1.15) * scale_t,
            ry=rng.uniform(0.85, 1.15) * scale_t,
            rz=rng.uniform(0.58, 0.78) * scale_t,
            seed_val=idx_t * 100 + b1 * 13
        )

        # 2차 부가지 (Secondary Twigs: 각 주가지 끝에서 3갈래로 분지)
        for b2 in range(3):
            az2 = az1 + math.radians((b2 - 1) * 38.0 + rng.uniform(-12.0, 12.0))
            el2 = math.radians(rng.uniform(22.0, 58.0))
            L2  = rng.uniform(0.95, 1.45) * scale_t
            end_b2 = (
                end_b1[0] + L2 * math.cos(el2) * math.cos(az2),
                end_b1[1] + L2 * math.cos(el2) * math.sin(az2),
                end_b1[2] + L2 * math.sin(el2)
            )
            add_tapered_tube_3d(bark_v, bark_f, end_b1, end_b2, 0.046 * scale_t, 0.018 * scale_t, n_seg=5)

            # 2차 가지 끝단 수관 클러스터 (중간층 진녹색 + 상부 연녹색 교차 배치)
            rx_c = rng.uniform(0.82, 1.25) * scale_t
            ry_c = rng.uniform(0.82, 1.25) * scale_t
            rz_c = rng.uniform(0.62, 0.92) * scale_t
            if b2 == 1 or end_b2[2] > z_g + 4.3 * scale_t:
                add_organic_foliage_cluster(sun_v, sun_f, (end_b2[0], end_b2[1], end_b2[2] + 0.18), rx_c, ry_c, rz_c, seed_val=idx_t * 300 + b1 * 30 + b2)
            else:
                add_organic_foliage_cluster(mid_v, mid_f, end_b2, rx_c, ry_c, rz_c, seed_val=idx_t * 300 + b1 * 30 + b2)

    # 4) 수관 정점부(Crown Apex) 풍성한 상단 수관 클러스터 3개 추가
    for top_k in range(3):
        ang_t = rot_z0 + top_k * 2.094
        c_top = (
            p3[0] + 0.45 * math.cos(ang_t) * scale_t,
            p3[1] + 0.45 * math.sin(ang_t) * scale_t,
            p3[2] + rng.uniform(2.15, 2.65) * scale_t
        )
        add_organic_foliage_cluster(
            sun_v, sun_f, c_top,
            rx=rng.uniform(1.05, 1.35) * scale_t,
            ry=rng.uniform(1.05, 1.35) * scale_t,
            rz=rng.uniform(0.75, 0.98) * scale_t,
            seed_val=idx_t * 500 + top_k
        )

create_mesh_obj(f"04B_실사형가로수_주철보호판_및_보호틀_{len(tree_positions)}주", grate_v, grate_f, mat_tree_grate, col_site)
create_mesh_obj(f"04C_실사형가로수_다중분지수간_및_가지_{len(tree_positions)}주", bark_v,  bark_f,  mat_bark,       col_site)
create_mesh_obj(f"04D_실사형가로수_수관상부_햇빛연녹색잎_{len(tree_positions)}주", sun_v,   sun_f,   mat_leaf_sun,   col_site)
create_mesh_obj(f"04E_실사형가로수_수관중간_자연녹색잎_{len(tree_positions)}주",   mid_v,   mid_f,   mat_leaf_mid,   col_site)
create_mesh_obj(f"04F_실사형가로수_수관하부_음영진녹색잎_{len(tree_positions)}주", deep_v,  deep_f,  mat_leaf_deep,  col_site)

# ==============================================================================
# 5. 실사형 한국 도심 경수대로 아치형 LED 가로등 (H = 8.5m, 차도 방향 2.6m 캔틸레버 암)
# ==============================================================================
lamp_pole_v, lamp_pole_f = [], []
lamp_arm_v,  lamp_arm_f  = [], []
lamp_led_v,  lamp_led_f  = [], []

lamp_positions = []
# 북측 보도 가로등 열 (차도 남측 방향 angle = -90 deg 지향)
for xl in range(-36, 208, 26):
    if 15 <= xl <= 30 or 74 <= xl <= 88:
        continue
    yl = 26.8 if xl < 55 else (28.5 if xl < 88 else 29.2 + 0.04 * max(0, xl - 115))
    lamp_positions.append((float(xl), yl, -90.0))
# 남측 보도 가로등 열 (차도 북측 방향 angle = +90 deg 지향)
for xl in range(-36, 208, 26):
    if 40 <= xl <= 61 or 150 <= xl <= 165:
        continue
    yl = -7.6 if xl < 55 else (-8.8 if xl < 115 else -7.5 + 0.04 * (xl - 115))
    lamp_positions.append((float(xl), yl, 90.0))

for (lx, ly, dir_deg) in lamp_positions:
    rad_l = math.radians(dir_deg)
    dx_l, dy_l = math.cos(rad_l), math.sin(rad_l)

    # 1) 기초 플랜지 & 하부 안전기함(점검구) + 8.0m 테이퍼 강관 등주
    add_tapered_tube_3d(lamp_pole_v, lamp_pole_f, (lx, ly, 0.15), (lx, ly, 0.35), 0.24, 0.22, n_seg=8)
    add_tapered_tube_3d(lamp_pole_v, lamp_pole_f, (lx, ly, 0.35), (lx, ly, 1.55), 0.16, 0.14, n_seg=8)
    add_tapered_tube_3d(lamp_pole_v, lamp_pole_f, (lx, ly, 1.55), (lx, ly, 7.60), 0.13, 0.075, n_seg=8)

    # 2) 5단 유선형 아치 붐암 (Gooseneck Curved Arm: Z=7.3m -> Z=8.55m, 수평 돌출 2.65m)
    arm_pts = [
        (lx,                ly,                7.35),
        (lx + 0.45 * dx_l,  ly + 0.45 * dy_l,  7.85),
        (lx + 1.05 * dx_l,  ly + 1.05 * dy_l,  8.22),
        (lx + 1.75 * dx_l,  ly + 1.75 * dy_l,  8.44),
        (lx + 2.45 * dx_l,  ly + 2.45 * dy_l,  8.52),
    ]
    for k in range(len(arm_pts) - 1):
        add_tapered_tube_3d(lamp_arm_v, lamp_arm_f, arm_pts[k], arm_pts[k+1], 0.068 - 0.008*k, 0.060 - 0.008*k, n_seg=6)
    # 보조 타이바(Tie-bar) 브라켓
    add_tapered_tube_3d(lamp_arm_v, lamp_arm_f, (lx, ly, 6.75), arm_pts[2], 0.035, 0.030, n_seg=6)

    # 3) 다이캐스트 유선형 LED 등기구 헤드 & 하부 고휘도 발광 LED 렌즈
    hx1, hy1 = lx + 2.15 * dx_l, ly + 2.15 * dy_l
    hx2, hy2 = lx + 3.05 * dx_l, ly + 3.05 * dy_l
    add_box_3d(lamp_pole_v, lamp_pole_f, (hx1, hy1), (hx2, hy2), 8.46, 8.60, 0.42)
    add_box_3d(lamp_led_v,  lamp_led_f,  (hx1 + 0.08 * dx_l, hy1 + 0.08 * dy_l), (hx2 - 0.06 * dx_l, hy2 - 0.06 * dy_l), 8.41, 8.46, 0.34)

create_mesh_obj(f"04G_실사형가로등_테이퍼등주_및_헤드하우징_{len(lamp_positions)}기", lamp_pole_v, lamp_pole_f, mat_pole_dark,   col_site)
create_mesh_obj(f"04H_실사형가로등_유선형아치붐암_브라켓_{len(lamp_positions)}기",    lamp_arm_v,  lamp_arm_f,  mat_pole_silver, col_site)
create_mesh_obj(f"04I_실사형가로등_고휘도LED발광모듈_{len(lamp_positions)}기",        lamp_led_v,  lamp_led_f,  mat_led_emit,    col_site)

# ==============================================================================
# 6. CAD 원본(지-신호등-현황) 1:1 실사형 교통신호등 갠트리 및 4구/3구/보행자 신호등기구
# ==============================================================================
sig_post_v, sig_post_f = [], []
sig_box_v,  sig_box_f  = [], []
sig_r_v,    sig_r_f    = [], []
sig_y_v,    sig_y_f    = [], []
sig_g_v,    sig_g_f    = [], []

def build_signal_gantry(post_xy, arm_end_xy, n_heads=2, is_four_aspect=True, has_ped=True):
    px, py = post_xy
    ex, ey = arm_end_xy
    dx, dy = ex - px, ey - py
    L_arm = math.hypot(dx, dy)
    if L_arm < 0.5:
        return
    ux, uy = dx / L_arm, dy / L_arm
    # 신호등 전면이 바라보는 방향 (암에 수직인 차로 진행 방향)
    nx, ny = -uy, ux

    # 1) 중량급 신호등 강관 지주 (H = 6.3m, Ø320 -> Ø220) + 기초 플랜지 + 교통신호제어기함
    add_tapered_tube_3d(sig_post_v, sig_post_f, (px, py, 0.0), (px, py, 0.35), 0.28, 0.25, n_seg=10)
    add_tapered_tube_3d(sig_post_v, sig_post_f, (px, py, 0.35), (px, py, 6.30), 0.18, 0.12, n_seg=10)

    # 2) 수평 캔틸레버 메인 암(Z=5.55m) + 상부 경사 타이로드(Z=6.20m -> 암 65% 지점)
    add_tapered_tube_3d(sig_post_v, sig_post_f, (px, py, 5.55), (ex, ey, 5.65), 0.11, 0.075, n_seg=8)
    mid_x, mid_y = px + 0.65 * dx, py + 0.65 * dy
    add_tapered_tube_3d(sig_post_v, sig_post_f, (px, py, 6.22), (mid_x, mid_y, 5.62), 0.055, 0.045, n_seg=6)

    # 3) 보행자 신호등 (2색 수직형: Z=2.5m ~ 3.2m)
    if has_ped:
        ped_p1 = (px + 0.25 * ux - 0.18 * nx, py + 0.25 * uy - 0.18 * ny)
        ped_p2 = (px + 0.25 * ux + 0.18 * nx, py + 0.25 * uy + 0.18 * ny)
        add_box_3d(sig_box_v, sig_box_f, ped_p1, ped_p2, 2.45, 3.25, 0.28)
        # 적색(상) & 녹색(하) 보행자 렌즈
        add_tapered_tube_3d(sig_r_v, sig_r_f, (px + 0.25 * ux, py + 0.25 * uy, 3.02), (px + 0.42 * ux, py + 0.42 * uy, 3.02), 0.11, 0.11, n_seg=8)
        add_tapered_tube_3d(sig_g_v, sig_g_f, (px + 0.25 * ux, py + 0.25 * uy, 2.68), (px + 0.42 * ux, py + 0.42 * uy, 2.68), 0.11, 0.11, n_seg=8)

    # 4) 캔틸레버 암 상의 4색/3색 수평형 차량 신호등기구 (차양막 Visor 포함!)
    fractions = [0.52, 0.88] if n_heads >= 2 else [0.75]
    for idx_h, frac in enumerate(fractions):
        hx, hy = px + frac * dx, py + frac * dy
        hz = 5.55 + frac * 0.10 - 0.15
        n_lights = 4 if (is_four_aspect or idx_h == 0) else 3
        box_half_len = 0.22 * n_lights
        b_p1 = (hx - box_half_len * ux, hy - box_half_len * uy)
        b_p2 = (hx + box_half_len * ux, hy + box_half_len * uy)
        # 흑색 신호등 본체 하우징
        add_box_3d(sig_box_v, sig_box_f, b_p1, b_p2, hz - 0.22, hz + 0.22, 0.26)

        # 각 신호 렌즈 (적색, 황색, 좌회전 녹색화살표, 녹색) + 차양막(Visor Hood)
        for l_i in range(n_lights):
            off_u = (-box_half_len + 0.22 + l_i * 0.44)
            lx_i = hx + off_u * ux
            ly_i = hy + off_u * uy
            # 양방향에서 모두 보이도록 전면(+n)과 후면(-n) 모두 렌즈 및 차양막 배치
            for sign_n in (-1.0, 1.0):
                p_lens0 = (lx_i + sign_n * 0.12 * nx, ly_i + sign_n * 0.12 * ny, hz)
                p_lens1 = (lx_i + sign_n * 0.18 * nx, ly_i + sign_n * 0.18 * ny, hz)
                p_visor = (lx_i + sign_n * 0.34 * nx, ly_i + sign_n * 0.34 * ny, hz + 0.03)
                # 차양막 (Visor)
                add_tapered_tube_3d(sig_box_v, sig_box_f, p_lens0, p_visor, 0.155, 0.165, n_seg=8)
                # 발광 LED 렌즈
                if l_i == 0:
                    add_tapered_tube_3d(sig_r_v, sig_r_f, p_lens0, p_lens1, 0.135, 0.135, n_seg=8)
                elif l_i == 1:
                    add_tapered_tube_3d(sig_y_v, sig_y_f, p_lens0, p_lens1, 0.135, 0.135, n_seg=8)
                else:
                    add_tapered_tube_3d(sig_g_v, sig_g_f, p_lens0, p_lens1, 0.135, 0.135, n_seg=8)

# CAD 원본(지-신호등-현황) 실제 교차로 신호등 지주 및 암 위치 + 서측/동측 사거리 교차로 신호등 배치
gantry_specs = [
    # 1) 교육원삼거리 (정거장 중앙 교차로 — CAD 지-신호등-현황 1:1 좌표)
    ((51.84, 26.38),  (51.67, 16.19), 2, True,  True),   # 북측 지주 -> 남측 본선 차로 방향 11.1m 암 (4구x2)
    ((51.84, 26.38),  (60.04, 26.25), 2, False, False),  # 북측 지주 -> 동측 횡단보도/이면도로 방향 9.1m 암 (3구x2)
    ((76.89, -12.77), (76.41, -1.78), 2, True,  True),   # 남동측 지주(송정각 앞) -> 북측 본선 방향 11.9m 암 (4구+3구)
    ((67.09, -25.46), (58.09, -25.63),2, False, True),   # 남측 이면도로 동측 지주 -> 서측 방향 9.9m 암 (3구x2)
    ((44.61, -25.83), (52.50, -25.80),1, False, True),   # 남측 이면도로 서측 지주 -> 동측 방향 암
    # 2) 서측 사거리 교차로 (X ≈ -33m ~ -24m 횡단보도 및 교차로 구간)
    ((-25.50, 26.80), (-25.50, 15.20),2, True,  True),   # 서측 사거리 북동 지주 -> 본선 상행 방향 암
    ((-34.50, -7.20), (-34.50,  4.20),2, True,  True),   # 서측 사거리 남서 지주 -> 본선 하행 방향 암
    # 3) 동측 정거장 종점부 횡단보도 교차로 (X ≈ 119m ~ 126m)
    ((119.50, 28.50), (119.50, 17.50),2, True,  True),   # 동측 북부 지주 -> 본선 상행 방향 암
    ((125.50, -6.50), (125.50,  4.50),2, True,  True),   # 동측 남부 지주 -> 본선 하행 방향 암
]

for post_xy, arm_xy, nh, is_4, has_p in gantry_specs:
    build_signal_gantry(post_xy, arm_xy, n_heads=nh, is_four_aspect=is_4, has_ped=has_p)

create_mesh_obj("04J_실사형교통신호등_강관지주_및_캔틸레버암", sig_post_v, sig_post_f, mat_pole_silver, col_site)
create_mesh_obj("04K_실사형교통신호등_4색3색등기구본체_및_차양막", sig_box_v, sig_box_f, mat_sig_body, col_site)
create_mesh_obj("04L_실사형교통신호등_적색LED신호렌즈", sig_r_v, sig_r_f, mat_sig_red, col_site)
create_mesh_obj("04M_실사형교통신호등_황색LED신호렌즈", sig_y_v, sig_y_f, mat_sig_yellow, col_site)
create_mesh_obj("04N_실사형교통신호등_녹색LED신호렌즈", sig_g_v, sig_g_f, mat_sig_green, col_site)

# 카메라를 가로수·가로등·교통신호등과 정거장 8단계 교통처리가 함께 잘 보이는 입체 조감 각도로 설정
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'
                    space.shading.show_cavity = True
                    space.shading.cavity_type = 'BOTH'
                    r3d = space.region_3d
                    r3d.view_perspective = 'PERSP'
                    r3d.view_location = Vector((62.0, 8.0, 2.0))
                    r3d.view_distance = 72.0
                    r3d.view_rotation = Euler((math.radians(56.0), 0.0, math.radians(-18.0)), 'XYZ').to_quaternion()

bpy.ops.wm.save_as_mainfile(filepath=blend_save_path)
if os.path.exists(os.path.dirname(repo_blend_path)):
    bpy.ops.wm.save_as_mainfile(filepath=repo_blend_path, compress=True, copy=True)

print("Successfully upgraded to realistic multi-branch street trees, arched LED street lamps, and 4-aspect traffic signal gantries!")
