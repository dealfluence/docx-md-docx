from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr

class EditOperationType(str, Enum):
    INSERTION = "INSERTION"
    DELETION = "DELETION"
    MODIFICATION = "MODIFICATION"

class DocumentEdit(BaseModel):
    """
    Represents a single atomic edit suggested by the LLM.
    """
    operation: EditOperationType
    
    target_text: str = Field(
        ..., 
        description="Exact text to find. If the text appears multiple times (e.g. 'Fee'), include surrounding context (e.g. 'Section 2: Fee') to ensure the correct instance is matched. For INSERTION, this is the anchor immediately PRECEDING the new content."
    )
    
    new_text: Optional[str] = Field(
        None, 
        description="The new text to insert. If you included context in target_text to ensure uniqueness, you MUST repeat that context here (e.g. target='Section 2: Fee', new='Section 2: Price')."
    )
    
    comment: Optional[str] = Field(
        None,
        description="Text to appear in a comment bubble (Review Pane) linked to this edit. Use this to explain the 'why' behind the change."
    )
    
    # Internal use only. PrivateAttr is invisible to the MCP API schema.
    _match_start_index: Optional[int] = PrivateAttr(default=None)