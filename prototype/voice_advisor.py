"""FitSense AI - Spoken Voice Feedback & Rate Limiting Engine.

Generates concise athletic coaching cues based on detected form flags
and personal baseline alerts. Strictly rate-limited to at most one cue
every 5 seconds.
"""

from prototype.config import PushUpConfig
from prototype.models import FormFlag, Repetition


class VoiceAdvisor:
    """Manages audio coaching cues with strict cooldown rate-limiting."""

    CUE_MESSAGES = {
        FormFlag.PARTIAL_RANGE.value: "Go a little lower",
        FormFlag.HIPS_SAGGING.value: "Keep your hips up",
        FormFlag.HIPS_PIKED.value: "Lower your hips",
        FormFlag.TOO_FAST.value: "Slow down your pace",
    }

    # Word representations for clean rep counts
    NUMBER_WORDS = [
        "Zero",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
        "Fifteen",
        "Sixteen",
        "Seventeen",
        "Eighteen",
        "Nineteen",
        "Twenty",
    ]

    def __init__(self, config: PushUpConfig | None = None):
        self.config = config or PushUpConfig()
        self.last_spoken_time_sec = -999.0

    def reset(self) -> None:
        """Reset advisor timing state."""
        self.last_spoken_time_sec = -999.0

    def get_rep_feedback(
        self,
        rep: Repetition,
        current_time_sec: float,
        baseline_alert: bool = False,
    ) -> str | None:
        """Determine spoken feedback for a completed repetition.

        Returns:
            Optional[str]: Audio cue text, or None if rate-limited or low confidence.
        """
        # Low confidence reps get no form feedback
        if rep.low_confidence:
            return None

        # Check rate limit cooldown (5 seconds)
        if (
            current_time_sec - self.last_spoken_time_sec
        ) < self.config.VOICE_CUE_COOLDOWN_SEC:
            return None

        # Prioritize form error cues over rep count
        for flag in [
            FormFlag.PARTIAL_RANGE.value,
            FormFlag.HIPS_SAGGING.value,
            FormFlag.HIPS_PIKED.value,
            FormFlag.TOO_FAST.value,
        ]:
            if flag in rep.flags:
                cue = self.CUE_MESSAGES.get(flag)
                if cue:
                    self.last_spoken_time_sec = current_time_sec
                    return cue

        if baseline_alert:
            self.last_spoken_time_sec = current_time_sec
            return "Focus on your baseline form"

        # If clean rep, speak rep count
        if rep.is_clean:
            self.last_spoken_time_sec = current_time_sec
            if 0 <= rep.n < len(self.NUMBER_WORDS):
                return self.NUMBER_WORDS[rep.n]
            return f"Rep {rep.n}"

        return None
