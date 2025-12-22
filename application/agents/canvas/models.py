from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class WorkflowTransition(BaseModel):
    name: str
    next: str
    manual: bool

class WorkflowState(BaseModel):
    name: str
    transitions: List[WorkflowTransition]

class WorkflowSchema(BaseModel):
    version: str
    name: str
    desc: str
    initialState: str
    active: bool
    states: List[WorkflowState]

class EntityField(BaseModel):
    name: str
    type: str

class EntitySchema(BaseModel):
    name: str
    fields: List[EntityField]
