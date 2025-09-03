"""
Real Social Media Research Service - replaces all mock social media research
Uses real APIs and web scraping for production data
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import re
from urllib.parse import quote

from backend.core.config import get_settings
from backend.core.http_migration_helper import get_sync_client

logger = logging.getLogger(__name__)
settings = get_settings()

class RealSocialResearchService:
    """Real social media research using APIs and web scraping"""
    
    def __init__(self):
        self.serper_api_key = settings.serper_api_key
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY required for social media research")
    
    def research_twitter_trends(self, topic: str, limit: int = 10) -> Dict[str, Any]:
        """Research real Twitter trends and content using Serper API"""
        try:
            # Search for Twitter-specific content about the topic
            search_query = f"site:twitter.com {topic} OR site:x.com {topic}"
            
            payload = {
                "q": search_query,
                "gl": "us",
                "hl": "en",
                "num": limit,
                "tbm": "nws"  # News search to get recent content
            }
            
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            client = get_sync_client()
            response = client.post(
                "https://google.serper.dev/search",
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            # Also search for general Twitter trends about the topic
            general_payload = {
                "q": f"twitter trends {topic} hashtag",
                "gl": "us",
                "hl": "en",
                "num": 5
            }
            
            general_response = requests.post(
                "https://google.serper.dev/search",
                json=general_payload,
                headers=headers,
                timeout=15
            )
            
            general_data = {}
            if general_response.status_code == 200:
                general_data = general_response.json()
            
            # Process results
            twitter_insights = {
                'topic': topic,
                'platform': 'twitter',
                'trending_content': [],
                'hashtag_insights': [],
                'engagement_patterns': [],
                'research_summary': {
                    'total_sources': len(data.get('organic', [])) + len(data.get('news', [])),
                    'research_date': datetime.utcnow().isoformat(),
                    'method': 'serper_web_search'
                }
            }
            
            # Extract trending content from news results
            for news_item in data.get('news', [])[:limit]:
                title = news_item.get('title', '')
                snippet = news_item.get('snippet', '')
                
                # Extract hashtags from text
                hashtags = re.findall(r'#\w+', title + ' ' + snippet)
                
                twitter_insights['trending_content'].append({
                    'title': title,
                    'summary': snippet,
                    'source': news_item.get('source', ''),
                    'date': news_item.get('date', ''),
                    'url': news_item.get('link', ''),
                    'hashtags_mentioned': hashtags[:5]
                })
            
            # Extract hashtag insights from general search
            for result in general_data.get('organic', [])[:5]:
                content = result.get('title', '') + ' ' + result.get('snippet', '')
                hashtags = re.findall(r'#\w+', content)
                
                if hashtags:
                    twitter_insights['hashtag_insights'].append({
                        'source': result.get('displayLink', ''),
                        'context': result.get('snippet', '')[:200],
                        'hashtags': list(set(hashtags))[:10],
                        'url': result.get('link', '')
                    })
            
            # Analyze engagement patterns from content
            engagement_indicators = ['viral', 'trending', 'popular', 'engagement', 'retweet', 'like']
            for content in twitter_insights['trending_content']:
                text = (content['title'] + ' ' + content['summary']).lower()
                found_indicators = [indicator for indicator in engagement_indicators if indicator in text]
                
                if found_indicators:
                    twitter_insights['engagement_patterns'].append({
                        'content_title': content['title'][:100],
                        'engagement_signals': found_indicators,
                        'source': content['source']
                    })
            
            logger.info(f"Researched Twitter trends for topic: {topic}")
            return twitter_insights
            
        except Exception as e:
            logger.error(f"Failed to research Twitter trends: {e}")
            raise
    
    def research_instagram_content(self, topic: str, content_type: str = "general") -> Dict[str, Any]:
        """Research real Instagram content and trends"""
        try:
            # Search for Instagram-specific content
            search_query = f"site:instagram.com {topic} {content_type}"
            
            payload = {
                "q": search_query,
                "gl": "us",
                "hl": "en", 
                "num": 10
            }
            
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            client = get_sync_client()
            response = client.post(
                "https://google.serper.dev/search",
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            # Search for Instagram marketing insights
            insights_query = f"instagram marketing {topic} strategy trends 2024"
            insights_payload = {
                "q": insights_query,
                "gl": "us",
                "hl": "en",
                "num": 5
            }
            
            insights_response = requests.post(
                "https://google.serper.dev/search",
                json=insights_payload,
                headers=headers,
                timeout=15
            )
            
            insights_data = {}
            if insights_response.status_code == 200:
                insights_data = insights_response.json()
            
            instagram_research = {
                'topic': topic,
                'content_type': content_type,
                'platform': 'instagram',
                'content_ideas': [],
                'visual_trends': [],
                'hashtag_strategies': [],
                'marketing_insights': [],
                'research_summary': {
                    'total_sources': len(data.get('organic', [])),
                    'research_date': datetime.utcnow().isoformat()
                }
            }
            
            # Process organic results for content ideas
            for result in data.get('organic', []):
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                
                # Extract hashtags
                hashtags = re.findall(r'#\w+', title + ' ' + snippet)
                
                # Look for visual indicators
                visual_keywords = ['photo', 'image', 'video', 'story', 'reel', 'carousel', 'visual']
                visual_indicators = [kw for kw in visual_keywords if kw in (title + snippet).lower()]
                
                instagram_research['content_ideas'].append({
                    'title': title,
                    'description': snippet,
                    'source': result.get('displayLink', ''),
                    'url': result.get('link', ''),
                    'hashtags': hashtags[:8],
                    'visual_elements': visual_indicators
                })
            
            # Process marketing insights
            for insight in insights_data.get('organic', [])[:5]:
                content = insight.get('snippet', '')
                
                # Look for strategy keywords
                strategy_keywords = ['engagement', 'reach', 'growth', 'algorithm', 'best time', 'frequency']
                found_strategies = [kw for kw in strategy_keywords if kw in content.lower()]
                
                if found_strategies:
                    instagram_research['marketing_insights'].append({
                        'source': insight.get('displayLink', ''),
                        'insight': content[:250],
                        'strategies_mentioned': found_strategies,
                        'url': insight.get('link', '')
                    })
            
            # Extract hashtag strategies
            all_hashtags = []
            for idea in instagram_research['content_ideas']:
                all_hashtags.extend(idea['hashtags'])
            
            # Count hashtag frequency
            hashtag_counts = {}
            for hashtag in all_hashtags:
                hashtag_counts[hashtag] = hashtag_counts.get(hashtag, 0) + 1
            
            # Get top hashtags
            top_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:15]
            
            instagram_research['hashtag_strategies'] = [{
                'hashtag': tag,
                'frequency': count,
                'popularity_score': min(count * 20, 100)
            } for tag, count in top_hashtags]
            
            logger.info(f"Researched Instagram content for topic: {topic}")
            return instagram_research
            
        except Exception as e:
            logger.error(f"Failed to research Instagram content: {e}")
            raise
    
    def research_linkedin_professional_content(self, topic: str, industry: str = "") -> Dict[str, Any]:
        """Research real LinkedIn professional content trends"""
        try:
            # Search for LinkedIn-specific professional content
            search_query = f"site:linkedin.com {topic} {industry} professional"
            
            payload = {
                "q": search_query,
                "gl": "us",
                "hl": "en",
                "num": 10
            }
            
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            client = get_sync_client()
            response = client.post(
                "https://google.serper.dev/search",
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            # Search for LinkedIn marketing best practices
            best_practices_query = f"linkedin marketing {topic} {industry} best practices 2024"
            bp_payload = {
                "q": best_practices_query,
                "gl": "us",
                "hl": "en",
                "num": 5
            }
            
            bp_response = requests.post(
                "https://google.serper.dev/search",
                json=bp_payload,
                headers=headers,
                timeout=15
            )
            
            bp_data = {}
            if bp_response.status_code == 200:
                bp_data = bp_response.json()
            
            linkedin_research = {
                'topic': topic,
                'industry': industry,
                'platform': 'linkedin',
                'professional_content': [],
                'thought_leadership_trends': [],
                'engagement_strategies': [],
                'industry_insights': [],
                'research_summary': {
                    'total_sources': len(data.get('organic', [])),
                    'industry_focus': industry or 'general',
                    'research_date': datetime.utcnow().isoformat()
                }
            }
            
            # Process LinkedIn content
            for result in data.get('organic', []):
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                
                # Look for professional indicators
                professional_keywords = ['leadership', 'strategy', 'insights', 'experience', 
                                       'industry', 'professional', 'business', 'career']
                prof_indicators = [kw for kw in professional_keywords if kw in (title + snippet).lower()]
                
                # Look for thought leadership indicators
                thought_leadership = ['opinion', 'perspective', 'thought', 'analysis', 'trend', 'future']
                tl_indicators = [kw for kw in thought_leadership if kw in (title + snippet).lower()]
                
                content_item = {
                    'title': title,
                    'summary': snippet,
                    'source': result.get('displayLink', ''),
                    'url': result.get('link', ''),
                    'professional_signals': prof_indicators,
                    'thought_leadership_signals': tl_indicators
                }
                
                linkedin_research['professional_content'].append(content_item)
                
                # Categorize as thought leadership if strong signals
                if len(tl_indicators) >= 2:
                    linkedin_research['thought_leadership_trends'].append({
                        'topic_angle': title[:100],
                        'leadership_approach': ', '.join(tl_indicators),
                        'source_authority': result.get('displayLink', ''),
                        'content_preview': snippet[:150]
                    })
            
            # Process best practices and strategies
            for practice in bp_data.get('organic', [])[:5]:
                content = practice.get('snippet', '')
                
                # Look for engagement strategy keywords
                engagement_keywords = ['engagement', 'connection', 'network', 'post', 'share', 'comment']
                found_strategies = [kw for kw in engagement_keywords if kw in content.lower()]
                
                if found_strategies:
                    linkedin_research['engagement_strategies'].append({
                        'source': practice.get('displayLink', ''),
                        'strategy_summary': content[:200],
                        'key_tactics': found_strategies,
                        'url': practice.get('link', '')
                    })
            
            # Extract industry-specific insights
            if industry:
                for content in linkedin_research['professional_content']:
                    if industry.lower() in (content['title'] + content['summary']).lower():
                        linkedin_research['industry_insights'].append({
                            'insight': content['title'],
                            'detail': content['summary'][:150],
                            'relevance_score': len(content['professional_signals']) * 20,
                            'source': content['source']
                        })
            
            logger.info(f"Researched LinkedIn content for topic: {topic}, industry: {industry}")
            return linkedin_research
            
        except Exception as e:
            logger.error(f"Failed to research LinkedIn content: {e}")
            raise
    
    def research_youtube_video_trends(self, topic: str, limit: int = 8) -> Dict[str, Any]:
        """Research real YouTube video trends and content"""
        try:
            # Search for YouTube videos about the topic
            search_query = f"site:youtube.com {topic} OR site:youtu.be {topic}"
            
            payload = {
                "q": search_query,
                "gl": "us",
                "hl": "en",
                "num": limit
            }
            
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            client = get_sync_client()
            response = client.post(
                "https://google.serper.dev/search",
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            # Search for YouTube trends and strategies
            trends_query = f"youtube trends {topic} video content strategy 2024"
            trends_payload = {
                "q": trends_query,
                "gl": "us",
                "hl": "en",
                "num": 5
            }
            
            trends_response = requests.post(
                "https://google.serper.dev/search",
                json=trends_payload,
                headers=headers,
                timeout=15
            )
            
            trends_data = {}
            if trends_response.status_code == 200:
                trends_data = trends_response.json()
            
            youtube_research = {
                'topic': topic,
                'platform': 'youtube',
                'video_content': [],
                'trending_formats': [],
                'content_strategies': [],
                'optimization_tips': [],
                'research_summary': {
                    'total_videos_analyzed': len(data.get('organic', [])),
                    'research_date': datetime.utcnow().isoformat()
                }
            }
            
            # Process YouTube video results
            for result in data.get('organic', []):
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                url = result.get('link', '')
                
                # Extract video format indicators
                format_keywords = ['tutorial', 'review', 'unboxing', 'vlog', 'interview', 
                                 'demo', 'guide', 'tips', 'how to', 'explained']
                found_formats = [kw for kw in format_keywords if kw in (title + snippet).lower()]
                
                # Extract engagement indicators from titles/descriptions
                engagement_keywords = ['viral', 'trending', 'popular', 'must watch', 'breaking']
                engagement_signals = [kw for kw in engagement_keywords if kw in (title + snippet).lower()]
                
                video_data = {
                    'title': title,
                    'description': snippet,
                    'url': url,
                    'video_formats': found_formats,
                    'engagement_signals': engagement_signals,
                    'estimated_popularity': len(engagement_signals) * 25 + len(found_formats) * 15
                }
                
                youtube_research['video_content'].append(video_data)
                
                # Categorize trending formats
                for format_type in found_formats:
                    existing_format = next((f for f in youtube_research['trending_formats'] 
                                          if f['format'] == format_type), None)
                    if existing_format:
                        existing_format['frequency'] += 1
                    else:
                        youtube_research['trending_formats'].append({
                            'format': format_type,
                            'frequency': 1,
                            'example_title': title[:80]
                        })
            
            # Process content strategy insights
            for strategy in trends_data.get('organic', [])[:5]:
                content = strategy.get('snippet', '')
                
                # Look for strategy and optimization keywords
                strategy_keywords = ['algorithm', 'seo', 'thumbnail', 'title', 'engagement', 
                                   'subscribe', 'retention', 'analytics']
                found_strategies = [kw for kw in strategy_keywords if kw in content.lower()]
                
                if found_strategies:
                    youtube_research['content_strategies'].append({
                        'source': strategy.get('displayLink', ''),
                        'strategy_insight': content[:200],
                        'optimization_areas': found_strategies,
                        'url': strategy.get('link', '')
                    })
            
            # Sort trending formats by frequency
            youtube_research['trending_formats'].sort(key=lambda x: x['frequency'], reverse=True)
            
            logger.info(f"Researched YouTube trends for topic: {topic}")
            return youtube_research
            
        except Exception as e:
            logger.error(f"Failed to research YouTube trends: {e}")
            raise
    
    def get_cross_platform_insights(self, topic: str) -> Dict[str, Any]:
        """Get comprehensive cross-platform social media insights"""
        try:
            insights = {
                'topic': topic,
                'analysis_date': datetime.utcnow().isoformat(),
                'platform_research': {},
                'cross_platform_trends': [],
                'content_opportunities': [],
                'summary': {
                    'platforms_analyzed': 0,
                    'total_insights': 0,
                    'research_method': 'real_api_data'
                }
            }
            
            # Research each platform
            platforms = [
                ('twitter', self.research_twitter_trends),
                ('instagram', self.research_instagram_content),
                ('linkedin', self.research_linkedin_professional_content),
                ('youtube', self.research_youtube_video_trends)
            ]
            
            for platform_name, research_func in platforms:
                try:
                    if platform_name == 'instagram':
                        platform_data = research_func(topic, 'general')
                    elif platform_name == 'linkedin':
                        platform_data = research_func(topic, '')
                    else:
                        platform_data = research_func(topic)
                    
                    insights['platform_research'][platform_name] = platform_data
                    insights['summary']['platforms_analyzed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to research {platform_name}: {e}")
                    insights['platform_research'][platform_name] = {
                        'error': str(e),
                        'status': 'failed'
                    }
            
            # Analyze cross-platform trends
            all_hashtags = []
            all_keywords = []
            
            for platform, data in insights['platform_research'].items():
                if 'error' not in data:
                    # Extract common elements
                    if 'hashtag_insights' in data:
                        for hashtag_data in data['hashtag_insights']:
                            all_hashtags.extend(hashtag_data.get('hashtags', []))
                    
                    # Extract keywords from titles and content
                    content_fields = ['trending_content', 'content_ideas', 'professional_content', 'video_content']
                    for field in content_fields:
                        if field in data:
                            for item in data[field]:
                                title = item.get('title', '')
                                words = re.findall(r'\b\w{4,}\b', title.lower())
                                all_keywords.extend(words)
            
            # Find cross-platform trending hashtags
            hashtag_counts = {}
            for hashtag in all_hashtags:
                hashtag_counts[hashtag] = hashtag_counts.get(hashtag, 0) + 1
            
            cross_platform_hashtags = [tag for tag, count in hashtag_counts.items() if count > 1]
            
            # Find cross-platform trending keywords
            keyword_counts = {}
            for keyword in all_keywords:
                if len(keyword) > 4:  # Filter short words
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            trending_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            insights['cross_platform_trends'] = {
                'trending_hashtags': cross_platform_hashtags[:10],
                'trending_keywords': [kw for kw, count in trending_keywords],
                'keyword_frequencies': dict(trending_keywords)
            }
            
            # Generate content opportunities
            for keyword, frequency in trending_keywords[:5]:
                if frequency >= 2:  # Appears on multiple platforms
                    insights['content_opportunities'].append({
                        'opportunity': f"Create content about '{keyword}' - trending across {frequency} platforms",
                        'keyword': keyword,
                        'cross_platform_score': frequency * 20,
                        'suggested_approach': f"Adapt '{keyword}' content for each platform's unique format"
                    })
            
            insights['summary']['total_insights'] = len(insights['content_opportunities'])
            
            logger.info(f"Completed cross-platform research for topic: {topic}")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get cross-platform insights: {e}")
            raise