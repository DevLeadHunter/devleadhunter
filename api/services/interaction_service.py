"""
Interaction service for managing prospect interactions.
"""

import json

from sqlalchemy.orm import Session

from models.prospect_interaction import ProspectInteraction


class InteractionService:
    """Service for managing prospect interactions."""

    def create_interaction(
        self,
        db: Session,
        prospect_id: int,
        user_id: int,
        interaction_type: str,
        description: str,
        metadata: dict | None = None,
    ) -> ProspectInteraction:
        """
        Create a new interaction.

        Args:
            db: Database session
            prospect_id: Prospect ID
            user_id: User ID
            interaction_type: Type of interaction
            description: Description of the interaction
            metadata: Optional metadata dictionary

        Returns:
            Created interaction
        """
        interaction = ProspectInteraction(
            prospect_id=prospect_id,
            user_id=user_id,
            interaction_type=interaction_type,
            description=description,
            interaction_metadata=json.dumps(metadata) if metadata else None,
        )

        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        return interaction

    def get_prospect_interactions(
        self, db: Session, prospect_id: int, user_id: int, limit: int = 100
    ) -> list[ProspectInteraction]:
        """
        Get all interactions for a prospect.

        Args:
            db: Database session
            prospect_id: Prospect ID
            user_id: User ID (for security)
            limit: Maximum number of interactions to return

        Returns:
            List of interactions
        """
        interactions = (
            db.query(ProspectInteraction)
            .filter(ProspectInteraction.prospect_id == prospect_id, ProspectInteraction.user_id == user_id)
            .order_by(ProspectInteraction.created_at.desc())
            .limit(limit)
            .all()
        )

        return interactions

    def log_email_sent(
        self, db: Session, prospect_id: int, user_id: int, email_log_id: int, subject: str
    ) -> ProspectInteraction:
        """
        Log an email sent interaction.

        Args:
            db: Database session
            prospect_id: Prospect ID
            user_id: User ID
            email_log_id: Email log ID
            subject: Email subject

        Returns:
            Created interaction
        """
        return self.create_interaction(
            db=db,
            prospect_id=prospect_id,
            user_id=user_id,
            interaction_type="email_sent",
            description=f"Email envoyé : {subject}",
            metadata={"email_log_id": email_log_id},
        )

    def log_email_opened(self, db: Session, prospect_id: int, user_id: int, email_log_id: int) -> ProspectInteraction:
        """
        Log an email opened interaction.

        Args:
            db: Database session
            prospect_id: Prospect ID
            user_id: User ID
            email_log_id: Email log ID

        Returns:
            Created interaction
        """
        return self.create_interaction(
            db=db,
            prospect_id=prospect_id,
            user_id=user_id,
            interaction_type="email_opened",
            description="Email ouvert",
            metadata={"email_log_id": email_log_id},
        )

    def log_email_clicked(
        self, db: Session, prospect_id: int, user_id: int, email_log_id: int, url: str | None = None
    ) -> ProspectInteraction:
        """
        Log an email link clicked interaction.

        Args:
            db: Database session
            prospect_id: Prospect ID
            user_id: User ID
            email_log_id: Email log ID
            url: URL that was clicked

        Returns:
            Created interaction
        """
        description = "Lien cliqué dans l'email"
        if url:
            description += f" : {url}"

        return self.create_interaction(
            db=db,
            prospect_id=prospect_id,
            user_id=user_id,
            interaction_type="email_clicked",
            description=description,
            metadata={"email_log_id": email_log_id, "url": url},
        )


# Singleton instance
interaction_service = InteractionService()
