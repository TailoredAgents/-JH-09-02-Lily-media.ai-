"""
Pressure washing pricing engine with org-scoped rules and quote computation
"""

from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
import math
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.db.models import PricingRule, Organization, User
from backend.services.settings_resolver import SettingsResolver, PricingSettings

logger = logging.getLogger(__name__)


class PricingQuoteRequest:
    """Request model for pricing quote computation"""
    
    def __init__(
        self,
        organization_id: str,
        service_types: List[str],
        surfaces: Dict[str, Any],
        location: Optional[Dict[str, Any]] = None,
        preferred_date: Optional[date] = None,
        additional_services: Optional[List[str]] = None,
        customer_tier: str = "standard",
        rush_job: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.organization_id = organization_id
        self.service_types = service_types or []
        self.surfaces = surfaces or {}
        self.location = location or {}
        self.preferred_date = preferred_date
        self.additional_services = additional_services or []
        self.customer_tier = customer_tier
        self.rush_job = rush_job
        self.metadata = metadata or {}


class PricingQuote:
    """Computed pricing quote result"""
    
    def __init__(self):
        self.base_total: Decimal = Decimal('0.00')
        self.bundle_discount: Decimal = Decimal('0.00')
        self.seasonal_modifier: Decimal = Decimal('0.00')
        self.travel_fee: Decimal = Decimal('0.00')
        self.rush_fee: Decimal = Decimal('0.00')
        self.additional_services_total: Decimal = Decimal('0.00')
        self.subtotal: Decimal = Decimal('0.00')
        self.tax_rate: Decimal = Decimal('0.00')
        self.tax_amount: Decimal = Decimal('0.00')
        self.total: Decimal = Decimal('0.00')
        self.currency: str = "USD"
        self.breakdown: List[Dict[str, Any]] = []
        self.applied_rules: List[str] = []
        self.warning_messages: List[str] = []
        self.valid_until: Optional[datetime] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert quote to dictionary for JSON serialization"""
        return {
            "base_total": float(self.base_total),
            "bundle_discount": float(self.bundle_discount),
            "seasonal_modifier": float(self.seasonal_modifier),
            "travel_fee": float(self.travel_fee),
            "rush_fee": float(self.rush_fee),
            "additional_services_total": float(self.additional_services_total),
            "subtotal": float(self.subtotal),
            "tax_rate": float(self.tax_rate),
            "tax_amount": float(self.tax_amount),
            "total": float(self.total),
            "currency": self.currency,
            "breakdown": self.breakdown,
            "applied_rules": self.applied_rules,
            "warning_messages": self.warning_messages,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }


class PricingService:
    """
    Pressure washing pricing engine with organization-scoped rules
    """
    
    def __init__(self, settings_resolver: SettingsResolver):
        self.settings_resolver = settings_resolver
    
    def compute_quote(
        self, 
        request: PricingQuoteRequest, 
        db: Session,
        user_id: int
    ) -> PricingQuote:
        """
        Compute a comprehensive pricing quote based on organization rules
        """
        try:
            # Get active pricing rule for organization
            pricing_rule = self._get_active_pricing_rule(request.organization_id, db)
            if not pricing_rule:
                raise ValueError(f"No active pricing rules found for organization {request.organization_id}")
            
            # Get pricing settings from settings resolver
            pricing_settings = self.settings_resolver.get_pricing_settings(
                request.organization_id, db, user_id
            )
            
            quote = PricingQuote()
            quote.currency = pricing_rule.currency
            quote.applied_rules.append(pricing_rule.name)
            
            # 1. Calculate base pricing for services and surfaces
            self._calculate_base_pricing(request, pricing_rule, quote)
            
            # 2. Apply bundle discounts if applicable
            self._apply_bundle_discounts(request, pricing_rule, quote)
            
            # 3. Apply seasonal modifiers
            self._apply_seasonal_modifiers(request, pricing_rule, quote)
            
            # 4. Calculate travel fees
            self._calculate_travel_fees(request, pricing_rule, quote)
            
            # 5. Add rush job fees if applicable
            self._apply_rush_fees(request, pricing_rule, quote)
            
            # 6. Calculate additional services
            self._calculate_additional_services(request, pricing_rule, quote)
            
            # 7. Apply business rules and constraints
            self._apply_business_rules(request, pricing_rule, quote)
            
            # 8. Calculate subtotal
            quote.subtotal = (
                quote.base_total + 
                quote.bundle_discount +  # Note: bundle_discount is negative
                quote.seasonal_modifier + 
                quote.travel_fee + 
                quote.rush_fee + 
                quote.additional_services_total
            )
            
            # 9. Apply tax calculations
            self._calculate_taxes(request, pricing_rule, pricing_settings, quote)
            
            # 10. Set quote validity period
            self._set_quote_validity(pricing_rule, quote)
            
            # Ensure minimum job total
            if quote.total < pricing_rule.min_job_total:
                original_total = quote.total
                quote.total = pricing_rule.min_job_total
                quote.warning_messages.append(
                    f"Quote adjusted to minimum job total: {quote.currency} {pricing_rule.min_job_total}"
                )
                quote.breakdown.append({
                    "type": "minimum_adjustment",
                    "description": "Minimum job total adjustment",
                    "original_amount": float(original_total),
                    "adjusted_amount": float(quote.total)
                })
            
            return quote
            
        except Exception as e:
            logger.error(f"Error computing pricing quote: {str(e)}")
            raise
    
    def _get_active_pricing_rule(self, organization_id: str, db: Session) -> Optional[PricingRule]:
        """Get the active pricing rule for an organization with highest priority"""
        now = datetime.now(timezone.utc)
        
        pricing_rule = db.query(PricingRule).filter(
            and_(
                PricingRule.organization_id == organization_id,
                PricingRule.is_active == True,
                or_(
                    PricingRule.effective_from == None,
                    PricingRule.effective_from <= now
                ),
                or_(
                    PricingRule.effective_until == None,
                    PricingRule.effective_until >= now
                )
            )
        ).order_by(
            PricingRule.priority.desc(),
            PricingRule.created_at.desc()
        ).first()
        
        return pricing_rule
    
    def _calculate_base_pricing(self, request: PricingQuoteRequest, pricing_rule: PricingRule, quote: PricingQuote):
        """Calculate base pricing for services and surfaces"""
        base_rates = pricing_rule.base_rates
        
        for service_type in request.service_types:
            if service_type not in base_rates:
                quote.warning_messages.append(f"No base rate found for service type: {service_type}")
                continue
                
            service_rates = base_rates[service_type]
            service_total = Decimal('0.00')
            
            # Calculate pricing based on surface measurements
            if "surfaces" in service_rates:
                for surface_type, surface_data in request.surfaces.items():
                    if surface_type in service_rates["surfaces"]:
                        surface_rate = Decimal(str(service_rates["surfaces"][surface_type]))
                        area = Decimal(str(surface_data.get("area", 0)))
                        surface_cost = surface_rate * area
                        service_total += surface_cost
                        
                        quote.breakdown.append({
                            "type": "base_service",
                            "service": service_type,
                            "surface": surface_type,
                            "area": float(area),
                            "rate": float(surface_rate),
                            "amount": float(surface_cost)
                        })
            
            # Apply flat rate if specified
            if "flat_rate" in service_rates and service_total == 0:
                flat_rate = Decimal(str(service_rates["flat_rate"]))
                service_total = flat_rate
                
                quote.breakdown.append({
                    "type": "base_service",
                    "service": service_type,
                    "rate_type": "flat_rate",
                    "amount": float(flat_rate)
                })
            
            quote.base_total += service_total
    
    def _apply_bundle_discounts(self, request: PricingQuoteRequest, pricing_rule: PricingRule, quote: PricingQuote):
        """Apply bundle discounts for multiple services"""
        bundles = pricing_rule.bundles
        
        for bundle in bundles:
            bundle_services = set(bundle.get("services", []))
            request_services = set(request.service_types)
            
            # Check if all bundle services are included in request
            if bundle_services.issubset(request_services):
                discount_type = bundle.get("discount_type", "percentage")
                discount_value = Decimal(str(bundle.get("discount_value", 0)))
                
                if discount_type == "percentage":
                    discount_amount = quote.base_total * (discount_value / Decimal('100'))
                else:  # flat discount
                    discount_amount = discount_value
                
                # Bundle discounts are negative (reduce total)
                quote.bundle_discount -= discount_amount
                
                quote.breakdown.append({
                    "type": "bundle_discount",
                    "bundle_name": bundle.get("name", "Bundle Discount"),
                    "services": list(bundle_services),
                    "discount_type": discount_type,
                    "discount_value": float(discount_value),
                    "amount": float(-discount_amount)
                })
                
                break  # Apply only the first matching bundle
    
    def _apply_seasonal_modifiers(self, request: PricingQuoteRequest, pricing_rule: PricingRule, quote: PricingQuote):
        """Apply seasonal pricing modifiers"""
        if not request.preferred_date:
            return
            
        seasonal_modifiers = pricing_rule.seasonal_modifiers
        current_month = request.preferred_date.month
        
        # Check for specific month modifiers
        month_key = str(current_month)
        if month_key in seasonal_modifiers:
            modifier = Decimal(str(seasonal_modifiers[month_key]))
            modifier_amount = quote.base_total * (modifier / Decimal('100'))
            quote.seasonal_modifier += modifier_amount
            
            quote.breakdown.append({
                "type": "seasonal_modifier",
                "month": current_month,
                "modifier_percent": float(modifier),
                "amount": float(modifier_amount)
            })
        
        # Check for season-based modifiers
        season = self._get_season(current_month)
        if season in seasonal_modifiers:
            modifier = Decimal(str(seasonal_modifiers[season]))
            modifier_amount = quote.base_total * (modifier / Decimal('100'))
            quote.seasonal_modifier += modifier_amount
            
            quote.breakdown.append({
                "type": "seasonal_modifier",
                "season": season,
                "modifier_percent": float(modifier),
                "amount": float(modifier_amount)
            })
    
    def _calculate_travel_fees(self, request: PricingQuoteRequest, pricing_rule: PricingRule, quote: PricingQuote):
        """Calculate travel fees based on distance"""
        travel_settings = pricing_rule.travel_settings
        
        if not request.location or "distance_miles" not in request.location:
            return
            
        distance = Decimal(str(request.location["distance_miles"]))
        
        # Check if within free travel radius
        free_radius = Decimal(str(travel_settings.get("free_radius_miles", 0)))
        if distance <= free_radius:
            return
            
        # Calculate travel fee
        rate_per_mile = Decimal(str(travel_settings.get("rate_per_mile", 0)))
        min_travel_fee = Decimal(str(travel_settings.get("minimum_fee", 0)))
        
        billable_distance = distance - free_radius
        calculated_fee = billable_distance * rate_per_mile
        travel_fee = max(calculated_fee, min_travel_fee)
        
        quote.travel_fee = travel_fee
        
        quote.breakdown.append({
            "type": "travel_fee",
            "total_distance": float(distance),
            "free_radius": float(free_radius),
            "billable_distance": float(billable_distance),
            "rate_per_mile": float(rate_per_mile),
            "amount": float(travel_fee)
        })
    
    def _apply_rush_fees(self, request: PricingQuoteRequest, pricing_rule: PricingRule, quote: PricingQuote):
        """Apply rush job fees if applicable"""
        if not request.rush_job:
            return
            
        business_rules = pricing_rule.business_rules
        rush_fee_config = business_rules.get("rush_fee", {})
        
        if not rush_fee_config.get("enabled", False):
            return
            
        fee_type = rush_fee_config.get("type", "percentage")
        fee_value = Decimal(str(rush_fee_config.get("value", 0)))
        
        if fee_type == "percentage":
            rush_fee = quote.base_total * (fee_value / Decimal('100'))
        else:  # flat fee
            rush_fee = fee_value
        
        quote.rush_fee = rush_fee
        
        quote.breakdown.append({
            "type": "rush_fee",
            "fee_type": fee_type,
            "fee_value": float(fee_value),
            "amount": float(rush_fee)
        })
    
    def _calculate_additional_services(self, request: PricingQuoteRequest, pricing_rule: PricingRule, quote: PricingQuote):
        """Calculate pricing for additional services"""
        additional_services = pricing_rule.additional_services
        
        for service_name in request.additional_services:
            if service_name not in additional_services:
                quote.warning_messages.append(f"Additional service not found: {service_name}")
                continue
                
            service_config = additional_services[service_name]
            service_cost = Decimal(str(service_config.get("price", 0)))
            
            quote.additional_services_total += service_cost
            
            quote.breakdown.append({
                "type": "additional_service",
                "service": service_name,
                "description": service_config.get("description", ""),
                "amount": float(service_cost)
            })
    
    def _apply_business_rules(self, request: PricingQuoteRequest, pricing_rule: PricingRule, quote: PricingQuote):
        """Apply business rules and constraints"""
        business_rules = pricing_rule.business_rules
        
        # Apply customer tier discounts
        tier_discounts = business_rules.get("customer_tiers", {})
        if request.customer_tier in tier_discounts:
            tier_config = tier_discounts[request.customer_tier]
            discount_percent = Decimal(str(tier_config.get("discount_percent", 0)))
            
            if discount_percent > 0:
                tier_discount = quote.base_total * (discount_percent / Decimal('100'))
                quote.base_total -= tier_discount
                
                quote.breakdown.append({
                    "type": "customer_tier_discount",
                    "tier": request.customer_tier,
                    "discount_percent": float(discount_percent),
                    "amount": float(-tier_discount)
                })
    
    def _calculate_taxes(self, request: PricingQuoteRequest, pricing_rule: PricingRule, pricing_settings: PricingSettings, quote: PricingQuote):
        """Calculate tax amounts"""
        # Use tax rate from pricing settings or fallback to business rules
        tax_rate = Decimal(str(pricing_settings.tax_rate))
        if tax_rate == 0:
            business_rules = pricing_rule.business_rules
            tax_rate = Decimal(str(business_rules.get("tax_rate", 0)))
        
        quote.tax_rate = tax_rate
        quote.tax_amount = quote.subtotal * (tax_rate / Decimal('100'))
        quote.total = quote.subtotal + quote.tax_amount
        
        if quote.tax_amount > 0:
            quote.breakdown.append({
                "type": "tax",
                "tax_rate": float(tax_rate),
                "taxable_amount": float(quote.subtotal),
                "amount": float(quote.tax_amount)
            })
    
    def _set_quote_validity(self, pricing_rule: PricingRule, quote: PricingQuote):
        """Set quote validity period"""
        business_rules = pricing_rule.business_rules
        validity_days = business_rules.get("quote_validity_days", 30)
        
        quote.valid_until = datetime.now(timezone.utc).replace(
            hour=23, minute=59, second=59, microsecond=0
        ) + timezone.utc.localize(datetime.now()).replace(
            tzinfo=None
        ).replace(
            day=datetime.now().day + validity_days
        ).replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    
    def _get_season(self, month: int) -> str:
        """Get season name from month number"""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "fall"
        return "unknown"


# Convenience function for standalone usage
def compute_pricing_quote(
    organization_id: str,
    service_types: List[str],
    surfaces: Dict[str, Any],
    db: Session,
    user_id: int,
    settings_resolver: SettingsResolver,
    **kwargs
) -> PricingQuote:
    """
    Convenience function to compute a pricing quote
    """
    request = PricingQuoteRequest(
        organization_id=organization_id,
        service_types=service_types,
        surfaces=surfaces,
        **kwargs
    )
    
    pricing_service = PricingService(settings_resolver)
    return pricing_service.compute_quote(request, db, user_id)