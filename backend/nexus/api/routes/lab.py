from fastapi import APIRouter, status

from ...services import lab as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_lab import (
    BacktestIn, BootstrapIn, ConsumptionIn, DebtIn, EmploymentIn, GBMIn, IndustrialIn, InflationIn, RegressionIn, ScenariosIn, SensitivityIn,
    SimulationOut, SimulationRename, SimulationSummary, TaylorIn, TradeIn,
)

router = APIRouter(prefix="/lab", tags=["economic-lab"])


def _route(kind: str, model, summary: str):
    def handler(data: model, db: DB, user: CurrentUser, settings: AppSettings):  # type: ignore[valid-type]
        return svc.run(db, user, kind, data, settings)

    router.add_api_route(f"/simulations/{kind}", handler, methods=["POST"], response_model=SimulationOut,
                         status_code=status.HTTP_201_CREATED, summary=summary, name=f"run_{kind}")


_route("monte_carlo", GBMIn, "Monte Carlo (moto browniano geometrico)")
_route("monte_carlo_bootstrap", BootstrapIn, "Monte Carlo bootstrap su rendimenti storici di una serie")
_route("debt", DebtIn, "Dinamica del debito pubblico, shock sui tassi, crisi, incertezza")
_route("sensitivity", SensitivityIn, "Sensitività one-at-a-time del debito")
_route("inflation", InflationIn, "Scenari di inflazione")
_route("monetary_policy", TaylorIn, "Confronto tra regole di politica monetaria")
_route("regression", RegressionIn, "Regressione OLS tra serie")
_route("backtest", BacktestIn, "Backtest senza look-ahead")
_route("scenarios", ScenariosIn, "Proiezione di una serie sotto più scenari di crescita")
_route("industrial_production", IndustrialIn, "Produzione industriale: domanda, energia, capacità (base, ottimistico, pessimistico)")
_route("employment", EmploymentIn, "Occupazione con la legge di Okun (base, ottimistico, pessimistico)")
_route("trade", TradeIn, "Commercio internazionale: elasticità al reddito e al cambio (base, ottimistico, pessimistico)")
_route("consumption", ConsumptionIn, "Consumi delle famiglie: reddito disponibile e ricchezza (base, ottimistico, pessimistico)")


@router.get("/limits", summary="Limiti dei calcoli del laboratorio (configurabili dal server)")
def limits(settings: AppSettings) -> dict:
    return {"max_paths": settings.lab_max_paths, "max_years": settings.lab_max_years, "max_cells": settings.lab_max_cells,
            "block_cells": settings.lab_block_cells, "fan_points": settings.lab_fan_points}


@router.get("/simulations", response_model=list[SimulationSummary])
def list_simulations(db: DB, user: CurrentUser, kind: str | None = None):
    return svc.list_runs(db, user, kind)


@router.get("/simulations/{sim_id}", response_model=SimulationOut)
def get_simulation(sim_id: int, db: DB, user: CurrentUser):
    return svc.get(db, user, sim_id)


@router.delete("/simulations/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_simulation(sim_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete(db, user, sim_id, confirm)


@router.patch("/simulations/{sim_id}", response_model=SimulationOut)
def rename_simulation(sim_id: int, data: SimulationRename, db: DB, user: CurrentUser):
    return svc.rename(db, user, sim_id, data.title)
