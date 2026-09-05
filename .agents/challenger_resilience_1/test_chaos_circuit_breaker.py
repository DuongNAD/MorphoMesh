"""
Chaos Test Suite 1: Circuit Breaker FSM & Concurrency Stress Harness
MorphoMesh Phase 2: Resilience & Chaos Challenger
"""

import concurrent.futures
import threading
import time
import unittest
from morphomesh.connectors.base import CircuitBreakerState
from morphomesh.connectors.registry import CircuitBreaker
from morphomesh.models import ERR_BACKEND_UNAVAILABLE, MorphoMeshException


class TestCircuitBreakerChaos(unittest.TestCase):
    """Empirical chaos testing of CircuitBreaker state machine, concurrency, and fallback routing."""

    def test_fsm_lifecycle_deterministic(self):
        """Verify strict FSM transitions: CLOSED -> 3 failures -> OPEN -> timeout -> HALF_OPEN -> CLOSED."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.15)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertTrue(cb.can_attempt())
        self.assertEqual(cb.failure_count, 0)

        # 1st failure
        cb.record_failure(ValueError("Fail 1"))
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 1)

        # 2nd failure
        cb.record_failure(ValueError("Fail 2"))
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 2)

        # 3rd failure -> Trips to OPEN
        cb.record_failure(ValueError("Fail 3"))
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
        self.assertEqual(cb.failure_count, 3)

        # In OPEN state before timeout: rejection of direct execution
        self.assertFalse(cb.can_attempt())
        with self.assertRaises(MorphoMeshException) as ctx:
            cb.call(lambda: "should_not_run")
        self.assertEqual(ctx.exception.code, ERR_BACKEND_UNAVAILABLE)
        self.assertIn("Circuit breaker is OPEN", ctx.exception.message)

        # Fallback invocation when OPEN
        fb_result = cb.call(lambda: "should_not_run", fallback=lambda: "fallback_executed")
        self.assertEqual(fb_result, "fallback_executed")

        # Wait for recovery timeout to elapse
        time.sleep(0.20)

        # Next check transitions to HALF_OPEN
        self.assertTrue(cb.can_attempt())
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        # Successful probe closes breaker back to CLOSED
        cb.record_success()
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)
        self.assertEqual(cb._half_open_attempts, 0)
        self.assertTrue(cb.can_attempt())

    def test_fsm_half_open_failure_retrips(self):
        """Verify probe failure during HALF_OPEN immediately re-trips to OPEN."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.15)
        cb.trip()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        time.sleep(0.20)
        # Probe call transitions to HALF_OPEN
        self.assertTrue(cb.can_attempt())
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        # Probe fails
        cb.record_failure(RuntimeError("Probe failed"))
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
        self.assertFalse(cb.can_attempt())

    def test_concurrent_failure_injection(self):
        """Stress-test concurrent failure injection across 50 threads against CircuitBreaker."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1.0)
        concurrency = 50
        errors_caught = []

        def failing_task(idx: int):
            def faulty_remote():
                raise ConnectionResetError(f"Simulated remote network drop #{idx}")

            def safe_fallback():
                return f"fallback_val_{idx}"

            return cb.call(faulty_remote, fallback=safe_fallback)

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(failing_task, i) for i in range(concurrency)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All 50 calls must successfully return fallback values without unhandled exceptions
        self.assertEqual(len(results), concurrency)
        for i, res in enumerate(results):
            self.assertTrue(res.startswith("fallback_val_"))

        # State must be OPEN
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
        self.assertEqual(cb.total_calls, concurrency)
        self.assertGreaterEqual(cb.failure_count, 5)

    def test_concurrent_half_open_probe_limiting(self):
        """Verify that under concurrent racing threads in HALF_OPEN, only the allowed probe calls proceed."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.15, half_open_max_attempts=1)
        cb.trip()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        # Wait for timeout
        time.sleep(0.20)

        # 40 threads race to call can_attempt()
        thread_count = 40
        results = []
        barrier = threading.Barrier(thread_count)

        def race_probe():
            barrier.wait()  # Synchronize threads for maximal contention
            return cb.can_attempt()

        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(race_probe) for _ in range(thread_count)]
            results = [f.result() for f in futures]

        allowed_count = sum(1 for r in results if r is True)
        rejected_count = sum(1 for r in results if r is False)

        # Exactly 1 thread must be allowed as probe; all 39 others must be rejected
        self.assertEqual(allowed_count, 1, f"Expected exactly 1 allowed probe, got {allowed_count}")
        self.assertEqual(rejected_count, thread_count - 1)
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

    def test_high_contention_chaos_alternating(self):
        """High-throughput multi-threaded torture test: 100 threads alternating operations."""
        cb = CircuitBreaker(failure_threshold=4, recovery_timeout=0.10)
        num_tasks = 200
        lock_exceptions = []

        def worker(idx: int):
            try:
                if idx % 3 == 0:
                    # Successful invocation
                    return cb.call(lambda: f"ok_{idx}", fallback=lambda: f"fallback_{idx}")
                elif idx % 3 == 1:
                    # Failing invocation
                    def fail_fn():
                        raise TimeoutError(f"Chaos timeout {idx}")
                    return cb.call(fail_fn, fallback=lambda: f"fallback_{idx}")
                else:
                    # State probe
                    allowed = cb.can_attempt()
                    if allowed and cb.state == CircuitBreakerState.HALF_OPEN:
                        cb.record_success()
                    return f"probe_{allowed}"
            except Exception as ex:
                lock_exceptions.append(ex)
                return f"exception_{ex}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            futures = [executor.submit(worker, i) for i in range(num_tasks)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(lock_exceptions), 0, f"Thread contention produced exceptions: {lock_exceptions}")
        self.assertEqual(len(results), num_tasks)
        self.assertIn(cb.state, (CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN))
        self.assertGreaterEqual(cb.total_calls, 0)
        self.assertGreaterEqual(cb.failure_count, 0)
        self.assertGreaterEqual(cb.success_count, 0)

    def test_fallback_argument_preservation(self):
        """Verify that fallback call receives identical args and kwargs passed to cb.call."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        cb.trip()

        captured_args = {}

        def fallback_target(*args, **kwargs):
            captured_args["args"] = args
            captured_args["kwargs"] = kwargs
            return "fallback_return_payload"

        res = cb.call(
            lambda *a, **kw: "original",
            "pos1", 42,
            fallback=fallback_target,
            kw1="test_val",
            kw2=999,
        )

        self.assertEqual(res, "fallback_return_payload")
        self.assertEqual(captured_args["args"], ("pos1", 42))
        self.assertEqual(captured_args["kwargs"], {"kw1": "test_val", "kw2": 999})


if __name__ == "__main__":
    unittest.main()
