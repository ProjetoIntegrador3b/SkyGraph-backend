"""Generic use cases over a BaseRepository.

The repository answers with None or False when nothing matched; the service
turns that into a domain error, so callers always get an entity or an error.
"""

from pydantic import BaseModel

from app.models import Page, PageParams
from app.repositories.base import BaseRepository
from app.services.errors import MissingReferenceError, NotFoundError


class BaseService[M: BaseModel, F: PageParams]:
    # Raised with the entity's key when it does not exist.
    not_found: type[NotFoundError]

    def __init__(self, repository: BaseRepository[M, F]) -> None:
        self._repository = repository

    async def get(self, key: object) -> M:
        entity = await self._repository.get(key)
        if entity is None:
            raise self.not_found(key)
        return entity

    async def get_all(self, filters: F) -> Page[M]:
        return await self._repository.get_all(filters)

    async def create(self, entity: M) -> M:
        created = await self._repository.create(entity)
        if created is None:
            raise MissingReferenceError(
                f"{type(entity).__name__} {self._key(entity)} refers to a resource "
                "that does not exist"
            )
        return created

    async def update(self, entity: M) -> M:
        updated = await self._repository.update(entity)
        if updated is None:
            raise self.not_found(self._key(entity))
        return updated

    async def delete(self, key: object) -> None:
        if not await self._repository.delete(key):
            raise self.not_found(key)

    def _key(self, entity: M) -> object:
        return getattr(entity, self._repository.key)
