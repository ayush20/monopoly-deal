"""Game-rule validation errors safe to surface as rejected player actions."""


class GameRuleError(ValueError):
    """Raised when a requested state transition is not legal."""
