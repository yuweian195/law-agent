from app.tools.compensation import _compensation_years, calculate_compensation
from app.tools.question_parser import extract_facts


def test_compensation_years_rounding():
    assert _compensation_years(3, 2) == 3.5
    assert _compensation_years(2, 5) == 2.5
    assert _compensation_years(3, 6) == 4.0
    assert _compensation_years(1, 0) == 1.0


def test_illegal_dismissal_compensation():
    facts = extract_facts("公司违法解除劳动合同，我工作3年2个月，月薪2万")
    result = calculate_compensation(facts)

    assert result is not None
    assert result.applies is True
    assert result.amount == 140000
    assert result.years == 3.5


def test_mutual_termination_compensation():
    facts = extract_facts("工作2年5个月，月薪15000，协商解除")
    result = calculate_compensation(facts)

    assert result is not None
    assert result.amount == 37500
    assert "经济补偿" in result.formula


def test_missing_salary_returns_none():
    facts = extract_facts("公司违法解除劳动合同，我工作了3年")
    assert calculate_compensation(facts) is None
