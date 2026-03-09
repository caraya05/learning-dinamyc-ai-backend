"""
Excepciones personalizadas para el módulo de analytics.

Este módulo define excepciones específicas del dominio que permiten
un manejo de errores más granular y semanticamente correcto.
"""


class AnalyticsException(Exception):
    """Excepción base para todas las excepciones de analytics."""
    pass


class AnalyticNotFoundError(AnalyticsException):
    """Se lanza cuando no se encuentra un registro de analítica."""
    def __init__(self, identifier: str, identifier_type: str = "session_id"):
        self.identifier = identifier
        self.identifier_type = identifier_type
        super().__init__(
            f"Registro de analítica no encontrado: {identifier_type}={identifier}"
        )


class InvalidAnalyticDataError(AnalyticsException):
    """Se lanza cuando los datos de analítica son inválidos."""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Datos inválidos en campo '{field}': {message}")


class InvalidProgressError(InvalidAnalyticDataError):
    """Se lanza cuando el valor de progreso está fuera del rango permitido."""
    def __init__(self, value: int):
        super().__init__(
            "progress",
            f"El progreso debe estar entre 1 y 3, recibido: {value}"
        )


class InvalidScoreError(InvalidAnalyticDataError):
    """Se lanza cuando la puntuación es negativa."""
    def __init__(self, value: int):
        super().__init__(
            "score",
            f"La puntuación no puede ser negativa, recibido: {value}"
        )


class InvalidDurationError(InvalidAnalyticDataError):
    """Se lanza cuando la duración es negativa."""
    def __init__(self, value: int):
        super().__init__(
            "duration",
            f"La duración no puede ser negativa, recibido: {value}"
        )


class InvalidViewsError(InvalidAnalyticDataError):
    """Se lanza cuando la cantidad de vistas es negativa."""
    def __init__(self, value: int):
        super().__init__(
            "views",
            f"Las vistas no pueden ser negativas, recibido: {value}"
        )


class InvalidLikesError(InvalidAnalyticDataError):
    """Se lanza cuando la cantidad de likes es negativa."""
    def __init__(self, value: int):
        super().__init__(
            "likes",
            f"Los likes no pueden ser negativos, recibido: {value}"
        )


class InvalidPlaysError(InvalidAnalyticDataError):
    """Se lanza cuando la cantidad de plays es negativa."""
    def __init__(self, value: int):
        super().__init__(
            "plays",
            f"Los plays no pueden ser negativos, recibido: {value}"
        )


class UnauthorizedAnalyticAccessError(AnalyticsException):
    """Se lanza cuando un usuario intenta acceder a analíticas que no le pertenecen."""
    def __init__(self, user_id: str, analytic_id: str):
        self.user_id = user_id
        self.analytic_id = analytic_id
        super().__init__(
            f"Acceso denegado: el usuario {user_id} no puede acceder a la analítica {analytic_id}"
        )


class DatabaseError(AnalyticsException):
    """Se lanza cuando hay un error en la base de datos."""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(
            f"Error en operación de BD '{operation}': {message}"
        )

