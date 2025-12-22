from datetime import datetime

from app.states import AgentState

def init_new_state() -> AgentState:
    new_state = AgentState(
        messages=[],

    )
    return new_state