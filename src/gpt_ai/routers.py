from fastapi import APIRouter
from .services import get_openai_billing

router = APIRouter(prefix="/gpt_ai", tags=["gpt_ai"])

@router.get("/billing", summary="Consulta el billing de OpenAI", deprecated=True)
def billing():
    """Devuelve el gasto y crédito restante de la cuenta de OpenAI."""
    return get_openai_billing()

