"""
MorphoMesh: Connector Registry and Circuit Breaker Fault Tolerance Engine.

Provides the central registry for open-source AI connectors with lifecycle
management, health diagnostics, dependency audits, and resilient execution.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union

from morphomesh.connectors.base import (
    BaseConnector,
    CircuitBreakerState,
    DependencyCheckResult,
    HealthCheckResult,
)
from morphomesh.models import (
    ERR_BACKEND_UNAVAILABLE,
    ERR_INVALID_ARGUMENT,
    MorphoMeshException,
)

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Three-state Circuit Breaker pattern implementation.
    
    States:
      - CLOSED: Normal operation; failures are counted.
      - OPEN: Failures exceeded threshold; calls fail fast or route to fallback.
      - HALF_OPEN: Recovery timeout elapsed; permits probe call to test service recovery.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_attempts: int = 1,
    ) -> None:
        self.failure_threshold: int = max(1, failure_threshold)
        self.recovery_timeout: float = max(0.1, recovery_timeout)
        self.half_open_max_attempts: int = max(1, half_open_max_attempts)

        self.state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.total_calls: int = 0
        self.last_failure_time: float = 0.0
        self.last_success_time: float = 0.0
        self._half_open_attempts: int = 0
        self._lock: threading.Lock = threading.Lock()

    def can_attempt(self) -> bool:
        """
        Evaluate whether an execution attempt is allowed under current state.
        
        Returns:
            bool: True if call should proceed, False if blocked by OPEN state.
        """
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True

            if self.state == CircuitBreakerState.OPEN:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self._half_open_attempts = 1
                    logger.info(
                        "CircuitBreaker transitioned to HALF_OPEN after %.2fs timeout.",
                        elapsed,
                    )
                    return True
                return False

            if self.state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_attempts < self.half_open_max_attempts:
                    self._half_open_attempts += 1
                    return True
                return False

            return False

    def record_success(self) -> None:
        """Record successful invocation, closing breaker and resetting failure counts."""
        with self._lock:
            self.success_count += 1
            self.failure_count = 0
            self._half_open_attempts = 0
            self.last_success_time = time.time()
            if self.state != CircuitBreakerState.CLOSED:
                logger.info("CircuitBreaker successfully closed following healthy probe.")
                self.state = CircuitBreakerState.CLOSED

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """
        Record failed invocation, incrementing counters and tripping breaker if threshold reached.
        """
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitBreakerState.HALF_OPEN:
                logger.warning(
                    "CircuitBreaker probe failed in HALF_OPEN. Re-tripping to OPEN. Error: %s",
                    error,
                )
                self.state = CircuitBreakerState.OPEN
            elif self.failure_count >= self.failure_threshold:
                logger.warning(
                    "CircuitBreaker tripped to OPEN after %d consecutive failures. Error: %s",
                    self.failure_count,
                    error,
                )
                self.state = CircuitBreakerState.OPEN

    def trip(self) -> None:
        """Force breaker into OPEN state."""
        with self._lock:
            self.state = CircuitBreakerState.OPEN
            self.last_failure_time = time.time()

    def reset(self) -> None:
        """Force breaker into CLOSED state and clear failure counters."""
        with self._lock:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self._half_open_attempts = 0

    def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        fallback: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute callable protected by the circuit breaker with fallback routing.
        
        Args:
            func: Target callable to execute.
            *args: Positional arguments for func.
            fallback: Optional fallback callable if breaker is OPEN or call fails.
            **kwargs: Keyword arguments for func.
            
        Returns:
            Any: Result of func or fallback.
            
        Raises:
            MorphoMeshException: When call fails and no fallback is supplied.
        """
        with self._lock:
            self.total_calls += 1

        if not self.can_attempt():
            if fallback is not None:
                logger.warning("CircuitBreaker is OPEN: routing immediately to fallback.")
                return fallback(*args, **kwargs)
            raise MorphoMeshException(
                code=ERR_BACKEND_UNAVAILABLE,
                message="Circuit breaker is OPEN. Target connector backend unavailable.",
                details={
                    "state": self.state.value,
                    "failure_count": self.failure_count,
                    "recovery_timeout_remaining": max(
                        0.0, self.recovery_timeout - (time.time() - self.last_failure_time)
                    ),
                },
            )

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            if fallback is not None:
                logger.warning(
                    "Connector execution failed (%s): invoking fallback handler.",
                    exc,
                )
                return fallback(*args, **kwargs)
            raise


class ConnectorRegistry:
    """
    Thread-safe central registry for MorphoMesh connectors.
    
    Provides dynamic discovery, singleton instantiation, health auditing,
    and resilient execution with fallback routing.
    """

    _registry: Dict[str, Type[BaseConnector]] = {}
    _instances: Dict[str, BaseConnector] = {}
    _lock: threading.RLock = threading.RLock()
    _auto_registered: bool = False

    @classmethod
    def _ensure_auto_registered(cls) -> None:
        """Lazily import and register canonical Phase 2 connectors."""
        if cls._auto_registered:
            return

        with cls._lock:
            if cls._auto_registered:
                return

            try:
                from morphomesh.connectors.trellis_connector import TrellisConnector
                cls._registry[TrellisConnector.connector_id] = TrellisConnector
            except ImportError as e:
                logger.debug("TrellisConnector auto-registration deferred: %s", e)

            try:
                from morphomesh.connectors.animals3d_connector import Animals3DConnector
                cls._registry[Animals3DConnector.connector_id] = Animals3DConnector
            except ImportError as e:
                logger.debug("Animals3DConnector auto-registration deferred: %s", e)

            try:
                from morphomesh.connectors.anycreature_connector import AnyCreatureConnector
                cls._registry[AnyCreatureConnector.connector_id] = AnyCreatureConnector
            except ImportError as e:
                logger.debug("AnyCreatureConnector auto-registration deferred: %s", e)

            try:
                from morphomesh.connectors.meshanything_connector import MeshAnythingConnector
                cls._registry[MeshAnythingConnector.connector_id] = MeshAnythingConnector
            except ImportError as e:
                logger.debug("MeshAnythingConnector auto-registration deferred: %s", e)

            try:
                from morphomesh.connectors.hunyuan_connector import HunyuanConnector
                cls._registry[HunyuanConnector.connector_id] = HunyuanConnector
            except ImportError as e:
                logger.debug("HunyuanConnector auto-registration deferred: %s", e)

            cls._auto_registered = True

    @classmethod
    def register(
        cls, connector: Union[Type[BaseConnector], BaseConnector]
    ) -> Union[Type[BaseConnector], BaseConnector]:
        """
        Register a connector class or instance in the registry.
        
        Args:
            connector: BaseConnector class or instance.
            
        Returns:
            The registered class or instance.
        """
        with cls._lock:
            cls._ensure_auto_registered()
            if isinstance(connector, type) and issubclass(connector, BaseConnector):
                cid = connector.connector_id
                cls._registry[cid] = connector
            elif isinstance(connector, BaseConnector):
                cid = connector.connector_id
                cls._registry[cid] = type(connector)
                cls._instances[cid] = connector
            else:
                raise TypeError(f"Expected BaseConnector subclass or instance, got {type(connector)}")
            return connector

    @classmethod
    def get(cls, connector_id: str, auto_initialize: bool = True) -> BaseConnector:
        """
        Retrieve or lazily instantiate a singleton connector instance.
        
        Args:
            connector_id: Unique string identifier for connector.
            auto_initialize: Whether to call initialize() on instantiation.
            
        Returns:
            BaseConnector: Connector singleton instance.
            
        Raises:
            MorphoMeshException: When connector_id is not registered.
        """
        with cls._lock:
            cls._ensure_auto_registered()
            if connector_id not in cls._instances:
                if connector_id not in cls._registry:
                    raise MorphoMeshException(
                        code=ERR_INVALID_ARGUMENT,
                        message=(
                            f"Connector '{connector_id}' is not registered. "
                            f"Available connectors: {sorted(list(cls._registry.keys()))}"
                        ),
                        details={"requested": connector_id, "available": list(cls._registry.keys())},
                    )
                connector_cls = cls._registry[connector_id]
                breaker = CircuitBreaker()
                instance = connector_cls(circuit_breaker=breaker)
                if auto_initialize:
                    instance.initialize()
                cls._instances[connector_id] = instance
            return cls._instances[connector_id]

    @classmethod
    def get_all(cls) -> Dict[str, BaseConnector]:
        """
        Retrieve all registered connectors as instantiated singletons.
        
        Returns:
            Dict[str, BaseConnector]: Map of connector IDs to instances.
        """
        with cls._lock:
            cls._ensure_auto_registered()
            result: Dict[str, BaseConnector] = {}
            for cid in cls.list_connectors():
                result[cid] = cls.get(cid, auto_initialize=False)
            return result

    @classmethod
    def list_connectors(cls) -> List[str]:
        """
        List all registered connector IDs.
        
        Returns:
            List[str]: Alphabetical list of registered connector IDs.
        """
        with cls._lock:
            cls._ensure_auto_registered()
            return sorted(list(cls._registry.keys()))

    @classmethod
    def health_check_all(cls) -> Dict[str, HealthCheckResult]:
        """
        Perform health check diagnostics across all registered connectors.
        
        Returns:
            Dict[str, HealthCheckResult]: Connector ID to diagnostic result mapping.
        """
        with cls._lock:
            cls._ensure_auto_registered()
            results: Dict[str, HealthCheckResult] = {}
            for cid in cls.list_connectors():
                try:
                    inst = cls.get(cid, auto_initialize=False)
                    results[cid] = inst.health_check()
                except Exception as e:
                    results[cid] = HealthCheckResult(
                        status="unhealthy",
                        message=f"Health probe error: {e}",
                        details={"error": str(e)},
                    )
            return results

    @classmethod
    def check_dependencies_all(cls) -> Dict[str, DependencyCheckResult]:
        """
        Inspect dependencies across all registered connectors.
        
        Returns:
            Dict[str, DependencyCheckResult]: Connector ID to dependency result mapping.
        """
        with cls._lock:
            cls._ensure_auto_registered()
            results: Dict[str, DependencyCheckResult] = {}
            for cid in cls.list_connectors():
                try:
                    inst = cls.get(cid, auto_initialize=False)
                    results[cid] = inst.check_dependencies()
                except Exception as e:
                    results[cid] = DependencyCheckResult(
                        satisfied=False,
                        details={"error": str(e)},
                    )
            return results

    @classmethod
    def execute_with_fallback(
        cls,
        primary_name: str,
        fallback_fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute request on primary connector with resilient fallback.
        
        Args:
            primary_name: ID of primary connector.
            fallback_fn: Fallback callable to execute if primary fails or trips.
            *args: Arguments for connector execute.
            **kwargs: Keyword arguments for connector execute.
            
        Returns:
            Any: Result of primary execution or fallback.
        """
        with cls._lock:
            cls._ensure_auto_registered()
        
        try:
            connector = cls.get(primary_name, auto_initialize=True)
            if connector.circuit_breaker is not None:
                return connector.circuit_breaker.call(
                    connector.execute,
                    *args,
                    fallback=fallback_fn,
                    **kwargs,
                )
            return connector.execute(*args, **kwargs)
        except Exception as e:
            logger.warning(
                "Primary connector '%s' execution failed (%s). Executing fallback.",
                primary_name,
                e,
            )
            return fallback_fn(*args, **kwargs)

    @classmethod
    def reset_all(cls) -> None:
        """Close and discard all active connector instances (useful for isolated tests)."""
        with cls._lock:
            for inst in cls._instances.values():
                try:
                    inst.close()
                except Exception as e:
                    logger.debug("Error closing connector %s: %s", inst.connector_id, e)
            cls._instances.clear()


def get_connector_registry() -> Type[ConnectorRegistry]:
    """Return the central ConnectorRegistry class."""
    return ConnectorRegistry
