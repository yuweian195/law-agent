from app.schemas import QARequest


def test_illegal_dismissal_question(qa_service):
    record = qa_service.ask(
        QARequest(question="公司违法解除劳动合同，我工作3年2个月，月薪2万，能拿多少赔偿？")
    )

    assert record.intent == "severance"
    assert record.calculation is not None
    assert record.calculation.amount == 140000
    assert "140,000" in record.conclusion
    assert any(item.article_id == "labor-87" for item in record.citations)
    assert record.disclaimer


def test_probation_question_has_correct_conclusion(qa_service):
    record = qa_service.ask(QARequest(question="试用期6个月合法吗？合同期1年"))

    assert record.intent == "probation"
    assert "不得超过 2 个月" in record.conclusion
    assert any(item.article_id == "labor-19" for item in record.citations)


def test_non_compete_question_is_retrieved(qa_service):
    record = qa_service.ask(QARequest(question="竞业限制没有约定补偿金，还有效吗？"))

    assert record.intent == "non_compete"
    assert {item.article_id for item in record.citations} & {"labor-23", "labor-24"}
    assert "经济补偿" in record.conclusion


def test_qa_record_is_persisted(qa_service):
    record = qa_service.ask(QARequest(question="加班费怎么计算？工作日和法定节假日一样吗？"))
    loaded = qa_service.get_record(record.id)

    assert loaded is not None
    assert loaded.question == record.question
    assert loaded.citations
    assert qa_service.list_recent(5)[0].id == record.id
