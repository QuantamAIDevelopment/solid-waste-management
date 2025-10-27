"""Test script for automatic token generation."""
import os
import sys
import time
from loguru import logger

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.auth_service import get_auth_service

def test_auth_service():
    """Test the authentication service."""
    logger.info("🔐 Testing Automatic Token Generation")
    
    # Get auth service instance
    auth_service = get_auth_service()
    
    # Test token generation
    logger.info("📋 Getting token info...")
    token_info = auth_service.get_token_info()
    print(f"Token Info: {token_info}")
    
    # Test getting valid token
    logger.info("🎫 Getting valid token...")
    token = auth_service.get_valid_token()
    if token:
        logger.success(f"✅ Token generated successfully (length: {len(token)})")
        print(f"Token preview: {token[:50]}...")
    else:
        logger.error("❌ Failed to generate token")
    
    # Test force refresh
    logger.info("🔄 Testing force refresh...")
    success = auth_service.force_refresh()
    if success:
        logger.success("✅ Token refresh successful")
        new_token_info = auth_service.get_token_info()
        print(f"New Token Info: {new_token_info}")
    else:
        logger.error("❌ Token refresh failed")
    
    # Stop the refresh thread
    auth_service.stop_token_refresh()
    logger.info("🛑 Stopped token refresh thread")

if __name__ == "__main__":
    test_auth_service()