import os
from supabase import create_client, Client
from typing import Optional, Dict, List
import logging
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Initialize Supabase client and tables"""
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.initialize_tables()

    def initialize_tables(self):
        """Create tables if they don't exist"""
        try:
            # Check if influencers table exists
            self.supabase.table("influencers").select("*").limit(1).execute()
        except Exception as e:
            # If table doesn't exist, create it
            try:
                self.supabase.rpc('execute_sql', {
                    'sql': """
                    CREATE TABLE influencers (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        heygen_avatar_id TEXT,
                        original_asset_path TEXT,
                        voice_id TEXT DEFAULT 'default_voice',
                        affiliate_id TEXT,
                        chat_page_url TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    """
                }).execute()
            except Exception as create_error:
                logger.error(f"Influencers table creation failed: {str(create_error)}")
        
        try:
            # Check if affiliate_links table exists
            self.supabase.table("affiliate_links").select("*").limit(1).execute()
        except Exception as e:
            # If table doesn't exist, create it
            try:
                self.supabase.rpc('execute_sql', {
                    'sql': """
                    CREATE TABLE affiliate_links (
                        id TEXT PRIMARY KEY,
                        influencer_id TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        affiliate_id TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        FOREIGN KEY (influencer_id) REFERENCES influencers(id) ON DELETE CASCADE
                    );
                    """
                }).execute()
            except Exception as create_error:
                logger.error(f"Affiliate links table creation failed: {str(create_error)}")
                
        try:
            # Check if chat_interactions table exists
            self.supabase.table("chat_interactions").select("*").limit(1).execute()
        except Exception as e:
            # If table doesn't exist, create it
            try:
                self.supabase.rpc('execute_sql', {
                    'sql': """
                    CREATE TABLE chat_interactions (
                        id TEXT PRIMARY KEY,
                        influencer_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        bot_response TEXT NOT NULL,
                        product_recommendations BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        FOREIGN KEY (influencer_id) REFERENCES influencers(id) ON DELETE CASCADE
                    );
                    """
                }).execute()
            except Exception as create_error:
                logger.error(f"Chat interactions table creation failed: {str(create_error)}")
                
    # Authentication methods
    def create_influencer(self, influencer_data: Dict) -> Optional[Dict]:
        """Create a new influencer with authentication credentials"""
        required_fields = {'id', 'username', 'email', 'password_hash'}
        if not all(field in influencer_data for field in required_fields):
            logger.error(f"Missing required fields: {required_fields}")
            return None

        # Generate chat page URL
        username = influencer_data['username']
        influencer_data['chat_page_url'] = f"/chat/{username}"
        
        try:
            response = self.supabase.table('influencers').insert(influencer_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating influencer: {str(e)}")
            return None

    def get_influencer_by_username(self, username: str) -> Optional[Dict]:
        """Get influencer by username"""
        try:
            response = self.supabase.table('influencers') \
                .select('*') \
                .eq('username', username) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting influencer: {str(e)}")
            return None

    def get_influencer_by_email(self, email: str) -> Optional[Dict]:
        """Get influencer by email"""
        try:
            response = self.supabase.table('influencers') \
                .select('*') \
                .eq('email', email) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting influencer: {str(e)}")
            return None

    # Profile management methods
    def get_influencer(self, influencer_id: str) -> Optional[Dict]:
        """Get influencer by ID"""
        try:
            response = self.supabase.table('influencers') \
                .select('*') \
                .eq('id', influencer_id) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting influencer: {str(e)}")
            return None

    def update_influencer(self, influencer_id: str, updates: Dict) -> bool:
        """Update influencer data"""
        if not updates:
            return False

        try:
            updates['updated_at'] = 'now()'
            response = self.supabase.table('influencers') \
                .update(updates) \
                .eq('id', influencer_id) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"Error updating influencer: {str(e)}")
            return False

    def delete_influencer(self, influencer_id: str) -> bool:
        """Delete an influencer"""
        try:
            response = self.supabase.table('influencers') \
                .delete() \
                .eq('id', influencer_id) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting influencer: {str(e)}")
            return False

    def get_all_influencers(self) -> List[Dict]:
        """Get all influencers"""
        try:
            response = self.supabase.table('influencers') \
                .select('*') \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting all influencers: {str(e)}")
            return []

    # Avatar management methods
    def store_original_asset(self, influencer_id: str, file_bytes: bytes, file_name: str) -> Optional[str]:
        try:
            bucket_name = "influencer-assets"  # Changed to hyphen
            file_path = f"original_avatars/{influencer_id}/{file_name}"
            self.supabase.storage.from_(bucket_name).upload(file_path, file_bytes)
            self.update_influencer(influencer_id, {'original_asset_path': file_path})
            return file_path
        except Exception as e:
            logger.error(f"Error storing asset: {str(e)}")
            return None

    def get_original_asset(self, influencer_id: str) -> Optional[bytes]:
        """Retrieve original avatar file"""
        try:
            influencer = self.get_influencer(influencer_id)
            if not influencer or not influencer.get('original_asset_path'):
                return None
                
            bucket_name = "influencer-assets"
            file_path = influencer['original_asset_path']
            
            return self.supabase.storage.from_(bucket_name).download(file_path)
        except Exception as e:
            logger.error(f"Error retrieving original asset: {str(e)}")
            return None
            
    # Affiliate management methods
    def add_affiliate_link(self, influencer_id: str, platform: str, affiliate_id: str) -> Optional[Dict]:
        """Add an affiliate link for an influencer"""
        try:
            affiliate_data = {
                "id": str(uuid.uuid4()),
                "influencer_id": influencer_id,
                "platform": platform,
                "affiliate_id": affiliate_id
            }
            
            response = self.supabase.table('affiliate_links').insert(affiliate_data).execute()
            
            # Also update the influencer's default affiliate_id if none exists
            influencer = self.get_influencer(influencer_id)
            if not influencer.get('affiliate_id'):
                self.update_influencer(influencer_id, {'affiliate_id': affiliate_id})
                
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error adding affiliate link: {str(e)}")
            return None
            
    def get_affiliate_links(self, influencer_id: str) -> List[Dict]:
        """Get all affiliate links for an influencer"""
        try:
            response = self.supabase.table('affiliate_links') \
                .select('*') \
                .eq('influencer_id', influencer_id) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting affiliate links: {str(e)}")
            return []
            
    def get_primary_affiliate_id(self, influencer_id: str) -> Optional[str]:
        """Get the primary affiliate ID for an influencer"""
        try:
            influencer = self.get_influencer(influencer_id)
            return influencer.get('affiliate_id') if influencer else None
        except Exception as e:
            logger.error(f"Error getting primary affiliate ID: {str(e)}")
            return None
            
    # Chat interaction methods
    def log_chat_interaction(self, influencer_id: str, user_message: str, 
                             bot_response: str, product_recommendations: bool) -> Optional[Dict]:
        """Log a chat interaction"""
        try:
            interaction_data = {
                "id": str(uuid.uuid4()),
                "influencer_id": influencer_id,
                "user_message": user_message,
                "bot_response": bot_response,
                "product_recommendations": product_recommendations
            }
            
            response = self.supabase.table('chat_interactions').insert(interaction_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error logging chat interaction: {str(e)}")
            return None