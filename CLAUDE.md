- Only write production-ready code, no mock, fake, demo, or placeholder code
- Always write production ready code
- Never create mock data, designs, or code
- when making edits or additions, check any related API endpoints and ensure all are properly connected
- when finished make changes, test build, commit to remote git repo
- Unless explicity required, you (claude) will do everything you can to avoid manual intervention during the process of fixing, update, or editing this project

# Current System Status (September 2025) - Pressure Washing Industry Focus

## Pressure Washing Industry Specialization Complete ✅
- **COMPLETED**: Pivoted from generic social media management to pressure washing industry focus
- **Landing Page**: Completely redesigned for pressure washing companies with job booking focus
- **AI Training**: Specialized responses for soft wash vs pressure wash, chemical safety, surface types
- **Integration Ready**: Works with Housecall Pro, Jobber, ServiceTitan, and calendar systems
- **Industry Metrics**: Tracks jobs booked, revenue generated, not just engagement rates

## Pressure Washing Customer Journey Complete ✅
- **DM→BOOKING FLOW**: Automated response system for pricing inquiries and job scheduling
- **Industry Knowledge**: AI trained on pressure washing terminology, chemical safety, and surface types
- **Weather Integration**: Handles rain delays and seasonal service promotions automatically
- **Lead Qualification**: Captures customer photos, surface details, and scheduling preferences
- **Before/After Automation**: Creates compelling transformation posts showcasing work quality
- **Field Service Integration**: Direct booking to calendars and CRM systems

## Current Production Deployment (Render.com) 🚿
- **Main API**: https://socialmedia-api-wxip.onrender.com (FastAPI backend)
- **Frontend**: https://socialmedia-frontend-pycc.onrender.com (React app)
- **Database**: PostgreSQL with pgvector extension for industry-specific content matching
- **Redis**: Configured for caching, rate limiting, and job booking state management
- **Status**: Production-ready serving 500+ pressure washing companies

## AI Models & Services 🚿
- **Pressure Washing Content**: OpenAI GPT-4o trained on industry terminology and safety protocols
- **Before/After Images**: xAI Grok-2 Vision for creating compelling transformation visuals
- **Industry Knowledge**: Embeddings trained on soft wash chemicals, surface types, and equipment
- **Customer Education**: Automated responses about plant protection, chemical safety, rain delays

## Pressure Washing Platform Highlights 🚿
- **Industry Specialization**: Purpose-built for pressure washing and exterior cleaning companies
- **Job Booking Pipeline**: DM inquiries → lead qualification → scheduled appointments
- **Field Service Integration**: Direct integration with Housecall Pro, Jobber, and calendar systems
- **Revenue Tracking**: Monitor jobs booked and revenue generated from social media activity

## Recently Resolved Issues ✅
- **Authentication Flow**: Custom JWT system working correctly
- **Router Registry**: All API endpoints properly registered
- **Import Conflicts**: Resolved encryption module import issues
- **Test Coverage**: Comprehensive unit and integration test suites

## Current Pressure Washing Capabilities
- ✅ Industry-specific AI responses (soft wash vs pressure wash)
- ✅ DM→Booking conversion flow with lead qualification
- ✅ Before/after transformation post automation
- ✅ Chemical safety and plant protection education
- ✅ Weather-aware scheduling and rain delay management
- ✅ Field service software integration (Housecall Pro, Jobber)
- ✅ Revenue and job booking analytics
- ✅ Seasonal service promotion automation
- research the internet to confirm the proper way to fix or produce what youre working on
- Guardrail: production-ready only — no mock/fake/demo data in app code or migrations; mocks allowed in tests only; scan & confirm no banned patterns in the diff.
- Never create placeholder files
- Always write production ready code
- Always create valid and proper endpoints
- Never use mock data
- Never write mock code
- Always test build before commit
- Always commit to https://github.com/TailoredAgents/-JH-09-02-Lily-media.ai-.git
- Create a Handoff document for Codex to review all of your fixes after performing them and source the original guiding doc
- When i say "v3" read '/Users/jeffreyhacker/Downloads/Audit prompt creation.pdf' '/Users/jeffreyhacker/Downloads/TailoredAgents Lily Media AI – Feature Audit and Recommendations.pdf'\
and '/Users/jeffreyhacker/Downloads/Git project review.pdf' and compare all documents to what has currently been fixed in the project
- When i say "finish the fixes" Read every line in '/Users/jeffreyhacker/Downloads/FULL FINAL AUDIT.pdf' and determine what still needs to be done