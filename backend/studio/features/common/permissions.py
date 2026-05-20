"""Re-export legado — prefira importar de studio.permissions."""

from studio.permissions import RoleByActionPermission, get_user_role


__all__ = ["RoleByActionPermission", "get_user_role"]
