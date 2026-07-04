"""Domain exceptions for material catalog operations."""


class MaterialCatalogError(Exception):
    """Base exception for all catalog-related errors."""


class MaterialNotFoundError(MaterialCatalogError):
    """Raised when a material code cannot be resolved to a catalog entry."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Material not found in catalog: '{code}'")


class EdgeNotFoundError(MaterialCatalogError):
    """Raised when an edge banding code cannot be resolved."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Edge banding not found in catalog: '{code}'")


class CatalogUnavailableError(MaterialCatalogError):
    """Raised when the catalog database is not accessible."""

    def __init__(self, path: str, cause: Exception | None = None):
        self.path = path
        self.cause = cause
        super().__init__(f"Catalog unavailable at: '{path}'")
