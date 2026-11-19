import pytest
from app.core.levels import calculate_progress
@pytest.mark.parametrize("points, level, current_exp, remaining", [(0, 1, 0, 100), (15, 1, 15, 85), (99, 1, 99, 1),
        (100, 2, 0, 100), (175, 2, 75, 25), (250, 3, 50, 50), (500, 6, 0, 100),])
def test_level_calculation(points, level, current_exp, remaining):
    result = calculate_progress(points)
    assert result["current_level"] == level
    assert result["exp_in_level"] == current_exp
    assert result["exp_to_next_level"] == remaining

def test_negative_points():
    with pytest.raises(ValueError):
        calculate_progress(-1)
