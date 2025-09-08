🚿 **PRESSURE WASHING IMPLEMENTATION**: See PRESSURE_WASHING_TODO.md for all features to implement
- When working on pressure washing features, ALWAYS check PRESSURE_WASHING_TODO.md first
- Update PRESSURE_WASHING_TODO.md as you plan and implement features
- Use PRESSURE_WASHING_TODO.md for multi-agent coordination

- Only write production-ready code, no mock, fake, demo, or placeholder code
- Always write production ready code
- Never create mock data, designs, or code
- when making edits or additions, check any related API endpoints and ensure all are properly connected
- when finished make changes, test build, commit to remote git repo
- Unless explicity required, you (claude) will do everything you can to avoid manual intervention during the process of fixing, update, or editing this project

# Current System Status (December 2024) - Pressure Washing Industry Focus

## 🔴 IMPORTANT: Read PRESSURE_WASHING_TODO.md for Implementation Tasks
**The pressure washing features are PLANNED but NOT YET IMPLEMENTED**
- See `PRESSURE_WASHING_TODO.md` for the complete implementation roadmap
- Update that file daily with progress and new requirements
- Use it for multi-agent coordination and task planning

## Pressure Washing Industry Pivot Status 🔶
- **COMPLETED**: Landing page messaging and documentation updated
- **IN PROGRESS**: Planning implementation of pressure washing features
- **NOT STARTED**: AI training for pressure washing terminology
- **NOT STARTED**: Field service software integrations
- **NOT STARTED**: DM→Booking conversion flow

## Pressure Washing Customer Journey (PLANNED) 🔶
- **DM→BOOKING FLOW**: [TO BUILD] Automated response system for pricing inquiries
- **Industry Knowledge**: [TO BUILD] AI training on pressure washing terminology
- **Weather Integration**: [TO BUILD] Rain delay and seasonal promotion handling
- **Lead Qualification**: [TO BUILD] Photo capture and surface detail collection
- **Before/After Automation**: [TO BUILD] Transformation post creation
- **Field Service Integration**: [TO BUILD] Housecall Pro, Jobber connections

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

## Planned Pressure Washing Capabilities (See PRESSURE_WASHING_TODO.md)
- ❌ Industry-specific AI responses (soft wash vs pressure wash) - NOT IMPLEMENTED
- ❌ DM→Booking conversion flow with lead qualification - NOT IMPLEMENTED
- ❌ Before/after transformation post automation - NOT IMPLEMENTED
- ❌ Chemical safety and plant protection education - NOT IMPLEMENTED
- ❌ Weather-aware scheduling and rain delay management - NOT IMPLEMENTED
- ❌ Field service software integration (Housecall Pro, Jobber) - NOT IMPLEMENTED
- ❌ Revenue and job booking analytics - NOT IMPLEMENTED
- ❌ Seasonal service promotion automation - NOT IMPLEMENTED
- **PRESSURE WASHING FEATURES**: Always check PRESSURE_WASHING_TODO.md for implementation status
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