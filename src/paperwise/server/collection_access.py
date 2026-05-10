from fastapi import HTTPException, status

from paperwise.application.interfaces import CollectionRepository
from paperwise.domain.models import Collection, User


def get_collection_or_404(
    *,
    collection_id: str,
    repository: CollectionRepository,
    current_user: User,
) -> Collection:
    collection = repository.get_collection(collection_id)
    if collection is None or collection.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection
