import uuid
from typing import Protocol, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import InstrumentedAttribute


class OwnedModel(Protocol):
    user_id: InstrumentedAttribute[uuid.UUID]


OwnedModelT = TypeVar("OwnedModelT", bound=OwnedModel)


def owner_scoped_select(model: type[OwnedModelT], user_id: uuid.UUID) -> Select[tuple[OwnedModelT]]:
    return select(model).where(model.user_id == user_id)
