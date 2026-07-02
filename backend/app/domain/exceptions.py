class BaseAppException(Exception):

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(" f"message={self.message!r}, details={self.details})"


class DomainException(BaseAppException):
    pass


class PriceNotFoundError(DomainException):

    def __init__(self, price_id: int | None = None, component: str | None = None):
        details = {}
        if price_id:
            details["price_id"] = price_id
        if component:
            details["component"] = component
        super().__init__(message="Price record not found", details=details)


class InvalidPriceError(DomainException):

    def __init__(self, value: float | None, reason: str):
        super().__init__(
            message=f"Invalid price value: {reason}",
            details={"value": value, "reason": reason},
        )


class DuplicatePriceError(DomainException):

    def __init__(self, component: str, source: str):
        super().__init__(
            message=f"Price record already exists for {component} from {source}",
            details={"component": component, "source": source},
        )


class MarketSegmentNotFoundError(DomainException):

    def __init__(self, segment: str):
        super().__init__(
            message=f"Market segment '{segment}' not found",
            details={"segment": segment},
        )


class InfrastructureException(BaseAppException):
    pass


class DatabaseError(InfrastructureException):
    pass


class ScraperError(InfrastructureException):

    def __init__(self, url: str, reason: str, is_retryable: bool = True):
        super().__init__(
            message=f"Scraping failed for {url}: {reason}",
            details={
                "url": url,
                "reason": reason,
                "is_retryable": is_retryable,
            },
        )
        self.is_retryable = is_retryable


class CacheError(InfrastructureException):
    pass


class ApplicationException(BaseAppException):
    pass


class DataProcessingError(ApplicationException):
    pass


class ValidationError(ApplicationException):

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation failed for '{field}': {reason}",
            details={"field": field, "reason": reason},
        )
