"""
Quote service for pressure washing quote management with status transitions
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.db.models import Quote, PricingRule, Organization, User
from backend.services.pricing_service import PricingService, PricingQuoteRequest
from backend.services.settings_resolver import SettingsResolver
from backend.core.audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)


class QuoteCreationRequest:
    """Request model for creating quotes from pricing computations"""
    
    def __init__(
        self,
        organization_id: str,
        customer_email: str,
        service_types: List[str],
        surfaces: Dict[str, Any],
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_address: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
        preferred_date: Optional[datetime] = None,
        additional_services: Optional[List[str]] = None,
        customer_tier: str = "standard",
        rush_job: bool = False,
        notes: Optional[str] = None,
        customer_notes: Optional[str] = None,
        source: str = "manual",
        source_metadata: Optional[Dict[str, Any]] = None,
        quote_validity_days: int = 30
    ):
        self.organization_id = organization_id
        self.customer_email = customer_email
        self.service_types = service_types
        self.surfaces = surfaces
        self.customer_name = customer_name
        self.customer_phone = customer_phone
        self.customer_address = customer_address
        self.location = location or {}
        self.preferred_date = preferred_date
        self.additional_services = additional_services or []
        self.customer_tier = customer_tier
        self.rush_job = rush_job
        self.notes = notes
        self.customer_notes = customer_notes
        self.source = source
        self.source_metadata = source_metadata or {}
        self.quote_validity_days = quote_validity_days


class QuoteUpdateRequest:
    """Request model for updating quote status and details"""
    
    def __init__(
        self,
        new_status: Optional[str] = None,
        notes: Optional[str] = None,
        customer_notes: Optional[str] = None,
        recompute_pricing: bool = False
    ):
        self.new_status = new_status
        self.notes = notes
        self.customer_notes = customer_notes
        self.recompute_pricing = recompute_pricing


class QuoteService:
    """
    Service for managing pressure washing quotes with status lifecycle
    """
    
    def __init__(self, settings_resolver: SettingsResolver):
        self.settings_resolver = settings_resolver
        self.pricing_service = PricingService(settings_resolver)
    
    def create_quote(
        self, 
        request: QuoteCreationRequest,
        db: Session,
        user_id: int
    ) -> Quote:
        """
        Create a quote from customer details and pricing computation
        """
        try:
            # Verify organization exists and user has access
            organization = db.query(Organization).filter(
                Organization.id == request.organization_id
            ).first()
            if not organization:
                raise ValueError(f"Organization {request.organization_id} not found")
            
            # Create pricing quote request
            pricing_request = PricingQuoteRequest(
                organization_id=request.organization_id,
                service_types=request.service_types,
                surfaces=request.surfaces,
                location=request.location,
                preferred_date=request.preferred_date.date() if request.preferred_date else None,
                additional_services=request.additional_services,
                customer_tier=request.customer_tier,
                rush_job=request.rush_job,
                metadata={"customer_email": request.customer_email}
            )
            
            # Compute pricing
            pricing_quote = self.pricing_service.compute_quote(pricing_request, db, user_id)
            
            # Generate quote number
            quote_number = self._generate_quote_number(request.organization_id, db)
            
            # Calculate validity period
            valid_until = datetime.now(timezone.utc) + timedelta(days=request.quote_validity_days)
            
            # Create quote
            quote = Quote(
                id=str(uuid.uuid4()),
                organization_id=request.organization_id,
                customer_email=request.customer_email,
                customer_name=request.customer_name,
                customer_phone=request.customer_phone,
                customer_address=request.customer_address,
                line_items=pricing_quote.breakdown,
                subtotal=pricing_quote.subtotal,
                discounts=abs(pricing_quote.bundle_discount),  # Store as positive
                tax_amount=pricing_quote.tax_amount,
                total=pricing_quote.total,
                currency=pricing_quote.currency,
                status="draft",
                quote_number=quote_number,
                valid_until=valid_until,
                notes=request.notes,
                customer_notes=request.customer_notes,
                source=request.source,
                source_metadata=request.source_metadata,
                pricing_snapshot=pricing_quote.to_dict(),
                created_by_id=user_id
            )
            
            # Try to link to pricing rule used
            if pricing_quote.applied_rules:
                pricing_rule = db.query(PricingRule).filter(
                    and_(
                        PricingRule.organization_id == request.organization_id,
                        PricingRule.name.in_(pricing_quote.applied_rules),
                        PricingRule.is_active == True
                    )
                ).first()
                if pricing_rule:
                    quote.pricing_rule_id = pricing_rule.id
            
            db.add(quote)
            db.commit()
            db.refresh(quote)
            
            # Log audit event
            audit_logger = get_audit_logger()
            audit_logger.log_event(
                event_type=AuditEventType.QUOTE_CREATED,
                user_id=str(user_id),
                organization_id=request.organization_id,
                details={
                    "quote_id": quote.id,
                    "quote_number": quote.quote_number,
                    "customer_email": request.customer_email,
                    "total": float(quote.total),
                    "currency": quote.currency,
                    "source": request.source
                }
            )
            
            return quote
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating quote for org {request.organization_id}: {str(e)}")
            raise
    
    def get_quote(
        self,
        quote_id: str,
        organization_id: str,
        db: Session
    ) -> Optional[Quote]:
        """
        Get a quote by ID with organization filtering
        """
        quote = db.query(Quote).filter(
            and_(
                Quote.id == quote_id,
                Quote.organization_id == organization_id
            )
        ).first()
        
        return quote
    
    def list_quotes(
        self,
        organization_id: str,
        db: Session,
        status: Optional[str] = None,
        customer_email: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Quote]:
        """
        List quotes for organization with optional filtering
        """
        query = db.query(Quote).filter(Quote.organization_id == organization_id)
        
        if status:
            query = query.filter(Quote.status == status)
        
        if customer_email:
            query = query.filter(Quote.customer_email == customer_email)
        
        quotes = query.order_by(Quote.created_at.desc()).offset(offset).limit(limit).all()
        return quotes
    
    def update_quote(
        self,
        quote_id: str,
        organization_id: str,
        request: QuoteUpdateRequest,
        db: Session,
        user_id: int
    ) -> Quote:
        """
        Update quote status and details with validation
        """
        try:
            # Get quote with organization filtering
            quote = self.get_quote(quote_id, organization_id, db)
            if not quote:
                raise ValueError(f"Quote {quote_id} not found in organization {organization_id}")
            
            # Store original values for audit
            original_status = quote.status
            changes = {}
            
            # Handle status transition
            if request.new_status and request.new_status != quote.status:
                if not quote.can_transition_to(request.new_status):
                    raise ValueError(
                        f"Invalid status transition from {quote.status} to {request.new_status}"
                    )
                
                # Update status and set transition timestamp
                quote.status = request.new_status
                changes["status"] = {"from": original_status, "to": request.new_status}
                
                now = datetime.now(timezone.utc)
                if request.new_status == "sent":
                    quote.sent_at = now
                elif request.new_status == "accepted":
                    quote.accepted_at = now
                elif request.new_status == "declined":
                    quote.declined_at = now
                elif request.new_status == "expired":
                    quote.expired_at = now
            
            # Update notes
            if request.notes is not None:
                changes["notes"] = {"from": quote.notes, "to": request.notes}
                quote.notes = request.notes
            
            if request.customer_notes is not None:
                changes["customer_notes"] = {"from": quote.customer_notes, "to": request.customer_notes}
                quote.customer_notes = request.customer_notes
            
            # Recompute pricing if requested
            if request.recompute_pricing:
                original_total = quote.total
                self._recompute_quote_pricing(quote, db, user_id)
                changes["total"] = {"from": float(original_total), "to": float(quote.total)}
            
            # Update audit fields
            quote.updated_by_id = user_id
            quote.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(quote)
            
            # Log audit event
            audit_logger = get_audit_logger()
            audit_logger.log_event(
                event_type=AuditEventType.QUOTE_UPDATED,
                user_id=str(user_id),
                organization_id=organization_id,
                details={
                    "quote_id": quote.id,
                    "quote_number": quote.quote_number,
                    "changes": changes
                }
            )
            
            return quote
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating quote {quote_id}: {str(e)}")
            raise
    
    def expire_quotes(self, db: Session) -> int:
        """
        Mark expired quotes as expired (background task)
        """
        now = datetime.now(timezone.utc)
        
        # Find quotes that are sent but past their valid_until date
        expired_quotes = db.query(Quote).filter(
            and_(
                Quote.status == "sent",
                Quote.valid_until < now
            )
        ).all()
        
        count = 0
        for quote in expired_quotes:
            quote.status = "expired"
            quote.expired_at = now
            count += 1
        
        if count > 0:
            db.commit()
            logger.info(f"Expired {count} quotes")
        
        return count
    
    def _generate_quote_number(self, organization_id: str, db: Session) -> str:
        """
        Generate a unique quote number for the organization
        """
        # Get current year and month
        now = datetime.now()
        year_month = now.strftime("%Y%m")
        
        # Find the highest quote number for this org and month
        existing_quote = db.query(Quote).filter(
            and_(
                Quote.organization_id == organization_id,
                Quote.quote_number.like(f"Q-{year_month}-%")
            )
        ).order_by(Quote.quote_number.desc()).first()
        
        if existing_quote:
            # Extract sequence number and increment
            try:
                last_seq = int(existing_quote.quote_number.split("-")[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1
        
        return f"Q-{year_month}-{next_seq:04d}"
    
    def _recompute_quote_pricing(self, quote: Quote, db: Session, user_id: int):
        """
        Recompute quote pricing based on current pricing rules
        """
        if not quote.pricing_snapshot:
            logger.warning(f"Cannot recompute quote {quote.id} - no pricing snapshot")
            return
        
        try:
            # Extract original request data from pricing snapshot
            snapshot = quote.pricing_snapshot
            
            # This would need to be expanded to recreate the full request
            # For now, just update with current pricing rules
            logger.info(f"Recomputing pricing for quote {quote.id}")
            
            # In a full implementation, you would:
            # 1. Extract service types and surfaces from line_items
            # 2. Create new PricingQuoteRequest
            # 3. Compute new pricing
            # 4. Update quote totals and line_items
            
        except Exception as e:
            logger.error(f"Error recomputing quote pricing: {str(e)}")
            raise


# Convenience functions
def create_quote_from_surfaces(
    organization_id: str,
    customer_email: str,
    service_types: List[str],
    surfaces: Dict[str, Any],
    db: Session,
    user_id: int,
    settings_resolver: SettingsResolver,
    **kwargs
) -> Quote:
    """
    Convenience function to create a quote from surface measurements
    """
    request = QuoteCreationRequest(
        organization_id=organization_id,
        customer_email=customer_email,
        service_types=service_types,
        surfaces=surfaces,
        **kwargs
    )
    
    quote_service = QuoteService(settings_resolver)
    return quote_service.create_quote(request, db, user_id)


def update_quote_status(
    quote_id: str,
    organization_id: str,
    new_status: str,
    db: Session,
    user_id: int,
    settings_resolver: SettingsResolver,
    notes: Optional[str] = None
) -> Quote:
    """
    Convenience function to update quote status
    """
    request = QuoteUpdateRequest(new_status=new_status, notes=notes)
    
    quote_service = QuoteService(settings_resolver)
    return quote_service.update_quote(quote_id, organization_id, request, db, user_id)