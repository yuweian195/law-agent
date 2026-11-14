import json
from pathlib import Path

from app.tools.contract_parser import parse_contract
from app.tools.risk_rules import overall_risk, risk_score, scan_contract

ROOT = Path(__file__).resolve().parents[1]


def test_parse_contract_splits_clauses(contract_text):
    parsed = parse_contract(contract_text("labor_contract_risky.txt"))

    assert parsed.title == "劳动合同"
    assert len(parsed.parties) == 2
    assert len(parsed.clauses) == 9
    assert parsed.clauses[0].title.startswith("第一条")
    assert "试用期" in parsed.clauses[1].text


def test_risky_labor_contract_hits_expected_rules(contract_text):
    parsed = parse_contract(contract_text("labor_contract_risky.txt"))
    findings = scan_contract(parsed, "labor")
    rule_ids = {finding.rule_id for finding in findings}

    expected = {
        "probation_limit",
        "probation_salary",
        "service_period_penalty",
        "non_compete_compensation",
        "social_insurance",
        "overtime_pay",
        "unilateral_termination",
        "unilateral_change",
        "final_interpretation",
    }
    assert expected <= rule_ids
    assert overall_risk(findings).value == "high"
    assert risk_score(findings) >= 90


def test_clean_labor_contract_has_no_findings(contract_text):
    parsed = parse_contract(contract_text("labor_contract_clean.txt"))
    findings = scan_contract(parsed, "labor")

    assert findings == []
    assert overall_risk(findings).value == "low"
    assert risk_score(findings) == 0.0


def test_service_contract_detects_liquidated_damages(contract_text):
    parsed = parse_contract(contract_text("service_contract.txt"))
    findings = scan_contract(parsed, "service")
    rule_ids = {finding.rule_id for finding in findings}

    assert {"liquidated_damages", "final_interpretation", "auto_renewal"} <= rule_ids
    assert overall_risk(findings).value == "medium"


def test_labels_cover_expected_rules(contract_text):
    labels = json.loads(
        (ROOT / "data" / "fixtures" / "review_labels.json").read_text(encoding="utf-8")
    )
    for item in labels:
        parsed = parse_contract(contract_text(item["contract"]))
        actual = {
            finding.rule_id for finding in scan_contract(parsed, item["contract_type"])
        }
        assert set(item["expected_rules"]) <= actual
