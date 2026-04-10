"""Custom exception hierarchy for AEDM."""


class AEDMError(Exception):
    """Base exception for all AEDM errors."""


class ValidationError(AEDMError):
    """Raised when input data fails validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        summary = f"{len(errors)} validation error(s): {'; '.join(errors[:3])}"
        if len(errors) > 3:
            summary += f" ... and {len(errors) - 3} more"
        super().__init__(summary)


class MappingError(AEDMError):
    """Raised when a job title cannot be mapped to a SOC code."""

    def __init__(self, title: str) -> None:
        self.title = title
        super().__init__(
            f"Could not map job title '{title}' to a SOC code. "
            "Provide a soc_code column or check the title spelling."
        )


class InsufficientDataError(AEDMError):
    """Raised when there is not enough data for an analysis."""

    def __init__(self, operation: str, required: int, provided: int) -> None:
        self.operation = operation
        self.required = required
        self.provided = provided
        super().__init__(
            f"{operation} requires at least {required} data points, "
            f"but only {provided} were provided."
        )


class ReferenceDataError(AEDMError):
    """Raised when reference data is missing or malformed."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Reference data error: {detail}")
