import os
import requests
from datetime import date

def get_openai_billing():
    api_key = os.environ.get("OPENAI_API_KEY")
    org_id = os.environ.get("OPENAI_API_ORG_ID")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set in environment"}
    headers = {"Authorization": f"Bearer {api_key}"}
    if org_id:
        headers["OpenAI-Organization"] = org_id
    start_date = date.today().replace(day=1).isoformat()
    end_date = date.today().isoformat()
    usage_url = f"https://api.openai.com/v1/dashboard/billing/usage?start_date={start_date}&end_date={end_date}"
    credit_url = "https://api.openai.com/v1/dashboard/billing/credit_grants"
    try:
        usage = requests.get(usage_url, headers=headers, timeout=10).json()
        credit = requests.get(credit_url, headers=headers, timeout=10).json()
        return {
            "gasto_total_usd": usage.get("total_usage", 0) / 100,
            "credito_restante_usd": credit.get("total_available", 0),
            "detalles_uso": usage,
            "detalles_credito": credit
        }
    except Exception as e:
        return {"error": str(e)}