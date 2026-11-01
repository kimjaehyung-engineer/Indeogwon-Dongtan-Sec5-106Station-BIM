import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector

# Load exact alignment engine
drain_script_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\770731a9-ce60-48bb-9690-7a68027016c5\scratch\build_drainage_bim.py"
exec(open(drain_script_path, encoding="utf-8").read().split("# ==============================================================================\n# 2.")[0])

def get_or_create_mat(name, rgba, metallic=0.5, roughness=0.35, alpha=1.0, emission=0.0):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if emission > 0 and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = emission
    mat.diffuse_color = (rgba[0], rgba[1], rgba[2], alpha)
    return mat

mat_hbeam_rib   = get_or_create_mat("MAT_NATM_Steel_Rib_H150",     (0.88, 0.36, 0.08, 1.0), metallic=0.85, roughness=0.25)
mat_lattice_rib = get_or_create_mat("MAT_NATM_Lattice_Girder_LG",  (0.95, 0.68, 0.12, 1.0), metallic=0.80, roughness=0.28)
mat_rockbolt    = get_or_create_mat("MAT_NATM_RockBolt_D25",       (0.15, 0.92, 0.45, 1.0), metallic=0.75, roughness=0.25, emission=0.15)
mat_plate_nut   = get_or_create_mat("MAT_NATM_BearingPlate_150",   (0.20, 0.25, 0.30, 1.0), metallic=0.90, roughness=0.20)
mat_umbrella    = get_or_create_mat("MAT_NATM_UmbrellaPipe_L12m",  (0.12, 0.68, 0.98, 1.0), metallic=0.82, roughness=0.22, emission=0.15)
mat_footpile    = get_or_create_mat("MAT_NATM_FootSide_Grouting",  (0.75, 0.28, 0.95, 1.0), metallic=0.75, roughness=0.28)
mat_shot_stage  = get_or_create_mat("MAT_NATM_Shotcrete_Stage",    (0.52, 0.56, 0.60, 0.48), metallic=0.10, roughness=0.75, alpha=0.48)
mat_exc_upper   = get_or_create_mat("MAT_NATM_ExcFace_UpperHalf",  (0.72, 0.54, 0.34, 0.88), metallic=0.05, roughness=0.85, alpha=0.88)
mat_exc_core    = get_or_create_mat("MAT_NATM_ExcFace_RingCore",   (0.85, 0.66, 0.38, 0.92), metallic=0.05, roughness=0.85, alpha=0.92)
mat_exc_lower   = get_or_create_mat("MAT_NATM_ExcFace_LowerBench", (0.55, 0.42, 0.28, 0.90), metallic=0.05, roughness=0.85, alpha=0.90)
mat_exc_invert  = get_or_create_mat("MAT_NATM_ExcFace_Invert",     (0.42, 0.35, 0.26, 0.92), metallic=0.05, roughness=0.85, alpha=0.92)
mat_grout_halo  = get_or_create_mat("MAT_NATM_WaterGrouting_180",  (0.18, 0.82, 0.88, 0.22), metallic=0.10, roughness=0.40, alpha=0.22)

col_21 = bpy.data.collections.get("21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400")
if not col_21:
    col_21 = bpy.data.collections.new("21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400")
    bpy.context.scene.collection.children.link(col_21)
else:
    for obj in list(col_21.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

def add_tube(bm, pts, radius=0.03, n_seg=6, closed=False, cap=True):
    if len(pts) < 2:
        return
    rings = []
    n_pts = len(pts)
    for i, p in enumerate(pts):
        if closed:
            t = (pts[(i + 1) % n_pts] - pts[(i - 1) % n_pts]).normalized()
        else:
            if i == 0:
                t = (pts[1] - pts[0]).normalized()
            elif i == n_pts - 1:
                t = (pts[-1] - pts[-2]).normalized()
            else:
                t = (pts[i + 1] - pts[i - 1]).normalized()
        if t.length < 1e-6:
            t = Vector((1, 0, 0))
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        b1 = t.cross(up).normalized()
        b2 = t.cross(b1).normalized()
        ring = []
        for k in range(n_seg):
            ang = 2.0 * math.pi * k / n_seg
            v = p + (math.cos(ang) * b1 + math.sin(ang) * b2) * radius
            ring.append(bm.verts.new(v))
        rings.append(ring)

    limit = n_pts if closed else (n_pts - 1)
    for i in range(limit):
        r0 = rings[i]
        r1 = rings[(i + 1) % n_pts]
        for k in range(n_seg):
            kn = (k + 1) % n_seg
            try:
                bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
            except:
                pass
    if cap and not closed and len(rings) >= 2:
        try:
            bm.faces.new(rings[0][::-1])
            bm.faces.new(rings[-1])
        except:
            pass

def add_oriented_box(bm, center, e1, e2, e3, sx, sy, sz):
    vs = []
    for dx in [-0.5 * sx, 0.5 * sx]:
        for dy in [-0.5 * sy, 0.5 * sy]:
            for dz in [-0.5 * sz, 0.5 * sz]:
                vs.append(bm.verts.new(center + e1 * dx + e2 * dy + e3 * dz))
    faces = [
        (0, 1, 3, 2), (4, 6, 7, 5),
        (0, 4, 5, 1), (2, 3, 7, 6),
        (0, 2, 6, 4), (1, 5, 7, 3)
    ]
    for f in faces:
        try:
            bm.faces.new((vs[f[0]], vs[f[1]], vs[f[2]], vs[f[3]]))
        except:
            pass

def build_obj(bm, name, mat, col):
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj

def is_left_opening(sta, ang_deg, v_height):
    if 12780.2 <= sta <= 12788.6 and ang_deg < 44.0:
        return True
    for n_sta in [11825.60, 12214.80, 12614.80]:
        if abs(sta - n_sta) <= 2.85 and ang_deg < 30.0 and v_height < 4.95:
            return True
    return False

# Support pattern helper from 04.구조물 설계도(1권) 지질 및 지보패턴 계획도(1),(2) (Streams 46, 48, 57)
def get_support_pattern(sta):
    if 11896.0 <= sta <= STA_106_START:
        return "PD-6-3" # H-150x150, @0.8m, L2 직천공 대구경 강관다단 180°, 차수그라우팅 180°
    elif STA_106_END <= sta <= 12139.52:
        return "PD-6-3" # 연장 95.20m, 직천공 L2, 상/하(M)
    elif 12139.52 < sta <= 12189.92:
        return "PD-6-2" # 연장 50.40m, L2, 상반(M)/하반(B)
    elif 12189.92 < sta <= 12469.92:
        return "PD-6-3" # 연장 280.00m, 직천공 L2, 상/하(M)
    elif 12469.92 < sta <= 12705.12:
        return "PD-6-2" # 연장 235.20m, L2, 상반(M)/하반(B)
    elif 12705.12 < sta <= 12860.0:
        return "PD-6-1" # 연장 733.6m 시점부, L1 (상반 120° 대구경 강관다단), H-125x125, 록볼트 L=4.0m
    else:
        # STA 11660.0 ~ 11896.0: Showcase Staged Excavation (11660~11720) & PD-4 / PD-5 Lattice Girder + Rockbolt zone
        if sta < 11780.0:
            return "PD-4-2"
        else:
            return "PD-5-1"

# ==============================================================================
# 1. 강지보재 (H-150x150, H-125x125, 격자지보 LG-70/LG-50, 연결볼트/타이로드, 베이스플레이트)
# ==============================================================================
bm_hbeam_ribs   = bmesh.new()
bm_lattice_ribs = bmesh.new()
bm_rockbolts    = bmesh.new()
bm_plates       = bmesh.new()
bm_umbrella     = bmesh.new()
bm_footpiles    = bmesh.new()
bm_grout_zone   = bmesh.new()

arch_degs = np.linspace(-28.0, 208.0, 29)
R_RIB = 5.65 # Inside shotcrete layer (r_in=5.55, r_out=5.75)

# Note: STA 11660 ~ 11716 is reserved for the 5-Step Staged Excavation Showcase!
# From STA 11716 ~ 11934.68 and STA 12044.32 ~ 12860.0, build full tunnel support elements
for sta_a, sta_b in [(11716.0, STA_106_START), (STA_106_END, 12860.0)]:
    s_cur = sta_a
    ring_idx = 0
    prev_rib_sta = None

    while s_cur <= sta_b + 0.01:
        s = min(s_cur, sta_b)
        pat = get_support_pattern(s)
        p, t, n_left, up_v = get_frame(s)

        # Determine rib spacing (visual step = 2x design C.T.C for clean 3D performance while preserving exact density near portals/S007)
        near_focus = (abs(s - sta_a) < 15.0 or abs(s - sta_b) < 15.0 or abs(s - 12784.40) < 18.0)
        if pat.startswith("PD-6"):
            step_s = 0.80 if near_focus else 1.60
            is_hbeam = True
            rib_radius = 0.075 if pat == "PD-6-3" else 0.065
        else:
            step_s = 1.20 if near_focus else 2.00
            is_hbeam = False
            rib_radius = 0.055

        target_bm = bm_hbeam_ribs if is_hbeam else bm_lattice_ribs

        # (A) Steel Rib Arch (상반 아치 + 하반 레그 분할 이음 플랜지 포함)
        rib_pts = []
        for deg in arch_degs:
            rad = math.radians(deg)
            u = R_RIB * math.cos(rad)
            v = max(-0.42, 2.45 + R_RIB * math.sin(rad))
            if is_left_opening(s, deg, v):
                if len(rib_pts) >= 2:
                    add_tube(target_bm, rib_pts, radius=rib_radius, n_seg=4)
                rib_pts = []
            else:
                rib_pts.append(p + n_left * u + up_v * v)
        if len(rib_pts) >= 2:
            add_tube(target_bm, rib_pts, radius=rib_radius, n_seg=4)

        # Baseplates (PL-180x180x10) & Splice Plates at Springline (S.L v=2.45m, 상·하반 이음부) & Crown (90°)
        for deg_sp in [-28.0, 0.0, 90.0, 180.0, 208.0]:
            rad = math.radians(deg_sp)
            u = R_RIB * math.cos(rad)
            v = max(-0.42, 2.45 + R_RIB * math.sin(rad))
            if not is_left_opening(s, deg_sp, v):
                pt_sp = p + n_left * u + up_v * v
                r_dir = (math.cos(rad) * n_left + math.sin(rad) * up_v).normalized()
                t_arc = (-math.sin(rad) * n_left + math.cos(rad) * up_v).normalized()
                add_oriented_box(bm_plates, pt_sp, t, r_dir, t_arc, 0.22, 0.22, 0.04)

        # Longitudinal Tie-Rods (연결봉 D16 / 간격재) between consecutive ribs
        if prev_rib_sta is not None and (s - prev_rib_sta) <= 2.5:
            p_prev, _, nl_prev, up_prev = get_frame(prev_rib_sta)
            for deg_tie in [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]:
                rad = math.radians(deg_tie)
                u = R_RIB * math.cos(rad)
                v = 2.45 + R_RIB * math.sin(rad)
                if not is_left_opening(s, deg_tie, v):
                    p1 = p_prev + nl_prev * u + up_prev * v
                    p2 = p + n_left * u + up_v * v
                    add_tube(target_bm, [p1, p2], radius=0.016, n_seg=4, cap=False)

        # (B) System Rock Bolts (SD400 D25, L=4.0m radial bolts + 150x150x10t Bearing Plates)
        # Note: In Stream 57, PD-4/5 have 13.5~17.5 bolts/ring (L=4.0m), PD-6-1/6-2 have 8.0~4.0 bolts/ring (L=4.0m),
        # and PD-6-3 has Foot/Sidewall rock/grout bolts!
        if pat in ["PD-4-2", "PD-5-1"]:
            bolt_degs = np.linspace(-10.0, 190.0, 14 if (ring_idx % 2 == 0) else 13)
            bolt_len = 4.0
        elif pat in ["PD-6-1", "PD-6-2"]:
            bolt_degs = [-12.0, 8.0, 28.0, 48.0, 132.0, 152.0, 172.0, 192.0] # 8 bolts on sidewalls/shoulders below 120° umbrella arch
            bolt_len = 4.0
        else:
            # PD-6-3: Sidewall & lower bench radial reinforcement bolts
            bolt_degs = [-15.0, 5.0, 175.0, 195.0]
            bolt_len = 4.0

        for deg_b in bolt_degs:
            rad = math.radians(deg_b)
            u_in = (R_RIB - 0.08) * math.cos(rad)
            v_in = 2.45 + (R_RIB - 0.08) * math.sin(rad)
            if is_left_opening(s, deg_b, v_in):
                continue
            r_dir = (math.cos(rad) * n_left + math.sin(rad) * up_v).normalized()
            t_arc = (-math.sin(rad) * n_left + math.cos(rad) * up_v).normalized()
            p_head = p + n_left * u_in + up_v * v_in
            p_tip  = p_head + r_dir * bolt_len
            add_tube(bm_rockbolts, [p_head - r_dir * 0.08, p_tip], radius=0.022, n_seg=4)
            # 150x150x10t Bearing Plate & Nut at rockbolt head
            add_oriented_box(bm_plates, p_head, t, t_arc, r_dir, 0.18, 0.18, 0.03)

        # (C) PD-6-3 / PD-6-2 각부 보강공 (Foot Piles at Upper Half & Lower Bench Base, L=4.5m angled 35° downward)
        if pat in ["PD-6-3", "PD-6-2"] and (ring_idx % 2 == 0):
            for sgn in [-1.0, 1.0]:
                if sgn > 0 and is_left_opening(s, 0.0, 2.0):
                    continue
                # Upper half foot pile (상반 각부 보강그라우팅, v = 2.45m) & Lower bench foot pile (하반 각부 보강그라우팅, v = 0.20m)
                for v_foot in [2.45, 0.25]:
                    p_f0 = p + n_left * (sgn * 5.62) + up_v * v_foot
                    f_dir = (sgn * math.cos(math.radians(35.0)) * n_left - math.sin(math.radians(35.0)) * up_v).normalized()
                    p_f1 = p_f0 + f_dir * 4.50
                    add_tube(bm_footpiles, [p_f0, p_f1], radius=0.032, n_seg=5)

        prev_rib_sta = s
        s_cur += step_s
        ring_idx += 1

    # (D) 강관다단그라우팅 (Umbrella Arch Method: L=12.0m, C.T.C 5.6m longitudinal step, C.T.C 500mm transverse, α=10° look-up angle)
    # PD-6-3 / PD-6-2 (L2): θ = 180° (0° ~ 180°, 37 pipes per umbrella ring)
    # PD-6-1 (L1) / PD-4/5 (Forepoling): θ = 120° (30° ~ 150°, 25 pipes per umbrella ring)
    s_umb = sta_a + 1.0
    while s_umb <= sta_b - 6.0:
        pat_u = get_support_pattern(s_umb)
        p_u0, t_u0, nl_u0, up_u0 = get_frame(s_umb)
        p_u1, t_u1, nl_u1, up_u1 = get_frame(min(sta_b, s_umb + 12.0))

        if pat_u in ["PD-6-3", "PD-6-2"]:
            umb_degs = np.linspace(0.0, 180.0, 33) # θ = 180° (상반 180° 보강)
            pipe_len = 12.0
            step_umb = 5.60 # C.T.C (종) 5,600mm (2겹 이상의 강관 중첩!)
        elif pat_u == "PD-6-1":
            umb_degs = np.linspace(30.0, 150.0, 23) # θ = 120° (상반 120° 보강)
            pipe_len = 12.0
            step_umb = 5.60
        else:
            umb_degs = np.linspace(30.0, 150.0, 21) # 훠폴링 θ = 120°
            pipe_len = 4.0
            step_umb = 3.00

        p_end_s, _, nl_end, up_end = get_frame(min(sta_b, s_umb + pipe_len))
        for deg_u in umb_degs:
            rad = math.radians(deg_u)
            r_start = 5.72
            # 10° outward flare over L=12m (+0.85m radial flare at tip for overlapping umbrella canopy)
            r_end   = 5.72 + (0.75 if pipe_len == 12.0 else 0.30)
            pt0 = p_u0    + nl_u0  * (r_start * math.cos(rad)) + up_u0  * (2.45 + r_start * math.sin(rad))
            pt1 = p_end_s + nl_end * (r_end   * math.cos(rad)) + up_end * (2.45 + r_end   * math.sin(rad))
            add_tube(bm_umbrella, [pt0, pt1], radius=0.036 if pipe_len == 12.0 else 0.024, n_seg=5)

        s_umb += step_umb

# ==============================================================================
# 2. 터널 단계별 굴착공법 (Staged Excavation Sequence: STA 11km660 ~ 11km716)
# ==============================================================================
# Let's hide the continuous west lining/shotcrete only inside the 56m showcase window?
# Wait: Instead of deleting the west lining, let's build the 5-Stage Excavation Showcase at STA 11km660 ~ 11km716
# AND trim `NATM_본선터널_시점부_콘크리트라이닝_11K660_11K935` & `숏크리트방수층` to start at STA 11km705 so that
# STA 11km660 ~ 11km705 shows the authentic Step-by-Step NATM Excavation Progression (막장 단계별 굴착 시뮬레이션)!
bm_stage_shot = bmesh.new()
bm_face_upper = bmesh.new()
bm_face_core  = bmesh.new()
bm_face_lower = bmesh.new()
bm_face_inv   = bmesh.new()

# Define the 5 NATM Construction Stages along STA 11660.0 -> 11716.0 (advancing from East 11716 towards West 11660):
# - Stage 1 (STA 11660 ~ 11672): Pre-excavation Umbrella Arch Grouting Canopy (대구경 강관다단그라우팅 L=12m θ=180° 선시공 + 선진수평시추/TSP) & Upper Half Working Face (상반 막장면)
# - Stage 2 (STA 11672 ~ 11684): Upper Half Excavation (상반 굴착 및 링컷 코어 Ring-Cut Core 존치 + 상반 1차 숏크리트 + 상반 강지보 H-150 + 상반 록볼트 + 상반 각부 보강공)
# - Stage 3 (STA 11684 ~ 11696): Lower Bench Excavation (하반 분할 굴착 + 하반 강지보 레그 연장 + 하반 숏크리트 + 측벽 록볼트 + 하반 각부 보강공)
# - Stage 4 (STA 11696 ~ 11706): Invert Excavation & Closure (인버트 굴착 H=300~500mm + 버림/채움 콘크리트 타설 + 방수쉬트/부직포 포설)
# - Stage 5 (STA 11706 ~ 11716): Final Rebar Cage Assembly & Concrete Lining Cast (콘크리트 라이닝 복배근 조립 및 라이닝 타설 완료)

def build_solid_section_block(bm, sta_start, sta_end, profile_uv, n_steps=6):
    stas = np.linspace(sta_start, sta_end, n_steps)
    rings = []
    n_p = len(profile_uv)
    for s in stas:
        p, _, nl, up = get_frame(s)
        rings.append([bm.verts.new(p + nl * u + up * v) for u, v in profile_uv])
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for j in range(n_p):
            jn = (j + 1) % n_p
            bm.faces.new((r0[j], r0[jn], r1[jn], r1[j]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])

# 1) Unexcavated Upper Half Rock Mass / Working Face at STA 11660 ~ 11672
prof_upper_rock = []
for k in range(25):
    ang = math.radians(180.0 * k / 24.0)
    prof_upper_rock.append((5.65 * math.cos(ang), 2.45 + 5.65 * math.sin(ang)))
build_solid_section_block(bm_face_upper, 11660.0, 11672.0, prof_upper_rock, n_steps=5)

# 2) Ring-Cut Central Core Rock Mass (링컷 중앙 코어부 존치: STA 11672 ~ 11678, supporting upper face stability)
prof_core_rock = []
for k in range(19):
    ang = math.radians(180.0 * k / 18.0)
    prof_core_rock.append((3.40 * math.cos(ang), 2.45 + 3.10 * math.sin(ang)))
build_solid_section_block(bm_face_core, 11672.0, 11678.0, prof_core_rock, n_steps=4)

# 3) Lower Bench Rock Mass (하반 벤치부 암반: STA 11660 ~ 11684, with stepped bench cut at 11684)
prof_lower_bench = [(-5.65, 0.0), (5.65, 0.0), (5.65, 2.45), (-5.65, 2.45)]
build_solid_section_block(bm_face_lower, 11660.0, 11684.0, prof_lower_bench, n_steps=6)

# 4) Unexcavated Invert Rock Mass (인버트 굴착 전 바닥 암반: STA 11660 ~ 11696)
prof_invert_rock = [(-5.40, -0.65), (5.40, -0.65), (5.65, 0.0), (-5.65, 0.0)]
build_solid_section_block(bm_face_inv, 11660.0, 11696.0, prof_invert_rock, n_steps=6)

# 5) Staged Shotcrete Shell & Steel Ribs / Rockbolts / Umbrella Pipes in STA 11660 ~ 11716
# - Upper Half Shotcrete & Upper Ribs only in STA 11672 ~ 11684 (Stage 2: Top Heading)
for s in np.arange(11672.0, 11684.1, 0.80):
    p, t, nl, up = get_frame(s)
    # Upper Half H-150 Rib (0° ~ 180° only!)
    u_pts = [p + nl * (R_RIB * math.cos(math.radians(d))) + up * (2.45 + R_RIB * math.sin(math.radians(d))) for d in np.linspace(0.0, 180.0, 19)]
    add_tube(bm_hbeam_ribs, u_pts, radius=0.075, n_seg=4)
    # Upper Half Footplates at Springline (v=2.45m) + Upper Foot Piles (상반 각부 보강그라우팅)
    for sgn in [-1.0, 1.0]:
        pt_sl = p + nl * (sgn * R_RIB) + up * 2.45
        add_oriented_box(bm_plates, pt_sl, t, nl, up, 0.24, 0.24, 0.04)
        f_dir = (sgn * math.cos(math.radians(35.0)) * nl - math.sin(math.radians(35.0)) * up).normalized()
        add_tube(bm_footpiles, [pt_sl, pt_sl + f_dir * 4.50], radius=0.035, n_seg=5)
    # Upper Half Radial Rockbolts (15° ~ 165°)
    for deg_b in np.linspace(15.0, 165.0, 11):
        rad = math.radians(deg_b)
        r_dir = (math.cos(rad) * nl + math.sin(rad) * up).normalized()
        t_arc = (-math.sin(rad) * nl + math.cos(rad) * up).normalized()
        p_h = p + nl * ((R_RIB - 0.08) * math.cos(rad)) + up * (2.45 + (R_RIB - 0.08) * math.sin(rad))
        add_tube(bm_rockbolts, [p_h - r_dir * 0.08, p_h + r_dir * 4.0], radius=0.024, n_seg=4)
        add_oriented_box(bm_plates, p_h, t, t_arc, r_dir, 0.18, 0.18, 0.03)

# Upper Half Shotcrete Arch Shell (STA 11672 ~ 11684, 0° ~ 180°)
prof_shot_upper = []
for k in range(21):
    ang = math.radians(180.0 * k / 20.0)
    prof_shot_upper.append((5.78 * math.cos(ang), 2.45 + 5.78 * math.sin(ang)))
for k in range(20, -1, -1):
    ang = math.radians(180.0 * k / 20.0)
    prof_shot_upper.append((5.55 * math.cos(ang), 2.45 + 5.55 * math.sin(ang)))
build_solid_section_block(bm_stage_shot, 11672.0, 11684.0, prof_shot_upper, n_steps=5)

# - Full Horseshoe Shotcrete & Full Ribs + Lower Bench Rockbolts in STA 11684 ~ 11716 (Stages 3, 4, 5)
for s in np.arange(11684.8, 11716.0, 0.80):
    p, t, nl, up = get_frame(s)
    f_pts = [p + nl * (R_RIB * math.cos(math.radians(d))) + up * max(-0.42, 2.45 + R_RIB * math.sin(math.radians(d))) for d in arch_degs]
    add_tube(bm_hbeam_ribs, f_pts, radius=0.075, n_seg=4)
    # Invert Strut Rib (인버트 폐합 강지보 H-150) in Stage 4 & 5 (STA 11696 ~ 11716)
    if s >= 11696.0:
        inv_rib_pts = [p + nl * u + up * (-0.42 - 0.18 * (1.0 - (u / 4.90)**2)) for u in np.linspace(-4.90, 4.90, 11)]
        add_tube(bm_hbeam_ribs, inv_rib_pts, radius=0.070, n_seg=4)
    for deg_b in np.linspace(-15.0, 195.0, 15):
        rad = math.radians(deg_b)
        r_dir = (math.cos(rad) * nl + math.sin(rad) * up).normalized()
        t_arc = (-math.sin(rad) * nl + math.cos(rad) * up).normalized()
        p_h = p + nl * ((R_RIB - 0.08) * math.cos(rad)) + up * (2.45 + (R_RIB - 0.08) * math.sin(rad))
        add_tube(bm_rockbolts, [p_h - r_dir * 0.08, p_h + r_dir * 4.0], radius=0.024, n_seg=4)
        add_oriented_box(bm_plates, p_h, t, t_arc, r_dir, 0.18, 0.18, 0.03)
    for sgn in [-1.0, 1.0]:
        for v_foot in [2.45, 0.20]:
            pt_f = p + nl * (sgn * 5.62) + up * v_foot
            f_dir = (sgn * math.cos(math.radians(35.0)) * nl - math.sin(math.radians(35.0)) * up).normalized()
            add_tube(bm_footpiles, [pt_f, pt_f + f_dir * 4.50], radius=0.035, n_seg=5)

prof_shot_full = []
for k in range(29):
    ang = math.radians(-28.0 + 236.0 * k / 28.0)
    prof_shot_full.append((5.78 * math.cos(ang), max(-0.55, 2.45 + 5.78 * math.sin(ang))))
for k in range(28, -1, -1):
    ang = math.radians(-28.0 + 236.0 * k / 28.0)
    prof_shot_full.append((5.55 * math.cos(ang), max(-0.42, 2.45 + 5.55 * math.sin(ang))))
build_solid_section_block(bm_stage_shot, 11684.0, 11716.0, prof_shot_full, n_steps=8)

# Umbrella Arch Grouting Canopy (대구경 강관다단그라우팅 L=12.0m, θ=180°, @500mm) across Staged Excavation Showcase (STA 11660 ~ 11716)
for s_u in np.arange(11660.0, 11715.0, 5.60):
    p_u0, _, nl_u0, up_u0 = get_frame(s_u)
    p_u1, _, nl_u1, up_u1 = get_frame(s_u + 12.0)
    for deg_u in np.linspace(0.0, 180.0, 35):
        rad = math.radians(deg_u)
        pt0 = p_u0 + nl_u0 * (5.72 * math.cos(rad)) + up_u0 * (2.45 + 5.72 * math.sin(rad))
        pt1 = p_u1 + nl_u1 * (6.52 * math.cos(rad)) + up_u1 * (2.45 + 6.52 * math.sin(rad))
        add_tube(bm_umbrella, [pt0, pt1], radius=0.042, n_seg=6)

# Also add Forepoling / Face Bolts (막장 수평 록볼트 / 페이스볼트 L=12m) into the Upper Half Face at STA 11672 -> 11660
p_f0, _, nl_f0, up_f0 = get_frame(11660.0)
p_f1, _, nl_f1, up_f1 = get_frame(11672.0)
for u_fb in [-3.5, -2.1, -0.7, 0.7, 2.1, 3.5]:
    for v_fb in [3.2, 4.5, 5.8]:
        if u_fb*u_fb + (v_fb - 2.45)**2 < 4.8**2:
            add_tube(bm_footpiles, [p_f0 + nl_f0 * u_fb + up_f0 * v_fb, p_f1 + nl_f1 * u_fb + up_f1 * v_fb], radius=0.032, n_seg=5)

# Trim the existing West Concrete Lining, Shotcrete, and Invert objects in col_14 so STA 11660 ~ 11706 reveals the Staged Excavation!
# Let's check vertices of NATM_본선터널_시점부_콘크리트라이닝_11K660_11K935 and shift any vertex with s < 11706 to 11706!
p_cut_lin, t_cut_lin, nl_cut_lin, up_cut_lin = get_frame(11706.0)
for oname, cut_sta in [
    ("NATM_본선터널_시점부_콘크리트라이닝_11K660_11K935", 11706.0),
    ("NATM_본선터널_시점부_숏크리트방수층_11K660_11K935", 11706.0),
    ("NATM_본선터널_시점부_인버트및공동구_11K660_11K935", 11698.0),
]:
    o_w = bpy.data.objects.get(oname)
    if o_w and o_w.type == 'MESH':
        p_c, t_c, nl_c, up_c = get_frame(cut_sta)
        for v in o_w.data.vertices:
            # Project vertex onto alignment station near west end
            d_vec = v.co - p_c
            along = d_vec.dot(t_c)
            if along < 0.0:
                v.co = v.co - t_c * along
        o_w.data.update()

# Build 3D Text Labels for the 5 Staged Excavation Zones at STA 11660 ~ 11716
def add_stage_label(name, text_str, sta, z_off=9.8):
    p_l, t_l, nl_l, up_l = get_frame(sta)
    curve_data = bpy.data.curves.new(name=name + "_Curve", type='FONT')
    curve_data.body = text_str
    curve_data.size = 1.65
    curve_data.extrude = 0.12
    curve_data.align_x = 'CENTER'
    curve_data.align_y = 'BOTTOM'
    for fp in [r"C:\Windows\Fonts\malgunbd.ttf", r"C:\Windows\Fonts\malgun.ttf"]:
        try:
            curve_data.font = bpy.data.fonts.load(fp, check_existing=True)
            break
        except:
            pass
    obj = bpy.data.objects.new(name, curve_data)
    obj.location = p_l + up_l * z_off
    rz = math.atan2(t_l.y, t_l.x)
    obj.rotation_euler = (math.radians(65.0), 0.0, rz)
    obj.data.materials.append(mat_lattice_rib)
    col_21.objects.link(obj)

add_stage_label("NATM_STAGE_LBL_1", "[1단계: 막장 전방보강]\n대구경 강관다단그라우팅(L=12m, θ=180°, @500)\n+ 막장 수평보강공(Face Bolt) + TSP 전방탐사", 11666.0, 9.5)
add_stage_label("NATM_STAGE_LBL_2", "[2단계: 상반 분할굴착 및 링컷 코어 존치]\n상반 굴착(굴진장 0.8~1.2m) + 1차 숏크리트(SFRS)\n+ 상반 강지보(H-150) + 상반 록볼트(L=4m) + 상반 각부보강공", 11678.0, 9.5)
add_stage_label("NATM_STAGE_LBL_3", "[3단계: 하반 벤치굴착 및 측벽 지보]\n하반 굴착 + 하반 강지보 레그 연장결속\n+ 2차 숏크리트(t=200~250mm) + 측벽 록볼트 + 하반 각부보강공", 11690.0, 9.5)
add_stage_label("NATM_STAGE_LBL_4", "[4단계: 인버트 굴착 및 폐합]\n바닥 인버트 굴착(H=300~500mm) + 인버트 폐합 강지보\n+ 버림·채움콘크리트 + 부직포/방수쉬트 및 유공관 매설", 11701.0, 9.5)
add_stage_label("NATM_STAGE_LBL_5", "[5단계: 라이닝 철근조립 및 콘크리트 타설]\n내·외측 복배근(TUN_REB_01~06) 조립\n+ 본선 콘크리트 라이닝(t=400mm) 및 양측 공동구 타설", 11712.0, 9.5)

# Finalize all objects in Collection 21
build_obj(bm_hbeam_ribs,   "NATM_SUP_01A_강지보재_H150x150_및_H125x125_PD6구간_800간격_1권지보도", mat_hbeam_rib,   col_21)
build_obj(bm_lattice_ribs, "NATM_SUP_01B_격자지보재_LG70_LG50_및_연결타이로드_PD4_PD5구간_1권지보도", mat_lattice_rib, col_21)
build_obj(bm_rockbolts,    "NATM_SUP_02_시스템록볼트_SD400_D25_L4000_방사형정착_전구간_1권지보도",    mat_rockbolt,    col_21)
build_obj(bm_plates,       "NATM_SUP_02A_록볼트지압판_150x150x10_및_강지보이음베이스플레이트",        mat_plate_nut,   col_21)
build_obj(bm_umbrella,     "NATM_SUP_03_대구경강관다단그라우팅_L12m_θ180도_및_훠폴링_우산형보강망",   mat_umbrella,    col_21)
build_obj(bm_footpiles,    "NATM_SUP_03A_상하반_각부보강그라우팅_L4.5m_및_막장페이스볼트",            mat_footpile,    col_21)
build_obj(bm_stage_shot,   "NATM_SUP_04_단계별굴착구간_1차_2차_강섬유보강숏크리트_SFRS_t250mm",       mat_shot_stage,  col_21)
build_obj(bm_face_upper,   "NATM_EXC_01_단계별굴착_1단계_상반굴착전_원지반암반_및_상반막장면",        mat_exc_upper,   col_21)
build_obj(bm_face_core,    "NATM_EXC_02_단계별굴착_2단계_상반링컷_중앙코어부_Core_존치암반",          mat_exc_core,    col_21)
build_obj(bm_face_lower,   "NATM_EXC_03_단계별굴착_3단계_하반벤치컷_BenchCut_굴착막장면",             mat_exc_lower,   col_21)
build_obj(bm_face_inv,     "NATM_EXC_04_단계별굴착_4단계_바닥인버트_Invert_굴착단면",                 mat_exc_invert,  col_21)

bpy.ops.wm.save_mainfile()
print("SUCCESS: Built NATM Support & Staged Excavation Collection 21 with", len(col_21.objects), "objects!")
