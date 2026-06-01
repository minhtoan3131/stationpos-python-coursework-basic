from typing import List
from app.core.database.base_repository import BaseRepository
from app.modules.dashboard.repositories.activity_log_repository import ActivityLogRepository
from app.modules.dashboard.dtos.activity_log_dto import ActivityLogDTO


class ActivityLogRepositoryImpl(BaseRepository, ActivityLogRepository):
    def __init__(self, connection):
        super().__init__(connection)

    def add_log(self, action_type: str, reference_code: str | None, description: str) -> bool:
        query = """
            INSERT INTO activity_logs (action_type, reference_code, description)
            VALUES (%s, %s, %s)
        """
        self.cursor.execute(query, (action_type, reference_code, description))
        return True

    def get_logs_by_date(self, date_str: str) -> List[ActivityLogDTO]:
        query = """
            SELECT id, action_type, reference_code, description, created_at
            FROM activity_logs
            WHERE DATE(created_at) = %s
            ORDER BY created_at DESC
        """
        self.cursor.execute(query, (date_str,))
        rows = self.cursor.fetchall()

        result = []
        for row in rows:
            result.append(ActivityLogDTO(
                id=row['id'],
                action_type=row['action_type'],
                reference_code=row['reference_code'],
                description=row['description'],
                created_at=row['created_at']
            ))
        return result