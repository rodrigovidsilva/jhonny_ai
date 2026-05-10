from __future__ import annotations

from pathlib import Path

from src.agent import RetailAgent
from src.business_tools import RetailBusinessTools
from src.llm_client import DatabricksLLMClient, LLMNotConfiguredError, OpenAILLMClient
from src.odoo_client import OdooClient, OdooConfig, load_env


def create_agent(root: Path | None = None) -> RetailAgent:
    project_root = root or Path(__file__).resolve().parents[1]
    load_env(project_root / ".env")
    client = OdooClient(OdooConfig.from_env())
    client.authenticate()
    try:
        llm = OpenAILLMClient.from_env()
    except LLMNotConfiguredError:
        try:
            llm = DatabricksLLMClient.from_env()
        except LLMNotConfiguredError:
            llm = None
    return RetailAgent(RetailBusinessTools(client), llm=llm)
