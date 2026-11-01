import bpy
import math
from mathutils import Vector, Euler

# ==============================================================================
# AUTHENTIC 12-STEP 4D CONSTRUCTION SEQUENCE CONTROLLER
# (106정거장 하향 굴착 1~11단 버팀보 가설 -> 단별 해체 및 Stage01~08C 상향 RC 축조 + NATM터널/S007 병행 공정)
# ==============================================================================
CONTROLLER_CODE = r'''import bpy
import math
from mathutils import Vector, Euler

def get_strut_objs(levels):
    """Return all 띠장/버팀보/화타/ㄷ형강 object names in 01_가시설_단별해체_버팀보_띠장_ㄷ형강 for given level numbers (1..11)."""
    col = bpy.data.collections.get("01_가시설_단별해체_버팀보_띠장_ㄷ형강")
    if not col:
        return []
    prefixes = tuple(f"_{lvl:02d}단_" for lvl in levels)
    return [o.name for o in col.objects if any(p in o.name for p in prefixes)]

# All objects in 00_가시설_외벽엄지말뚝_차수_토류판 except front cutaway walls (so interior excavation & struts are clearly visible from South!)
OUTER_SHORING_CUTAWAY = [
    "01A_차수그라우팅_배면_북동측",
    "01C_그라우팅_중심홀_438EA",
    "02A_측면파일_배면_북측",
    "02B_측면파일_배면_동측",
    "02D_측면파일_단차벽체_27EA",
    "03A_토류판_벽체_배면및단차",
]

STAGE_RC_B4_LOW = [
    "Stage01_지하4층하부_기초슬래브_T1700",
    "Stage02A_지하4층하부_RC벽체및기둥",
    "Stage02B_지하4층하부_상부슬래브_T900",
    "Stage02C_지하4층하부_거더",
]
STAGE_RC_B4_MAIN_SLAB = STAGE_RC_B4_LOW + [
    "Stage03_지하4층본동_기초슬래브_T1700",
]
STAGE_RC_B3_SLAB = STAGE_RC_B4_MAIN_SLAB + [
    "Stage04_지하4층_RC외벽및중앙벽기둥",
    "Stage05A_지하3층단차구간_기초슬래브_T1300",
    "Stage05B_지하3층_바닥슬래브_T900",
    "Stage05C_지하3층_바닥거더_Girders",
]
STAGE_RC_B2_SLAB = STAGE_RC_B3_SLAB + [
    "Stage06A_지하3층_RC외벽및기둥",
    "Stage06B_지하2층_바닥슬래브_T800",
    "Stage06C_지하2층_바닥거더_Girders",
]
STAGE_RC_B1_SLAB = STAGE_RC_B2_SLAB + [
    "Stage07A_지하2층_RC외벽및기둥",
    "Stage07B_지하1층_바닥슬래브_T800",
    "Stage07C_지하1층_바닥거더_Girders",
]
STAGE_RC_ROOF_COMPLETE = STAGE_RC_B1_SLAB + [
    "Stage08A_지하1층_RC외벽및기둥",
    "Stage08B_최상부_루프슬래브_T1200",
    "Stage08C_최상부_루프거더_Girders",
]

PHASES = {
    1: {
        "frame": 10,
        "title": "Step 01 [굴착 준비] : 외곽 엄지말뚝(H-Pile)·차수그라우팅·중간말뚝(122본) 및 #S-007 가시설 항타",
        "work":  "• 정거장 외벽 H-Pile·차수벽(438공)·중간말뚝(122본), 출입구 가시설 말뚝 및 #S-007 수직구 가시설 H-Pile(18본) 항타",
        "safety": "[안전] 지하 매설물(고압선·상하수도) 이설 확인 및 천공·항타장비 지반 지지력 확보",
        "cost":   "[원가/설계변경] 중간말뚝 #104, #22 등 14개소가 본체 RC기둥(#13, #35) 위치와 직접 간섭! 항타 전 중간말뚝 열 조정 또는 장지간 버팀보 VE 필수",
        "quality":"[품질] 엄지말뚝·중간말뚝 수직도(1/200 이내) 및 암반 근입깊이 검측",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "06A_기둥_중간말뚝_BIM간섭검측_보고",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + [
            "06A_간섭검측_중간말뚝_기둥직접관통_5개소_Red",
            "06B_간섭검측_중간말뚝_기둥근접거푸집간섭_4개소_Org",
            "S007_수직구가시설_링빔1_10단_및_HPile18본_4권가시설도",
        ],
        "cam_target": (50.0, 12.0, -16.0),
        "cam_dist": 95.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    2: {
        "frame": 20,
        "title": "Step 02 [상부 1~3단 굴착] : GL~Z-9.0m 굴착, 복공판 및 1~3단 버팀보(S1~S3) 가설 / #S-007 상부굴착",
        "work":  "• 정거장 상부 굴착(Z=0~-9.0m) + 토류판 시공 + 1단(S1, Z=-0.5m)·2단(S2, Z=-4.5m)·3단(S3, Z=-8.5m) 버팀보·띠장 가설 (4~11단은 미굴착)",
        "safety": "[안전] 1~3단 단계별 굴착 시 과굴착 금지 및 복공하부 1단 버팀보(S1) 용접·볼트 체결 상태 점검",
        "cost":   "[원가/공정] 상부 매립층·풍화토 굴착 중 지장물 보호공 및 지하수 유출 시 배면 차수 보강",
        "quality":"[품질] 1~3단 버팀보 잭킹(Pre-loading) 축력 도입 및 띠장-엄지말뚝 브래킷 밀착 시공",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3]) + [
            "S007_수직구가시설_링빔1_10단_및_HPile18본_4권가시설도",
            "S007_연직갱_상부가시설_외벽케이싱_H23597",
        ],
        "cam_target": (50.0, 12.0, -12.0),
        "cam_dist": 90.0,
        "cam_angles": (62.0, 0.0, -35.0),
    },
    3: {
        "frame": 30,
        "title": "Step 03 [중층 4~6단 굴착] : Z-9.0~-21.0m 굴착, 4~6단 버팀보(S5~S9) 가설 / #S-007 수직구·횡갱 선굴착",
        "work":  "• 정거장 중층 굴착(Z=-9~-21m) + 4단(S5, Z=-12.5m)·5단(S7, Z=-16.5m)·6단(S9, Z=-20.5m) 버팀보 추가 가설 (1~6단 가설 상태) + 출입구 가시설 버팀보",
        "safety": "[안전] 굴착 심도 증가에 따른 상부 1~3단 버팀보 축력 재점검 및 #S-007 수직구 전단키(EL+143.90) 암반 굴착 안전관리",
        "cost":   "[원가/설계변경] #S-007 수직구 전단키 블록(Key Block) 암반 발파 여굴 무수축 채움 및 하단 가시설 링빔 보강 반영",
        "quality":"[품질] 4~6단 버팀보 이음부 볼트 토크 및 중앙말뚝 화타( 브래킷) 수평도 검측",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
            "11_외부출입구_가시설_단별버팀보_띠장_어스앵커",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3, 4, 5, 6]) + [
            "S007_수직구가시설_링빔1_10단_및_HPile18본_4권가시설도",
            "S007_연직갱_상부가시설_외벽케이싱_H23597",
            "S007_연직갱_전단키블록_KeyBlock_EL143.904",
            "S007_연결터널_횡갱_PA2_폭8.0m_연장7.63m",
        ],
        "cam_target": (50.0, 12.0, -16.0),
        "cam_dist": 95.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    4: {
        "frame": 40,
        "title": "Step 04 [하층 7~11단 완료굴착 & NATM 터널 굴진] : 7~11단 버팀보(S11~S17)·최하단 앵커(EA1,2)·버림타설 및 터널 굴착",
        "work":  "• 정거장 최종 굴착(Z=-37.5m) + 7~11단 버팀보(1~11단 전체 가설) + 최하단 제거식 어스앵커(EA1,EA2) + 바닥 버림콘크리트(t=150) + 본선 NATM터널 단계별 굴착/지보",
        "safety": "[안전] 대심도 최하단 굴착면 암반 이완·지하수 용출 관리 및 터널 상·하반 분할굴착 막장 안정성(링컷 코어 존치) 확보",
        "cost":   "[원가/설계변경] ① 정거장 시·종점 갱문 돌파부 문형 라멘 가시설 보강, ② 본선 STA 12k665~ 양호암(RMR 56~74) 구간 PD-6-1 오적용 정정",
        "quality":"[품질] 정거장 맨바닥 계획고 암반 지지력 확인 및 본선터널 강관다단(L=12m)·강지보(H-150/125)·숏크리트·록볼트(L=4m) 검측",
        "cols_on": [
            "01B_본체_최하단_제거식어스앵커_EA1_EA2",
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "03_기초전_맨바닥계획고_버림콘크리트",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
            "11_외부출입구_가시설_단별버팀보_띠장_어스앵커",
            "21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]) + [
            "NATM_본선터널_시점부_숏크리트방수층_11K660_11K935",
            "NATM_본선터널_종점부1_숏크리트방수층_12K044_12K780",
            "NATM_본선터널_종점부2_동탄방향_숏크리트방수층_12K788_12K860",
            "S007_수직구가시설_링빔1_10단_및_HPile18본_4권가시설도",
            "S007_연직갱_상부가시설_외벽케이싱_H23597",
            "S007_연직갱_전단키블록_KeyBlock_EL143.904",
            "S007_연결터널_횡갱_PA2_폭8.0m_연장7.63m",
        ],
        "cam_target": (50.0, 12.0, -20.0),
        "cam_dist": 100.0,
        "cam_angles": (58.0, 0.0, -35.0),
    },
    5: {
        "frame": 50,
        "title": "Step 05 [B4F 하부포켓 축조] : 11단·10단 버팀보(S17,S15) 해체 → 지하4층 하부 기초·벽체·슬래브(Stage01~02C) 타설",
        "work":  "• 11단 버팀보(S17, Z=-37.5m) 해체 → 지하4층 하부 기초슬래브(Stage01 T=1700) 타설 → 10단 버팀보(S15, Z=-35.0m) 해체 → 하부 벽체·기둥·슬래브(Stage02A~C) 타설 (1~9단 버팀보 존치)",
        "safety": "[안전] 최하단 11단·10단 버팀보 해체 시 토류벽 하단 변위 계측 및 하부 포켓 거푸집/동바리 전도 방지",
        "cost":   "[원가/공정] 대심도 단차 구간 수직 버림콘크리트 마감벽 및 암반 여굴 콘크리트 채움 물량 반영",
        "quality":"[품질] 지하4층 하부 기초슬래브(T=1,700mm) 매스콘크리트 수화열 제어 및 바닥 방수층 시공 품질 확보",
        "cols_on": [
            "01B_본체_최하단_제거식어스앵커_EA1_EA2",
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "03_기초전_맨바닥계획고_버림콘크리트",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
            "11_외부출입구_가시설_단별버팀보_띠장_어스앵커",
            "21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3, 4, 5, 6, 7, 8, 9]) + STAGE_RC_B4_LOW + [
            "Clash_Slab_B4_vs_S14",
            "NATM_본선터널_시점부_숏크리트방수층_11K660_11K935",
            "NATM_본선터널_종점부1_숏크리트방수층_12K044_12K780",
            "NATM_본선터널_종점부2_동탄방향_숏크리트방수층_12K788_12K860",
        ],
        "cam_target": (55.0, 12.0, -24.0),
        "cam_dist": 85.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    6: {
        "frame": 60,
        "title": "Step 06 [B4F 본동 기초슬래브] : 9단 버팀보(S14) 해체 → 기초 정밀복배근·전단보강근(13번) 및 본동 기초슬래브(Stage03) 타설",
        "work":  "• 9단 버팀보(S14, Z=-32.0m) 및 최하단 앵커 해체 → 기초슬래브 복배근(D32/D29)·전단보강근(AS1, 우마철근, 펀칭보강) 조립 → 지하4층 본동 기초슬래브(Stage03 T=1700) 및 집수정/정화조 타설 (1~8단 버팀보 존치)",
        "safety": "[안전] 9단 버팀보(S14) 해체 시 8단 버팀보(S13)로의 하중 전이 확인 및 중량 철근(D32) 크레인 인양 안전 준수",
        "cost":   "[원가/설계변경] 기초슬래브 전단보강근(AS1 135° 후크), 대형 우마철근(D19) 및 기둥 하부 펀칭전단보강근 정밀 물량 반영",
        "quality":"[품질] 슬래브 관통 중간말뚝(122본) 주변 지수링(08B) 용접 상태 및 기초 주철근 피복두께(80mm) 확인",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "03_기초전_맨바닥계획고_버림콘크리트",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
            "11_외부출입구_가시설_단별버팀보_띠장_어스앵커",
            "13_바닥기초슬래브_정밀전단및복배근_LOD400",
            "21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3, 4, 5, 6, 7, 8]) + STAGE_RC_B4_MAIN_SLAB + [
            "DRAIN_01_106정거장_집수정_본체RC_STA12k010_27mx2.6mx4.2m",
            "DRAIN_01C_106정거장_집수정_철근배근_LOD400",
            "DRAIN_02_106정거장_정화조_본체RC_STA11k994_27.31mx13.0mx4.5m",
            "DRAIN_02C_106정거장_정화조_철근배근_LOD400",
            "NATM_본선터널_시점부_숏크리트방수층_11K660_11K935",
            "NATM_본선터널_종점부1_숏크리트방수층_12K044_12K780",
            "NATM_본선터널_종점부2_동탄방향_숏크리트방수층_12K788_12K860",
        ],
        "cam_target": (55.0, 12.0, -24.0),
        "cam_dist": 80.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    7: {
        "frame": 70,
        "title": "Step 07 [B4F 벽체/기둥 & B3F 바닥슬래브] : 8단·7단 버팀보(S13,S11) 해체 → B4 벽체·기둥(Stage04) 및 B3 바닥슬래브(Stage05) 타설 + 터널 배수·방수",
        "work":  "• 8단(S13, Z=-28.5m) 해체 → B4 외벽·중앙기둥(Stage04) 타설 → 7단(S11, Z=-24.5m) 해체 → B3 단차기초·바닥슬래브·거더(Stage05A~C) 타설 (1~6단 버팀보 존치) + 본선터널 배수관망(Ø300/Ø150)·T/Y형 연결관·방수쉬트 포설",
        "safety": "[안전] 8단·7단 버팀보 연속 해체 전 B4 기초슬래브-외벽 측압 지지 강도 확인 및 B3 슬래브 시스템 동바리 구조안전 점검",
        "cost":   "[원가/설계변경] ① 중간말뚝-기둥 간섭부(14개소) 거푸집/철근 보강, ② 터널 횡배수관(Ø150, 10m 간격)과 인버트 철근 간섭 방지용 맹암거 단면 확대",
        "quality":"[품질] 터널 T형 연결관 분기소켓-횡배수관 동축 일치 시공 및 부직포·방수쉬트 용착부 기밀시험 수행",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
            "11_외부출입구_가시설_단별버팀보_띠장_어스앵커",
            "20_정거장_및_터널_배수시설_집수정_정화조_맨홀_배수관망",
            "21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3, 4, 5, 6]) + STAGE_RC_B3_SLAB + [
            "정거장_기둥_주철근_D29_골격",
            "구조상세_CZSECM100_지하4층_기초개구부및헌치상세",
            "Clash_Slab_B3_vs_S11S12",
            "NATM_본선터널_시점부_숏크리트방수층_11K660_11K935",
            "NATM_본선터널_종점부1_숏크리트방수층_12K044_12K780",
            "NATM_본선터널_종점부2_동탄방향_숏크리트방수층_12K788_12K860",
        ],
        "cam_target": (55.0, 12.0, -21.0),
        "cam_dist": 85.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    8: {
        "frame": 80,
        "title": "Step 08 [B3F 벽체/기둥 & B2F 바닥슬래브 + 터널 상세철근] : 6단·5단 버팀보(S9,S7) 해체 → B3 벽체·B2 바닥슬래브(Stage06A~C) 타설 + 터널 복배근 조립",
        "work":  "• 6단(S9, Z=-20.5m) 해체 → B3 외벽·기둥(Stage06A) 타설 → 5단(S7, Z=-16.5m) 해체 → B2 바닥슬래브·거더(Stage06B~C) 타설 (1~4단 버팀보 존치) + 본선터널·기재갱·#S-007 라이닝 상세철근(18번, 19번 컬렉션) 조립",
        "safety": "[안전] 6단·5단 버팀보 해체 시 크레인 인양 간섭 주의 및 터널 철근 조립 대차(Jumbo) 고소작업 추락 방지",
        "cost":   "[원가/설계변경] ① 기재갱(#11~#13)·#S-007 개구부 절단철근 보강 추가, ② 공동구 2차 후타설 정착용 시공이음 다우얼 철근(H13 @250) 사전 매립!",
        "quality":"[품질] 터널 아치 복배근(1~6번)·인버트(9~11번)·우각부 헌치(7,8번)·전단보강근(A)·받침철근(T1~T3) 간격 및 방수막 보호 상태 검측",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
            "11_외부출입구_가시설_단별버팀보_띠장_어스앵커",
            "18_본선터널_및_기재갱_철근배근_LOD400",
            "19_S007환기구_수직구_연결터널_상부박스_철근배근_LOD400",
            "20_정거장_및_터널_배수시설_집수정_정화조_맨홀_배수관망",
            "21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3, 4]) + STAGE_RC_B2_SLAB + [
            "정거장_기둥_주철근_D29_골격",
            "구조상세_CZSECM30_지하3층_승강장계단및개구부상세",
            "Clash_Slab_B2_vs_S7S8",
        ],
        "cam_target": (65.0, 12.0, -18.0),
        "cam_dist": 90.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    9: {
        "frame": 90,
        "title": "Step 09 [B2F 벽체/기둥 & B1F 바닥슬래브 + 터널 라이닝 타설] : 4단 버팀보(S5) 해체 → B2 벽체·B1 바닥슬래브(Stage07A~C) 및 터널 라이닝 타설",
        "work":  "• 4단(S5, Z=-12.5m) 해체 → B2 외벽·기둥(Stage07A) 및 B1 바닥슬래브·거더(Stage07B~C) 타설 (1~3단 버팀보 존치) + 본선터널·기재갱·#S-007 콘크리트 라이닝(t=400mm) 및 인버트 타설",
        "safety": "[안전] 본선터널 강제 거푸집(Steel Form Traveler) 이동 및 콘크리트 압송 시 좌·우 대칭 타설(편압 방지) 준수",
        "cost":   "[원가/설계변경] #S-007 연직갱(D=8.0m) ↔ 연결터널(W=8.0m) 동경 접합부 3차원 안장형 예각부(Knife-Edge) 특수 거푸집 및 필렛 할증",
        "quality":"[품질] 터널 라이닝 천단부 공극 충진용 배면 컨택트 그라우팅(Contact Grouting) 및 정거장 외벽 수평 시공조인트(CJ) 지수판 시공",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "10_외부출입구_가시설_엄지말뚝_차수_토류판",
            "11_외부출입구_가시설_단별버팀보_띠장_어스앵커",
            "12_본구조물_철근배근_3D_BIM_LOD400",
            "18_본선터널_및_기재갱_철근배근_LOD400",
            "19_S007환기구_수직구_연결터널_상부박스_철근배근_LOD400",
            "20_정거장_및_터널_배수시설_집수정_정화조_맨홀_배수관망",
            "21_본선터널_NATM지보재_강지보_록볼트_강관다단_단계별굴착_LOD400",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1, 2, 3]) + STAGE_RC_B1_SLAB + [
            "정거장_RC중앙기둥_36개소_실물콘크리트",
            "구조상세_CZDIMA139_지하2층_내력벽기둥및거더상세",
            "Clash_Slab_B1_vs_S4S5",
            "NATM_본선터널_시점부_콘크리트라이닝_11K660_11K935",
            "NATM_본선터널_시점부_인버트및공동구_11K660_11K935",
            "NATM_본선터널_종점부1_콘크리트라이닝_12K044_12K780",
            "NATM_본선터널_종점부1_인버트및공동구_12K044_12K780",
            "NATM_본선터널_환기구접속개구부_12K780_12K788",
            "NATM_본선터널_환기구접속인버트_12K780_12K788",
            "NATM_본선터널_종점부2_동탄방향_콘크리트라이닝_12K788_12K860",
            "NATM_본선터널_종점부2_동탄방향_인버트및공동구_12K788_12K860",
            "S007_연직갱_하부기초슬래브_EL130.196",
            "S007_연직갱_하부접속구간_라이닝_EL130.196",
            "S007_연직갱_하부암반구간_상단_SH3_SH2",
            "S007_연결터널_횡갱_PA2_폭8.0m_연장7.63m",
            "S007_연결터널_바닥인버트_배수경사0.5pct",
        ],
        "cam_target": (55.0, 12.0, -15.0),
        "cam_dist": 90.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    10: {
        "frame": 100,
        "title": "Step 10 [B1F 벽체 & 최상부 루프슬래브 + 터널 공동구/S007 상부박스] : 3단·2단 버팀보(S3,S2) 해체 → 루프슬래브(Stage08B~C) 및 터널 공동구 타설",
        "work":  "• 3단(S3, Z=-8.5m)·2단(S2, Z=-4.5m) 해체 → B1 외벽·기둥(Stage08A) 및 최상부 루프슬래브·거더(Stage08B~C)·시종점 마감벽(17번) 타설 (1단 복공버팀보만 존치) + 터널 양측 공동구(C1,C2) 및 #S-007 상부 개착박스 완공",
        "safety": "[안전] 최상부 루프슬래브(T=1,200mm) 고하중 동바리 구조검토 및 자재투입구 개구부 추락방지망 설치",
        "cost":   "[원가/설계변경] 공동구 내측 배수관(Ø50mm, 10m 간격) 수평 유도배수 슬리브 반영 및 루프슬래브 방수·보호몰탈 시공",
        "quality":"[품질] 정거장 시·종점 본체 마감벽(T=1,200mm) ↔ 터널 갱문 칼라부 신축이음지수판(Expansion Joint Waterstop) 수밀 시공",
        "cols_on": [
            "02_가시설_중간말뚝_슬래브관통매입_추후해체",
            "05_본체구조도_개구부_자재투입구_계단실_상세",
            "14_본선터널_연결구간_NATM복선",
            "15_환기구7_수직구_및_양방향터널접속",
            "17_정거장_시종점_본체마감벽_및_갱문칼라",
            "18_본선터널_및_기재갱_철근배근_LOD400",
            "19_S007환기구_수직구_연결터널_상부박스_철근배근_LOD400",
            "20_정거장_및_터널_배수시설_집수정_정화조_맨홀_배수관망",
        ],
        "objs_on": OUTER_SHORING_CUTAWAY + get_strut_objs([1]) + STAGE_RC_ROOF_COMPLETE + [
            "정거장_RC중앙기둥_36개소_실물콘크리트",
            "Clash_Slab_Roof_vs_S2",
        ],
        "cam_target": (55.0, 12.0, -14.0),
        "cam_dist": 95.0,
        "cam_angles": (60.0, 0.0, -35.0),
    },
    11: {
        "frame": 110,
        "title": "Step 11 [가시설 해체·되메우기 & 외부출입구/승강장/궤도 완공] : 1단 버팀보·중간말뚝(08C) 해체 → 출입구(09번)·승강장/PSD(16번)·KR60 궤도 완공",
        "work":  "• 1단 버팀보(S1)·복공판 및 층간 노출 중간말뚝(08C 122본) 절단 해체 + 슬래브 관통부 무수축 패치(08B) 마감 + 외부 출입구/환기구(09번) + 내부 승강장·PSD·ES·EV(16번) + 콘크리트 도상·KR60 레일 완공",
        "safety": "[안전] 층간 중간말뚝(08C) 산소절단·인양 시 화재/낙하 방지 및 야간 복공판 해체·도로포장 복구 시 교통통제 철저",
        "cost":   "[원가/품질] 중간말뚝 절단면(08A/08B) 방수하자 예방을 위한 지수링·무수축 몰탈 충진 및 상부 복합방수 정산",
        "quality":"[품질] 본선 KR60 장대레일 궤간(1,435mm)·선형 검측 및 승강장 스크린도어(PSD)·에스컬레이터(ES)·엘리베이터(EV) 시운전",
        "cols_on": [
            "05_본체구조도_개구부_자재투입구_계단실_상세",
            "09_외부출입구_환기구_연결구조물_External",
            "14_본선터널_연결구간_NATM복선",
            "15_환기구7_수직구_및_양방향터널접속",
            "16_정거장_내부승강장_PSD_ES_EV_환기덕트",
            "17_정거장_시종점_본체마감벽_및_갱문칼라",
            "20_정거장_및_터널_배수시설_집수정_정화조_맨홀_배수관망",
        ],
        "objs_on": STAGE_RC_ROOF_COMPLETE + [
            "정거장_RC중앙기둥_36개소_실물콘크리트",
            "08A_중간파일_기초및슬래브관통_영구매입부_122EA",
            "08B_중간파일_슬래브관통부_지수링및무수축매입패치_122EA",
        ],
        "cam_target": (55.0, 12.0, -14.0),
        "cam_dist": 125.0,
        "cam_angles": (62.0, 0.0, -36.0),
    },
    12: {
        "frame": 120,
        "title": "Step 12 [전 공정 마스터 검증 뷰] : 가시설 + 본체RC + 상세철근 + NATM지보재/단계별굴착 + 배수 + BIM간섭검측 전체 통합",
        "work":  "• 106정거장 + 단별 가시설(1~11단) + 본선 NATM터널(시점부 5단계 굴착 쇼케이스 포함) + #S-007 환기구 + 전 구간 상세철근 + 배수계통 + 간섭검측 마커 통합 표시",
        "safety": "[안전] 시공 전~준공 전 단계 3D BIM 기반 위험요소 및 공종 간 간섭(Clash) 상시 시뮬레이션",
        "cost":   "[원가/VE] 발주처 원설계 오류 12건(중간말뚝 기둥관통, 단별 버팀보-슬래브 간섭, 공동구 배수/다우얼 누락, 개구부 보강누락, 지보패턴 오적용 등) 설계변경 총괄",
        "quality":"[품질] 1:1 LOD 400 시공 연동형 디지털 트윈 마스터 모델",
        "cols_on": "ALL",
        "objs_on": [],
        "cam_target": (55.0, 12.0, -16.0),
        "cam_dist": 135.0,
        "cam_angles": (60.0, 0.0, -35.0),
    }
}

def update_hud_text(phase_idx):
    info = PHASES.get(phase_idx, PHASES[12])
    hud_obj = bpy.data.objects.get("HUD_4D_Construction_Banner")
    if hud_obj and hud_obj.type == 'FONT':
        hud_obj.data.body = (
            f"■ {info['title']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▶ [금회 시공공정] {info['work']}\n"
            f"▶ {info['safety']}\n"
            f"▶ {info['cost']}\n"
            f"▶ {info['quality']}"
        )

def apply_construction_phase(phase_idx, move_camera=False):
    info = PHASES.get(phase_idx, PHASES[12])
    bpy.context.scene["active_4d_phase"] = phase_idx

    all_mode = (info["cols_on"] == "ALL")
    cols_on_set = set(info["cols_on"]) if not all_mode else set()
    objs_on_set = set(info["objs_on"])

    # Always keep root & HUD collections visible
    cols_on_set.add("22_4D공정시뮬레이션_현황판_및_사전리스크체크_HUD")
    cols_on_set.add("106_Station_BIM_CAD044")

    for col in bpy.data.collections:
        if col.name in ["22_4D공정시뮬레이션_현황판_및_사전리스크체크_HUD", "106_Station_BIM_CAD044"]:
            col.hide_viewport = False
            for o in col.objects:
                o.hide_viewport = False
            continue

        if all_mode:
            col.hide_viewport = False
            for o in col.objects:
                # Keep front cutaway walls hidden even in ALL mode so inside is visible!
                if "전면RC외벽_투시전환용" in o.name or "전면_남서측_투시전환용" in o.name:
                    o.hide_viewport = True
                else:
                    o.hide_viewport = False
        else:
            has_specific_obj = any(o.name in objs_on_set for o in col.objects)
            if col.name in cols_on_set:
                col.hide_viewport = False
                for o in col.objects:
                    if "전면RC외벽_투시전환용" in o.name or "전면_남서측_투시전환용" in o.name:
                        o.hide_viewport = True
                    elif phase_idx <= 9 and col.name == "14_본선터널_연결구간_NATM복선" and ("콘크리트도상" in o.name or "KR60_레일" in o.name):
                        o.hide_viewport = True
                    else:
                        o.hide_viewport = False
            elif has_specific_obj:
                col.hide_viewport = False
                for o in col.objects:
                    o.hide_viewport = (o.name not in objs_on_set)
            else:
                col.hide_viewport = True

    def sync_lcol(lcol):
        if lcol.collection != bpy.context.scene.collection:
            lcol.exclude = False
            lcol.hide_viewport = lcol.collection.hide_viewport
        for ch in lcol.children:
            sync_lcol(ch)
    sync_lcol(bpy.context.view_layer.layer_collection)

    update_hud_text(phase_idx)

    hud_obj = bpy.data.objects.get("HUD_4D_Construction_Banner")
    if hud_obj:
        tx, ty, tz = info["cam_target"]
        hud_obj.location = Vector((tx - 38.0, ty + 18.0, tz + 24.0))

    if move_camera:
        tx, ty, tz = info["cam_target"]
        ax, ay, az = info["cam_angles"]
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            rv3d = space.region_3d
                            rv3d.view_perspective = 'PERSP'
                            rv3d.view_location = Vector((tx, ty, tz))
                            rv3d.view_distance = info["cam_dist"]
                            rv3d.view_rotation = Euler((math.radians(ax), math.radians(ay), math.radians(az)), 'XYZ').to_quaternion()

def on_frame_change(scene):
    f = scene.frame_current
    p_idx = max(1, min(12, int(round(f / 10.0))))
    if scene.get("active_4d_phase", -1) != p_idx:
        apply_construction_phase(p_idx, move_camera=False)

class BIM4D_OT_SetPhase(bpy.types.Operator):
    bl_idname = "bim4d.set_phase"
    bl_label = "공정단계 전환"
    bl_description = "실제 현장 시공순서(하향굴착 1~11단 가설 -> 단별 해체 및 Stage01~08C 상향 RC 축조 + 터널 병행)로 전환합니다"

    phase: bpy.props.IntProperty(default=12)
    move_cam: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        p = max(1, min(12, self.phase))
        context.scene["active_4d_phase"] = p
        context.scene.frame_set(p * 10)
        apply_construction_phase(p, move_camera=self.move_cam)
        return {'FINISHED'}

class VIEW3D_PT_4DConstructionBIM(bpy.types.Panel):
    bl_label = "4D 실제 시공순서 시뮬레이션 (Step 01~12)"
    bl_idname = "VIEW3D_PT_4d_construction_bim"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "4D 시공관리 BIM"

    def draw(self, context):
        layout = self.layout
        cur_p = context.scene.get("active_4d_phase", 12)
        info = PHASES.get(cur_p, PHASES[12])

        box_top = layout.box()
        box_top.label(text=info["title"], icon='TIME')
        row_nav = box_top.row(align=True)
        op_prev = row_nav.operator("bim4d.set_phase", text="◀ 이전 시공단계 (Prev)", icon='TRIA_LEFT')
        op_prev.phase = max(1, cur_p - 1)
        op_prev.move_cam = True
        op_next = row_nav.operator("bim4d.set_phase", text="다음 시공단계 (Next) ▶", icon='TRIA_RIGHT')
        op_next.phase = min(12, cur_p + 1)
        op_next.move_cam = True

        box_risk = layout.box()
        box_risk.label(text="금회 시공내용 & 사전 리스크 체크 (안전·원가·품질)", icon='ERROR')
        box_risk.label(text=info["work"])
        box_risk.label(text=info["safety"], icon='SHADING_SOLID')
        box_risk.label(text=info["cost"], icon='MOD_BUILD')
        box_risk.label(text=info["quality"], icon='CHECKMARK')

        box_exc = layout.box()
        box_exc.label(text="[I. 가시설 및 하향 단계별 굴착 (1단→11단 버팀보 가설)]", icon='SORT_ASC')
        for p_idx in range(1, 5):
            p_info = PHASES[p_idx]
            row = box_exc.row(align=True)
            row.alert = (p_idx == cur_p)
            op = row.operator("bim4d.set_phase", text=p_info["title"], icon=('RADIOBUT_ON' if p_idx == cur_p else 'RADIOBUT_OFF'))
            op.phase = p_idx
            op.move_cam = True

        box_rc = layout.box()
        box_rc.label(text="[II. 단별 버팀보 해체(11단→1단) & 상향 RC 축조 + 터널 병행]", icon='SORT_DESC')
        for p_idx in range(5, 13):
            p_info = PHASES[p_idx]
            row = box_rc.row(align=True)
            row.alert = (p_idx == cur_p)
            op = row.operator("bim4d.set_phase", text=p_info["title"], icon=('RADIOBUT_ON' if p_idx == cur_p else 'RADIOBUT_OFF'))
            op.phase = p_idx
            op.move_cam = True

def register_4d_bim():
    for cls in [BIM4D_OT_SetPhase, VIEW3D_PT_4DConstructionBIM]:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        bpy.utils.register_class(cls)
    bpy.app.handlers.frame_change_post[:] = [h for h in bpy.app.handlers.frame_change_post if h.__name__ != "on_frame_change"]
    bpy.app.handlers.frame_change_post.append(on_frame_change)

register_4d_bim()
'''

txt_block = bpy.data.texts.get("4D_BIM_Controller.py")
if not txt_block:
    txt_block = bpy.data.texts.new("4D_BIM_Controller.py")
txt_block.clear()
txt_block.write(CONTROLLER_CODE)
txt_block.use_module = True

bpy.context.scene.frame_start = 10
bpy.context.scene.frame_end = 120
exec(CONTROLLER_CODE, globals())
bpy.ops.bim4d.set_phase(phase=7, move_cam=True)
bpy.ops.wm.save_mainfile()
print("SUCCESS: Authentic 12-Step Downward Excavation & Bottom-Up Structure/Tunnel 4D BIM Sequence registered and saved!")
