"""Erros de dominio convertidos em ValidationError do DRF nos serializers."""


class ServiceValidationError(Exception):
    def __init__(self, detail):
        self.detail = detail if isinstance(detail, (dict, list)) else {"detail": str(detail)}


def raise_if_invalid(condition: bool, detail) -> None:
    if not condition:
        raise ServiceValidationError(detail)
