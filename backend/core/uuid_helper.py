"""
UUID Helper Utilities

Provides utilities for managing public UUIDs in models while maintaining internal integer IDs.
"""
import uuid as uuid_module
from typing import Any, Optional, Union
from sqlalchemy.orm import Session


def generate_uuid() -> uuid_module.UUID:
    """Generate a new UUID."""
    return uuid_module.uuid4()


def ensure_public_id(instance: Any) -> uuid_module.UUID:
    """
    Ensure an instance has a public_id, generating one if needed.
    
    Args:
        instance: Model instance that should have a public_id
        
    Returns:
        The public_id UUID
    """
    if not hasattr(instance, 'public_id') or not instance.public_id:
        instance.public_id = generate_uuid()
    return instance.public_id


def find_by_public_id(
    db: Session,
    model_class: Any,
    public_id: Union[str, uuid_module.UUID]
) -> Optional[Any]:
    """
    Find a model instance by its public_id.
    
    Args:
        db: Database session
        model_class: Model class to search
        public_id: Public UUID to find
        
    Returns:
        Model instance or None if not found
    """
    if isinstance(public_id, str):
        try:
            public_id = uuid_module.UUID(public_id)
        except ValueError:
            return None
            
    return db.query(model_class).filter(model_class.public_id == public_id).first()


def get_public_id_str(instance: Any) -> Optional[str]:
    """
    Get the public_id as a string.
    
    Args:
        instance: Model instance
        
    Returns:
        Public ID as string or None if not set
    """
    if hasattr(instance, 'public_id') and instance.public_id:
        return str(instance.public_id)
    return None


class PublicIdMixin:
    """
    Mixin class that provides public_id functionality.
    
    Add this to models that need public UUIDs:
    
    class MyModel(Base, PublicIdMixin):
        __tablename__ = "my_models"
        id = Column(Integer, primary_key=True)
        # public_id column added by mixin
    """
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Automatically add public_id column to subclasses."""
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'public_id'):
            from sqlalchemy import Column
            from sqlalchemy.dialects.postgresql import UUID
            cls.public_id = Column(
                UUID(as_uuid=True), 
                default=generate_uuid, 
                unique=True, 
                index=True, 
                nullable=False
            )
    
    def get_public_id(self) -> Optional[str]:
        """Get public ID as string."""
        return get_public_id_str(self)
    
    def ensure_public_id(self) -> uuid_module.UUID:
        """Ensure this instance has a public_id."""
        return ensure_public_id(self)


def migrate_existing_records(db: Session, model_class: Any, batch_size: int = 1000):
    """
    Migrate existing records to have public_id values.
    
    Args:
        db: Database session
        model_class: Model class to migrate
        batch_size: Number of records to process at once
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not hasattr(model_class, 'public_id'):
        logger.warning("Model {} does not have public_id column".format(model_class.__name__))
        return
    
    # Find records without public_id
    records_without_uuid = db.query(model_class).filter(model_class.public_id.is_(None)).limit(batch_size).all()
    
    if not records_without_uuid:
        logger.info("No records need UUID migration for {}".format(model_class.__name__))
        return
    
    logger.info("Migrating {} records for {}".format(len(records_without_uuid), model_class.__name__))
    
    # Add UUIDs in batch
    for record in records_without_uuid:
        record.public_id = generate_uuid()
    
    db.commit()
    logger.info("Successfully migrated {} records".format(len(records_without_uuid)))
    
    # Check if there are more records to migrate
    remaining = db.query(model_class).filter(model_class.public_id.is_(None)).count()
    if remaining > 0:
        logger.info("{} records remaining for migration".format(remaining))
    else:
        logger.info("All records migrated for {}".format(model_class.__name__))