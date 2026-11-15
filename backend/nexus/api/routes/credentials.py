from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ...services import credentials as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_finance import CredentialIn, CredentialOut

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.get("", response_model=list[CredentialOut], summary="Credenziali configurate (mai restituite in chiaro)")
def list_credentials(db: DB, user: CurrentUser):
    return svc.list_credentials(db, user)


@router.put("", response_model=CredentialOut)
def set_credential(data: CredentialIn, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.set_credential(db, user, settings, data)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(provider: str, db: DB, user: CurrentUser) -> None:
    svc.delete_credential(db, user, provider)


class AccountKey(BaseModel):
    service: str = Field(max_length=20)
    key: str = Field(max_length=500)


class AccountConnect(AccountKey):
    model: str = Field(max_length=120)


@router.get("/ai-accounts", summary="Servizi AI collegabili con il proprio account (chiave API)")
def ai_accounts() -> list[dict]:
    from ...services import ai_accounts

    return ai_accounts.catalog()


@router.post("/ai-accounts/models", summary="Modelli disponibili con la chiave indicata (la chiave non viene salvata)")
def ai_account_models(data: AccountKey, user: CurrentUser) -> list[str]:  # noqa: ARG001 - solo utenti autenticati
    from ...services import ai_accounts

    return ai_accounts.list_models(data.service, data.key)


@router.post("/ai-accounts/connect", summary="Collega il proprio account AI e usalo subito")
def ai_account_connect(data: AccountConnect, db: DB, user: CurrentUser, settings: AppSettings) -> dict:
    from ...services import ai_accounts

    return ai_accounts.connect(db, user, settings, data.service, data.key, data.model)
