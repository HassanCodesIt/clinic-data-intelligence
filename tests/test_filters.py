from backend.models import PracticeFilter


def test_state_is_normalised():
    assert PracticeFilter(state="vic").state == "VIC"
