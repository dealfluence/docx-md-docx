# 📋 Project Status & Handover

## ✅ Completed Features
*   **Core Architecture**: `RedlineEngine` successfully injects `w:ins` and `w:del` tags into existing DOCX files without corrupting them.
*   **Mapping Engine**: `DocumentMapper` correctly maps linear text offsets to XML DOM nodes, including handling split runs (`_split_run_at_index`).
*   **Diff Engine**: `diff-match-patch` integration works to convert full-text rewrites into atomic edits.
*   **Alignment**: Ingestion logic (`ingest.py`) and Mapper logic are aligned to use raw run concatenation, resolving most "Target Not Found" errors.
*   **CLI**: Functional CLI for Extract -> Edit -> Redline workflow.
*   **Offset Precision**: Fixed a critical bug in `DocumentMapper` where virtual newlines (`\n\n`) caused split-point calculations to drift, misplacing insertions in multi-paragraph matches.
*   **Start-of-Document Handling**: `diff.py` now supports insertions at the very start of the document by converting them to modifications of the following text anchor.

## 🐛 Known Issues
### 1. Table Layouts
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
