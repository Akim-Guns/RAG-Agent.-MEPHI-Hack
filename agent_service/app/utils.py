from datetime import datetime

from states import AgentState

def init_new_state() -> AgentState:
    new_state = AgentState(
        messages=[],
        created_at=datetime.strftime(datetime.now(), format="%Y-%m-%d %H:%M:%S"),
        updated_at=datetime.strftime(datetime.now(), format="%Y-%m-%d %H:%M:%S"),
    )
    return new_state