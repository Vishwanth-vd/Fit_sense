"""FitSense AI - Core Push-up Biomechanics Analyzer.

Analyzes 33-point pose landmark streams frame-by-frame:
- Selects dominant side with higher visibility.
- Applies moving-average coordinate smoothing.
- Extracts per-frame angles and biomechanical features.
- Enforces body orientation gate (<= 35 deg from horizontal).
- Drives the Repetition Finite State Machine with hysteresis.
- Evaluates form flags, baseline calibration, and spoken feedback.
"""

from prototype.baseline import PersonalBaselineTracker
from prototype.config import PushUpConfig
from prototype.math_utils import (
    LandmarkSmoother,
    calculate_angle_3points,
    calculate_line_horizontal_angle,
    calculate_signed_hip_deviation,
)
from prototype.models import (
    DominantSide,
    FormFlag,
    FrameFeatures,
    Landmark,
    Repetition,
    RepState,
)
from prototype.voice_advisor import VoiceAdvisor


class PushUpAnalyzer:
    """Stateful biomechanics push-up analyzer."""

    def __init__(self, config: PushUpConfig | None = None):
        self.config = config or PushUpConfig()
        self.smoother = LandmarkSmoother(window_size=self.config.SMOOTHING_WINDOW_SIZE)
        self.baseline_tracker = PersonalBaselineTracker(config=self.config)
        self.voice_advisor = VoiceAdvisor(config=self.config)

        # FSM State
        self.state: RepState = RepState.UP
        self.rep_count: int = 0
        self.clean_rep_count: int = 0
        self.completed_reps: list[Repetition] = []

        # Current Rep Tracking Accumulators
        self.rep_start_time_s: float | None = None
        self.down_time_s: float | None = None
        self.reached_down: bool = False
        self.min_elbow_angle_in_rep: float = 180.0
        self.rep_frame_features: list[FrameFeatures] = []
        self.out_of_position_start_s: float | None = None

    def reset(self) -> None:
        """Reset the analyzer to initial clean state."""
        self.smoother.reset()
        self.baseline_tracker.reset()
        self.voice_advisor.reset()
        self.state = RepState.UP
        self.rep_count = 0
        self.clean_rep_count = 0
        self.completed_reps.clear()
        self._reset_current_rep()

    def _reset_current_rep(self) -> None:
        """Reset accumulators for the in-progress repetition."""
        self.rep_start_time_s = None
        self.down_time_s = None
        self.reached_down = False
        self.min_elbow_angle_in_rep = 180.0
        self.rep_frame_features.clear()
        self.out_of_position_start_s = None

    def process_frame(
        self,
        landmarks: dict[int, Landmark],
        timestamp_s: float,
    ) -> tuple[FrameFeatures | None, Repetition | None, str | None]:
        """Process a single video frame.

        Args:
            landmarks: Dictionary mapping landmark index to Landmark object.
            timestamp_s: Video frame presentation timestamp in seconds.

        Returns:
            Tuple[Optional[FrameFeatures], Optional[Repetition], Optional[str]]:
                - features: Extracted frame biomechanical features (or None if unresolvable)
                - completed_rep: A Repetition object if a rep completed this frame, else None
                - spoken_cue: Coaching voice cue text if triggered, else None
        """
        # Step 1: Smooth landmarks
        smoothed_lms = self.smoother.smooth(
            landmarks, min_visibility=self.config.MIN_LANDMARK_VISIBILITY
        )

        # Step 2: Determine dominant side
        dominant_side = self._select_dominant_side(smoothed_lms)
        if dominant_side == DominantSide.UNKNOWN:
            self._handle_out_of_position(timestamp_s)
            return None, None, None

        # Resolve landmark indices for chosen side
        if dominant_side == DominantSide.LEFT:
            s_idx = self.config.LEFT_SHOULDER
            e_idx = self.config.LEFT_ELBOW
            w_idx = self.config.LEFT_WRIST
            h_idx = self.config.LEFT_HIP
            a_idx = self.config.LEFT_ANKLE
        else:
            s_idx = self.config.RIGHT_SHOULDER
            e_idx = self.config.RIGHT_ELBOW
            w_idx = self.config.RIGHT_WRIST
            h_idx = self.config.RIGHT_HIP
            a_idx = self.config.RIGHT_ANKLE

        # Check required landmarks exist and meet minimal threshold
        req_indices = [s_idx, e_idx, w_idx, h_idx, a_idx]
        if any(idx not in smoothed_lms for idx in req_indices):
            self._handle_out_of_position(timestamp_s)
            return None, None, None

        shoulder = smoothed_lms[s_idx]
        elbow = smoothed_lms[e_idx]
        wrist = smoothed_lms[w_idx]
        hip = smoothed_lms[h_idx]
        ankle = smoothed_lms[a_idx]

        visibilities = [
            shoulder.visibility,
            elbow.visibility,
            wrist.visibility,
            hip.visibility,
            ankle.visibility,
        ]
        mean_vis = sum(visibilities) / len(visibilities)

        # Step 3: Biomechanical feature calculation
        elbow_angle = calculate_angle_3points(shoulder, elbow, wrist)
        body_line_angle = calculate_angle_3points(shoulder, hip, ankle)
        hip_dev = calculate_signed_hip_deviation(shoulder, hip, ankle)
        horizontal_angle = calculate_line_horizontal_angle(shoulder, ankle)

        # Body orientation gate: shoulder-ankle line within 35 deg of horizontal
        is_in_pushup_pos = horizontal_angle <= self.config.MAX_BODY_HORIZONTAL_ANGLE_DEG

        features = FrameFeatures(
            timestamp_ms=timestamp_s * 1000.0,
            elbow_angle=elbow_angle,
            body_line_angle=body_line_angle,
            hip_deviation=hip_dev,
            body_horizontal_angle=horizontal_angle,
            mean_visibility=mean_vis,
            dominant_side=dominant_side,
            is_in_pushup_position=is_in_pushup_pos,
        )

        if not is_in_pushup_pos:
            self._handle_out_of_position(timestamp_s)
            return features, None, None

        self.out_of_position_start_s = None

        # Step 4: Drive Repetition Finite State Machine
        completed_rep, spoken_cue = self._update_fsm(features, timestamp_s)
        return features, completed_rep, spoken_cue

    def _select_dominant_side(self, landmarks: dict[int, Landmark]) -> DominantSide:
        """Select body side with higher average visibility."""
        left_scores: list[float] = []
        for idx in self.config.LEFT_BODY_LANDMARKS:
            if idx in landmarks:
                left_scores.append(landmarks[idx].visibility)

        right_scores: list[float] = []
        for idx in self.config.RIGHT_BODY_LANDMARKS:
            if idx in landmarks:
                right_scores.append(landmarks[idx].visibility)

        left_avg = sum(left_scores) / len(left_scores) if left_scores else 0.0
        right_avg = sum(right_scores) / len(right_scores) if right_scores else 0.0

        if left_avg < 0.2 and right_avg < 0.2:
            return DominantSide.UNKNOWN

        return DominantSide.LEFT if left_avg >= right_avg else DominantSide.RIGHT

    def _handle_out_of_position(self, timestamp_s: float) -> None:
        """Handle when user leaves push-up position or tracking is lost."""
        if self.state != RepState.UP:
            if self.out_of_position_start_s is None:
                self.out_of_position_start_s = timestamp_s
            elif (timestamp_s - self.out_of_position_start_s) > 1.5:
                # Abandon incomplete rep if out of position for > 1.5s
                self.state = RepState.UP
                self._reset_current_rep()

    def _update_fsm(
        self, features: FrameFeatures, timestamp_s: float
    ) -> tuple[Repetition | None, str | None]:
        """Update finite state machine given current frame features."""
        angle = features.elbow_angle
        completed_rep: Repetition | None = None
        spoken_cue: str | None = None

        if self.state == RepState.UP:
            # Check for initiation of downward motion
            lower_threshold = (
                self.config.ELBOW_ANGLE_UP - self.config.LOWERING_HYSTERESIS_OFFSET
            )
            if angle < lower_threshold:
                self.state = RepState.LOWERING
                self.rep_start_time_s = timestamp_s
                self.rep_frame_features = [features]
                self.reached_down = False
                self.min_elbow_angle_in_rep = angle

        elif self.state == RepState.LOWERING:
            self.rep_frame_features.append(features)
            self.min_elbow_angle_in_rep = min(self.min_elbow_angle_in_rep, angle)

            # Reached bottom of push-up
            if angle <= self.config.ELBOW_ANGLE_DOWN:
                self.state = RepState.DOWN
                self.reached_down = True
                self.down_time_s = timestamp_s

            # Early reversal without reaching full depth (partial rep)
            elif angle > (self.min_elbow_angle_in_rep + 12.0) and angle > 110.0:
                self.state = RepState.RAISING

        elif self.state == RepState.DOWN:
            self.rep_frame_features.append(features)
            self.min_elbow_angle_in_rep = min(self.min_elbow_angle_in_rep, angle)

            # Ascending out of bottom
            raise_threshold = (
                self.config.ELBOW_ANGLE_DOWN + self.config.RAISING_HYSTERESIS_OFFSET
            )
            if angle > raise_threshold:
                self.state = RepState.RAISING

        elif self.state == RepState.RAISING:
            self.rep_frame_features.append(features)
            self.min_elbow_angle_in_rep = min(self.min_elbow_angle_in_rep, angle)

            # Completed return to top lockout position
            if angle >= self.config.ELBOW_ANGLE_UP:
                completed_rep = self._finalize_repetition(timestamp_s)
                self.state = RepState.UP

                if completed_rep:
                    # Update personal baseline
                    alert, _ = self.baseline_tracker.add_repetition(completed_rep)
                    # Voice advisor
                    spoken_cue = self.voice_advisor.get_rep_feedback(
                        completed_rep,
                        current_time_sec=timestamp_s,
                        baseline_alert=alert,
                    )

                self._reset_current_rep()

        return completed_rep, spoken_cue

    def _finalize_repetition(self, end_time_s: float) -> Repetition | None:
        """Aggregate frames and build Repetition object."""
        start_time_s = self.rep_start_time_s or (end_time_s - 1.0)
        duration_s = max(0.01, end_time_s - start_time_s)

        if self.down_time_s and self.reached_down:
            down_duration_s = max(0.01, self.down_time_s - start_time_s)
            up_duration_s = max(0.01, end_time_s - self.down_time_s)
        else:
            down_duration_s = duration_s * 0.5
            up_duration_s = duration_s * 0.5

        tempo = down_duration_s / (up_duration_s + 1e-4)

        if self.rep_frame_features:
            body_line_angles = [f.body_line_angle for f in self.rep_frame_features]
            mean_body_line = sum(body_line_angles) / len(body_line_angles)

            hip_devs = [f.hip_deviation for f in self.rep_frame_features]
            # Extreme deviation: max magnitude signed deviation
            max_hip_dev = max(hip_devs, key=abs) if hip_devs else 0.0

            visibilities = [f.mean_visibility for f in self.rep_frame_features]
            mean_vis = sum(visibilities) / len(visibilities)
        else:
            mean_body_line = 180.0
            max_hip_dev = 0.0
            mean_vis = 1.0

        flags: list[str] = []

        # Rule 6: Low-confidence rule
        low_confidence = mean_vis < self.config.MIN_REP_MEAN_VISIBILITY
        if low_confidence:
            flags.append(FormFlag.LOW_CONFIDENCE.value)

        # Rule 4: Partial-range rep
        if not self.reached_down:
            flags.append(FormFlag.PARTIAL_RANGE.value)

        # Rule 4 & 8: Duration constraint (too fast)
        if duration_s < self.config.MIN_REP_DURATION_SEC:
            flags.append(FormFlag.TOO_FAST.value)

        # Rule 8: Form flags (hip alignment)
        # Check if hip sag occurred during the rep
        if any(
            f.hip_deviation < self.config.HIP_SAG_THRESHOLD
            for f in self.rep_frame_features
        ):
            flags.append(FormFlag.HIPS_SAGGING.value)
        elif any(
            f.hip_deviation > self.config.HIP_PIKE_THRESHOLD
            for f in self.rep_frame_features
        ):
            flags.append(FormFlag.HIPS_PIKED.value)

        # Clean rep only if no error flags
        is_clean = len(flags) == 0

        self.rep_count += 1
        if is_clean:
            self.clean_rep_count += 1

        rep = Repetition(
            n=self.rep_count,
            duration_s=duration_s,
            down_duration_s=down_duration_s,
            up_duration_s=up_duration_s,
            down_up_tempo=tempo,
            min_elbow_angle=self.min_elbow_angle_in_rep,
            mean_body_line_angle=mean_body_line,
            max_hip_deviation=max_hip_dev,
            mean_visibility=mean_vis,
            is_clean=is_clean,
            low_confidence=low_confidence,
            flags=flags,
        )

        self.completed_reps.append(rep)
        return rep
