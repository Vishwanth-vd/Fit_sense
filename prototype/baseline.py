"""FitSense AI - Personal Baseline Calibration & Anomaly Detection.

Calibrates dynamic personal baseline from the first 5 non-low-confidence
reps of a session. Evaluates subsequent reps using z-scores and triggers
deviation alerts only when |z| > 2 on 3 consecutive reps.
"""

from prototype.config import PushUpConfig
from prototype.models import BaselineMetricStats, Repetition, UserBaseline


class PersonalBaselineTracker:
    """Tracks and evaluates personal baseline metrics across repetitions."""

    TRACKED_METRICS = [
        "min_elbow_angle",
        "duration_s",
        "mean_body_line_angle",
        "max_hip_deviation",
        "down_up_tempo",
    ]

    def __init__(self, config: PushUpConfig | None = None):
        self.config = config or PushUpConfig()
        self.calibration_reps: list[Repetition] = []
        self.baseline = UserBaseline(exercise_type="pushup")
        self.consecutive_anomalies = 0

    def reset(self) -> None:
        """Reset baseline state for a new workout session."""
        self.calibration_reps.clear()
        self.baseline = UserBaseline(exercise_type="pushup")
        self.consecutive_anomalies = 0

    @property
    def is_calibrated(self) -> bool:
        """Whether the baseline has accumulated enough calibration reps."""
        return self.baseline.is_calibrated

    def add_repetition(self, rep: Repetition) -> tuple[bool, dict[str, float]]:
        """Process a completed repetition.

        Returns:
            Tuple[bool, Dict[str, float]]:
                - alert_triggered: True if |z| > 2 on 3 consecutive reps
                - z_scores: dict mapping metric name to calculated z-score (empty if not calibrated)
        """
        # Low confidence reps are excluded from baseline and feedback
        if rep.low_confidence:
            return False, {}

        # Accumulate calibration reps if not yet calibrated
        if not self.baseline.is_calibrated:
            self.calibration_reps.append(rep)
            if len(self.calibration_reps) >= self.config.BASELINE_CALIBRATION_REPS:
                self._compute_baseline()
            return False, {}

        # Evaluate against calibrated baseline
        z_scores: dict[str, float] = {}
        has_large_deviation = False

        for metric in self.TRACKED_METRICS:
            val = getattr(rep, metric, None)
            if val is not None and metric in self.baseline.feature_stats:
                stats = self.baseline.feature_stats[metric]
                z = (val - stats.mean) / (stats.std + self.config.BASELINE_EPSILON)
                z_scores[metric] = z
                if abs(z) > self.config.Z_SCORE_DEVIATION_THRESHOLD:
                    has_large_deviation = True

        if has_large_deviation:
            self.consecutive_anomalies += 1
        else:
            self.consecutive_anomalies = 0

        self.baseline.consecutive_anomalies = self.consecutive_anomalies

        alert_triggered = (
            self.consecutive_anomalies >= self.config.CONSECUTIVE_ANOMALIES_TO_ALERT
        )
        return alert_triggered, z_scores

    def _compute_baseline(self) -> None:
        """Compute mean and standard deviation for each metric over calibration reps."""
        n = len(self.calibration_reps)
        if n == 0:
            return

        feature_stats: dict[str, BaselineMetricStats] = {}

        for metric in self.TRACKED_METRICS:
            values = [
                getattr(rep, metric)
                for rep in self.calibration_reps
                if hasattr(rep, metric)
            ]
            if not values:
                continue

            mean_val = sum(values) / len(values)
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            std_val = variance**0.5

            feature_stats[metric] = BaselineMetricStats(mean=mean_val, std=std_val)

        self.baseline.is_calibrated = True
        self.baseline.calibration_reps_count = n
        self.baseline.feature_stats = feature_stats
