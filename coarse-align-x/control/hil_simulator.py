"""
HORIZON Hardware-in-the-Loop Stochastic Latency Jitter & Packet Loss Simulator
==============================================================================
Simulates physical transport delay jitter tau ~ N(mean, std^2) and Bernoulli
packet drops for testing gimbal control under realistic communication channels.
"""

from __future__ import annotations

import collections
import random
from typing import Deque, Optional, Tuple


class HILLatencySimulator:
    """Stochastic transport delay jitter & packet loss simulator for HIL command streams."""

    def __init__(
        self,
        mean_latency_s: float = 0.02,
        std_latency_s: float = 0.005,
        packet_loss_prob: float = 0.02,
        seed: int = 42,
    ) -> None:
        self.mean_latency = mean_latency_s
        self.std_latency = std_latency_s
        self.packet_loss_prob = packet_loss_prob
        self.rng = random.Random(seed)

        # Buffer: Tuple[deliver_time_s, command_tuple]
        self._queue: Deque[Tuple[float, Tuple[float, float]]] = collections.deque()

    def send_command(self, pan_rate: float, tilt_rate: float, current_time_s: float) -> None:
        """Enqueue rate command with stochastic latency delay."""
        if self.rng.random() < self.packet_loss_prob:
            return  # Packet dropped

        delay = max(0.001, self.rng.gauss(self.mean_latency, self.std_latency))
        deliver_t = current_time_s + delay
        self._queue.append((deliver_t, (float(pan_rate), float(tilt_rate))))

    def receive_command(self, current_time_s: float) -> Optional[Tuple[float, float]]:
        """Retrieve most recent delivered rate command at current_time_s."""
        latest_cmd: Optional[Tuple[float, float]] = None
        while self._queue and self._queue[0][0] <= current_time_s:
            _, cmd = self._queue.popleft()
            latest_cmd = cmd

        return latest_cmd
