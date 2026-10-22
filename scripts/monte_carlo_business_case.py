"""
Monte Carlo cho Business Case - Lop kiem chung AI ho so boi thuong xe (K = 10%).

Don vi tien: dong (VND). Chay: python3 monte_carlo_business_case.py [--N 20000] [--iters 10000]
Moi tham so bat dinh duoc khai bao trong PARAMS (phan phoi + tham so + can cu).
Tham so quyet dinh (K, K_SIU, n, r) co dinh, khong lay mau.
"""
import argparse, json
import numpy as np
from scipy import stats, optimize

USD_VND = 26_300          # The Investor (2025): Vietcombank ban ra 26.310
LOAD = 1.215              # luong + 21,5% BHXH/BHYT/BHTN phia doanh nghiep (Thu Hang, 2026)

# ---------- Tham so quyet dinh (co dinh) ----------
DECISION = dict(
    N=20_000,        # ho so/nam qua kenh tu xa (kich ban co so)
    K=0.10,          # ty le ho so GDV xem ky (hang doi)
    K_SIU=0.01,      # trong K: 1% chuyen SIU, 9% yeu cau bo sung
    years=3, r=0.10, # NPV 3 nam, chiet khau 10%
    ramp_y1=0.75,    # nam 1: 3 thang chay song song (Chuong 4) -> 9/12 thang tao gia tri
)

# ---------- Tham so bat dinh: phan phoi dau vao ----------
PARAMS = {
  # Ty le ho so nhom B
  "p":        {"dist": "beta", "a": 21.32, "b": 269.42},          # P5=5%, P95=10%, mean 7,3%
  # Recall@10% tren frozen test (n_B = 49), posterior Jeffreys
  "rec_test_ai":   {"dist": "beta", "a": 11.5, "b": 38.5},         # XGBoost 11/49 = 22,4%
  "rec_test_rule": {"dist": "beta", "a": 8.5,  "b": 41.5},         # luat cung 8/49 = 16,3%
  # Ton that fraud tranh duoc
  "L_bar":    {"dist": "lognormal", "median": 20e6, "sigma": 0.75}, # P5 5,8tr; P95 68,7tr; mean 26,5tr
  "eta":      {"dist": "beta", "a": 9.22, "b": 5.94},              # ty le chi sai thuc su chan duoc, P5 40% P95 80%
  # Chi phi xem lai thu cong (yeu cau bo sung)
  "c_bs":     {"dist": "uniform", "low": 60e3, "high": 200e3},
  # Chi phi chuyen SIU
  "c_SIU":    {"dist": "uniform", "low": 1.5e6, "high": 6.0e6},
  # Chi phi false hold = c_CSKH + dq * V_KH
  "c_CSKH":   {"dist": "uniform", "low": 20e3, "high": 60e3},
  "dq":       {"dist": "beta", "a": 4.27, "b": 48.48},             # tang xac suat roi bo, P5 3% P95 15%
  "V_KH":     {"dist": "uniform", "low": 4e6, "high": 12e6},
  # Chi phi van hanh AI
  "AI_infra": {"dist": "uniform", "low": 1*0.736*8760*USD_VND, "high": 2*0.736*8760*USD_VND},  # 1-2 GPU T4
  "AI_staff": {"dist": "uniform", "low": 0.5*37.75e6*LOAD*12, "high": 1.0*37.75e6*LOAD*12},  # 0,5-1 FTE
  "AI_misc":  {"dist": "uniform", "low": 50e6, "high": 150e6},
  "c_AI_var": {"dist": "uniform", "low": 2e3, "high": 10e3},       # luu tru, bang thong, log / ho so
  "rule_cost":{"dist": "uniform", "low": 30e6, "high": 100e6},     # duy tri bo luat cung / nam
  # Dau tu ban dau
  "C0":       {"dist": "uniform", "low": 1.2e9, "high": 2.0e9},
}

def draw(spec, n, rng):
    d = spec["dist"]
    if d == "beta":      return rng.beta(spec["a"], spec["b"], n)
    if d == "uniform":   return rng.uniform(spec["low"], spec["high"], n)
    if d == "lognormal": return rng.lognormal(np.log(spec["median"]), spec["sigma"], n)
    raise ValueError(d)

# --- Chuyen Recall@K tu tap test (p_test = 24,5%) sang ty le p cua kenh that ---
# Gia dinh binormal phuong sai bang nhau: diem nhom B ~ N(d,1), nhom A ~ N(0,1).
P_TEST, K_TEST = 49/200, 0.10
def _recall(d, p, K):
    t = optimize.brentq(lambda t: p*stats.norm.sf(t-d) + (1-p)*stats.norm.sf(t) - K, -12, 12)
    return stats.norm.sf(t - d)
_D_GRID = np.linspace(0.0, 4.0, 401)
_R_TEST = np.array([_recall(d, P_TEST, K_TEST) for d in _D_GRID])
def d_from_test_recall(r):
    return np.interp(np.clip(r, _R_TEST[0], _R_TEST[-1]), _R_TEST, _D_GRID)
def recall_at(d, p, K):
    return np.array([_recall(di, pi, K) for di, pi in zip(np.atleast_1d(d), np.atleast_1d(p))])

# Recall AI va luat cung do tren CUNG 49 ho so nhom B -> sai so tuong quan.
# Gaussian copula rho = 0,5 (thay bang paired bootstrap tren du doan frozen test khi co).
RHO_RECALL = 0.5

def simulate(iters=10_000, seed=2026, overrides=None, dec=None):
    dec = {**DECISION, **(dec or {})}
    rng = np.random.default_rng(seed)
    S = {k: draw(v, iters, rng) for k, v in PARAMS.items()}
    z = rng.multivariate_normal([0, 0], [[1, RHO_RECALL], [RHO_RECALL, 1]], iters)
    u = stats.norm.cdf(z)
    for j, k in enumerate(["rec_test_ai", "rec_test_rule"]):
        S[k] = stats.beta(PARAMS[k]["a"], PARAMS[k]["b"]).ppf(u[:, j])
    for k, v in (overrides or {}).items(): S[k] = np.full(iters, v)
    N, K, Ks = dec["N"], dec["K"], dec["K_SIU"]
    p = S["p"]
    R_ai   = S.get("R_ai")   if "R_ai"   in (overrides or {}) else recall_at(d_from_test_recall(S["rec_test_ai"]), p, K)
    R_rule = S.get("R_rule") if "R_rule" in (overrides or {}) else recall_at(d_from_test_recall(S["rec_test_rule"]), p, K)
    Q, n_SIU = N*K, N*Ks; n_bs = Q - n_SIU
    c_FH = S["c_CSKH"] + S["dq"]*S["V_KH"]
    review = n_bs*S["c_bs"] + n_SIU*S["c_SIU"]
    def nv(R, system_cost):
        TP = N*p*R; FP = Q - TP
        prevented = TP*S["eta"]*S["L_bar"]
        return dict(TP=TP, FP=FP, prevented=prevented, review=review, fh=FP*c_FH,
                    system=system_cost, NV=prevented - review - FP*c_FH - system_cost,
                    precision=R*p/K, false_hold=FP/(N*(1-p)))
    ai_sys = S["AI_infra"] + S["AI_staff"] + S["AI_misc"] + N*S["c_AI_var"]
    A = nv(R_ai, ai_sys); B = nv(R_rule, S["rule_cost"])
    # Dong tien tang them so voi luat cung (review cost nhu nhau -> triet tieu)
    d_benefit = (A["prevented"] - B["prevented"]) + (B["fh"] - A["fh"])   # loi ich tang them / nam
    d_cost = A["system"] - B["system"]                                      # chi phi tang them / nam
    r, n = dec["r"], dec["years"]
    disc = np.array([(1+r)**-t for t in range(1, n+1)])
    ramp = np.array([dec["ramp_y1"]] + [1.0]*(n-1))
    flows = np.outer(d_benefit, ramp) - np.outer(d_cost, np.ones(n))      # iters x n
    pv_flows = flows*disc
    NPV = -S["C0"] + pv_flows.sum(1)
    pv_benefit = (np.outer(d_benefit, ramp)*disc).sum(1)
    pv_cost = S["C0"] + (np.outer(d_cost, np.ones(n))*disc).sum(1)
    ROI = (pv_benefit - pv_cost)/pv_cost
    cum = -S["C0"][:, None] + np.cumsum(pv_flows, 1)
    DPP = np.full(iters, np.inf)
    for i in range(iters):
        k = np.argmax(cum[i] >= 0) if (cum[i] >= 0).any() else -1
        if k >= 0:
            prev = -S["C0"][i] if k == 0 else cum[i, k-1]
            DPP[i] = k + (-prev)/pv_flows[i, k]
    # Precision hoa von (phu luc Net Value): Precision* = (c_review + c_FH + c_AI/K)/(L_eff + c_FH)
    c_review = (n_bs*S["c_bs"] + n_SIU*S["c_SIU"])/Q
    prec_star = (c_review + c_FH + (ai_sys/N)/K)/(S["eta"]*S["L_bar"] + c_FH)
    return dict(S=S, p=p, R_ai=R_ai, R_rule=R_rule, A=A, B=B, dNV=A["NV"]-B["NV"], flows=flows,
                NPV=NPV, ROI=ROI, DPP=DPP, prec_star=prec_star, c_FH=c_FH, ai_sys=ai_sys)

def q(x, ps=(5, 50, 95)): return [float(np.percentile(x, p_)) for p_ in ps]

def summary(res):
    A, B = res["A"], res["B"]
    out = {
      "p": q(res["p"]), "Recall_AI": q(res["R_ai"]), "Recall_rule": q(res["R_rule"]),
      "Precision_AI": q(A["precision"]), "FalseHold_AI": q(A["false_hold"]), "FalseHold_rule": q(B["false_hold"]),
      "c_FH": q(res["c_FH"]), "AI_system_cost": q(res["ai_sys"]),
      "prevented_AI": q(A["prevented"]), "review": q(A["review"]), "fh_AI": q(A["fh"]),
      "NV_AI": q(A["NV"]), "NV_rule": q(B["NV"]), "dNV": q(res["dNV"]),
      "NPV_inc": q(res["NPV"]), "ROI_inc": q(res["ROI"]),
      "DPP_median_if_finite": float(np.median(res["DPP"][np.isfinite(res["DPP"])])) if np.isfinite(res["DPP"]).any() else None,
      "Prec_star": q(res["prec_star"]),
      "P(NV_AI>0)": float((A["NV"] > 0).mean()), "P(dNV>0)": float((res["dNV"] > 0).mean()),
      "P(NPV_inc>0)": float((res["NPV"] > 0).mean()), "P(DPP<=3)": float((res["DPP"] <= 3).mean()),
      "P(Precision>Prec*)": float((A["precision"] > res["prec_star"]).mean()),
      "mean_NPV_inc": float(res["NPV"].mean()), "mean_dNV": float(res["dNV"].mean()), "mean_NV_AI": float(A["NV"].mean()),
    }
    return out

def irr_of_median(res):
    f = np.median(res["flows"], 0); c0 = np.median(res["S"]["C0"])
    g = lambda r: -c0 + sum(f[t]/(1+r)**(t+1) for t in range(len(f)))
    try: return optimize.brentq(g, -0.99, 10)
    except ValueError: return float("nan")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--N", type=int, default=20000); ap.add_argument("--iters", type=int, default=10000)
    a = ap.parse_args()
    res = simulate(a.iters, dec={"N": a.N})
    s = summary(res); s["IRR_median_flows"] = irr_of_median(res)
    print(json.dumps(s, indent=1, ensure_ascii=False))
