# -*- coding: utf-8 -*-
"""
钢板梁设计计算引擎
依据 JTG D64-2015 / JTG D60-2015
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict

# ============================================================
# 常量
# ============================================================
E_STEEL = 2.06e5          # 钢材弹性模量 (MPa)
G_STEEL = 7.9e4           # 钢材剪切模量 (MPa)
RHO_STEEL = 78.5          # 钢材容重 (kN/m³)
GAMMA_C = 25.0            # 混凝土容重 (kN/m³)
GAMMA_A = 24.0            # 沥青容重 (kN/m³)
Q_K = 10.5                # 公路-I级均布荷载 (kN/m)
F_FF_E50 = 200.0          # E50角焊缝强度设计值 (MPa)


def get_strength(t_mm: float, steel_grade: str = "Q345") -> Tuple[float, float, float]:
    """根据板厚返回 (f_d, f_vd, f_ce) 单位 MPa"""
    if steel_grade == "Q345":
        if t_mm <= 16:
            return 275.0, 160.0, 355.0
        elif t_mm <= 40:
            return 270.0, 155.0, 355.0
        elif t_mm <= 63:
            return 260.0, 150.0, 355.0
        else:
            return 250.0, 145.0, 355.0
    else:
        return 270.0, 155.0, 355.0


# ============================================================
# 数据结构
# ============================================================

@dataclass
class DesignParams:
    """设计基本参数"""
    L: float = 35.0              # 计算跨径 (m)
    B: float = 1.8               # 桥面板宽度 (m)
    H1: float = 0.08             # 混凝土桥面板厚度 (m)
    H2: float = 0.06             # 沥青铺装层厚度 (m)
    eta: float = 0.43            # 横向分布系数
    gamma_G: float = 1.2         # 恒载分项系数
    gamma_Q: float = 1.4         # 活载分项系数
    gamma_0: float = 1.1         # 结构重要性系数
    mu_impact: float = 1.14      # 活载冲击系数 (1+μ)
    steel_grade: str = "Q345"    # 钢材牌号
    electrode: str = "E50"       # 焊条型号


@dataclass
class SectionInput:
    """截面尺寸输入 (mm)"""
    h_w: float = 1800.0          # 腹板高度
    t_w: float = 14.0            # 腹板厚度
    b_f: float = 500.0           # 翼缘宽度 (跨中段)
    t_f: float = 28.0            # 翼缘厚度 (跨中段)
    b_f2: float = 0.0            # 变截面翼缘宽度 (0表示自动)
    t_f2: float = 0.0            # 变截面翼缘厚度 (0表示自动)


@dataclass
class SectionProps:
    """截面几何特性"""
    A: float = 0.0               # 面积 (mm²)
    I_x: float = 0.0             # 惯性矩 (mm⁴)
    W_x: float = 0.0             # 截面模量 (mm³)
    S: float = 0.0               # 半截面面积矩 (mm³)
    S_f: float = 0.0             # 翼缘对中性轴面积矩 (mm³)
    h: float = 0.0               # 总高 (mm)
    h_w: float = 0.0             # 腹板高 (mm)
    t_w: float = 0.0             # 腹板厚 (mm)
    b_f: float = 0.0             # 翼缘宽 (mm)
    t_f: float = 0.0             # 翼缘厚 (mm)
    g1: float = 0.0              # 钢梁自重 (kN/m)
    y_j: float = 0.0             # 腹板-翼缘交界距中性轴 (mm)


@dataclass
class StiffenerDesign:
    """加劲肋设计结果"""
    hw_tw_ratio: float = 0.0
    need_transverse: bool = False
    need_longitudinal: bool = False
    spacing: float = 0.0         # 间距 (mm)
    n_pairs: int = 0             # 对数
    b_s: float = 0.0             # 加劲肋宽度 (mm)
    t_s: float = 0.0             # 加劲肋厚度 (mm)
    # 支座加劲肋
    bearing_n: int = 2
    bearing_b: float = 160.0     # 宽 (mm)
    bearing_t: float = 16.0      # 厚 (mm)
    sigma_ce: float = 0.0        # 端面承压应力 (MPa)
    sigma_stab: float = 0.0      # 稳定应力 (MPa)
    ce_ok: bool = True
    stab_ok: bool = True


@dataclass
class WeldDesign:
    """焊缝设计结果"""
    # 等截面段
    S_f1: float = 0.0
    v1: float = 0.0              # 单位长度剪力 (N/mm)
    h_f_req1: float = 0.0        # 计算所需焊脚 (mm)
    h_f_min1: float = 0.0        # 构造最小焊脚 (mm)
    h_f_max1: float = 0.0        # 构造最大焊脚 (mm)
    h_f_chosen: float = 8.0      # 选用焊脚 (mm)
    # 变截面段
    S_f2: float = 0.0
    v2: float = 0.0
    h_f_req2: float = 0.0
    h_f_min2: float = 0.0
    h_f_max2: float = 0.0


@dataclass
class FatigueResult:
    """疲劳验算结果"""
    q_f1: float = 0.0
    P_f1: float = 0.0
    M_f: float = 0.0
    delta_sigma_p: float = 0.0
    check_base_metal: bool = True       # 翼缘母材(非焊接) Δσ_c=160
    check_fillet_weld: bool = True      # 翼缘-腹板连续角焊缝 Δσ_c=80
    delta_sigma_c_base: float = 160.0
    delta_sigma_D_base: float = 118.4
    delta_sigma_c_weld: float = 80.0
    delta_sigma_D_weld: float = 59.2


@dataclass
class ChecksResult:
    """各项验算结果"""
    # 跨中
    sigma_mid: float = 0.0; sigma_mid_ok: bool = True; sigma_mid_limit: float = 0.0
    tau_max: float = 0.0; tau_max_ok: bool = True; tau_max_limit: float = 0.0
    sigma_zs: float = 0.0; sigma_zs_ok: bool = True; sigma_zs_limit: float = 0.0
    deflection_q: float = 0.0; deflection_q_ok: bool = True; deflection_limit: float = 0.0
    deflection_g: float = 0.0; deflection_total: float = 0.0
    # 变截面
    sigma_var: float = 0.0; sigma_var_ok: bool = True; sigma_var_limit: float = 0.0
    tau_var: float = 0.0; tau_var_ok: bool = True; tau_var_limit: float = 0.0
    sigma_zs_var: float = 0.0; sigma_zs_var_ok: bool = True; sigma_zs_var_limit: float = 0.0
    # 整体稳定
    overall_stable: bool = True
    # 疲劳
    fatigue_base_ok: bool = True
    fatigue_weld_ok: bool = True
    # 支座加劲肋
    bearing_ce_ok: bool = True
    bearing_stab_ok: bool = True

    def all_ok(self) -> bool:
        checks = [
            self.sigma_mid_ok, self.tau_max_ok, self.sigma_zs_ok,
            self.deflection_q_ok, self.overall_stable,
            self.fatigue_base_ok, self.fatigue_weld_ok,
            self.sigma_var_ok, self.tau_var_ok, self.sigma_zs_var_ok,
            self.bearing_ce_ok, self.bearing_stab_ok,
        ]
        return all(checks)


@dataclass
class CalcResult:
    """完整计算结果"""
    params: DesignParams = field(default_factory=DesignParams)
    section: SectionInput = field(default_factory=SectionInput)
    # 荷载
    g2: float = 0.0
    g1: float = 0.0
    g: float = 0.0
    q_k: float = Q_K
    P_k: float = 0.0
    q: float = 0.0
    P: float = 0.0
    P_s: float = 0.0
    # 弯矩
    M_gk: float = 0.0
    M_qk: float = 0.0
    M_Ed: float = 0.0
    # 剪力
    V_gk: float = 0.0
    V_qk: float = 0.0
    V_Ed: float = 0.0
    # 截面特性
    props_mid: Optional[SectionProps] = None
    props_var: Optional[SectionProps] = None
    # 变截面处内力
    x_cut: float = 0.0           # 变截面位置 (距支座, m)
    M_gk_x: float = 0.0
    M_qk_x: float = 0.0
    M_Ed_x: float = 0.0
    V_Ed_x: float = 0.0
    # 验算
    checks: ChecksResult = field(default_factory=ChecksResult)
    # 子设计
    welds: Optional[WeldDesign] = None
    stiffeners: Optional[StiffenerDesign] = None
    fatigue: Optional[FatigueResult] = None
    # f_d 取值
    f_d_mid: float = 270.0
    f_vd_mid: float = 155.0
    f_d_var: float = 270.0
    f_vd_var: float = 155.0


# ============================================================
# 荷载计算
# ============================================================

def calc_highway_I_Pk(L: float) -> Tuple[float, float]:
    """公路-I级车道荷载 P_k (kN)
    返回 (P_k_for_moment, P_k_for_shear)
    JTG D60-2015 第4.3.1条
    """
    L_clamped = max(5.0, min(L, 50.0))
    if L <= 5.0:
        Pk = 270.0
    elif L >= 50.0:
        Pk = 360.0
    else:
        Pk = 270.0 + (360.0 - 270.0) * (L - 5.0) / (50.0 - 5.0)
    return Pk, Pk * 1.2


def calc_dead_load_2nd(B: float, H1: float, H2: float) -> float:
    """二期恒载 g2 (kN/m)"""
    return GAMMA_C * B * H1 + GAMMA_A * B * H2


def calc_steel_self_weight(A_mm2: float) -> float:
    """钢梁自重 g1 (kN/m), A 单位 mm²"""
    A_m2 = A_mm2 * 1e-6
    return A_m2 * RHO_STEEL


# ============================================================
# 截面特性
# ============================================================

def calc_section_props(h_w: float, t_w: float, b_f: float, t_f: float) -> SectionProps:
    """计算双轴对称工字形截面几何特性 (尺寸单位 mm)
    返回单位: A(mm²), I_x(mm⁴), W_x(mm³), S(mm³), S_f(mm³), h(mm), g1(kN/m)
    """
    h = h_w + 2.0 * t_f
    A = h_w * t_w + 2.0 * b_f * t_f
    # 腹板惯性矩
    I_w = t_w * h_w ** 3 / 12.0
    # 单翼缘对自身形心惯性矩 + 移轴
    d_f = (h_w + t_f) / 2.0  # 翼缘形心到中性轴距离
    I_f = 2.0 * (b_f * t_f ** 3 / 12.0 + b_f * t_f * d_f ** 2)
    I_x = I_w + I_f
    W_x = I_x / (h / 2.0) if h > 0 else 0.0
    # 半截面对中性轴面积矩
    S = b_f * t_f * d_f + t_w * (h_w / 2.0) ** 2 / 2.0
    # 翼缘对中性轴面积矩
    S_f = b_f * t_f * d_f
    # 腹板-翼缘交界距中性轴
    y_j = h_w / 2.0
    g1 = calc_steel_self_weight(A)
    return SectionProps(
        A=A, I_x=I_x, W_x=W_x, S=S, S_f=S_f, h=h,
        h_w=h_w, t_w=t_w, b_f=b_f, t_f=t_f, g1=g1, y_j=y_j
    )


# ============================================================
# 内力计算
# ============================================================

def calc_moment_simply_supported(g: float, q: float, P: float, L: float,
                                  with_concentrated: bool = True) -> float:
    """简支梁跨中弯矩标准值 (kN·m)"""
    M = g * L ** 2 / 8.0  # 均布荷载弯矩
    if with_concentrated:
        M += q * L ** 2 / 8.0 + P * L / 4.0
    return M


def calc_shear_simply_supported(g: float, q: float, P_s: float, L: float,
                                 with_concentrated: bool = True) -> float:
    """简支梁支座剪力标准值 (kN)"""
    V = g * L / 2.0
    if with_concentrated:
        V += q * L / 2.0 + P_s / 2.0
    return V


def calc_moment_udl_at_x(udl: float, L: float, x: float) -> float:
    """简支梁 x 处由均布荷载引起的弯矩标准值 (kN·m)
    udl: 均布荷载 (kN/m), L: 跨径 (m), x: 距支座距离 (m), x ≤ L/2
    """
    return udl * x * (L - x) / 2.0


def calc_moment_conc_at_x(P: float, L: float, x: float) -> float:
    """简支梁 x 处由跨中集中力引起的弯矩标准值 (kN·m)
    P: 集中力 (kN), x ≤ L/2
    """
    return P * x / 2.0


def calc_shear_at_x(g: float, q: float, P_s: float, L: float, x: float) -> float:
    """简支梁 x 处剪力标准值 (kN)
    x 距离支座 (m), 0 < x < L/2
    """
    V_udl = g * (L / 2.0 - x) + q * (L / 2.0 - x)
    V_conc = P_s / 2.0  # 集中力在跨中，x < L/2 时剪力为 P_s/2
    return V_udl + V_conc


def calc_design_value(gamma_0: float, gamma_G: float, gamma_Q: float,
                       mu: float, S_gk: float, S_qk: float) -> float:
    """承载能力极限状态设计值"""
    return gamma_0 * (gamma_G * S_gk + gamma_Q * mu * S_qk)


# ============================================================
# 强度、刚度验算
# ============================================================

def check_bending(M_Ed: float, W_x: float, f_d: float) -> Tuple[float, bool]:
    """抗弯强度验算
    M_Ed: kN·m, W_x: mm³, f_d: MPa
    返回 (σ MPa, ok)
    """
    if W_x <= 0:
        return 0.0, False
    sigma = M_Ed * 1e6 / W_x
    return sigma, sigma <= f_d


def check_shear(V_Ed: float, S: float, I_x: float, t_w: float,
                f_vd: float) -> Tuple[float, bool]:
    """抗剪强度验算
    V_Ed: kN, S: mm³, I_x: mm⁴, t_w: mm, f_vd: MPa
    返回 (τ MPa, ok)
    """
    if I_x <= 0 or t_w <= 0:
        return 0.0, False
    tau = V_Ed * 1e3 * S / (I_x * t_w)
    return tau, tau <= f_vd


def check_combined_stress(M_Ed: float, V_Ed: float, sec: SectionInput,
                           props: SectionProps, f_d: float) -> Tuple[float, float, float, bool]:
    """折算应力验算 (腹板-翼缘交界处)
    返回 (σ_j, τ_j, σ_zs, ok)
    """
    y_j = props.y_j
    sigma_j = M_Ed * 1e6 * y_j / props.I_x if props.I_x > 0 else 0.0
    S_f = props.S_f
    tau_j = V_Ed * 1e3 * S_f / (props.I_x * sec.t_w) if props.I_x > 0 else 0.0
    sigma_zs = math.sqrt(sigma_j ** 2 + 3.0 * tau_j ** 2)
    ok = sigma_zs <= 1.1 * f_d
    return sigma_j, tau_j, sigma_zs, ok


def check_deflection_live(q: float, P: float, L: float, E: float,
                           I_x: float, limit_ratio: float = 500.0) -> Tuple[float, float, bool]:
    """活载挠度验算 (不计冲击系数)
    q: kN/m, P: kN, L: m, E: MPa, I_x: mm⁴
    返回 (δ_q mm, [δ] mm, ok)
    """
    L_mm = L * 1000.0
    q_Nmm = q  # kN/m = N/mm (1 kN/m = 1 N/mm)
    P_N = P * 1000.0  # kN -> N
    delta_u = 5.0 * q_Nmm * L_mm ** 4 / (384.0 * E * I_x)
    delta_c = P_N * L_mm ** 3 / (48.0 * E * I_x)
    delta_q = delta_u + delta_c
    delta_limit = L_mm / limit_ratio
    return delta_q, delta_limit, delta_q <= delta_limit


def check_deflection_dead(g: float, L: float, E: float, I_x: float) -> float:
    """恒载挠度 (mm)"""
    L_mm = L * 1000.0
    g_Nmm = g
    delta_g = 5.0 * g_Nmm * L_mm ** 4 / (384.0 * E * I_x)
    return delta_g


# ============================================================
# 疲劳验算
# ============================================================

def check_fatigue(L: float, q_k: float, P_k_original: float, eta: float,
                   W_x: float) -> FatigueResult:
    """疲劳荷载模型 I (JTG D64-2015 第5.6节及附录C)"""
    q_f = 0.7 * q_k
    P_f = 0.7 * P_k_original
    q_f1 = eta * q_f
    P_f1 = eta * P_f
    M_f = q_f1 * L ** 2 / 8.0 + P_f1 * L / 4.0
    delta_sigma_p = M_f * 1e6 / W_x if W_x > 0 else 0.0

    delta_sigma_D_base = 0.74 * 160.0  # 118.4
    delta_sigma_D_weld = 0.74 * 80.0   # 59.2

    return FatigueResult(
        q_f1=q_f1, P_f1=P_f1, M_f=M_f,
        delta_sigma_p=delta_sigma_p,
        check_base_metal=(delta_sigma_p <= delta_sigma_D_base),
        check_fillet_weld=(delta_sigma_p <= delta_sigma_D_weld),
        delta_sigma_c_base=160.0, delta_sigma_D_base=delta_sigma_D_base,
        delta_sigma_c_weld=80.0, delta_sigma_D_weld=delta_sigma_D_weld,
    )


# ============================================================
# 截面自动估算
# ============================================================

def _round_to(value: float, step: float) -> float:
    """圆整到 step 的倍数"""
    return round(value / step) * step


def auto_estimate_section(L: float, M_Ed0: float, f_d: float,
                           f_vd: float = 155.0,
                           h_w_max: float = 3000.0) -> SectionInput:
    """
    自动估算截面尺寸
    M_Ed0: 不考虑钢梁自重的弯矩设计值 (kN·m)
    返回 SectionInput (mm)
    """
    # 1. 估算所需截面模量 W_req (mm³)
    W_req = M_Ed0 * 1e6 / f_d
    # 2. 经济梁高
    h_e = 7.0 * W_req ** (1.0 / 3.0) - 300.0
    # 3. 刚度要求
    h_min = L * 1000.0 / 15.0
    h_est = max(h_e, h_min)
    h_est = min(h_est, h_w_max)

    # 4. 预估翼缘厚度
    t_f_est = max(16.0, min(40.0, h_est / 30.0))
    t_f_est = _round_to(t_f_est, 2.0)

    # 5. 腹板高度
    h_w_est = h_est - 2.0 * t_f_est
    h_w_est = _round_to(h_w_est, 50.0)
    if h_w_est < 500:
        h_w_est = 500.0

    # 6. 腹板厚度
    t_w_est = max(h_w_est / 170.0, 8.0)
    t_w_est = _round_to(t_w_est, 2.0)
    if t_w_est < 8:
        t_w_est = 8.0

    # 7. 翼缘宽度 (满足整体稳定 b_f ≥ h/5)
    h_total = h_w_est + 2.0 * t_f_est
    b_f_min = max(h_total / 5.0, 200.0)

    # 8. 反算所需翼缘厚度
    # I_req = W_req * h_total / 2
    I_req_est = W_req * h_total / 2.0
    I_w_est = t_w_est * h_w_est ** 3 / 12.0
    I_f_req_est = I_req_est - I_w_est
    if I_f_req_est < 0:
        I_f_req_est = I_req_est * 0.7  # 强制分配

    # 试算 b_f, t_f
    b_f_est = _round_to(b_f_min, 10.0)
    # 由 I_f = 2 * [b_f*t_f^3/12 + b_f*t_f*((h_w+t_f)/2)^2] 迭代求 t_f
    d_f_est = (h_w_est + t_f_est) / 2.0
    # 近似: I_f ≈ 2 * b_f * t_f * d_f^2  (忽略翼缘自身惯性矩)
    t_f_from_I = I_f_req_est / (2.0 * b_f_est * d_f_est ** 2)
    t_f_est = max(t_f_est, t_f_from_I)
    t_f_est = _round_to(t_f_est, 2.0)
    if t_f_est < 10:
        t_f_est = 10.0
    if t_f_est > 60:
        t_f_est = 60.0

    # 9. 变截面段 (约 L/6 处)
    b_f2 = _round_to(max(b_f_est * 0.85, b_f_min * 0.9), 10.0)
    t_f2 = _round_to(max(t_f_est - 6, 10.0), 2.0)

    return SectionInput(
        h_w=h_w_est, t_w=t_w_est,
        b_f=b_f_est, t_f=t_f_est,
        b_f2=b_f2, t_f2=t_f2,
    )


# ============================================================
# 加劲肋设计
# ============================================================

def design_stiffeners(h_w: float, t_w: float, V_Ed: float,
                       L: float, f_d: float, f_ce: float) -> StiffenerDesign:
    """加劲肋设计 (JTG D64-2015 第5.7节)
    h_w, t_w: mm, V_Ed: kN, L: m, f_d/f_ce: MPa
    """
    ratio = h_w / t_w
    result = StiffenerDesign(hw_tw_ratio=ratio)

    if ratio <= 100:
        # 局部稳定自然满足
        result.need_transverse = False
        result.need_longitudinal = False
    elif ratio <= 170:
        result.need_transverse = True
        result.need_longitudinal = False
    else:
        result.need_transverse = True
        result.need_longitudinal = True

    if result.need_transverse:
        a_max = min(2.0 * h_w, 3000.0)
        # 满足 0.5h_w ≤ a ≤ a_max
        a = min(2000.0, a_max)
        if a < 0.5 * h_w:
            a = 0.5 * h_w
        result.spacing = a
        n_span = int((L * 1000.0) / a) + 1
        result.n_pairs = max(n_span - 1, 1)  # 除去支座

        # 构造尺寸
        b_s_min = h_w / 30.0 + 40.0
        b_s = _round_to(max(b_s_min, 80.0), 10.0)
        t_s_min = b_s / 15.0
        t_s = _round_to(max(t_s_min, 6.0), 2.0)
        result.b_s = b_s
        result.t_s = t_s

    # 支座加劲肋
    result.bearing_n = 2
    result.bearing_b = 160.0
    result.bearing_t = 16.0
    # 端面承压
    cut = 20.0  # 切角
    A_ce = result.bearing_n * (result.bearing_b - cut) * result.bearing_t
    if A_ce > 0:
        result.sigma_ce = V_Ed * 1e3 / A_ce
    result.ce_ok = result.sigma_ce <= f_ce

    # 压杆稳定 (十字形截面)
    # 有效截面: 2块加劲肋 + 腹板两侧各15t_w
    web_contrib = 15.0 * t_w
    A_eff = result.bearing_n * result.bearing_b * result.bearing_t + web_contrib * t_w
    # 简化惯性矩: 加劲肋绕腹板平面内
    I_eff = (result.bearing_t * (2.0 * result.bearing_b + t_w) ** 3 / 12.0
             + web_contrib * t_w ** 3 / 12.0)
    i_eff = math.sqrt(I_eff / A_eff) if A_eff > 0 else 1.0
    lam = h_w / i_eff
    # 简化稳定系数 (a类截面)
    if lam <= 30:
        phi = 0.900
    elif lam <= 60:
        phi = 0.900 - (lam - 30) * (0.900 - 0.800) / 30.0
    else:
        phi = 0.700
    if A_eff > 0:
        result.sigma_stab = V_Ed * 1e3 / (phi * A_eff)
    result.stab_ok = result.sigma_stab <= f_d

    return result


# ============================================================
# 焊缝设计
# ============================================================

def design_welds(sec_mid: SectionInput, props_mid: SectionProps,
                  sec_var: SectionInput, props_var: SectionProps,
                  V_Ed: float, V_Ed_x: float,
                  f_ff: float = F_FF_E50) -> WeldDesign:
    """翼缘-腹板连接焊缝设计"""
    w = WeldDesign()

    # --- 等截面段 (支座) ---
    w.S_f1 = props_mid.S_f
    w.v1 = V_Ed * 1e3 * w.S_f1 / props_mid.I_x if props_mid.I_x > 0 else 0.0
    # 双面角焊缝
    w.h_f_req1 = w.v1 / (2.0 * 0.7 * f_ff) if f_ff > 0 else 0.0
    w.h_f_min1 = 1.5 * math.sqrt(sec_mid.t_f)
    w.h_f_max1 = 1.2 * sec_mid.t_w

    # --- 变截面段 ---
    w.S_f2 = props_var.S_f
    w.v2 = V_Ed_x * 1e3 * w.S_f2 / props_var.I_x if props_var.I_x > 0 else 0.0
    w.h_f_req2 = w.v2 / (2.0 * 0.7 * f_ff) if f_ff > 0 else 0.0
    w.h_f_min2 = 1.5 * math.sqrt(sec_var.t_f)
    w.h_f_max2 = 1.2 * sec_var.t_w

    # 选用焊脚尺寸 (取构造最小值的较大者，圆整到1mm)
    h_f_chosen = max(w.h_f_min1, w.h_f_min2)
    h_f_chosen = max(h_f_chosen, w.h_f_req1, w.h_f_req2)
    h_f_chosen = math.ceil(h_f_chosen)
    h_f_max = min(w.h_f_max1, w.h_f_max2)

    if h_f_chosen < 6:
        h_f_chosen = 6.0  # 最小构造
    if h_f_chosen > h_f_max:
        h_f_chosen = h_f_max
    w.h_f_chosen = h_f_chosen

    return w


# ============================================================
# 主计算函数
# ============================================================

def calculate(params: DesignParams, section: Optional[SectionInput] = None) -> CalcResult:
    """执行完整设计计算"""
    result = CalcResult(params=params)

    # --- 1. 荷载计算 ---
    L = params.L
    g2 = calc_dead_load_2nd(params.B, params.H1, params.H2)
    P_k_orig, P_k_shear = calc_highway_I_Pk(L)
    q_live = params.eta * Q_K
    P_live = params.eta * P_k_orig
    P_s_live = params.eta * P_k_shear

    result.g2 = g2
    result.q_k = Q_K
    result.P_k = P_k_orig
    result.q = q_live
    result.P = P_live
    result.P_s = P_s_live

    # --- 2. 截面尺寸 ---
    if section is None:
        # 自动估算 (先用二期恒载初算)
        M_gk2 = g2 * L ** 2 / 8.0
        M_qk0 = q_live * L ** 2 / 8.0 + P_live * L / 4.0
        M_Ed0 = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                                   params.mu_impact, M_gk2, M_qk0)
        f_d_est = get_strength(28.0, params.steel_grade)[0]
        section = auto_estimate_section(L, M_Ed0, f_d_est)
        # 迭代修正 (考虑钢梁自重)
        for _ in range(3):
            props_tmp = calc_section_props(section.h_w, section.t_w, section.b_f, section.t_f)
            g1 = props_tmp.g1
            g = g2 + g1
            M_gk = g * L ** 2 / 8.0
            M_Ed = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                                      params.mu_impact, M_gk, M_qk0)
            section = auto_estimate_section(L, M_Ed, f_d_est)

    result.section = section

    # --- 3. 截面特性 ---
    props_mid = calc_section_props(section.h_w, section.t_w, section.b_f, section.t_f)
    result.props_mid = props_mid
    result.g1 = props_mid.g1
    result.g = g2 + props_mid.g1

    # 变截面参数
    if section.b_f2 <= 0 or section.t_f2 <= 0:
        section.b_f2 = _round_to(max(section.b_f * 0.85, 200.0), 10.0)
        section.t_f2 = _round_to(max(section.t_f - 6, 10.0), 2.0)

    props_var = calc_section_props(section.h_w, section.t_w, section.b_f2, section.t_f2)
    result.props_var = props_var

    # --- 4. 内力计算 ---
    g = result.g
    M_gk = g * L ** 2 / 8.0
    M_qk = q_live * L ** 2 / 8.0 + P_live * L / 4.0
    M_Ed = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                              params.mu_impact, M_gk, M_qk)
    V_gk = g * L / 2.0
    V_qk = q_live * L / 2.0 + P_s_live / 2.0
    V_Ed = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                              params.mu_impact, V_gk, V_qk)

    result.M_gk = M_gk; result.M_qk = M_qk; result.M_Ed = M_Ed
    result.V_gk = V_gk; result.V_qk = V_qk; result.V_Ed = V_Ed

    # 变截面处内力 (L/6)
    x_cut = L / 6.0
    result.x_cut = x_cut
    M_gk_x = calc_moment_udl_at_x(g, L, x_cut)
    M_qk_x = calc_moment_udl_at_x(q_live, L, x_cut) + calc_moment_conc_at_x(P_live, L, x_cut)
    M_Ed_x = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                                params.mu_impact, M_gk_x, M_qk_x)
    V_Ed_x = calc_design_value(params.gamma_0, params.gamma_G, params.gamma_Q,
                                params.mu_impact,
                                g * (L / 2.0 - x_cut),
                                q_live * (L / 2.0 - x_cut) + P_s_live / 2.0)

    result.M_gk_x = M_gk_x; result.M_qk_x = M_qk_x
    result.M_Ed_x = M_Ed_x; result.V_Ed_x = V_Ed_x

    # --- 5. 强度值 ---
    f_d_mid, f_vd_mid, f_ce_mid = get_strength(section.t_f, params.steel_grade)
    f_d_var, f_vd_var, f_ce_var = get_strength(section.t_f2, params.steel_grade)
    result.f_d_mid = f_d_mid; result.f_vd_mid = f_vd_mid
    result.f_d_var = f_d_var; result.f_vd_var = f_vd_var

    # --- 6. 强度验算 ---
    c = result.checks

    sigma_mid, c.sigma_mid_ok = check_bending(M_Ed, props_mid.W_x, f_d_mid)
    c.sigma_mid = sigma_mid
    c.sigma_mid_limit = f_d_mid

    tau_max, c.tau_max_ok = check_shear(V_Ed, props_mid.S, props_mid.I_x,
                                         section.t_w, f_vd_mid)
    c.tau_max = tau_max
    c.tau_max_limit = f_vd_mid

    sigma_j, tau_j, sigma_zs, c.sigma_zs_ok = check_combined_stress(
        M_Ed, V_Ed, section, props_mid, f_d_mid)
    c.sigma_zs = sigma_zs
    c.sigma_zs_limit = 1.1 * f_d_mid

    # 挠度
    delta_q, delta_limit, c.deflection_q_ok = check_deflection_live(
        q_live, P_live, L, E_STEEL, props_mid.I_x)
    c.deflection_q = delta_q
    c.deflection_limit = delta_limit
    c.deflection_g = check_deflection_dead(g, L, E_STEEL, props_mid.I_x)
    c.deflection_total = c.deflection_g + delta_q

    # --- 7. 变截面验算 ---
    sigma_var, c.sigma_var_ok = check_bending(M_Ed_x, props_var.W_x, f_d_var)
    c.sigma_var = sigma_var
    c.sigma_var_limit = f_d_var

    tau_var, c.tau_var_ok = check_shear(V_Ed_x, props_var.S, props_var.I_x,
                                          section.t_w, f_vd_var)
    c.tau_var = tau_var
    c.tau_var_limit = f_vd_var

    tmp_var = SectionInput(h_w=section.h_w, t_w=section.t_w,
                            b_f=section.b_f2, t_f=section.t_f2)
    _, _, sigma_zs_var, c.sigma_zs_var_ok = check_combined_stress(
        M_Ed_x, V_Ed_x, tmp_var, props_var, f_d_var)
    c.sigma_zs_var = sigma_zs_var
    c.sigma_zs_var_limit = 1.1 * f_d_var

    # 整体稳定
    c.overall_stable = True  # 混凝土桥面板提供侧向支撑

    # --- 8. 疲劳验算 ---
    fatigue = check_fatigue(L, Q_K, P_k_orig, params.eta, props_mid.W_x)
    result.fatigue = fatigue
    c.fatigue_base_ok = fatigue.check_base_metal
    c.fatigue_weld_ok = fatigue.check_fillet_weld

    # --- 9. 焊缝设计 ---
    welds = design_welds(section, props_mid, section, props_var, V_Ed, V_Ed_x)
    result.welds = welds

    # --- 10. 加劲肋设计 ---
    stiffeners = design_stiffeners(section.h_w, section.t_w, V_Ed, L, f_d_mid, f_ce_mid)
    result.stiffeners = stiffeners
    c.bearing_ce_ok = stiffeners.ce_ok
    c.bearing_stab_ok = stiffeners.stab_ok

    return result


# ============================================================
# 工具: 生成计算信息文本 (供GUI显示)
# ============================================================

def format_number(v: float, decimals: int = 2) -> str:
    """格式化数值"""
    if abs(v) < 1e-9:
        return "0"
    if abs(v) >= 1e6:
        return f"{v/1e6:.{decimals}f} × 10⁶"
    if abs(v) >= 1e4:
        return f"{v:.1f}"
    return f"{v:.{decimals}f}"


def format_ok(ok: bool) -> str:
    return "满足" if ok else "不满足"
