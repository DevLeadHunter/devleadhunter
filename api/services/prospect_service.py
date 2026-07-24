"""
Prospect data service.
"""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from models.prospect import Prospect, ProspectCreate, ProspectUpdate
from models.prospect_db import ProspectDB
from models.search import ProspectSearchRequest
from models.user import User


def _org_visibility_filter(user_id: int, organization_id: int | None):
    """SQLAlchemy filter: prospects owned by the user OR shared with their org.

    The org side is strictly scoped to ``organization_id`` — a prospect from
    another organization can never match (no cross-org leak).
    """
    if organization_id is None:
        return ProspectDB.user_id == user_id
    return or_(
        ProspectDB.user_id == user_id,
        ProspectDB.organization_id == organization_id,
    )


class ProspectService:
    """
    Service for managing prospect data operations.

    This service handles CRUD operations and search functionality
    for prospects using SQLAlchemy database.
    """

    def __init__(self):
        """Initialize the prospect service."""
        pass

    async def search_prospects(
        self, db: Session, request: ProspectSearchRequest, user_id: int | None = None
    ) -> list[Prospect]:
        """
        Search for prospects based on given criteria.

        Args:
            db: Database session
            request: Search criteria including category, city, and max results
            user_id: Optional user ID to filter prospects by user

        Returns:
            List of matching prospects

        Example:
            >>> request = ProspectSearchRequest(category="restaurant", city="Paris")
            >>> results = await service.search_prospects(db, request)
        """
        query = db.query(ProspectDB)

        # Filter by user if provided
        if user_id is not None:
            query = query.filter(ProspectDB.user_id == user_id)

        # Filter by category (partial match)
        if request.category:
            query = query.filter(ProspectDB.category.ilike(f"%{request.category}%"))

        # Filter by city
        if request.city:
            query = query.filter(ProspectDB.city.ilike(f"%{request.city}%"))

        # Order by creation date (most recent first)
        query = query.order_by(ProspectDB.created_at.desc())

        # Limit results
        db_prospects = query.limit(request.max_results).all()

        # Convert to Pydantic models
        return [Prospect.model_validate(p) for p in db_prospects]

    async def get_all_prospects(
        self,
        db: Session,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 1000,
        organization_id: int | None = None,
    ) -> list[Prospect]:
        """
        Get all prospects visible to a user (their own + their organization's).

        Args:
            db: Database session
            user_id: Optional user ID to filter prospects by user
            skip: Number of records to skip
            limit: Maximum number of records to return
            organization_id: The user's organization (None = personal scope only)

        Returns:
            List of all visible prospects, reservation names resolved
        """
        query = db.query(ProspectDB)

        # Filter by user if provided
        if user_id is not None:
            query = query.filter(_org_visibility_filter(user_id, organization_id))

        # Order by creation date (most recent first)
        query = query.order_by(ProspectDB.created_at.desc())

        db_prospects = query.offset(skip).limit(limit).all()

        return self._to_models_with_reservers(db, db_prospects)

    @staticmethod
    def _to_models_with_reservers(db: Session, db_prospects: list[ProspectDB]) -> list[Prospect]:
        """Convert rows to Pydantic models, resolving ``reserved_by_name`` in one query."""
        reserver_ids = {p.reserved_by_user_id for p in db_prospects if p.reserved_by_user_id}
        names: dict[int, str] = {}
        if reserver_ids:
            rows = db.execute(select(User.id, User.name).where(User.id.in_(reserver_ids))).all()
            names = {row[0]: row[1] for row in rows}

        prospects: list[Prospect] = []
        for db_prospect in db_prospects:
            prospect = Prospect.model_validate(db_prospect)
            if prospect.reserved_by_user_id:
                prospect.reserved_by_name = names.get(prospect.reserved_by_user_id)
            prospects.append(prospect)
        return prospects

    async def get_prospect(self, db: Session, prospect_id: int) -> Prospect | None:
        """
        Retrieve a prospect by ID.

        Args:
            db: Database session
            prospect_id: Unique prospect identifier

        Returns:
            Prospect object if found, None otherwise
        """
        db_prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if db_prospect:
            return Prospect.model_validate(db_prospect)
        return None

    async def create_prospect(
        self,
        db: Session,
        prospect: ProspectCreate,
        user_id: int,
        organization_id: int | None = None,
    ) -> Prospect:
        """
        Create a new prospect.

        Args:
            db: Database session
            prospect: Prospect data to create
            user_id: ID of the user creating the prospect
            organization_id: The creator's organization — the prospect is shared with it

        Returns:
            Created prospect with generated ID
        """
        # Convert Source enum to string
        source_value = prospect.source.value if hasattr(prospect.source, "value") else str(prospect.source)

        db_prospect = ProspectDB(
            name=prospect.name,
            address=prospect.address,
            city=prospect.city,
            phone=prospect.phone,
            email=prospect.email,
            website=prospect.website,
            category=prospect.category,
            source=source_value,
            confidence=prospect.confidence,
            user_id=user_id,
            organization_id=organization_id,
        )
        db.add(db_prospect)
        db.commit()
        db.refresh(db_prospect)

        return Prospect.model_validate(db_prospect)

    async def check_duplicate(self, db: Session, name: str, city: str | None, user_id: int) -> bool:
        """
        Check if a prospect with the same name and city already exists for this user.

        Args:
            db: Database session
            name: Business name
            city: City name
            user_id: User ID

        Returns:
            True if duplicate exists, False otherwise
        """
        query = db.query(ProspectDB).filter(and_(ProspectDB.user_id == user_id, ProspectDB.name.ilike(name)))

        if city:
            query = query.filter(ProspectDB.city.ilike(city))

        return query.first() is not None

    async def bulk_create_prospects(
        self, db: Session, prospects: list[ProspectCreate], user_id: int, skip_duplicates: bool = True
    ) -> tuple[list[Prospect], int]:
        """
        Create multiple prospects at once.

        Args:
            db: Database session
            prospects: List of prospect data to create
            user_id: ID of the user creating the prospects
            skip_duplicates: If True, skip prospects that already exist

        Returns:
            Tuple of (list of created prospects, number of skipped duplicates)
        """
        created_prospects = []
        skipped_count = 0

        for prospect_data in prospects:
            # Check for duplicates if requested
            if skip_duplicates:
                is_duplicate = await self.check_duplicate(
                    db=db, name=prospect_data.name, city=prospect_data.city, user_id=user_id
                )
                if is_duplicate:
                    skipped_count += 1
                    continue

            # Create the prospect
            created = await self.create_prospect(db, prospect_data, user_id)
            created_prospects.append(created)

        return created_prospects, skipped_count

    async def update_prospect(self, db: Session, prospect_id: int, update_data: ProspectUpdate) -> Prospect | None:
        """
        Update an existing prospect.

        Args:
            db: Database session
            prospect_id: Prospect ID to update
            update_data: Fields to update

        Returns:
            Updated prospect if found, None otherwise
        """
        db_prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if not db_prospect:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field == "source" and value is not None:
                # Convert Source enum to string
                value = value.value if hasattr(value, "value") else str(value)
            setattr(db_prospect, field, value)

        db.commit()
        db.refresh(db_prospect)

        return Prospect.model_validate(db_prospect)

    async def delete_prospect(self, db: Session, prospect_id: int) -> bool:
        """
        Delete a prospect.

        Args:
            db: Database session
            prospect_id: Prospect ID to delete

        Returns:
            True if deleted, False if not found
        """
        db_prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if db_prospect:
            db.delete(db_prospect)
            db.commit()
            return True
        return False

    async def get_prospects_count(self, db: Session, user_id: int | None = None) -> int:
        """
        Get total count of prospects.

        Args:
            db: Database session
            user_id: Optional user ID to filter by

        Returns:
            Total number of prospects
        """
        query = db.query(ProspectDB)
        if user_id is not None:
            query = query.filter(ProspectDB.user_id == user_id)
        return query.count()


# Global service instance
prospect_service = ProspectService()
