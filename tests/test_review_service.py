from app.schemas import ContractReviewRequest


def test_review_risky_contract_is_persisted(review_service, contract_text):
    review = review_service.review(
        ContractReviewRequest(
            contract_text=contract_text("labor_contract_risky.txt"), contract_type="labor"
        )
    )

    assert review.overall_risk.value == "high"
    assert review.risk_score >= 90
    assert len(review.findings) >= 8
    assert review.findings[0].legal_basis
    assert review.summary

    loaded = review_service.get_review(review.id)
    assert loaded is not None
    assert loaded.contract_title == review.contract_title
    assert review_service.list_recent(5)[0].id == review.id


def test_review_clean_contract(review_service, contract_text):
    review = review_service.review(
        ContractReviewRequest(
            contract_text=contract_text("labor_contract_clean.txt"), contract_type="labor"
        )
    )

    assert review.overall_risk.value == "low"
    assert review.findings == []
    assert review.risk_score == 0.0
