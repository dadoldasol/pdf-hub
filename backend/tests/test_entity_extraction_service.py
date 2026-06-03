from app.services.entity_extraction_service import EntityExtractionService


def test_extracts_known_terms() -> None:
    service = EntityExtractionService()

    candidates = service.extract("IFE supports RDI path and CSID debug flow.")
    by_name = {candidate.normalized_name: candidate for candidate in candidates}

    assert by_name["IFE"].entity_type == "ISP_BLOCK"
    assert by_name["CSID"].entity_type == "ISP_BLOCK"
    assert by_name["RDI"].entity_type == "FEATURE"
    assert by_name["DEBUG"].entity_type == "DEBUG_KEYWORD"


def test_extracts_pattern_candidates() -> None:
    service = EntityExtractionService()

    candidates = service.extract("CPAS votes bandwidth on SM8650 in cam_ife_hw_mgr.c.")
    by_name = {candidate.normalized_name: candidate for candidate in candidates}

    assert by_name["CPAS"].entity_type == "ISP_BLOCK"
    assert by_name["SM8650"].entity_type == "CHIPSET"
    assert by_name["CAM_IFE_HW_MGR.C"].entity_type == "CODE_FILE"


def test_prefers_higher_confidence_candidate_for_same_name() -> None:
    service = EntityExtractionService()

    candidates = service.extract("IFE")
    by_name = {candidate.normalized_name: candidate for candidate in candidates}

    assert by_name["IFE"].entity_type == "ISP_BLOCK"
    assert by_name["IFE"].confidence == 0.95


def test_filters_generic_acronyms_but_keeps_domain_acronyms() -> None:
    service = EntityExtractionService()

    candidates = service.extract("PDF API docs mention CPAS and VFE in the camera pipeline.")
    by_name = {candidate.normalized_name: candidate for candidate in candidates}

    assert "PDF" not in by_name
    assert "API" not in by_name
    assert by_name["CPAS"].entity_type == "ISP_BLOCK"
    assert by_name["VFE"].entity_type == "ISP_BLOCK"


def test_orders_candidates_by_confidence_before_name() -> None:
    service = EntityExtractionService()

    candidates = service.extract("cam_ife_hw_mgr.c calls cam_ife_hw_mgr_init and IFE.")

    assert candidates[0].normalized_name == "IFE"
