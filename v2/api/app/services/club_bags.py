from typing import Any

from sqlalchemy.orm import Session

from app.models import User, UserProfile

DEFAULT_BAG: dict[str, Any] = {"enabled": [], "distances": {}}


def get_club_bag(db: Session, *, owner: User) -> dict[str, Any]:
    profile = owner.profile
    if profile is None or profile.club_bag is None:
        return {"enabled": [], "distances": {}}
    bag = profile.club_bag
    return {
        "enabled": list(bag.get("enabled", [])),
        "distances": dict(bag.get("distances", {})),
    }


def set_club_bag(db: Session, *, owner: User, bag: dict[str, Any]) -> dict[str, Any]:
    if owner.profile is None:
        owner.profile = UserProfile()
    owner.profile.club_bag = {
        "enabled": list(bag.get("enabled", [])),
        "distances": dict(bag.get("distances", {})),
    }
    db.commit()
    db.refresh(owner)
    return get_club_bag(db, owner=owner)
