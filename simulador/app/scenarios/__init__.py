"""Catálogo de escenarios disponibles en el simulador."""
from app.scenarios.base import Scenario
from app.scenarios.black_friday import BlackFridayScenario
from app.scenarios.failover import FailoverScenario
from app.scenarios.flash_sale import FlashSaleScenario


def all_scenarios() -> dict[str, Scenario]:
    scenarios = [BlackFridayScenario(), FlashSaleScenario(), FailoverScenario()]
    return {s.key: s for s in scenarios}
