from app.models.evidence import ConfidenceLevel


class ConfidenceEngine:
    """
    Deterministic scoring engine that computes normalized confidence scores (0.0 to 1.0)
    and assigns standard categorical confidence levels (HIGH, MEDIUM, LOW).
    """

    @staticmethod
    def calculate_score(
        base_score: float,
        boosts: float = 0.0,
        penalties: float = 0.0,
        min_score: float = 0.10,
        max_score: float = 0.95,
    ) -> float:
        """
        Compute a bounded deterministic confidence score. Never returns 1.0 to prevent claiming absolute omniscience.
        """
        raw = base_score + boosts - penalties
        return round(max(min_score, min(max_score, raw)), 2)

    @staticmethod
    def get_level(score: float) -> str:
        """
        Maps numeric confidence to categorical rating.
        """
        if score >= 0.80:
            return ConfidenceLevel.HIGH.value
        elif score >= 0.50:
            return ConfidenceLevel.MEDIUM.value
        else:
            return ConfidenceLevel.LOW.value
