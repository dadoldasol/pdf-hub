# Entity Validation Prompt

Validate entity candidates extracted from Android camera, ISP, HAL, kernel, chipset, and debugging technical PDFs.

Accept only candidates that are meaningful technical concepts. Reject document-format words, generic acronyms, incidental all-caps words, and candidates without source evidence.

Return JSON that matches the configured schema:

- `candidate_name`: original candidate name.
- `accepted`: whether the candidate should be stored as an entity.
- `name`: preferred display name.
- `normalized_name`: merge key, usually uppercase acronym or canonical technical name.
- `entity_type`: one of the supported entity types.
- `definition`: short source-grounded definition, or an empty string when rejected.
- `confidence`: number from 0 to 1.
- `aliases`: alternative names from the context.
- `rejection_reason`: short reason when rejected, otherwise empty string.
