"""
Production Research Automation Service - replaces all mock implementations
Uses real APIs for comprehensive social media and market research
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

from backend.services.real_trends_service import RealTrendsService
from backend.services.real_social_research_service import RealSocialResearchService
from backend.services.web_research_service import WebResearchService
from backend.services.ai_insights_service import ai_insights_service
from backend.services.research_monitoring import get_research_monitoring_service, ResearchOperationTracker
from backend.core.config import get_settings
from backend.core.feature_flags import ff

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class ResearchQuery:
    """Research query configuration"""
    keywords: List[str]
    platforms: List[str]
    max_results: int = 20
    include_trends: bool = True
    include_competitors: bool = False
    timeframe: str = "7d"

@dataclass
class ResearchResult:
    """Research result data structure"""
    source: str
    platform: str
    content_id: str
    title: str
    content: str
    author: str
    published_at: datetime
    url: str
    engagement_metrics: Dict[str, Any]
    sentiment_score: float
    trending_score: float
    relevance_score: float
    media_urls: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None

class ProductionResearchAutomationService:
    """Production research service with real API integrations"""
    
    def __init__(self):
        self.trends_service = RealTrendsService()
        self.social_research_service = RealSocialResearchService()
        self.web_research_service = WebResearchService()
        # P0-10c: Initialize research monitoring service
        self.monitoring_service = get_research_monitoring_service()
        
    async def execute_comprehensive_research(self, query: ResearchQuery, user_plan: str = "unknown", 
                                           user_id: Optional[str] = None, industry: Optional[str] = None) -> Dict[str, Any]:
        """Execute comprehensive research using real APIs with proper feature gating and monitoring"""
        
        # P0-10c: Track research request
        self.monitoring_service.track_research_request(
            research_type="comprehensive_research",
            user_plan=user_plan,
            industry=industry or "general", 
            status="started"
        )
        
        # Use monitoring context manager for automatic tracking
        with ResearchOperationTracker("comprehensive_research", user_plan, industry):
            try:
                # P0-10b: RESEARCH FEATURE GATING - Check required research flags
                research_feature_validation = self._validate_research_features(query)
                if not research_feature_validation["allowed"]:
                    # Track feature gating rejection
                    self.monitoring_service.track_plan_enforcement(
                        action="feature_blocked",
                        user_plan=user_plan,
                        feature="comprehensive_research"
                    )
                    self.monitoring_service.track_research_request(
                        research_type="comprehensive_research",
                        user_plan=user_plan,
                        industry=industry or "general",
                        status="feature_blocked"
                    )
                    return research_feature_validation
                
                logger.info(f"Research feature validation passed - executing comprehensive research")
                
                research_results = {
                'query': query,
                'execution_time': datetime.utcnow().isoformat(),
                'platforms_researched': [],
                'results': {
                    'social_media': {},
                    'trends': {},
                    'web_research': {},
                    'ai_insights': {}
                },
                'summary': {
                    'total_results': 0,
                    'platforms_analyzed': 0,
                    'research_quality_score': 0,
                    'execution_method': 'production_apis'
                }
                }
                
                # Execute platform-specific research in parallel
                research_tasks = []
            
                if 'twitter' in query.platforms:
                    research_tasks.append(self._research_twitter(query.keywords[0]))
                    
                if 'instagram' in query.platforms:
                    research_tasks.append(self._research_instagram(query.keywords[0]))
                    
                if 'linkedin' in query.platforms:
                    research_tasks.append(self._research_linkedin(query.keywords[0]))
                    
                if 'youtube' in query.platforms:
                    research_tasks.append(self._research_youtube(query.keywords[0]))
                
                # Execute trends research
                if query.include_trends:
                    research_tasks.append(self._research_trends(query.keywords))
                
                # Execute web research
                research_tasks.append(self._research_web_content(query.keywords[0]))
                
                # Execute AI insights
                research_tasks.append(self._get_ai_insights(query.keywords[0]))
            
                # Run all research tasks concurrently
                task_results = await asyncio.gather(*research_tasks, return_exceptions=True)
                
                # Process results
                platform_index = 0
                for i, platform in enumerate(['twitter', 'instagram', 'linkedin', 'youtube']):
                    if platform in query.platforms:
                        result = task_results[platform_index]
                        if not isinstance(result, Exception):
                            research_results['results']['social_media'][platform] = result
                            research_results['platforms_researched'].append(platform)
                            research_results['summary']['platforms_analyzed'] += 1
                        else:
                            logger.error(f"Failed to research {platform}: {result}")
                        platform_index += 1
            
                # Process trends results
                if query.include_trends and platform_index < len(task_results):
                    trends_result = task_results[platform_index]
                    if not isinstance(trends_result, Exception):
                        research_results['results']['trends'] = trends_result
                    platform_index += 1
                
                # Process web research results
                if platform_index < len(task_results):
                    web_result = task_results[platform_index]
                    if not isinstance(web_result, Exception):
                        research_results['results']['web_research'] = web_result
                    platform_index += 1
                
                # Process AI insights results
                if platform_index < len(task_results):
                    ai_result = task_results[platform_index]
                    if not isinstance(ai_result, Exception):
                        research_results['results']['ai_insights'] = ai_result
            
                # Calculate summary metrics
                total_results = 0
                for category, data in research_results['results'].items():
                    if isinstance(data, dict):
                        # Count items in each category
                        for platform, platform_data in data.items():
                            if isinstance(platform_data, dict):
                                for key, value in platform_data.items():
                                    if isinstance(value, list):
                                        total_results += len(value)
                            elif isinstance(platform_data, list):
                                total_results += len(platform_data)
                
                research_results['summary']['total_results'] = total_results
                research_results['summary']['research_quality_score'] = min(
                    (research_results['summary']['platforms_analyzed'] * 25) + 
                    min(total_results * 2, 50), 100
                )
            
                # P0-10c: Track comprehensive research completion metrics
                quality_score = research_results['summary']['research_quality_score']
                
                # Track successful research completion
                self.monitoring_service.track_research_request(
                    research_type="comprehensive_research",
                    user_plan=user_plan,
                    industry=industry or "general",
                    status="completed"
                )
                
                # Track content opportunities if high quality
                if quality_score > 60:
                    opportunity_count = max(1, total_results // 10)  # Estimate content opportunities
                    for i in range(min(opportunity_count, 5)):  # Cap at 5 for cardinality
                        self.monitoring_service.track_content_opportunity(
                            industry=industry or "general",
                            urgency="normal",
                            opportunity_type="research_insight",
                            quality_score=quality_score
                        )
                
                # Track platform coverage metrics
                for platform in research_results['platforms_researched']:
                    self.monitoring_service.track_research_request(
                        research_type=f"platform_{platform}",
                        user_plan=user_plan,
                        industry=industry or "general",
                        status="completed"
                    )
                
                # Track quota usage for this research operation
                if user_id:
                    self.monitoring_service.track_quota_usage(
                        feature="comprehensive_research",
                        user_id=user_id,
                        user_plan=user_plan,
                        amount=1
                    )
                
                logger.info(f"Completed comprehensive research for {len(query.keywords)} keywords across {len(query.platforms)} platforms")
                logger.info(f"Research metrics: {total_results} results, quality={quality_score}, platforms={research_results['summary']['platforms_analyzed']}")
                return research_results
            
            except Exception as e:
                # P0-10c: Track research errors
                self.monitoring_service.track_research_error(
                    error_type=type(e).__name__,
                    component="comprehensive_research",
                    severity="error"
                )
                self.monitoring_service.track_research_request(
                    research_type="comprehensive_research",
                    user_plan=user_plan,
                    industry=industry or "general",
                    status="failed"
                )
                logger.error(f"Failed to execute comprehensive research: {e}")
                raise
    
    async def _research_twitter(self, topic: str) -> Dict[str, Any]:
        """Research Twitter using real API data"""
        try:
            twitter_data = self.social_research_service.research_twitter_trends(topic, limit=8)
            
            # Convert to ResearchResult format
            research_results = []
            for content in twitter_data.get('trending_content', []):
                result = ResearchResult(
                    source='twitter_serper_search',
                    platform='twitter',
                    content_id=f"twitter_{hash(content['title'])}",
                    title=content['title'],
                    content=content['summary'],
                    author=content.get('source', 'Unknown'),
                    published_at=datetime.fromisoformat(content.get('date', datetime.utcnow().isoformat())),
                    url=content['url'],
                    engagement_metrics={'source_authority': 'news_mention'},
                    sentiment_score=0.0,  # Could be enhanced with sentiment analysis
                    trending_score=0.8,   # High for news-mentioned content
                    relevance_score=0.9,
                    hashtags=content.get('hashtags_mentioned', [])
                )
                research_results.append(result)
            
            return {
                'platform': 'twitter',
                'research_method': 'serper_api',
                'results': [result.__dict__ for result in research_results],
                'insights': twitter_data.get('hashtag_insights', []),
                'engagement_patterns': twitter_data.get('engagement_patterns', []),
                'metadata': twitter_data.get('research_summary', {})
            }
            
        except Exception as e:
            logger.error(f"Failed Twitter research: {e}")
            raise
    
    async def _research_instagram(self, topic: str) -> Dict[str, Any]:
        """Research Instagram using real API data"""
        try:
            instagram_data = self.social_research_service.research_instagram_content(topic)
            
            # Convert to ResearchResult format
            research_results = []
            for idea in instagram_data.get('content_ideas', []):
                result = ResearchResult(
                    source='instagram_serper_search',
                    platform='instagram',
                    content_id=f"instagram_{hash(idea['title'])}",
                    title=idea['title'],
                    content=idea['description'],
                    author=idea.get('source', 'Unknown'),
                    published_at=datetime.utcnow() - timedelta(days=1),  # Approximate
                    url=idea['url'],
                    engagement_metrics={'visual_elements': len(idea.get('visual_elements', []))},
                    sentiment_score=0.1,   # Generally positive for content ideas
                    trending_score=0.7,
                    relevance_score=0.8,
                    hashtags=idea.get('hashtags', [])
                )
                research_results.append(result)
            
            return {
                'platform': 'instagram',
                'research_method': 'serper_api',
                'results': [result.__dict__ for result in research_results],
                'hashtag_strategies': instagram_data.get('hashtag_strategies', []),
                'marketing_insights': instagram_data.get('marketing_insights', []),
                'metadata': instagram_data.get('research_summary', {})
            }
            
        except Exception as e:
            logger.error(f"Failed Instagram research: {e}")
            raise
    
    async def _research_linkedin(self, topic: str) -> Dict[str, Any]:
        """Research LinkedIn using real API data"""
        try:
            linkedin_data = self.social_research_service.research_linkedin_professional_content(topic)
            
            # Convert to ResearchResult format
            research_results = []
            for content in linkedin_data.get('professional_content', []):
                result = ResearchResult(
                    source='linkedin_serper_search',
                    platform='linkedin',
                    content_id=f"linkedin_{hash(content['title'])}",
                    title=content['title'],
                    content=content['summary'],
                    author=content.get('source', 'Professional'),
                    published_at=datetime.utcnow() - timedelta(days=2),  # Approximate
                    url=content['url'],
                    engagement_metrics={
                        'professional_signals': len(content.get('professional_signals', [])),
                        'thought_leadership': len(content.get('thought_leadership_signals', []))
                    },
                    sentiment_score=0.2,   # Professional content tends to be positive
                    trending_score=0.6,
                    relevance_score=0.9
                )
                research_results.append(result)
            
            return {
                'platform': 'linkedin',
                'research_method': 'serper_api',
                'results': [result.__dict__ for result in research_results],
                'thought_leadership_trends': linkedin_data.get('thought_leadership_trends', []),
                'engagement_strategies': linkedin_data.get('engagement_strategies', []),
                'industry_insights': linkedin_data.get('industry_insights', []),
                'metadata': linkedin_data.get('research_summary', {})
            }
            
        except Exception as e:
            logger.error(f"Failed LinkedIn research: {e}")
            raise
    
    async def _research_youtube(self, topic: str) -> Dict[str, Any]:
        """Research YouTube using real API data"""
        try:
            youtube_data = self.social_research_service.research_youtube_video_trends(topic)
            
            # Convert to ResearchResult format
            research_results = []
            for video in youtube_data.get('video_content', []):
                result = ResearchResult(
                    source='youtube_serper_search',
                    platform='youtube',
                    content_id=f"youtube_{hash(video['title'])}",
                    title=video['title'],
                    content=video['description'],
                    author='YouTube Creator',
                    published_at=datetime.utcnow() - timedelta(days=3),  # Approximate
                    url=video['url'],
                    engagement_metrics={
                        'estimated_popularity': video.get('estimated_popularity', 0),
                        'engagement_signals': len(video.get('engagement_signals', []))
                    },
                    sentiment_score=0.0,
                    trending_score=min(video.get('estimated_popularity', 0) / 100, 1.0),
                    relevance_score=0.8,
                    media_urls=[video['url']]
                )
                research_results.append(result)
            
            return {
                'platform': 'youtube',
                'research_method': 'serper_api',
                'results': [result.__dict__ for result in research_results],
                'trending_formats': youtube_data.get('trending_formats', []),
                'content_strategies': youtube_data.get('content_strategies', []),
                'metadata': youtube_data.get('research_summary', {})
            }
            
        except Exception as e:
            logger.error(f"Failed YouTube research: {e}")
            raise
    
    async def _research_trends(self, keywords: List[str]) -> Dict[str, Any]:
        """Research trends using real trend data"""
        try:
            # Get trending topics for the first keyword's category
            trending_topics = self.trends_service.get_trending_topics(
                category='general', 
                count=10
            )
            
            # Get search volume data for keywords
            search_volume_data = self.trends_service.get_search_volume_data(
                keywords[:3],  # Limit to avoid API limits
                timeframe='today 3-m'
            )
            
            # Get seasonal trends if available
            seasonal_trends = self.trends_service.get_seasonal_trends(
                keywords[:2],
                months_back=6
            )
            
            return {
                'trending_topics': trending_topics,
                'search_volume': search_volume_data,
                'seasonal_patterns': seasonal_trends,
                'research_method': 'real_trends_api'
            }
            
        except Exception as e:
            logger.error(f"Failed trends research: {e}")
            raise
    
    async def _research_web_content(self, topic: str) -> Dict[str, Any]:
        """Research web content using existing web research service"""
        try:
            # Use the existing web research service which already uses real APIs
            web_results = await self.web_research_service.search_web_content(
                query=topic,
                max_results=5
            )
            
            return {
                'web_research_results': web_results,
                'research_method': 'web_research_service'
            }
            
        except Exception as e:
            logger.error(f"Failed web research: {e}")
            return {'error': str(e), 'research_method': 'web_research_service'}
    
    async def _get_ai_insights(self, topic: str) -> Dict[str, Any]:
        """Get AI insights using existing service"""
        try:
            # Use the existing AI insights service which already uses real APIs
            insights = await ai_insights_service.generate_weekly_insights()
            
            # Filter insights relevant to the topic
            relevant_insights = []
            for insight in insights.get('insights', []):
                if topic.lower() in insight.get('content', '').lower() or topic.lower() in insight.get('title', '').lower():
                    relevant_insights.append(insight)
            
            return {
                'ai_insights': relevant_insights,
                'all_insights': insights,
                'research_method': 'ai_insights_service'
            }
            
        except Exception as e:
            logger.error(f"Failed AI insights: {e}")
            return {'error': str(e), 'research_method': 'ai_insights_service'}
    
    async def research_competitors(self, industry: str, competitor_names: List[str]) -> Dict[str, Any]:
        """Research competitors using real market data"""
        try:
            competitor_analysis = self.trends_service.get_competitor_trends(
                industry=industry,
                competitor_keywords=competitor_names
            )
            
            # Get cross-platform insights for competitors
            competitor_insights = {}
            for competitor in competitor_names[:3]:  # Limit to avoid API limits
                try:
                    insights = self.social_research_service.get_cross_platform_insights(competitor)
                    competitor_insights[competitor] = insights
                except Exception as e:
                    logger.warning(f"Failed to get insights for {competitor}: {e}")
                    competitor_insights[competitor] = {'error': str(e)}
            
            return {
                'industry': industry,
                'competitor_trends': competitor_analysis,
                'competitor_social_insights': competitor_insights,
                'analysis_summary': {
                    'competitors_analyzed': len(competitor_names),
                    'successful_analyses': len([c for c in competitor_insights.values() if 'error' not in c]),
                    'research_date': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed competitor research: {e}")
            raise
    
    async def get_research_summary(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive summary of research results"""
        try:
            summary = {
                'execution_summary': research_results.get('summary', {}),
                'key_insights': [],
                'recommended_actions': [],
                'data_quality_assessment': {},
                'next_research_suggestions': []
            }
            
            # Extract key insights from each platform
            social_media_results = research_results.get('results', {}).get('social_media', {})
            
            for platform, data in social_media_results.items():
                if 'results' in data and len(data['results']) > 0:
                    # Get top trending content
                    top_content = sorted(
                        data['results'], 
                        key=lambda x: x.get('trending_score', 0), 
                        reverse=True
                    )[:3]
                    
                    for content in top_content:
                        summary['key_insights'].append({
                            'platform': platform,
                            'insight': f"High-trending content: {content.get('title', '')[:100]}",
                            'trending_score': content.get('trending_score', 0),
                            'url': content.get('url', '')
                        })
            
            # Generate recommended actions
            platforms_analyzed = research_results.get('summary', {}).get('platforms_analyzed', 0)
            total_results = research_results.get('summary', {}).get('total_results', 0)
            
            if platforms_analyzed > 0:
                summary['recommended_actions'].append({
                    'action': 'Create platform-specific content',
                    'priority': 'high',
                    'reason': f'Found trending content across {platforms_analyzed} platforms'
                })
            
            if total_results > 10:
                summary['recommended_actions'].append({
                    'action': 'Analyze engagement patterns',
                    'priority': 'medium',
                    'reason': f'Sufficient data ({total_results} results) for pattern analysis'
                })
            
            # Assess data quality
            summary['data_quality_assessment'] = {
                'completeness_score': min((platforms_analyzed / 4) * 100, 100),
                'data_freshness': 'real-time',
                'source_reliability': 'high',
                'api_success_rate': (platforms_analyzed / len(research_results.get('platforms_researched', []))) * 100 if research_results.get('platforms_researched') else 0
            }
            
            # Suggest next research steps
            if platforms_analyzed < 4:
                summary['next_research_suggestions'].append(
                    'Expand research to additional platforms for comprehensive insights'
                )
            
            if 'trends' not in research_results.get('results', {}):
                summary['next_research_suggestions'].append(
                    'Include trends analysis for seasonal and temporal insights'
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate research summary: {e}")
            raise
    
    def _validate_research_features(self, query: ResearchQuery) -> Dict[str, Any]:
        """
        P0-10b: Validate research feature flags before execution
        
        Args:
            query: Research query to validate
            
        Returns:
            Dict with validation results and blocked features
        """
        try:
            validation_result = {
                "allowed": True,
                "blocked_features": [],
                "warning_features": [],
                "feature_checks": []
            }
            
            # Check core research feature flag
            if not ff("ENABLE_DEEP_RESEARCH"):
                validation_result["allowed"] = False
                validation_result["blocked_features"].append({
                    "feature": "deep_research",
                    "flag": "ENABLE_DEEP_RESEARCH",
                    "reason": "Deep research functionality is currently disabled"
                })
                logger.warning("Research blocked: ENABLE_DEEP_RESEARCH flag disabled")
            
            validation_result["feature_checks"].append({
                "flag": "ENABLE_DEEP_RESEARCH",
                "enabled": ff("ENABLE_DEEP_RESEARCH"),
                "required": True
            })
            
            # Check AI-powered features for insights
            if not ff("AI_CONTENT_GENERATION"):
                validation_result["warning_features"].append({
                    "feature": "ai_insights",
                    "flag": "AI_CONTENT_GENERATION", 
                    "reason": "AI insights will be limited without AI content generation"
                })
                logger.info("AI insights may be limited: AI_CONTENT_GENERATION disabled")
            
            validation_result["feature_checks"].append({
                "flag": "AI_CONTENT_GENERATION",
                "enabled": ff("AI_CONTENT_GENERATION"),
                "required": False
            })
            
            # Check advanced features for enhanced research
            if not ff("ADVANCED_MEMORY"):
                validation_result["warning_features"].append({
                    "feature": "enhanced_research",
                    "flag": "ADVANCED_MEMORY",
                    "reason": "Research insights storage and retrieval will be basic without advanced memory"
                })
            
            validation_result["feature_checks"].append({
                "flag": "ADVANCED_MEMORY", 
                "enabled": ff("ADVANCED_MEMORY"),
                "required": False
            })
            
            # Check vector search for semantic analysis
            if not ff("VECTOR_SEARCH"):
                validation_result["warning_features"].append({
                    "feature": "semantic_analysis",
                    "flag": "VECTOR_SEARCH",
                    "reason": "Semantic similarity analysis will be unavailable"
                })
            
            validation_result["feature_checks"].append({
                "flag": "VECTOR_SEARCH",
                "enabled": ff("VECTOR_SEARCH"), 
                "required": False
            })
            
            # Platform-specific feature validation
            platform_features = {
                "twitter": "Social media platform research",
                "instagram": "Visual content analysis", 
                "linkedin": "Professional network insights",
                "youtube": "Video content trends"
            }
            
            for platform in query.platforms:
                if platform in platform_features:
                    # All platforms currently allowed, but this provides extension point
                    validation_result["feature_checks"].append({
                        "platform": platform,
                        "description": platform_features[platform],
                        "enabled": True,
                        "required": False
                    })
            
            # Advanced research features validation
            if query.include_competitors and not ff("ADVANCED_ANALYTICS"):
                validation_result["blocked_features"].append({
                    "feature": "competitor_analysis",
                    "flag": "ADVANCED_ANALYTICS",
                    "reason": "Competitor analysis requires advanced analytics features"
                })
                logger.warning("Competitor analysis blocked: ADVANCED_ANALYTICS disabled")
            
            validation_result["feature_checks"].append({
                "flag": "ADVANCED_ANALYTICS",
                "enabled": ff("ADVANCED_ANALYTICS"),
                "required": query.include_competitors
            })
            
            # Check if any critical features are blocked
            if validation_result["blocked_features"]:
                validation_result["allowed"] = False
                logger.error(f"Research blocked due to {len(validation_result['blocked_features'])} feature restrictions")
                
                return {
                    "status": "feature_blocked",
                    "allowed": False,
                    "message": f"Research execution blocked by {len(validation_result['blocked_features'])} feature restrictions",
                    "blocked_features": validation_result["blocked_features"],
                    "warning_features": validation_result["warning_features"],
                    "feature_checks": validation_result["feature_checks"],
                    "resolution": "Enable required feature flags or contact administrator",
                    "blocked_at": datetime.utcnow().isoformat()
                }
            
            # Log warnings but allow execution
            if validation_result["warning_features"]:
                logger.info(f"Research proceeding with {len(validation_result['warning_features'])} feature warnings")
            
            logger.info(f"Research feature validation passed - {len(validation_result['feature_checks'])} features checked")
            return {"allowed": True, "validation_result": validation_result}
            
        except Exception as e:
            logger.error(f"Research feature validation failed: {e}")
            return {
                "status": "validation_error",
                "allowed": False,
                "message": f"Feature validation failed: {str(e)}",
                "error": str(e),
                "blocked_at": datetime.utcnow().isoformat()
            }