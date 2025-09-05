#!/usr/bin/env python3
"""
Update existing Plan records with Stripe product and price IDs
This script adds sample/development Stripe IDs to our plans
"""
import sys
import os
sys.path.append('/Users/jeffreyhacker/Lily-Media.AI/socialmedia2')

from backend.db.database import SessionLocal, engine
from backend.db.models import Plan
from sqlalchemy import text

def update_stripe_price_ids():
    """Update Plan records with Stripe product and price IDs"""
    
    print("🔧 Updating Plan records with Stripe integration IDs...")
    
    try:
        db = SessionLocal()
        
        # Sample Stripe IDs for development/testing
        # In production, these would be real Stripe product/price IDs from your Stripe dashboard
        stripe_mappings = {
            "starter": {
                "product_id": "prod_starter_dev",
                "monthly_price_id": "price_starter_monthly_dev",
                "annual_price_id": "price_starter_annual_dev"
            },
            "pro": {
                "product_id": "prod_pro_dev", 
                "monthly_price_id": "price_pro_monthly_dev",
                "annual_price_id": "price_pro_annual_dev"
            },
            "enterprise": {
                "product_id": "prod_enterprise_dev",
                "monthly_price_id": "price_enterprise_monthly_dev", 
                "annual_price_id": "price_enterprise_annual_dev"
            }
        }
        
        # Get all existing plans
        plans = db.query(Plan).all()
        
        updated_count = 0
        for plan in plans:
            mapping = stripe_mappings.get(plan.name.lower())
            if mapping:
                # Update the plan with Stripe IDs
                plan.stripe_product_id = mapping["product_id"]
                plan.stripe_monthly_price_id = mapping["monthly_price_id"]
                plan.stripe_annual_price_id = mapping["annual_price_id"]
                
                print(f"✅ Updated {plan.name}: {mapping['product_id']}")
                updated_count += 1
            else:
                print(f"⚠️  No Stripe mapping found for plan: {plan.name}")
        
        # Commit changes
        db.commit()
        print(f"✅ Successfully updated {updated_count} plans with Stripe IDs")
        
        # Verify the updates
        print("\n📋 Plan verification:")
        plans = db.query(Plan).all()
        for plan in plans:
            print(f"  - {plan.name}: Product={plan.stripe_product_id}, Monthly={plan.stripe_monthly_price_id}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating Stripe IDs: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

def verify_stripe_integration():
    """Verify that Stripe integration is properly configured"""
    
    print("\n🔍 Verifying Stripe integration setup...")
    
    try:
        db = SessionLocal()
        
        # Check that all plans have Stripe IDs
        plans_without_stripe = db.query(Plan).filter(
            (Plan.stripe_product_id.is_(None)) | 
            (Plan.stripe_monthly_price_id.is_(None))
        ).all()
        
        if plans_without_stripe:
            print(f"⚠️  Found {len(plans_without_stripe)} plans without Stripe IDs:")
            for plan in plans_without_stripe:
                print(f"     - {plan.name}")
        else:
            print("✅ All plans have Stripe integration configured")
        
        # Check environment variables
        stripe_secret = os.getenv("STRIPE_SECRET_KEY")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        env_status = {
            "STRIPE_SECRET_KEY": "✅ Set" if stripe_secret else "❌ Missing",
            "STRIPE_WEBHOOK_SECRET": "✅ Set" if webhook_secret else "❌ Missing"
        }
        
        print(f"\n🔑 Environment Variables:")
        for var, status in env_status.items():
            print(f"     {var}: {status}")
        
        if stripe_secret and webhook_secret:
            print("✅ Stripe environment is properly configured")
        else:
            print("⚠️  Some Stripe environment variables are missing")
            print("   Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET for full functionality")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying Stripe integration: {e}")
        if 'db' in locals():
            db.close()
        return False

if __name__ == "__main__":
    print("🎯 Stripe Integration Setup for Plan-Based Billing")
    print("=" * 60)
    
    # Update Stripe price IDs
    if update_stripe_price_ids():
        # Verify the integration
        verify_stripe_integration()
        print("\n🎉 Stripe integration setup completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Set up real Stripe products in your Stripe dashboard")
        print("   2. Update the price IDs in this script with real Stripe IDs")
        print("   3. Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET environment variables")
        print("   4. Test the billing endpoints with your frontend")
    else:
        print("❌ Setup failed. Please check the errors above.")
        sys.exit(1)