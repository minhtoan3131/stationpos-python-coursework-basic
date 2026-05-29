from dataclasses import dataclass
import datetime
from typing import Optional

@dataclass
class ActivityLogDTO:
    id: int
    action_type: str
    reference_code: Optional[str]
    description: str
    created_at: datetime.datetime