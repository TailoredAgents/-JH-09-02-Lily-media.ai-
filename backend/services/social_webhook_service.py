"""
Social Media Webhook Service

Handles incoming webhooks from Facebook, Instagram, and X/Twitter
for comments, mentions, and direct messages.
"""

import logging
import json
import hmac
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.db.models import SocialInteraction, SocialPlatformConnection, User, Lead
from backend.db.database import get_db
from backend.services.personality_response_engine import get_personality_engine
from backend.services.dm_lead_service import get_dm_lead_service

logger = logging.getLogger(__name__)


class SocialWebhookService:
    """
    Unified webhook service for processing social media platform webhooks.
    Handles Facebook, Instagram, and X/Twitter webhooks for real-time interaction processing.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.personality_engine = get_personality_engine(db)
    
    def verify_facebook_webhook(self, payload: str, signature: str, app_secret: str) -> bool:
        """
        Verify Facebook webhook signature for security.
        
        Args:
            payload: Raw webhook payload
            signature: X-Hub-Signature-256 header value
            app_secret: Facebook app secret
            
        Returns:
            True if signature is valid
        """
        try:
            if not signature.startswith('sha256='):
                return False
            
            expected_signature = 'sha256=' + hmac.new(
                app_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Facebook webhook verification failed: {e}")
            return False
    
    def verify_instagram_webhook(self, payload: str, signature: str, app_secret: str) -> bool:
        """
        Verify Instagram webhook signature (same as Facebook).
        
        Args:
            payload: Raw webhook payload
            signature: X-Hub-Signature-256 header value  
            app_secret: Instagram app secret
            
        Returns:
            True if signature is valid
        """
        return self.verify_facebook_webhook(payload, signature, app_secret)
    
    def verify_twitter_webhook(self, payload: str, signature: str, consumer_secret: str) -> bool:
        """
        Verify X/Twitter webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: X-Twitter-Webhooks-Signature header value
            consumer_secret: Twitter consumer secret
            
        Returns:
            True if signature is valid
        """
        try:
            if not signature.startswith('sha256='):
                return False
            
            expected_signature = 'sha256=' + hmac.new(
                consumer_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Twitter webhook verification failed: {e}")
            return False
    
    def process_facebook_webhook(self, webhook_data: Dict[str, Any]) -> List[str]:
        """
        Process Facebook webhook payload and extract interactions.
        
        Args:
            webhook_data: Parsed webhook JSON payload
            
        Returns:
            List of created interaction IDs
        """
        created_interactions = []
        
        try:
            # Facebook webhook structure
            entry_list = webhook_data.get('entry', [])
            
            for entry in entry_list:
                page_id = entry.get('id')
                changes = entry.get('changes', [])
                
                for change in changes:
                    field = change.get('field')
                    value = change.get('value', {})
                    
                    if field == 'feed':
                        # Handle page post comments
                        interaction_id = self._process_facebook_comment(page_id, value)
                        if interaction_id:
                            created_interactions.append(interaction_id)
                    
                    elif field == 'mention':
                        # Handle page mentions
                        interaction_id = self._process_facebook_mention(page_id, value)
                        if interaction_id:
                            created_interactions.append(interaction_id)
                    
                    elif field == 'messages':
                        # Handle page messages
                        interaction_id = self._process_facebook_message(page_id, value)
                        if interaction_id:
                            created_interactions.append(interaction_id)
            
        except Exception as e:
            logger.error(f"Facebook webhook processing failed: {e}")
        
        return created_interactions
    
    def process_instagram_webhook(self, webhook_data: Dict[str, Any]) -> List[str]:
        """
        Process Instagram webhook payload and extract interactions.
        
        Args:
            webhook_data: Parsed webhook JSON payload
            
        Returns:
            List of created interaction IDs
        """
        created_interactions = []
        
        try:
            # Instagram webhook structure
            entry_list = webhook_data.get('entry', [])
            
            for entry in entry_list:
                instagram_id = entry.get('id')
                changes = entry.get('changes', [])
                
                for change in changes:
                    field = change.get('field')
                    value = change.get('value', {})
                    
                    if field == 'comments':
                        # Handle Instagram comments
                        interaction_id = self._process_instagram_comment(instagram_id, value)
                        if interaction_id:
                            created_interactions.append(interaction_id)
                    
                    elif field == 'mentions':
                        # Handle Instagram mentions
                        interaction_id = self._process_instagram_mention(instagram_id, value)
                        if interaction_id:
                            created_interactions.append(interaction_id)
            
        except Exception as e:
            logger.error(f"Instagram webhook processing failed: {e}")
        
        return created_interactions
    
    def process_twitter_webhook(self, webhook_data: Dict[str, Any]) -> List[str]:
        """
        Process Twitter/X webhook payload and extract interactions.
        
        Args:
            webhook_data: Parsed webhook JSON payload
            
        Returns:
            List of created interaction IDs
        """
        created_interactions = []
        
        try:
            # Twitter webhook structure varies by event type
            if 'tweet_create_events' in webhook_data:
                # Handle mentions and replies
                for tweet_event in webhook_data['tweet_create_events']:
                    interaction_id = self._process_twitter_mention(tweet_event)
                    if interaction_id:
                        created_interactions.append(interaction_id)
            
            if 'direct_message_events' in webhook_data:
                # Handle direct messages
                for dm_event in webhook_data['direct_message_events']:
                    interaction_id = self._process_twitter_dm(dm_event)
                    if interaction_id:
                        created_interactions.append(interaction_id)
        
        except Exception as e:
            logger.error(f"Twitter webhook processing failed: {e}")
        
        return created_interactions
    
    def _process_facebook_comment(self, page_id: str, comment_data: Dict[str, Any]) -> Optional[str]:
        """Process a Facebook comment webhook event"""
        try:
            # Find user connection for this page
            connection = self._find_connection_by_platform_id('facebook', page_id)
            if not connection:
                logger.warning(f"No Facebook connection found for page {page_id}")
                return None
            
            # Extract comment details
            comment_id = comment_data.get('comment_id')
            post_id = comment_data.get('post_id') 
            message = comment_data.get('message', '')
            created_time = comment_data.get('created_time')
            sender = comment_data.get('from', {})
            
            if not comment_id or not message.strip():
                return None
            
            # Create interaction record
            interaction = SocialInteraction(
                user_id=connection.user_id,
                connection_id=connection.id,
                platform='facebook',
                interaction_type='comment',
                external_id=comment_id,
                parent_external_id=post_id,
                author_platform_id=sender.get('id', ''),
                author_username=sender.get('name', 'Unknown'),
                author_display_name=sender.get('name', 'Unknown'),
                content=message,
                platform_created_at=self._parse_timestamp(created_time) or datetime.now(timezone.utc),
                platform_metadata={'webhook_data': comment_data}
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Created Facebook comment interaction: {interaction.id}")
            return interaction.id
            
        except Exception as e:
            logger.error(f"Failed to process Facebook comment: {e}")
            return None
    
    def _process_facebook_mention(self, page_id: str, mention_data: Dict[str, Any]) -> Optional[str]:
        """Process a Facebook mention webhook event"""
        try:
            connection = self._find_connection_by_platform_id('facebook', page_id)
            if not connection:
                return None
            
            # Extract mention details
            mention_id = mention_data.get('mention_id')
            message = mention_data.get('message', '')
            created_time = mention_data.get('created_time')
            sender = mention_data.get('from', {})
            
            if not mention_id or not message.strip():
                return None
            
            interaction = SocialInteraction(
                user_id=connection.user_id,
                connection_id=connection.id,
                platform='facebook',
                interaction_type='mention',
                external_id=mention_id,
                author_platform_id=sender.get('id', ''),
                author_username=sender.get('name', 'Unknown'),
                author_display_name=sender.get('name', 'Unknown'),
                content=message,
                platform_created_at=self._parse_timestamp(created_time) or datetime.now(timezone.utc),
                platform_metadata={'webhook_data': mention_data}
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Created Facebook mention interaction: {interaction.id}")
            return interaction.id
            
        except Exception as e:
            logger.error(f"Failed to process Facebook mention: {e}")
            return None
    
    def _process_facebook_message(self, page_id: str, message_data: Dict[str, Any]) -> Optional[str]:
        """Process a Facebook direct message webhook event"""
        try:
            connection = self._find_connection_by_platform_id('facebook', page_id)
            if not connection:
                return None
            
            # Extract message details
            message_id = message_data.get('message_id')
            text = message_data.get('text', '')
            created_time = message_data.get('created_time')
            sender = message_data.get('from', {})
            
            if not message_id or not text.strip():
                return None
            
            interaction = SocialInteraction(
                user_id=connection.user_id,
                connection_id=connection.id,
                platform='facebook',
                interaction_type='dm',
                external_id=message_id,
                author_platform_id=sender.get('id', ''),
                author_username=sender.get('name', 'Unknown'),
                author_display_name=sender.get('name', 'Unknown'),
                content=text,
                platform_created_at=self._parse_timestamp(created_time) or datetime.now(timezone.utc),
                platform_metadata={'webhook_data': message_data}
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Created Facebook message interaction: {interaction.id}")
            
            # PW-DM-REPLACE-001: Try to create lead from DM if pricing intent detected
            try:
                lead_service = get_dm_lead_service()
                lead = lead_service.create_lead_from_dm(
                    interaction, 
                    connection.organization_id if hasattr(connection, 'organization_id') else None, 
                    self.db, 
                    connection.user_id
                )
                if lead:
                    logger.info(f"Created lead {lead.id} from Facebook DM {interaction.id}")
            except Exception as e:
                logger.error(f"Failed to create lead from Facebook DM {interaction.id}: {e}")
                # Don't fail the webhook processing if lead creation fails
            
            return interaction.id
            
        except Exception as e:
            logger.error(f"Failed to process Facebook message: {e}")
            return None
    
    def _process_instagram_comment(self, instagram_id: str, comment_data: Dict[str, Any]) -> Optional[str]:
        """Process an Instagram comment webhook event"""
        try:
            connection = self._find_connection_by_platform_id('instagram', instagram_id)
            if not connection:
                logger.warning(f"No Instagram connection found for account {instagram_id}")
                return None
            
            # Extract comment details
            comment_id = comment_data.get('id')
            text = comment_data.get('text', '')
            timestamp = comment_data.get('timestamp')
            media_id = comment_data.get('media', {}).get('id')
            
            # Get commenter info (may require additional API call)
            from_user = comment_data.get('from', {})
            
            if not comment_id or not text.strip():
                return None
            
            interaction = SocialInteraction(
                user_id=connection.user_id,
                connection_id=connection.id,
                platform='instagram',
                interaction_type='comment',
                external_id=comment_id,
                parent_external_id=media_id,
                author_platform_id=from_user.get('id', ''),
                author_username=from_user.get('username', 'Unknown'),
                author_display_name=from_user.get('username', 'Unknown'),
                content=text,
                platform_created_at=self._parse_timestamp(timestamp) or datetime.now(timezone.utc),
                platform_metadata={'webhook_data': comment_data}
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Created Instagram comment interaction: {interaction.id}")
            return interaction.id
            
        except Exception as e:
            logger.error(f"Failed to process Instagram comment: {e}")
            return None
    
    def _process_instagram_mention(self, instagram_id: str, mention_data: Dict[str, Any]) -> Optional[str]:
        """Process an Instagram mention webhook event"""
        try:
            connection = self._find_connection_by_platform_id('instagram', instagram_id)
            if not connection:
                return None
            
            # Extract mention details
            comment_id = mention_data.get('comment_id')
            media_id = mention_data.get('media_id')
            text = mention_data.get('text', '')
            timestamp = mention_data.get('timestamp')
            
            if not comment_id or not text.strip():
                return None
            
            interaction = SocialInteraction(
                user_id=connection.user_id,
                connection_id=connection.id,
                platform='instagram',
                interaction_type='mention',
                external_id=comment_id,
                parent_external_id=media_id,
                author_platform_id='',  # Would need additional API call to get this
                author_username='Unknown',
                author_display_name='Unknown',
                content=text,
                platform_created_at=self._parse_timestamp(timestamp) or datetime.now(timezone.utc),
                platform_metadata={'webhook_data': mention_data}
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Created Instagram mention interaction: {interaction.id}")
            return interaction.id
            
        except Exception as e:
            logger.error(f"Failed to process Instagram mention: {e}")
            return None
    
    def _process_twitter_mention(self, tweet_data: Dict[str, Any]) -> Optional[str]:
        """Process a Twitter mention webhook event"""
        try:
            # Extract tweet details
            tweet_id = tweet_data.get('id_str')
            text = tweet_data.get('text', '')
            created_at = tweet_data.get('created_at')
            user = tweet_data.get('user', {})
            in_reply_to = tweet_data.get('in_reply_to_status_id_str')
            
            # Check if this is a mention of our account
            entities = tweet_data.get('entities', {})
            mentions = entities.get('user_mentions', [])
            
            # Find our account in the mentions
            our_connection = None
            for mention in mentions:
                connection = self._find_connection_by_username('twitter', mention.get('screen_name', ''))
                if connection:
                    our_connection = connection
                    break
            
            if not our_connection or not tweet_id or not text.strip():
                return None
            
            interaction = SocialInteraction(
                user_id=our_connection.user_id,
                connection_id=our_connection.id,
                platform='twitter',
                interaction_type='mention',
                external_id=tweet_id,
                parent_external_id=in_reply_to,
                author_platform_id=user.get('id_str', ''),
                author_username=user.get('screen_name', 'Unknown'),
                author_display_name=user.get('name', 'Unknown'),
                author_profile_url=f"https://twitter.com/{user.get('screen_name', '')}",
                author_profile_image=user.get('profile_image_url_https', ''),
                author_verified=user.get('verified', False),
                content=text,
                platform_created_at=self._parse_twitter_timestamp(created_at) or datetime.now(timezone.utc),
                platform_metadata={'webhook_data': tweet_data}
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Created Twitter mention interaction: {interaction.id}")
            return interaction.id
            
        except Exception as e:
            logger.error(f"Failed to process Twitter mention: {e}")
            return None
    
    def _process_twitter_dm(self, dm_data: Dict[str, Any]) -> Optional[str]:
        """Process a Twitter direct message webhook event"""
        try:
            # Extract DM details
            message_create = dm_data.get('message_create', {})
            message_data = message_create.get('message_data', {})
            sender_id = message_create.get('sender_id', '')
            recipient_id = message_create.get('target', {}).get('recipient_id', '')
            
            message_id = dm_data.get('id')
            text = message_data.get('text', '')
            created_timestamp = dm_data.get('created_timestamp')
            
            # Find our connection (we should be the recipient)
            connection = self._find_connection_by_platform_id('twitter', recipient_id)
            if not connection or not message_id or not text.strip():
                return None
            
            interaction = SocialInteraction(
                user_id=connection.user_id,
                connection_id=connection.id,
                platform='twitter',
                interaction_type='dm',
                external_id=message_id,
                author_platform_id=sender_id,
                author_username='Unknown',  # Would need additional API call
                author_display_name='Unknown',
                content=text,
                platform_created_at=datetime.fromtimestamp(int(created_timestamp) / 1000, tz=timezone.utc),
                platform_metadata={'webhook_data': dm_data}
            )
            
            self.db.add(interaction)
            self.db.commit()
            
            logger.info(f"Created Twitter DM interaction: {interaction.id}")
            
            # PW-DM-REPLACE-001: Try to create lead from DM if pricing intent detected
            try:
                lead_service = get_dm_lead_service()
                lead = lead_service.create_lead_from_dm(
                    interaction, 
                    connection.organization_id if hasattr(connection, 'organization_id') else None, 
                    self.db, 
                    connection.user_id
                )
                if lead:
                    logger.info(f"Created lead {lead.id} from Twitter DM {interaction.id}")
            except Exception as e:
                logger.error(f"Failed to create lead from Twitter DM {interaction.id}: {e}")
                # Don't fail the webhook processing if lead creation fails
            
            return interaction.id
            
        except Exception as e:
            logger.error(f"Failed to process Twitter DM: {e}")
            return None
    
    def _find_connection_by_platform_id(self, platform: str, platform_id: str) -> Optional[SocialPlatformConnection]:
        """Find a social platform connection by platform and platform user ID"""
        return self.db.query(SocialPlatformConnection).filter(
            SocialPlatformConnection.platform == platform,
            SocialPlatformConnection.platform_user_id == platform_id,
            SocialPlatformConnection.is_active == True
        ).first()
    
    def _find_connection_by_username(self, platform: str, username: str) -> Optional[SocialPlatformConnection]:
        """Find a social platform connection by platform and username"""
        return self.db.query(SocialPlatformConnection).filter(
            SocialPlatformConnection.platform == platform,
            SocialPlatformConnection.platform_username == username,
            SocialPlatformConnection.is_active == True
        ).first()
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse various timestamp formats to datetime"""
        if not timestamp_str:
            return None
        
        try:
            # Try ISO format first
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Try Unix timestamp
            if timestamp_str.isdigit():
                return datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
            
            return None
        except Exception:
            return None
    
    def _parse_twitter_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse Twitter timestamp format"""
        if not timestamp_str:
            return None
        
        try:
            # Twitter format: "Wed Oct 05 20:12:35 +0000 2022"
            return datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %z %Y')
        except Exception:
            return None


# Global webhook service instance
def get_webhook_service(db: Session) -> SocialWebhookService:
    """Get a SocialWebhookService instance"""
    return SocialWebhookService(db)