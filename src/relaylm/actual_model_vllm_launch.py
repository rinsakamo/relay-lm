from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VLLMLaunchMemoryAdmission:
    """One fresh GPU-memory admission shared by profiler and final vLLM launch."""

    free_bytes: int
    total_bytes: int

    def __post_init__(self) -> None:
        _require_int(self.free_bytes, "free_bytes")
        _require_int(self.total_bytes, "total_bytes")
        if self.free_bytes <= 0:
            raise ValueError("free_bytes must be positive")
        if self.total_bytes <= 0:
            raise ValueError("total_bytes must be positive")
        if self.free_bytes > self.total_bytes:
            raise ValueError("free_bytes must not exceed total_bytes")
        utilization_millis = self._utilization_millis
        if utilization_millis <= 0 or utilization_millis >= 1000:
            raise ValueError(
                "fresh GPU bytes must resolve a utilization strictly between 0.000 and 1.000"
            )

    @classmethod
    def from_fresh_bytes(
        cls,
        *,
        free_bytes: int,
        total_bytes: int,
    ) -> VLLMLaunchMemoryAdmission:
        return cls(free_bytes=free_bytes, total_bytes=total_bytes)

    @property
    def _utilization_millis(self) -> int:
        return (self.free_bytes * 1000) // self.total_bytes

    @property
    def gpu_memory_utilization(self) -> str:
        """Exact three-decimal startup admission derived by downward quantization."""

        return f"0.{self._utilization_millis:03d}"

    def profiler_memory_args(self) -> tuple[str, ...]:
        return (
            "--gpu-memory-utilization",
            self.gpu_memory_utilization,
            "--max-model-len",
            "auto",
        )

    def final_memory_args(self, *, kv_cache_memory_bytes: int) -> tuple[str, ...]:
        _require_int(kv_cache_memory_bytes, "kv_cache_memory_bytes")
        if kv_cache_memory_bytes <= 0:
            raise ValueError("kv_cache_memory_bytes must be positive")
        return (
            "--gpu-memory-utilization",
            self.gpu_memory_utilization,
            "--kv-cache-memory-bytes",
            str(kv_cache_memory_bytes),
            "--max-model-len",
            "auto",
        )


def _require_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
