"""
MorphoMesh: Base Connector Contract & Foundational Data Models.

Defines the abstract interface and Pydantic v2 schemas for all external
generative, parametric, and retopology connectors in MorphoMesh Phase 2.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class CircuitBreakerState(str, Enum):
    """Three-state finite state machine for connector fault tolerance."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class ConnectorStatus(str, Enum):
    """Operational health status classifications."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class PBRTextureMaps(BaseModel):
    """Decoupled 4-channel Physically Based Rendering (PBR) texture maps."""
    model_config = ConfigDict(extra="ignore")

    albedo_path: Optional[str] = Field(default=None, description="Path to BaseColor/Albedo sRGB texture map")
    normal_path: Optional[str] = Field(default=None, description="Path to Tangent-Space OpenGL Normal texture map")
    roughness_path: Optional[str] = Field(default=None, description="Path to Linear Roughness Non-Color texture map")
    metallic_path: Optional[str] = Field(default=None, description="Path to Linear Metallic Non-Color texture map")
    resolution: int = Field(default=2048, ge=256, le=8192, description="Texture pixel resolution (square)")
    color_space_map: Dict[str, str] = Field(
        default_factory=lambda: {
            "albedo": "sRGB",
            "normal": "Non-Color",
            "roughness": "Non-Color",
            "metallic": "Non-Color",
        },
        description="Blender Principled BSDF color space assignments",
    )

    def to_dict(self) -> Dict[str, str]:
        """Return non-empty texture map paths as a key-value dictionary."""
        res: Dict[str, str] = {}
        if self.albedo_path:
            res["albedo"] = self.albedo_path
        if self.normal_path:
            res["normal"] = self.normal_path
        if self.roughness_path:
            res["roughness"] = self.roughness_path
        if self.metallic_path:
            res["metallic"] = self.metallic_path
        return res


class HealthCheckResult(BaseModel):
    """Health check diagnostic payload for a connector instance."""
    model_config = ConfigDict(extra="ignore")

    status: Literal["healthy", "degraded", "unhealthy", "offline", "unknown"] = "healthy"
    latency_ms: float = 0.0
    last_checked: float = Field(default_factory=time.time)
    message: str = "Operating normally"
    details: Dict[str, Any] = Field(default_factory=dict)
    circuit_state: str = "CLOSED"
    dependencies_met: bool = True


# Canonical alias for architectural compatibility
HealthStatus = HealthCheckResult


class DependencyCheckResult(BaseModel):
    """Dependency inspection status covering packages, binaries, and hardware."""
    model_config = ConfigDict(extra="ignore")

    satisfied: bool = True
    missing_packages: List[str] = Field(default_factory=list)
    missing_binaries: List[str] = Field(default_factory=list)
    hardware_supported: bool = True
    vram_available_mb: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


# Canonical alias for architectural compatibility
DependencyStatus = DependencyCheckResult


class BaseConnector(ABC):
    """
    Authoritative abstract base class for all MorphoMesh Phase 2 external adapters.
    
    Subclasses manage lifecycle hooks, dependency auditing, health probes, and execution.
    """

    connector_id: str = "base"
    display_name: str = "Base Connector"
    version: str = "1.0.0"
    stage: int = 2
    description: str = ""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        circuit_breaker: Optional[Any] = None,
    ) -> None:
        self.config: Dict[str, Any] = config or {}
        self.circuit_breaker: Optional[Any] = circuit_breaker
        self.is_initialized: bool = False
        self._fallback_handler: Optional[Callable[..., Any]] = None

    @abstractmethod
    def initialize(self) -> bool:
        """
        Allocate resources, verify configuration or endpoints, or warm caches.
        
        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """
        Query connector endpoint, evaluate latency, or test local availability.
        
        Returns:
            HealthCheckResult: Diagnostic assessment.
        """
        pass

    @abstractmethod
    def check_dependencies(self) -> DependencyCheckResult:
        """
        Inspect Python packages, native binaries, and hardware accelerator support.
        
        Returns:
            DependencyCheckResult: Satisfaction report.
        """
        pass

    @abstractmethod
    def execute(self, request: Any, **kwargs: Any) -> Any:
        """
        Execute primary connector workload.
        
        Args:
            request: Typed request model or parameter payload.
            **kwargs: Additional runtime arguments.
            
        Returns:
            Any: Typed output payload.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Release allocated handles, sockets, sessions, or temporary files."""
        pass

    def is_available(self) -> bool:
        """Boolean convenience check for connector operational readiness."""
        try:
            health = self.health_check()
            return health.status in ("healthy", "degraded")
        except Exception:
            return False

    def register_fallback(self, handler: Callable[..., Any]) -> None:
        """
        Register a fallback callable to invoke if execution fails or circuit trips.
        
        Args:
            handler: Callable taking same arguments as execute.
        """
        self._fallback_handler = handler

    def execute_with_resilience(self, request: Any, **kwargs: Any) -> Any:
        """
        Execute primary workload guarded by the circuit breaker and registered fallback.
        
        Args:
            request: Workload input request.
            **kwargs: Extra execution arguments.
            
        Returns:
            Any: Output from execute or fallback.
        """
        if self.circuit_breaker is not None and hasattr(self.circuit_breaker, "call"):
            return self.circuit_breaker.call(
                self.execute,
                request,
                fallback=self._fallback_handler,
                **kwargs,
            )
        try:
            return self.execute(request, **kwargs)
        except Exception:
            if self._fallback_handler is not None:
                return self._fallback_handler(request, **kwargs)
            raise
