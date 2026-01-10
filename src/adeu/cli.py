import argparse
import sys
import json
from pathlib import Path
from io import BytesIO
from typing import List, Optional

from adeu.ingest import extract_text_from_stream
from adeu.diff import generate_edits_from_text
from adeu.redline.engine import RedlineEngine
from adeu.models import DocumentEdit, EditOperationType

# --- Helper Utilities ---

def _read_docx_text(path: Path) -> str:
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "rb") as f:
        return extract_text_from_stream(BytesIO(f.read()), filename=path.name)

def _load_edits_from_json(path: Path) -> List[DocumentEdit]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        edits = []
        for item in data:
            # Flexible parsing: allow "target_text" OR "original", "new_text" OR "replace"
            target = item.get("target_text") or item.get("original")
            new_val = item.get("new_text") or item.get("replace")
            comment = item.get("comment")
            
            # Infer operation if not provided
            op_str = item.get("operation")
            if op_str:
                op = EditOperationType(op_str)
            else:
                if target and new_val: op = EditOperationType.MODIFICATION
                elif target and not new_val: op = EditOperationType.DELETION
                elif not target and new_val: op = EditOperationType.INSERTION
                else: continue
            
            edits.append(DocumentEdit(
                operation=op, 
                target_text=target or "", 
                new_text=new_val, 
                comment=comment
            ))
        return edits
    except Exception as e:
        print(f"Error parsing JSON edits: {e}", file=sys.stderr)
        sys.exit(1)

# --- Command Handlers ---

def handle_extract(args):
    text = _read_docx_text(args.input)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extracted text to {args.output}", file=sys.stderr)
    else:
        print(text)

def handle_diff(args):
    text_orig = _read_docx_text(args.original)
    
    # Second arg can be DOCX or TEXT
    if args.modified.suffix == ".docx":
        text_mod = _read_docx_text(args.modified)
    else:
        with open(args.modified, "r", encoding="utf-8") as f:
            text_mod = f.read()

    edits = generate_edits_from_text(text_orig, text_mod)

    if args.json:
        # Dump structured edits
        output = [e.model_dump(exclude={'_match_start_index'}) for e in edits]
        print(json.dumps(output, indent=2))
    else:
        # Visual Summary
        print(f"Found {len(edits)} changes:", file=sys.stderr)
        for e in edits:
            if e.operation == EditOperationType.DELETION:
                print(f"[-] {e.target_text}")
            elif e.operation == EditOperationType.INSERTION:
                print(f"[+] {e.new_text}")
            elif e.operation == EditOperationType.MODIFICATION:
                print(f"[~] '{e.target_text}' -> '{e.new_text}'")

def handle_apply(args):
    # 1. Get Edits
    edits = []
    if args.changes.suffix.lower() == ".json":
        print(f"Loading structured edits from {args.changes}...", file=sys.stderr)
        edits = _load_edits_from_json(args.changes)
    else:
        print(f"Calculating diff from text file {args.changes}...", file=sys.stderr)
        text_orig = _read_docx_text(args.original)
        with open(args.changes, "r", encoding="utf-8") as f:
            text_mod = f.read()
        edits = generate_edits_from_text(text_orig, text_mod)

    print(f"Applying {len(edits)} edits...", file=sys.stderr)

    # 2. Apply
    with open(args.original, "rb") as f:
        stream = BytesIO(f.read())
    
    engine = RedlineEngine(stream, author=args.author)
    applied, skipped = engine.apply_edits(edits)

    # 3. Save
    output_path = args.output
    if not output_path:
        output_path = args.original.with_name(f"{args.original.stem}_redlined.docx")
        
    with open(output_path, "wb") as f:
        f.write(engine.save_to_stream().getvalue())

    print(f"✅ Saved to {output_path}", file=sys.stderr)
    print(f"Stats: {applied} applied, {skipped} skipped.", file=sys.stderr)
    if skipped > 0:
        sys.exit(1)

# --- Main Entrypoint ---

def main():
    parser = argparse.ArgumentParser(
        prog="adeu", 
        description="Adeu: Agentic DOCX Redlining Engine"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")

    # Command: extract
    p_extract = subparsers.add_parser("extract", help="Extract raw text from a DOCX file")
    p_extract.add_argument("input", type=Path, help="Input DOCX file")
    p_extract.add_argument("-o", "--output", type=Path, help="Output file (default: stdout)")
    p_extract.set_defaults(func=handle_extract)

    # Command: diff
    p_diff = subparsers.add_parser("diff", help="Compare two files (DOCX vs DOCX/Text)")
    p_diff.add_argument("original", type=Path, help="Original DOCX")
    p_diff.add_argument("modified", type=Path, help="Modified DOCX or Text file")
    p_diff.add_argument("--json", action="store_true", help="Output raw JSON edits")
    p_diff.set_defaults(func=handle_diff)

    # Command: apply
    p_apply = subparsers.add_parser("apply", help="Apply edits to a DOCX")
    p_apply.add_argument("original", type=Path, help="Original DOCX")
    p_apply.add_argument("changes", type=Path, help="JSON edits file OR Modified Text file")
    p_apply.add_argument("-o", "--output", type=Path, help="Output DOCX path")
    p_apply.add_argument("--author", type=str, default="Adeu AI", help="Author name for Track Changes")
    p_apply.set_defaults(func=handle_apply)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()