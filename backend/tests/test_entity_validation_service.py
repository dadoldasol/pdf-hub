from app.services.entity_extraction_service import EntityCandidate
from app.services.entity_validation_service import EntityValidationService


def _candidate(name: str = "IFE") -> EntityCandidate:
    service = EntityValidationService()
    return EntityCandidate(
        name=name,
        normalized_name=service.extractor.normalize_name(name),
        entity_type="CANDIDATE_TERM",
        confidence=0.55,
        source="pattern",
        snippet=f"{name} appears in the ISP pipeline.",
    )


def test_validation_disabled_accepts_rule_candidates(monkeypatch) -> None:
    monkeypatch.setattr("app.services.entity_validation_service.settings.enable_llm_entity_validation", False)
    service = EntityValidationService()

    result = service.validate_candidates([_candidate()], "IFE appears in the ISP pipeline.")

    assert result.accepted_candidates[0].name == "IFE"
    assert result.rejected_count == 0
    assert result.llm_used is False


def test_validation_falls_back_when_model_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.services.entity_validation_service.settings.enable_llm_entity_validation", True)
    monkeypatch.setattr("app.services.entity_validation_service.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.services.entity_validation_service.settings.llm_model", None)
    monkeypatch.setattr("app.services.entity_validation_service.settings.entity_validation_model", None)
    service = EntityValidationService()

    result = service.validate_candidates([_candidate()], "IFE appears in the ISP pipeline.")

    assert result.accepted_candidates[0].name == "IFE"
    assert result.error_message


def test_validation_accepts_and_rejects_llm_output(monkeypatch) -> None:
    monkeypatch.setattr("app.services.entity_validation_service.settings.enable_llm_entity_validation", True)
    monkeypatch.setattr("app.services.entity_validation_service.settings.llm_provider", "openai")
    monkeypatch.setattr("app.services.entity_validation_service.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.services.entity_validation_service.settings.entity_validation_model", "test-model")
    service = EntityValidationService()

    def fake_post(_prompt):
        return {
            "output_text": (
                '{"entities":['
                '{"candidate_name":"IFE","accepted":true,"name":"Image Front End",'
                '"normalized_name":"IFE","entity_type":"ISP_BLOCK",'
                '"definition":"Front-end block in the ISP pipeline.","confidence":0.91,'
                '"aliases":["Image Front-End"],"rejection_reason":""},'
                '{"candidate_name":"PDF","accepted":false,"name":"","normalized_name":"",'
                '"entity_type":"","definition":"","confidence":0,'
                '"aliases":[],"rejection_reason":"Document format word"}'
                "]}"
            )
        }

    monkeypatch.setattr(service, "_post_validation_request", fake_post)

    result = service.validate_candidates([_candidate("IFE"), _candidate("PDF")], "IFE appears.")

    assert len(result.accepted_candidates) == 1
    accepted = result.accepted_candidates[0]
    assert accepted.name == "Image Front End"
    assert accepted.normalized_name == "IFE"
    assert accepted.entity_type == "ISP_BLOCK"
    assert accepted.description == "Front-end block in the ISP pipeline."
    assert accepted.confidence == 0.91
    assert accepted.aliases == ("Image Front-End",)
    assert accepted.validation_source == "llm"
    assert result.rejected_count == 1
    assert result.llm_used is True


def test_validation_parses_ollama_chat_output(monkeypatch) -> None:
    monkeypatch.setattr("app.services.entity_validation_service.settings.enable_llm_entity_validation", True)
    monkeypatch.setattr("app.services.entity_validation_service.settings.llm_provider", "ollama")
    monkeypatch.setattr("app.services.entity_validation_service.settings.entity_validation_model", "qwen3:8b")
    service = EntityValidationService()

    def fake_post(_prompt):
        return {
            "message": {
                "content": (
                    '{"entities":[{"candidate_name":"IFE","accepted":true,'
                    '"name":"Image Front End","normalized_name":"IFE",'
                    '"entity_type":"ISP_BLOCK","definition":"ISP front-end block.",'
                    '"confidence":0.9,"aliases":[],"rejection_reason":""}]}'
                )
            }
        }

    monkeypatch.setattr(service, "_post_validation_request", fake_post)

    result = service.validate_candidates([_candidate("IFE")], "IFE appears.")

    assert result.accepted_candidates[0].name == "Image Front End"
    assert result.accepted_candidates[0].entity_type == "ISP_BLOCK"
    assert result.llm_used is True


def test_builds_ollama_payload_with_schema(monkeypatch) -> None:
    monkeypatch.setattr("app.services.entity_validation_service.settings.llm_provider", "ollama")
    monkeypatch.setattr("app.services.entity_validation_service.settings.entity_validation_model", "qwen3:8b")
    service = EntityValidationService()

    payload = service._build_ollama_payload("Validate this.")

    assert payload["model"] == "qwen3:8b"
    assert payload["stream"] is False
    assert payload["format"]["required"] == ["entities"]
    assert payload["options"]["temperature"] == 0
