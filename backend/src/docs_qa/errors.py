from uuid import UUID


class NotFoundError(Exception):
    def __init__(self, resource: str, resource_id: UUID) -> None:
        super().__init__(f"{resource} {resource_id} was not found.")
        self.resource = resource
        self.resource_id = resource_id
