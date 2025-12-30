# 📋 Project Status & Handover

## ✅ Completed Features
*   **Core Architecture**: `RedlineEngine` successfully injects `w:ins` and `w:del` tags into existing DOCX files without corrupting them.
*   **Mapping Engine**: `DocumentMapper` correctly maps linear text offsets to XML DOM nodes, including handling split runs (`_split_run_at_index`).
*   **Diff Engine**: `diff-match-patch` integration works to convert full-text rewrites into atomic edits.
*   **Alignment**: Ingestion logic (`ingest.py`) and Mapper logic are aligned to use raw run concatenation, resolving most "Target Not Found" errors.
*   **CLI**: Functional CLI for Extract -> Edit -> Redline workflow.

## 🐛 Known Issues
### 1. The "Extra Space" Artifact (Priority: High)
*   **Symptoms**: In complex run sequences (e.g., `ARTICLE3 FEES`), the engine sometimes places the inserted space *after* the subsequent run instead of between them, or the visual output in Word shows double spaces (`ARTICLE3  FEES`).
*   **Suspect**: The logic in `RedlineEngine._apply_single_edit` for determining the insertion point (`parent.insert(index + 1)`) might be off-by-one when runs are adjacent without spaces.
*   **Investigation**: Debug logs in `redline_engine.py` show the XML structure.
*   **Fix Strategy**: Create a dedicated unit test case in `tests/test_roundtrip.py` that replicates the `ARTICLE3 FEES` scenario specifically, then adjust the index calculation.

### 2. Table Layouts
*   **Status**: Basic support. Tables are extracted linearly (`|` separated).
*   **Limitation**: Edits spanning across cell boundaries (e.g., merging two cells) are NOT supported and will likely throw errors or be ignored.
*   **Next Step**: Implement explicit Table/Row/Cell awareness in `ComplianceEdit` target resolution.

## 🚀 Next Steps (Roadmap)
1.  **Unit Test Expansion**: The current test suite is minimal. We need rigorous property-based testing (using `hypothesis`?) to generate random run sequences and ensure edits always apply correctly.
2.  **Formatting Preservation**: Currently, inserted text inherits style from the anchor run. We need logic to handle cases where the insertion should inherit from the *next* run (e.g., inserting at the start of a bold sentence).
3.  **LLM Integration**: Connect the `ComplianceEdit` schema to an actual OpenAI/Anthropic function call to bypass the text-diffing step for simple instructions ("Change the governing law to NY").

## 📂 Key Files
*   `src/adeu/redline/engine.py`: **The Brain**. modifying this requires care.
*   `src/adeu/redline/mapper.py`: **The Map**. If searching fails, look here.
*   `tests/test_roundtrip.py`: **The Proof**. Run this before pushing.
