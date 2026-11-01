import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector

# ==============================================================================
# 0. ENSURE COMPLETE DRAINAGE & UTILITY DUCT BIM IS PRESENT (INCLUDING SEC 8 & 9)
# ==============================================================================
drain_script_path = r"C:\Users\20040178\.gemini\antigravity-cli\brain\770731a9-ce60-48bb-9690-7a68027016c5\scratch\build_drainage_bim.py"
exec(open(drain_script_path, encoding="utf-8").read())

# ==============================================================================
# 1. REBAR MATERIALS & COLLECTION SETUP
# ==============================================================================
def get_or_create_rebar_mat(name, rgba, metallic=0.78, roughness=0.26):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = rgba
    return mat

mat_h29_gold   = get_or_create_rebar_mat("MAT_REBAR_D29_Girder_Gold",  (0.96, 0.72, 0.12, 1.0))
mat_h25_cyan   = get_or_create_rebar_mat("MAT_REBAR_D25_Slab_Cyan",    (0.08, 0.78, 0.92, 1.0))
mat_h22_green  = get_or_create_rebar_mat("MAT_REBAR_D22_Wall_Green",   (0.18, 0.85, 0.36, 1.0))
mat_h19_blue   = get_or_create_rebar_mat("MAT_REBAR_D19_Dist_Blue",    (0.22, 0.48, 0.96, 1.0))
mat_h16_orange = get_or_create_rebar_mat("MAT_REBAR_H16_Invert_Orange",(0.96, 0.46, 0.12, 1.0))
mat_h13_mag    = get_or_create_rebar_mat("MAT_REBAR_D16_Stirrup_Mag",  (0.92, 0.22, 0.68, 1.0))
mat_h13_lime   = get_or_create_rebar_mat("MAT_REBAR_H13_Duct_Lime",    (0.65, 0.92, 0.15, 1.0))
mat_h32_red    = get_or_create_rebar_mat("MAT_REBAR_D32_Main_Red",     (0.95, 0.20, 0.18, 1.0))

# Also make tunnel lining & utility bench slightly translucent in viewport so internal rebar is visible
for mname, alpha_v in [
    ("MAT_NATM_Concrete_Lining", 0.32),
    ("MAT_NATM_Shotcrete_Outer", 0.22),
    ("MAT_NATM_Invert_Walkway",  0.38),
    ("MAT_DRAIN_Utility_RC",     0.35),
    ("MAT_S007_ConnTunnel_PA2",  0.32),
    ("MAT_S007_Shaft_TempZone",  0.32),
    ("MAT_S007_Shaft_RockZone",  0.32),
]:
    m = bpy.data.materials.get(mname)
    if m:
        m.diffuse_color = (m.diffuse_color[0], m.diffuse_color[1], m.diffuse_color[2], alpha_v)
        if m.use_nodes and m.node_tree.nodes.get("Principled BSDF"):
            bsdf = m.node_tree.nodes["Principled BSDF"]
            if "Alpha" in bsdf.inputs:
                bsdf.inputs["Alpha"].default_value = alpha_v

col_18 = bpy.data.collections.get("18_본선터널_및_기재갱_철근배근_LOD400")
if not col_18:
    col_18 = bpy.data.collections.new("18_본선터널_및_기재갱_철근배근_LOD400")
    bpy.context.scene.collection.children.link(col_18)
else:
    for obj in list(col_18.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

col_19 = bpy.data.collections.get("19_S007환기구_수직구_연결터널_상부박스_철근배근_LOD400")
if not col_19:
    col_19 = bpy.data.collections.new("19_S007환기구_수직구_연결터널_상부박스_철근배근_LOD400")
    bpy.context.scene.collection.children.link(col_19)
else:
    for obj in list(col_19.objects):
        if obj.name.startswith("S007_REB_"):
            bpy.data.objects.remove(obj, do_unlink=True)

# ==============================================================================
# 2. FAST SOLID REBAR TUBE GENERATOR
# ==============================================================================
def add_rebar_poly(bm, pts, radius=0.016, n_seg=4, closed=False):
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
    if not closed and len(rings) >= 2:
        try:
            bm.faces.new(rings[0][::-1])
            bm.faces.new(rings[-1])
        except:
            pass

def build_rebar_obj(bm, name, mat, col):
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj

# ==============================================================================
# 3. MAINLINE NATM TUNNEL DETAILED REBAR (04.구조물 설계도 1권 & 2권)
# ==============================================================================
# Cross-section geometry matching NATM_본선터널_콘크리트라이닝 & 인버트및공동구:
# Lining arch center: z_center = 2.45m, r_in = 5.15m, r_out = 5.55m, ang = -28° ~ +208°
# Inner rebar layer: r_reb_in = 5.22m
# Outer rebar layer: r_reb_out = 5.48m

bm_arch_main   = bmesh.new() # TUN_REB_01: 1~6번 주철근 (내·외측 복배근 + 겹이음)
bm_invert_reb  = bmesh.new() # TUN_REB_02: 9, 10, 11번 인버트 상·하면 주철근 및 바닥 종방향 배력근
bm_haunch_reb  = bmesh.new() # TUN_REB_03: 7, 8번 측벽 하단 우각부 헌치 경사보강근 및 기초 정착 후크
bm_long_dist   = bmesh.new() # TUN_REB_04: 내·외측 라이닝 종방향 배력철근 76열 (H13)
bm_shear_chair = bmesh.new() # TUN_REB_05: 전단보강근(A) 및 조립용 받침우마철근(T1, T2, T3) (H13)
bm_duct_rebar  = bmesh.new() # TUN_REB_06: 양측 공동구 철근배근 (C1, C2 @250mm + 종방향 배력근 40열)

tunnel_ranges = [
    (11660.0, STA_106_START), # 시점부 본선터널 (274.68m)
    (STA_106_END, 12860.0),   # 종점부 본선터널 (815.68m)
]

# Helper to check if left sidewall is open for #S-007 connecting tunnel (STA 12780.4 ~ 12788.4)
# or equipment niches #11 (11825.6), #12 (12214.8), #13 (12614.8)
def is_left_opening(sta, ang_deg, v_height):
    # #S-007 opening (u > 0 corresponds to ang in [-28°, +42°])
    if 12780.2 <= sta <= 12788.6 and ang_deg < 44.0:
        return True
    # Equipment niches #11, #12, #13 (width ±3.0m around niche STA, height v < 5.0m on left side u > 0)
    for n_sta in [11825.60, 12214.80, 12614.80]:
        if abs(sta - n_sta) <= 2.85 and ang_deg < 30.0 and v_height < 4.95:
            return True
    return False

n_arc_reb = 32
arch_degs = np.linspace(-27.0, 207.0, n_arc_reb + 1)

for sta_start, sta_end in tunnel_ranges:
    # Step at 1.25m for visual clarity (representing C.T.C 250mm bundle / every 5th bar in full 1.1km tunnel,
    # with dense 0.35m spacing near portals, niches, and #S-007!)
    stas_ring = []
    s_cur = sta_start
    while s_cur <= sta_end + 0.01:
        stas_ring.append(min(s_cur, sta_end))
        # Dense spacing near station portals, niches, and S-007
        near_special = (
            abs(s_cur - sta_start) < 8.0 or
            abs(s_cur - sta_end) < 8.0 or
            abs(s_cur - 11825.60) < 6.0 or
            abs(s_cur - 12214.80) < 6.0 or
            abs(s_cur - 12614.80) < 6.0 or
            abs(s_cur - 12784.40) < 12.0
        )
        s_cur += 0.45 if near_special else 1.20

    for idx_s, s in enumerate(stas_ring):
        p, t, n_left, up_v = get_frame(s)

        # ------------------------------------------------------------------
        # (A) TUN_REB_01: 내·외측 아치 주철근 (1~6번 철근, 복배근) + 겹이음(Lap Splice)
        # ------------------------------------------------------------------
        for r_layer in [5.22, 5.48]:
            seg_pts = []
            for deg in arch_degs:
                rad = math.radians(deg)
                u = r_layer * math.cos(rad)
                v = 2.45 + r_layer * math.sin(rad)
                if is_left_opening(s, deg, v):
                    if len(seg_pts) >= 2:
                        add_rebar_poly(bm_arch_main, seg_pts, radius=0.018, n_seg=4)
                    seg_pts = []
                else:
                    seg_pts.append(p + n_left * u + up_v * v)
            if len(seg_pts) >= 2:
                add_rebar_poly(bm_arch_main, seg_pts, radius=0.018, n_seg=4)

        # Lap splice bars (겹이음부 L=800mm) at 35°, 90°(천단), 145° every 2nd ring
        if idx_s % 2 == 0:
            for deg_lap in [35.0, 90.0, 145.0]:
                for r_layer in [5.22, 5.48]:
                    lap_pts = []
                    for d_sub in np.linspace(deg_lap - 6.5, deg_lap + 6.5, 5):
                        rad = math.radians(d_sub)
                        u = (r_layer + 0.022) * math.cos(rad)
                        v = 2.45 + (r_layer + 0.022) * math.sin(rad)
                        if not is_left_opening(s, d_sub, v):
                            lap_pts.append(p + n_left * u + up_v * v + t * 0.02)
                    if len(lap_pts) >= 2:
                        add_rebar_poly(bm_arch_main, lap_pts, radius=0.016, n_seg=4)

        # ------------------------------------------------------------------
        # (B) TUN_REB_02: 인버트(바닥부) 상·하면 주철근 (9, 10, 11번 H19/H22)
        # ------------------------------------------------------------------
        # Bottom invert main bar (9, 10번): spans u = -4.75 ~ +4.75 at v = -0.38m (curving up to -0.10m at ends)
        inv_bot_uv = [
            (-4.85, 0.05), (-4.55, -0.36), (-2.20, -0.38), (-0.45, -0.38),
            (0.45, -0.38), (2.20, -0.38), (4.55, -0.36), (4.85, 0.05)
        ]
        add_rebar_poly(bm_invert_reb, [p + n_left * u + up_v * v for u, v in inv_bot_uv], radius=0.017, n_seg=4)

        # Top invert main bar (11번): spans u = -4.65 ~ +4.65 at v = +0.18m with central drainage drop at u in [-0.38, +0.38]
        inv_top_uv = [
            (-4.65, 0.18), (-3.80, 0.18), (-0.42, 0.18), (-0.36, -0.20),
            (0.36, -0.20), (0.42, 0.18), (3.80, 0.18), (4.65, 0.18)
        ]
        add_rebar_poly(bm_invert_reb, [p + n_left * u + up_v * v for u, v in inv_top_uv], radius=0.017, n_seg=4)

        # Invert shear ties connecting top and bottom invert layers across width
        for u_tie in [-4.20, -3.20, -2.20, -1.20, -0.45, 0.45, 1.20, 2.20, 3.20, 4.20]:
            tie_uv = [(u_tie - 0.06, -0.36), (u_tie, -0.38), (u_tie, 0.18), (u_tie + 0.06, 0.16)]
            add_rebar_poly(bm_invert_reb, [p + n_left * u + up_v * v for u, v in tie_uv], radius=0.012, n_seg=4)

        # ------------------------------------------------------------------
        # (C) TUN_REB_03: 측벽 하단 우각부 헌치 경사보강근 및 기초 정착 후크 (7, 8번 H22)
        # ------------------------------------------------------------------
        for sgn in [-1.0, 1.0]:
            if sgn > 0 and is_left_opening(s, -15.0, 0.5):
                continue
            # 7번 외측 기초 정착 보강근 (L-shaped + 15° haunch hook into invert bottom)
            bar7_uv = [
                (sgn * 5.45, 1.85),
                (sgn * 5.20, 0.65),
                (sgn * 4.82, -0.12),
                (sgn * 4.52, -0.37),
                (sgn * 3.65, -0.37),
                (sgn * 3.65, -0.22), # 90° upward anchorage hook (b=150mm)
            ]
            add_rebar_poly(bm_haunch_reb, [p + n_left * u + up_v * v for u, v in bar7_uv], radius=0.018, n_seg=4)

            # 8번 내측 우각부 경사 헌치 보강근 (Diagonal haunch bar across sidewall-invert corner)
            bar8_uv = [
                (sgn * 5.14, 1.65),
                (sgn * 4.92, 0.72),
                (sgn * 4.15, 0.18),
                (sgn * 3.35, -0.34),
                (sgn * 2.75, -0.34),
            ]
            add_rebar_poly(bm_haunch_reb, [p + n_left * u + up_v * v for u, v in bar8_uv], radius=0.018, n_seg=4)

        # ------------------------------------------------------------------
        # (D) TUN_REB_05: 전단보강근(A) 및 조립용 받침우마철근(T1, T2, T3 H13)
        # ------------------------------------------------------------------
        # Placed around the arch every 7.5° (32 positions per ring)
        for k_ang, deg in enumerate(arch_degs):
            rad = math.radians(deg)
            v_mid = 2.45 + 5.35 * math.sin(rad)
            if is_left_opening(s, deg, v_mid):
                continue
            u_in,  v_in  = 5.21 * math.cos(rad), 2.45 + 5.21 * math.sin(rad)
            u_out, v_out = 5.49 * math.cos(rad), 2.45 + 5.49 * math.sin(rad)
            p_in  = p + n_left * u_in  + up_v * v_in
            p_out = p + n_left * u_out + up_v * v_out
            # Tangent vector along arch
            t_arc = (-math.sin(rad) * n_left + math.cos(rad) * up_v).normalized()

            if k_ang % 2 == 0:
                # 전단보강근 A (Cross-tie stirrup clamping inner & outer main bars with hooks)
                pts_A = [
                    p_in - t_arc * 0.05 + t * 0.04,
                    p_in,
                    p_out,
                    p_out + t_arc * 0.05 - t * 0.04
                ]
                add_rebar_poly(bm_shear_chair, pts_A, radius=0.011, n_seg=4)
            else:
                # 받침철근 T1/T2/T3 (Z/U-shaped spacer chair supporting outer & inner rebar layers: a=288, b=300, c=100)
                pts_T = [
                    p_in  - t * 0.14 - t_arc * 0.08,
                    p_in  - t * 0.14,
                    p_out,
                    p_out + t * 0.14,
                    p_out + t * 0.14 + t_arc * 0.08
                ]
                add_rebar_poly(bm_shear_chair, pts_T, radius=0.012, n_seg=4)

        # ------------------------------------------------------------------
        # (E) TUN_REB_06: 양측 공동구 철근배근 (2권 공동구 철근배근도 C6063164-001: C1, C2 @250mm)
        # ------------------------------------------------------------------
        # Left & Right utility bench (`공동구`) profile:
        # Bench occupies |u| = 3.78 ~ 5.02m, v = 0.00 ~ 1.02m, with upper 400x200 trough at |u| = 4.42 ~ 4.88m, v = 0.82 ~ 1.02m
        for sgn in [-1.0, 1.0]:
            if sgn > 0 and is_left_opening(s, -15.0, 0.5):
                continue
            # C2 철근 (H13, L=1,037mm, a=1,000, b=37): Outer/inner bench structural stirrup
            c2_uv = [
                (sgn * 3.82, -0.12), # anchored into invert slab
                (sgn * 3.82, 0.96),  # inner walkway vertical face
                (sgn * 4.38, 0.96),  # walkway top face
                (sgn * 4.38, 0.76),  # trough inner wall
                (sgn * 4.92, 0.76),  # trough bottom slab
                (sgn * 4.92, 0.02),  # outer vertical leg near lining sidewall
                (sgn * 4.20, 0.02),  # bottom horizontal tie
            ]
            add_rebar_poly(bm_duct_rebar, [p + n_left * u + up_v * v for u, v in c2_uv], radius=0.013, n_seg=4)

            # C1 철근 (H13, L=850mm, a=550, b=300): Upper 400x200 cable trough U-bar & cantilever wall bar
            c1_uv = [
                (sgn * 4.12, 0.92),
                (sgn * 4.40, 0.92),
                (sgn * 4.40, 0.78),
                (sgn * 4.88, 0.78),
                (sgn * 4.88, 0.98),
                (sgn * 4.98, 0.98),
                (sgn * 4.98, 0.65),
            ]
            add_rebar_poly(bm_duct_rebar, [p + n_left * u + up_v * v for u, v in c1_uv], radius=0.013, n_seg=4)

    # ----------------------------------------------------------------------
    # Continuous Longitudinal Rebar Sweeps along Tunnel Alignment
    # ----------------------------------------------------------------------
    stas_long = np.linspace(sta_start, sta_end, int((sta_end - sta_start) / 3.0) + 2)

    # 1) TUN_REB_04: 내·외측 아치 종방향 배력철근 (38 angles × 2 layers = 76 rows, H13)
    long_degs = np.linspace(-26.0, 206.0, 38)
    for r_layer in [5.24, 5.46]:
        for deg in long_degs:
            rad = math.radians(deg)
            u = r_layer * math.cos(rad)
            v = 2.45 + r_layer * math.sin(rad)
            seg_pts = []
            for s in stas_long:
                if is_left_opening(s, deg, v):
                    if len(seg_pts) >= 2:
                        add_rebar_poly(bm_long_dist, seg_pts, radius=0.012, n_seg=4)
                    seg_pts = []
                else:
                    p_s, _, nl_s, up_s = get_frame(s)
                    seg_pts.append(p_s + nl_s * u + up_s * v)
            if len(seg_pts) >= 2:
                add_rebar_poly(bm_long_dist, seg_pts, radius=0.012, n_seg=4)

    # 2) TUN_REB_02: 인버트(바닥부) 상·하면 종방향 배력철근 (34 rows across tunnel floor, H13)
    inv_u_rows = [-4.60, -4.20, -3.80, -3.40, -3.00, -2.60, -2.20, -1.80, -1.40, -1.00, -0.60,
                   0.60,  1.00,  1.40,  1.80,  2.20,  2.60,  3.00,  3.40,  3.80,  4.20,  4.60]
    for u_val in inv_u_rows:
        for v_val in [-0.36, +0.16]:
            pts_l = []
            for s in stas_long:
                p_s, _, nl_s, up_s = get_frame(s)
                pts_l.append(p_s + nl_s * u_val + up_s * v_val)
            add_rebar_poly(bm_invert_reb, pts_l, radius=0.012, n_seg=4)

    # 3) TUN_REB_06: 양측 공동구 종방향 배력철근 (좌·우 각 20열 = 총 40열, H13, 2권 C6063164-001)
    duct_uv_rows = [
        (3.84, 0.15), (3.84, 0.38), (3.84, 0.62), (3.84, 0.84), (3.84, 0.94),
        (4.02, 0.94), (4.20, 0.94), (4.38, 0.94), (4.38, 0.80),
        (4.52, 0.78), (4.68, 0.78), (4.84, 0.78),
        (4.88, 0.88), (4.88, 0.96), (4.96, 0.96),
        (4.92, 0.60), (4.92, 0.35), (4.92, 0.10),
        (4.40, 0.04), (4.10, 0.04)
    ]
    for sgn in [-1.0, 1.0]:
        for (u_d, v_d) in duct_uv_rows:
            seg_pts = []
            for s in stas_long:
                if sgn > 0 and is_left_opening(s, -15.0, 0.5):
                    if len(seg_pts) >= 2:
                        add_rebar_poly(bm_duct_rebar, seg_pts, radius=0.011, n_seg=4)
                    seg_pts = []
                else:
                    p_s, _, nl_s, up_s = get_frame(s)
                    seg_pts.append(p_s + nl_s * (sgn * u_d) + up_s * v_d)
            if len(seg_pts) >= 2:
                add_rebar_poly(bm_duct_rebar, seg_pts, radius=0.011, n_seg=4)

# ==============================================================================
# 4. 통합기재갱 (#11, #12, #13) 라이닝 복배근, 마감벽 격자배근(C1~C4) 및 개구부 보강 (1권 Stream 1283)
# ==============================================================================
bm_niche_reb = bmesh.new() # TUN_REB_07

for cp_sta, cp_label in [
    (11825.60, "11호"),
    (12214.80, "12호"),
    (12614.80, "13호"),
]:
    pos_cp, tang_cp, nl_cp, up_cp = get_frame(cp_sta)
    th_cp = Vector((tang_cp.x, tang_cp.y, 0.0)).normalized()

    # 1) Horseshoe arch + invert double-layer rings along niche depth d = 4.95m ~ 9.50m (@300mm)
    d_rings = np.linspace(4.95, 9.45, 16)
    for d_off in d_rings:
        c_pt = pos_cp + nl_cp * d_off
        # Outer & Inner horseshoe arch + invert closed ring
        for inset in [0.06, 0.24]:
            w_half = 2.40 - inset
            h_top  = 4.25 - inset
            h_bot  = 0.02 + inset * 0.5
            ring_pts = [
                c_pt - th_cp * w_half + up_cp * h_bot,
                c_pt + th_cp * w_half + up_cp * h_bot,
                c_pt + th_cp * w_half + up_cp * 2.20,
            ]
            for k_a in range(1, 12):
                ang = math.radians(180.0 * k_a / 12.0)
                ring_pts.append(c_pt + th_cp * (w_half * math.cos(ang)) + up_cp * (2.20 + (h_top - 2.20) * math.sin(ang)))
            ring_pts.append(c_pt - th_cp * w_half + up_cp * 2.20)
            add_rebar_poly(bm_niche_reb, ring_pts, radius=0.016, n_seg=4, closed=True)

        # Radial stirrups & spacer chairs along niche ring
        for k_s in range(0, 13, 2):
            ang = math.radians(180.0 * k_s / 12.0)
            p1 = c_pt + th_cp * (2.34 * math.cos(ang)) + up_cp * (2.20 + 1.99 * math.sin(ang))
            p2 = c_pt + th_cp * (2.16 * math.cos(ang)) + up_cp * (2.20 + 1.81 * math.sin(ang))
            add_rebar_poly(bm_niche_reb, [p1, p2], radius=0.011, n_seg=4)

    # 2) Longitudinal distribution bars along niche depth (d = 4.90m ~ 9.48m)
    for inset in [0.08, 0.22]:
        w_half = 2.40 - inset
        h_top  = 4.25 - inset
        # Sidewalls & Floor longitudinal bars
        for w_f in np.linspace(-w_half, w_half, 11):
            p_a = pos_cp + nl_cp * 4.90 + th_cp * w_f + up_cp * (0.04 + inset * 0.5)
            p_b = pos_cp + nl_cp * 9.48 + th_cp * w_f + up_cp * (0.04 + inset * 0.5)
            add_rebar_poly(bm_niche_reb, [p_a, p_b], radius=0.012, n_seg=4)
        for sgn_w in [-1.0, 1.0]:
            for h_w in np.linspace(0.35, 2.15, 7):
                p_a = pos_cp + nl_cp * 4.90 + th_cp * (sgn_w * w_half) + up_cp * h_w
                p_b = pos_cp + nl_cp * 9.48 + th_cp * (sgn_w * w_half) + up_cp * h_w
                add_rebar_poly(bm_niche_reb, [p_a, p_b], radius=0.012, n_seg=4)
        # Arch longitudinal bars
        for k_a in range(1, 12):
            ang = math.radians(180.0 * k_a / 12.0)
            u_w = w_half * math.cos(ang)
            v_h = 2.20 + (h_top - 2.20) * math.sin(ang)
            p_a = pos_cp + nl_cp * 4.90 + th_cp * u_w + up_cp * v_h
            p_b = pos_cp + nl_cp * 9.48 + th_cp * u_w + up_cp * v_h
            add_rebar_poly(bm_niche_reb, [p_a, p_b], radius=0.012, n_seg=4)

    # 3) 마감벽 (Back End Wall at d = 9.25m ~ 9.48m) 수직·수평 복배근 격자 (C1~C4 H16 @250mm + T4 H13 전단타이)
    for d_wall in [9.28, 9.44]:
        c_w = pos_cp + nl_cp * d_wall
        # Vertical bars C1, C2 (@250mm)
        for w_x in np.linspace(-2.25, 2.25, 19):
            ratio = min(1.0, abs(w_x) / 2.30)
            h_max = 2.20 + 1.95 * math.sqrt(max(0.0, 1.0 - ratio * ratio))
            p_bot = c_w + th_cp * w_x + up_cp * 0.05
            p_top = c_w + th_cp * w_x + up_cp * h_max
            add_rebar_poly(bm_niche_reb, [p_bot - nl_cp * 0.25, p_bot, p_top, p_top - nl_cp * 0.25], radius=0.014, n_seg=4)
        # Horizontal bars C3, C4 (@250mm) with U-hooks into niche sidewalls
        for h_y in np.linspace(0.20, 3.95, 16):
            if h_y <= 2.20:
                w_span = 2.28
            else:
                dy = (h_y - 2.20) / 1.95
                w_span = 2.28 * math.sqrt(max(0.0, 1.0 - dy * dy))
            if w_span > 0.30:
                p_L = c_w - th_cp * w_span + up_cp * h_y
                p_R = c_w + th_cp * w_span + up_cp * h_y
                add_rebar_poly(bm_niche_reb, [p_L - nl_cp * 0.30, p_L, p_R, p_R - nl_cp * 0.30], radius=0.014, n_seg=4)

    # 4) 본선 접속부 개구부 집중 보강 칼라 (Portal Collar Cage around niche entrance d = 4.65m ~ 5.15m)
    for d_col in [4.72, 4.88, 5.04]:
        c_col = pos_cp + nl_cp * d_col
        for inset_c in [-0.15, 0.0, 0.15]:
            w_c = 2.55 + inset_c
            h_c = 4.45 + inset_c
            pts_c = [
                c_col - th_cp * w_c + up_cp * (-0.15),
                c_col + th_cp * w_c + up_cp * (-0.15),
                c_col + th_cp * w_c + up_cp * 2.30,
            ]
            for k_a in range(1, 12):
                ang = math.radians(180.0 * k_a / 12.0)
                pts_c.append(c_col + th_cp * (w_c * math.cos(ang)) + up_cp * (2.30 + (h_c - 2.30) * math.sin(ang)))
            pts_c.append(c_col - th_cp * w_c + up_cp * 2.30)
            add_rebar_poly(bm_niche_reb, pts_c, radius=0.020, n_seg=4, closed=True)

# ==============================================================================
# 5. 정거장 시·종점 터널 갱문 칼라부 집중 보강철근 (2권 Stream 19: H29 주철근 + S1/S3 스터럽)
# ==============================================================================
bm_portal_reb = bmesh.new() # TUN_REB_08

for portal_sta, dir_sign in [(STA_106_START, -1.0), (STA_106_END, +1.0)]:
    # 8 rings of heavy H29 triple-layer hoop rebar + closed stirrups S1(H22)/S3(H19) within 3.2m of portal
    for d_s in np.linspace(0.15, 3.20, 9):
        s_val = portal_sta + dir_sign * d_s
        p, t, n_left, up_v = get_frame(s_val)
        for r_layer in [5.18, 5.38, 5.58]:
            pts_p = []
            for deg in np.linspace(-28.0, 208.0, 36):
                rad = math.radians(deg)
                pts_p.append(p + n_left * (r_layer * math.cos(rad)) + up_v * (2.45 + r_layer * math.sin(rad)))
            add_rebar_poly(bm_portal_reb, pts_p, radius=0.022, n_seg=4)

        # Closed portal collar stirrups (S1 H22 / S3 H19) wrapping all 3 layers every 6°
        for deg in np.linspace(-26.0, 206.0, 38):
            rad = math.radians(deg)
            p_in  = p + n_left * (5.16 * math.cos(rad)) + up_v * (2.45 + 5.16 * math.sin(rad))
            p_out = p + n_left * (5.60 * math.cos(rad)) + up_v * (2.45 + 5.60 * math.sin(rad))
            pts_st = [
                p_in  - t * 0.12,
                p_out - t * 0.12,
                p_out + t * 0.12,
                p_in  + t * 0.12,
            ]
            add_rebar_poly(bm_portal_reb, pts_st, radius=0.015, n_seg=4, closed=True)

    # Longitudinal portal dowel bars anchoring into 106 Station end wall (L=3.6m)
    p0, t0, nl0, up0 = get_frame(portal_sta)
    for deg in np.linspace(-26.0, 206.0, 44):
        rad = math.radians(deg)
        for r_l in [5.20, 5.56]:
            pt_start = p0 - t0 * (dir_sign * 0.45) + nl0 * (r_l * math.cos(rad)) + up0 * (2.45 + r_l * math.sin(rad))
            pt_end   = p0 + t0 * (dir_sign * 3.25) + nl0 * (r_l * math.cos(rad)) + up0 * (2.45 + r_l * math.sin(rad))
            add_rebar_poly(bm_portal_reb, [pt_start, pt_end], radius=0.018, n_seg=4)

# Build the 8 distinct LOD 400 Rebar Objects in Collection 18
build_rebar_obj(bm_arch_main,   "TUN_REB_01_본선터널_콘크리트라이닝_내외측_주철근_1_6번_복배근_1권구조도",        mat_h25_cyan,   col_18)
build_rebar_obj(bm_invert_reb,  "TUN_REB_02_본선터널_인버트바닥부_상하면주철근_9_10_11번_및_종방향배력근_1권구조도", mat_h16_orange, col_18)
build_rebar_obj(bm_haunch_reb,  "TUN_REB_03_본선터널_측벽하단_우각부헌치보강철근_7_8번_기초정착후크_1권구조도",     mat_h22_green,  col_18)
build_rebar_obj(bm_long_dist,   "TUN_REB_04_본선터널_콘크리트라이닝_내외측_종방향배력근_76열_H13_1권구조도",        mat_h19_blue,   col_18)
build_rebar_obj(bm_shear_chair, "TUN_REB_05_본선터널_전단보강스터럽_A_및_조립용받침우마철근_T1_T2_T3_H13_1권구조도", mat_h13_mag,    col_18)
build_rebar_obj(bm_duct_rebar,  "TUN_REB_06_본선터널_양측공동구_철근배근_C1_C2_및_종방향배력근40열_H13_2권구조도",   mat_h13_lime,   col_18)
build_rebar_obj(bm_niche_reb,   "TUN_REB_07_통합기재갱_11_12_13호_라이닝복배근_마감벽격자배근_C1_C4_1권구조도",      mat_h29_gold,   col_18)
build_rebar_obj(bm_portal_reb,  "TUN_REB_08_정거장시종점_갱문칼라부_집중보강철근_H29주근_S1_S3스터럽_2권구조도",     mat_h32_red,    col_18)

# ==============================================================================
# 6. #S-007 환기구 연결터널(PA-2) 인버트/우각부/스터럽(SB,ST) 및 연직갱 상세배근 (2권 Streams 132~142, 314~330)
# ==============================================================================
bm_s007_detail = bmesh.new()

STA_S007 = 12784.40
p_main, t_main, n_left, up_v = get_frame(STA_S007)
t_horiz = Vector((t_main.x, t_main.y, 0.0)).normalized()
p_shaft_xy = (p_main.x + n_left.x * 16.162, p_main.y + n_left.y * 16.162)
cx, cy = p_shaft_xy

def el_to_z(el):
    return -28.0 + (el - 140.82)

Z_GL       = el_to_z(167.500)
Z_SHEARKEY = el_to_z(143.904)
Z_FL_MAIN  = el_to_z(130.696)
Z_FL_SHAFT = el_to_z(130.196)

# 1) PA-2 연결터널 (d = 4.90m ~ 12.60m, 폭 8.0m, 높이 6.5m):
# S1~S7 아치 복배근, S8/S9 바닥 인버트 복배근, 우각부 헌치 보강근(R=200, 314mm 후크), SB/ST 스터럽
d_pa2_list = np.linspace(4.95, 12.55, 22)
for d_val in d_pa2_list:
    u_slope = (d_val - 4.90) / (12.60 - 4.90)
    z_base = Z_FL_MAIN * (1.0 - u_slope) + Z_FL_SHAFT * u_slope
    c_pt = Vector((p_main.x + n_left.x * d_val, p_main.y + n_left.y * d_val, z_base))

    # Inner (r=3.66m) & Outer (r=3.94m) arch + sidewall bars (S1~S7 H19)
    for r_pa in [3.66, 3.94]:
        arch_pa = [c_pt - t_horiz * r_pa + Vector((0, 0, -0.35)), c_pt - t_horiz * r_pa + Vector((0, 0, 2.90))]
        for k in range(1, 20):
            ang = math.radians(180.0 - 180.0 * k / 20.0)
            arch_pa.append(c_pt + t_horiz * (r_pa * math.cos(ang)) + Vector((0, 0, 2.90 + r_pa * math.sin(ang))))
        arch_pa.append(c_pt + t_horiz * r_pa + Vector((0, 0, 2.90)))
        arch_pa.append(c_pt + t_horiz * r_pa + Vector((0, 0, -0.35)))
        add_rebar_poly(bm_s007_detail, arch_pa, radius=0.016, n_seg=4)

    # Bottom (S8) & Top (S9) invert floor bars across PA-2 width (-3.90m ~ +3.90m)
    for h_inv in [-0.36, -0.02]:
        p_L = c_pt - t_horiz * 3.90 + Vector((0, 0, h_inv))
        p_R = c_pt + t_horiz * 3.90 + Vector((0, 0, h_inv))
        add_rebar_poly(bm_s007_detail, [p_L + Vector((0, 0, 0.22)), p_L, p_R, p_R + Vector((0, 0, 0.22))], radius=0.016, n_seg=4)

    # Corner haunch diagonal bars (우각부 보강근 R=200, hook=314mm) at left & right bottom corners
    for sgn_w in [-1.0, 1.0]:
        pts_hc = [
            c_pt + t_horiz * (sgn_w * 3.92) + Vector((0, 0, 1.15)),
            c_pt + t_horiz * (sgn_w * 3.65) + Vector((0, 0, 0.35)),
            c_pt + t_horiz * (sgn_w * 2.85) + Vector((0, 0, -0.34)),
            c_pt + t_horiz * (sgn_w * 2.35) + Vector((0, 0, -0.34)),
        ]
        add_rebar_poly(bm_s007_detail, pts_hc, radius=0.016, n_seg=4)

    # Radial shear stirrups SB (H13 L=1.037m) & ST (H13 L=1.596m) around arch and invert
    for k in range(0, 21, 2):
        ang = math.radians(180.0 * k / 20.0)
        p_in  = c_pt + t_horiz * (3.65 * math.cos(ang)) + Vector((0, 0, 2.90 + 3.65 * math.sin(ang)))
        p_out = c_pt + t_horiz * (3.95 * math.cos(ang)) + Vector((0, 0, 2.90 + 3.95 * math.sin(ang)))
        add_rebar_poly(bm_s007_detail, [p_in - n_left * 0.08, p_in, p_out, p_out + n_left * 0.08], radius=0.011, n_seg=4)

# PA-2 Longitudinal distribution bars (64 rows across arch, sidewalls, and invert floor)
c_pa_start = Vector((p_main.x + n_left.x * 4.90, p_main.y + n_left.y * 4.90, Z_FL_MAIN))
c_pa_end   = Vector((p_main.x + n_left.x * 12.60, p_main.y + n_left.y * 12.60, Z_FL_SHAFT))
for r_pa in [3.68, 3.92]:
    for k in range(21):
        ang = math.radians(180.0 * k / 20.0)
        off_v = t_horiz * (r_pa * math.cos(ang)) + Vector((0, 0, 2.90 + r_pa * math.sin(ang)))
        add_rebar_poly(bm_s007_detail, [c_pa_start + off_v, c_pa_end + off_v], radius=0.012, n_seg=4)
for w_inv in np.linspace(-3.60, 3.60, 15):
    for h_inv in [-0.34, -0.04]:
        off_v = t_horiz * w_inv + Vector((0, 0, h_inv))
        add_rebar_poly(bm_s007_detail, [c_pa_start + off_v, c_pa_end + off_v], radius=0.012, n_seg=4)

# 2) #S-007 연직갱 수직 배력근 보강 (내·외측 각 48열 = 96열) 및 전단키 블록(EL.143.904) 방사형 정착 보강근
ang_to_main = math.atan2(-n_left.y, -n_left.x)
for r_sh in [3.66, 3.94]:
    for i in range(48):
        ang = 2.0 * math.pi * i / 48.0
        # Check if angle falls in PA-2 tunnel opening (within ±48° of ang_to_main below Z_FL_SHAFT + 6.5m)
        d_ang = (ang - ang_to_main + math.pi) % (2.0 * math.pi) - math.pi
        z_bot_bar = (Z_FL_SHAFT + 6.55) if abs(d_ang) < math.radians(48.0) else (Z_FL_SHAFT - 1.05)
        vx = cx + r_sh * math.cos(ang)
        vy = cy + r_sh * math.sin(ang)
        add_rebar_poly(bm_s007_detail, [Vector((vx, vy, z_bot_bar)), Vector((vx, vy, Z_GL + 0.40))], radius=0.015, n_seg=4)

# 전단키 블록 (Shear Key Collar at EL.143.904) radial U-stirrups & triple hoop rings
for i in range(48):
    ang = 2.0 * math.pi * i / 48.0
    ca, sa = math.cos(ang), math.sin(ang)
    pts_sk = [
        Vector((cx + 3.65 * ca, cy + 3.65 * sa, Z_SHEARKEY - 0.70)),
        Vector((cx + 4.50 * ca, cy + 4.50 * sa, Z_SHEARKEY - 0.42)),
        Vector((cx + 4.50 * ca, cy + 4.50 * sa, Z_SHEARKEY + 0.42)),
        Vector((cx + 3.65 * ca, cy + 3.65 * sa, Z_SHEARKEY + 0.70)),
    ]
    add_rebar_poly(bm_s007_detail, pts_sk, radius=0.016, n_seg=4)

build_rebar_obj(bm_s007_detail, "S007_REB_04_연결터널PA2_인버트S8_S9_우각부헌치_전단스터럽SB_ST_및_연직갱상세배근_2권구조도", mat_h16_orange, col_19)

# Clean up viewport outline clutter
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.show_object_outline = False
                space.shading.show_xray = True
                space.shading.xray_alpha = 0.55

bpy.ops.wm.save_mainfile()
print("SUCCESS: Detailed Tunnel & S-007 Rebar built and saved! Col 18 objs:", len(col_18.objects), "Col 19 objs:", len(col_19.objects))
