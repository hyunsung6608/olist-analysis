"""판매자 불만율 베타-이항 경험적 베이지안 보정과 관리 대상 판매자 선정 (Q4 노트북과 같은 기준)."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import betabinom

MIN_ORDERS = 30        # 순위·관리 대상에 넣는 최소 주문 수
WATCH_MULTIPLIER = 1.5  # 보정 불만율이 전체 평균의 몇 배 이상이면 관리 대상인지


def fit_beta_binomial(k: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """판매자별 (불만 수 k, 주문 수 n)로 베타-이항 사전분포 Beta(α, β)를 최대우도로 추정한다."""
    def nll(log_params):
        a, b = np.exp(log_params)
        return -betabinom.logpmf(k, n, a, b).sum()
    m = k.sum() / n.sum()
    res = minimize(nll, x0=np.log([m * 20, (1 - m) * 20]), method="Nelder-Mead",
                   options={"maxiter": 2000, "xatol": 1e-6, "fatol": 1e-6})
    return tuple(np.exp(res.x))


def score_sellers(sellers: pd.DataFrame, k_col: str, n_col: str = "n_orders", prefix: str = "") -> tuple[pd.DataFrame, tuple[float, float]]:
    """보정 전 비율(<prefix>raw)과 보정 후 비율(<prefix>adj) 컬럼을 추가하고 사전분포 (α, β)를 돌려준다."""
    k, n = sellers[k_col].to_numpy(float), sellers[n_col].to_numpy(float)
    a, b = fit_beta_binomial(k, n)
    out = sellers.copy()
    out[f"{prefix}raw"] = k / n
    out[f"{prefix}adj"] = (k + a) / (n + a + b)
    return out, (a, b)


def watch_list_mask(sellers: pd.DataFrame, k_col: str, adj_col: str, n_col: str = "n_orders") -> pd.Series:
    """관리 대상: 주문 MIN_ORDERS건 이상이고 보정 불만율이 전체 평균의 WATCH_MULTIPLIER배 이상."""
    overall = sellers[k_col].sum() / sellers[n_col].sum()
    return (sellers[n_col] >= MIN_ORDERS) & (sellers[adj_col] >= overall * WATCH_MULTIPLIER)
