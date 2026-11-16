"""Schemi API — Economic Laboratory (Fase 6). Limiti espliciti su ogni parametro."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .schemas import ORMModel, UTCDateTime

Rate = Field(ge=-0.5, le=2.0)


class Titled(BaseModel):
    """Ogni simulazione può avere un titolo scelto dall'utente (altrimenti quello predefinito del modello)."""

    title: str | None = Field(default=None, max_length=300)


class GBMIn(Titled):
    s0: float = Field(gt=0, le=1e12)
    mu: float = Field(ge=-1, le=1)
    sigma: float = Field(ge=0, le=3)
    years: float = Field(gt=0, le=50)
    steps_per_year: int = Field(default=12, ge=1, le=252)
    n_paths: int = Field(default=2000, ge=100, le=20000)
    seed: int = Field(default=42, ge=0, le=2**31)
    threshold: float | None = None


class BootstrapIn(Titled):
    series_id: int
    years: float = Field(gt=0, le=30)
    n_paths: int = Field(default=2000, ge=100, le=10000)
    block: int = Field(default=6, ge=1, le=60)
    seed: int = Field(default=42, ge=0, le=2**31)


class CrisisIn(BaseModel):
    start: int = Field(ge=1, le=100)
    years: int = Field(ge=1, le=20)
    g_shock: float = Field(default=0.0, ge=-0.5, le=0.5)
    r_shock: float = Field(default=0.0, ge=-0.2, le=0.5)
    pb_shock: float = Field(default=0.0, ge=-30, le=30)


class StochasticIn(BaseModel):
    n_paths: int = Field(default=2000, ge=100, le=10000)
    sd_r: float = Field(default=0.01, ge=0, le=0.2)
    sd_g: float = Field(default=0.02, ge=0, le=0.3)
    corr: float = Field(default=0.0, ge=-1, le=1)


class DebtIn(Titled):
    d0: float = Field(ge=0, le=1000, description="Debito iniziale, % PIL")
    r_eff0: float = Rate
    r_market: float = Rate
    avg_maturity: float = Field(default=7.0, gt=0, le=50)
    g: float = Rate
    pb: float = Field(default=0.0, ge=-30, le=30, description="Saldo primario, % PIL")
    years: int = Field(default=10, ge=1, le=100)
    rate_shock: float = Field(default=0.0, ge=-0.2, le=0.5)
    shock_start: int = Field(default=1, ge=1, le=100)
    crisis: CrisisIn | None = None
    stochastic: StochasticIn | None = None
    seed: int = Field(default=42, ge=0, le=2**31)
    counterfactual: bool = False


class SensitivityIn(Titled):
    base: DebtIn
    ranges: dict[Literal["d0", "r_eff0", "r_market", "avg_maturity", "g", "pb"], tuple[float, float]] = Field(min_length=1)


class InflationIn(Titled):
    amount: float = Field(gt=0, le=1e12)
    nominal_rate: float = Rate
    years: int = Field(ge=1, le=100)
    inflation_levels: list[float] = Field(min_length=1, max_length=8)


class TaylorRuleIn(BaseModel):
    name: str = Field(max_length=60)
    a: float = Field(ge=-3, le=5)
    b: float = Field(ge=-3, le=5)
    floor: float | None = Field(default=None, ge=-0.1, le=0.2)


class TaylorIn(Titled):
    labels: list[str] = Field(min_length=1, max_length=400)
    inflation: list[float] = Field(min_length=1, max_length=400)
    output_gap: list[float] = Field(min_length=1, max_length=400)
    actual_rate: list[float] | None = None
    rules: list[TaylorRuleIn] = Field(min_length=1, max_length=6)
    r_star: float = Field(default=0.02, ge=-0.05, le=0.1)
    pi_target: float = Field(default=0.02, ge=-0.05, le=0.2)


class RegressionIn(Titled):
    y_series_id: int
    x_series_ids: list[int] = Field(min_length=1, max_length=5)
    transform: Literal["levels", "diff", "pct"] = "diff"
    lags: int = Field(default=0, ge=0, le=12)
    target_frequency: Literal["D", "W", "M", "Q", "A"] | None = None
    method: Literal["last", "mean", "sum"] = "mean"


class BacktestIn(Titled):
    series_id: int
    strategy: Literal["buy_hold", "ma_cross", "momentum"]
    fast: int = Field(default=10, ge=1, le=500)
    slow: int = Field(default=50, ge=2, le=1000)
    lookback: int = Field(default=12, ge=1, le=500)
    cost_bps: float = Field(default=10, ge=0, le=500)
    rf: float = Field(default=0.0, ge=-0.05, le=0.3)


class ScenarioIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    growth: float = Field(ge=-0.5, le=1.0, description="Crescita annua composta (0.03 = +3% l'anno)")


class ScenariosIn(Titled):
    """Proiezione di una serie (o di un valore di partenza) sotto più ipotesi di crescita."""

    series_id: int | None = None
    base_value: float | None = Field(default=None, gt=0, le=1e15)
    base_year: int | None = Field(default=None, ge=1000, le=2200)
    unit: str = Field(default="", max_length=60)
    horizon: int = Field(default=25, ge=1, le=100)
    scenarios: list[ScenarioIn] = Field(min_length=1, max_length=6)
    uncertainty: float = Field(default=0.0, ge=0, le=0.5, description="Deviazione standard annua della crescita: banda al 90%")
    history_years: int = Field(default=10, ge=2, le=100, description="Anni per la crescita storica di riferimento")
    # Serie non annuali: come passare ad anni (obbligatorio, nessuna scelta implicita).
    aggregation: Literal["mean", "sum", "last"] | None = None
    # Genera da solo base, ottimistico e pessimistico: base = crescita storica della serie (o il primo scenario), ± spread.
    three_scenarios: bool = False
    spread: float = Field(default=0.01, gt=0, le=0.2)


class SectorIn(Titled):
    """Base comune dei modelli settoriali: orizzonte, unità e scenari alternativi (parametri che cambiano)."""

    years: int = Field(ge=1, le=100)
    unit: str = Field(default="", max_length=60)
    optimistic: dict[str, float] = Field(default_factory=dict, max_length=12)
    pessimistic: dict[str, float] = Field(default_factory=dict, max_length=12)

    def base_params(self) -> dict:
        return self.model_dump(exclude={"title", "unit", "optimistic", "pessimistic"})


Share = Field(ge=-1, le=1)


class IndustrialIn(SectorIn):
    ip0: float = Field(gt=0, le=1e9, description="Indice di partenza (es. 100)")
    trend_growth: float = Share
    demand_growth: float = Share
    demand_elasticity: float = Field(ge=0, le=5)
    energy_price_change: float = Field(ge=-1, le=5, description="Variazione annua del prezzo dell'energia (0.1 = +10%)")
    energy_elasticity: float = Field(ge=0, le=2)
    capacity_ratio: float = Field(ge=1, le=3, description="Capacità iniziale / produzione iniziale (1.2 = utilizzo all'83%)")
    capacity_growth: float = Share


class EmploymentIn(SectorIn):
    labour_force0: float = Field(gt=0, le=1e10)
    u0: float = Field(ge=0.01, le=0.6, description="Tasso di disoccupazione iniziale (0.07 = 7%)")
    gdp_growth: float = Share
    potential_growth: float = Share
    okun_beta: float = Field(ge=0, le=2)
    labour_force_growth: float = Field(ge=-0.2, le=0.2)


class TradeIn(SectorIn):
    exports0: float = Field(gt=0, le=1e15)
    imports0: float = Field(gt=0, le=1e15)
    gdp0: float = Field(gt=0, le=1e16)
    world_growth: float = Share
    domestic_growth: float = Share
    income_elasticity_exports: float = Field(ge=0, le=5)
    income_elasticity_imports: float = Field(ge=0, le=5)
    price_elasticity_exports: float = Field(ge=0, le=5)
    price_elasticity_imports: float = Field(ge=0, le=5)
    reer_change: float = Field(ge=-0.5, le=0.5, description="Variazione annua del cambio reale (+ = apprezzamento)")


class ConsumptionIn(SectorIn):
    income0: float = Field(gt=0, le=1e16)
    income_growth: float = Share
    tax_rate: float = Field(ge=0, le=0.9)
    mpc: float = Field(ge=0, le=1.2, description="Propensione marginale al consumo")
    autonomous: float = Field(ge=0, le=1e16)
    wealth0: float = Field(ge=0, le=1e17)
    wealth_effect: float = Field(ge=0, le=0.2)
    wealth_growth: float = Share


class SimulationRename(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class SimulationOut(ORMModel):
    id: int
    kind: str
    title: str
    params: dict
    result: dict
    counterfactual: bool
    created_at: UTCDateTime


class SimulationSummary(ORMModel):
    id: int
    kind: str
    title: str
    counterfactual: bool
    created_at: UTCDateTime
