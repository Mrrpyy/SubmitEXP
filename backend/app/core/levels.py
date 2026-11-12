EXP_PER_LEVEL = 100
def calculate_progress(total_points: int) -> dict[str, int]:
    if total_points < 0:
        raise ValueError("Total EXP cannot be negative")

    current_level = (total_points // EXP_PER_LEVEL) + 1
    exp_in_level = total_points % EXP_PER_LEVEL

    return {
        "current_level": current_level,
        "exp_in_level": exp_in_level,
        "exp_for_next_level": EXP_PER_LEVEL,
        "exp_to_next_level": EXP_PER_LEVEL - exp_in_level,
        "progress_percent": (
            exp_in_level * 100 // EXP_PER_LEVEL
        ),
    }
