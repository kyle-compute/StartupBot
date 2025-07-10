class ELOEngine:
    """Handles ELO calculations and rating updates"""
    
    @staticmethod
    def calculate_expected_score(player_elo: int, opponent_elo: int) -> float:
        """Calculate expected score using ELO formula"""
        return 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    
    @staticmethod
    def calculate_new_elo(current_elo: int, expected_score: float, actual_score: int, k_factor: int) -> int:
        """Calculate new ELO rating"""
        return int(current_elo + k_factor * (actual_score - expected_score))
    
    @staticmethod
    def get_k_factor(total_challenges: int, k_factor_new: int, k_factor_stable: int, stable_threshold: int) -> int:
        """Determine K-factor based on user experience"""
        return k_factor_new if total_challenges < stable_threshold else k_factor_stable 