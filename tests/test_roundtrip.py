import io
from docx import Document
from adeu.models import ComplianceEdit, EditOperationType
from adeu.redline.engine import RedlineEngine
from adeu.ingest import extract_text_from_stream

def test_full_roundtrip_workflow(simple_docx_stream):
    """
    Tests the full lifecycle:
    1. Ingest DOCX -> Text
    2. Simulate LLM creating an Edit
    3. Apply Edit -> Redlined DOCX
    """
    # 1. Ingestion
    extracted_text = extract_text_from_stream(simple_docx_stream)
    assert "Contract Agreement" in extracted_text
    assert "Seller" in extracted_text

    # 2. Simulate LLM Response (ComplianceEdit)
    # Let's change "Seller" to "Vendor"
    edit = ComplianceEdit(
        operation=EditOperationType.MODIFICATION,
        target_text_to_change_or_anchor="Seller",
        proposed_new_text="Vendor",
        thought_process="Standardizing terminology."
    )

    # 3. Injection (Redlining)
    # Reset stream pointer for the engine (simulating fresh read)
    simple_docx_stream.seek(0)
    engine = RedlineEngine(simple_docx_stream)
    
    engine.apply_edits([edit])
    
    result_stream = engine.save_to_stream()
    
    # 4. Verification
    # Parse the result and check for Track Changes XML
    doc = Document(result_stream)
    
    # Check text content (python-docx .text property usually shows the "current" view, 
    # but exact behavior depends on how it parses w:ins/w:del. 
    # We check the XML directly for the most robust test.)
    
    xml_content = doc.element.xml
    
    # Check for Deletion tag
    assert "w:del" in xml_content
    assert "<w:delText>Seller</w:delText>" in xml_content
    
    # Check for Insertion tag
    assert "w:ins" in xml_content
    assert "<w:t>Vendor</w:t>" in xml_content

def test_split_run_behavior():
    """
    Tests that the engine correctly splits a run when the target text 
    is in the middle of a sentence.
    """
    doc = Document()
    p = doc.add_paragraph()
    run = p.add_run("The quick brown fox.")
    
    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    
    edit = ComplianceEdit(
        operation=EditOperationType.DELETION,
        target_text_to_change_or_anchor="brown", # Middle of the run
        proposed_new_text=None
    )
    
    engine = RedlineEngine(stream)
    engine.apply_edits([edit])
    
    result_stream = engine.save_to_stream()
    
    # Check XML
    doc = Document(result_stream)
    xml_content = doc.element.xml
    
    # "brown" should be wrapped in delete
    # "The quick " and " fox." should remain as runs (or be split out)
    assert "<w:delText>brown</w:delText>" in xml_content

def test_insertion_spacing_between_complex_runs():
    """
    Reproduction test for 'Extra Space' or misplaced insertion bug.
    Scenario: Text is 'ARTICLE3FEES' split into runs ['ARTICLE', '3', 'FEES'].
    Action: Insert ' ' after '3'.
    Expected: 'ARTICLE' -> '3' -> INS(' ') -> 'FEES'
    """
    doc = Document()
    p = doc.add_paragraph()
    
    # Create fragmented runs (simulate bold/not bold to prevent coalescing)
    r1 = p.add_run("ARTICLE")
    r1.bold = True
    r2 = p.add_run("3")
    r2.bold = False
    r3 = p.add_run("FEES")
    r3.bold = True
    
    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    
    # Insert space after "3" (Anchor="ARTICLE3")
    # Note: We anchor to "3" specifically to test strict adjacency
    edit = ComplianceEdit(
        operation=EditOperationType.INSERTION,
        target_text_to_change_or_anchor="3", 
        proposed_new_text=" "
    )
    
    engine = RedlineEngine(stream)
    engine.apply_edits([edit])
    
    result_stream = engine.save_to_stream()
    doc = Document(result_stream)
    xml = doc.element.xml
    
    # Assertions
    # 1. Verify "3" is still there (not deleted)
    assert ">3</w:t>" in xml
    # 2. Verify "FEES" is there
    assert ">FEES</w:t>" in xml
    # 3. Verify Insertion of space
    assert '<w:t xml:space="preserve"> </w:t>' in xml or '<w:t> </w:t>' in xml

    # 4. Verify Order: 3 ... ins ... FEES
    # We find indices in the XML string
    idx_3 = xml.find(">3</w:t>")
    idx_fees = xml.find(">FEES</w:t>")
    idx_ins = xml.find('<w:t xml:space="preserve"> </w:t>')
    if idx_ins == -1:
        idx_ins = xml.find('<w:t> </w:t>')
        
    assert idx_3 < idx_ins, "Space should be after 3"
    assert idx_ins < idx_fees, "Space should be before FEES"

def test_insertion_at_start_of_document():
    """
    Tests inserting text at the very beginning of the document.
    Original: "Contract"
    Modified: "Big Contract"
    """
    doc = Document()
    doc.add_paragraph("Contract")
    
    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    
    original_text = extract_text_from_stream(stream)
    modified_text = "Big " + original_text
    
    # We use generate_edits_from_text to test the Diff logic specifically
    from adeu.diff import generate_edits_from_text
    edits = generate_edits_from_text(original_text, modified_text)
    
    assert len(edits) > 0, "Should generate an edit for start-of-doc insertion"
    assert "Big" in edits[0].proposed_new_text
    assert edits[0].target_text_to_change_or_anchor in original_text