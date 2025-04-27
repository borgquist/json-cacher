import requests
import time
import json
import os
import logging
import random
import shutil
from dotenv import load_dotenv
from datetime import datetime, timedelta
from logger_config import configure_logging

# Configure logging with our central configuration
logger = configure_logging("fetcher")

# Load environment variables
load_dotenv()

# Constants
CACHE_FILE = "cached_data.json"
STATE_FILE = "fetcher_state.json"
CONFIG_FILE = "config.json"
BACKUP_FILE = "last_successful_response.json"
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds

# API authentication (from environment)
API_KEY = os.getenv("API_KEY")

# Default configuration values
DEFAULT_CONFIG = {
    "fetch_interval_seconds": 300,  # Cache refresh interval (5 minutes)
    "rate_limit_enabled": True,
    # If rate limiting is enabled, use the fetch interval by default
    # This simplifies configuration by using one value for both by default
}

# Default state
DEFAULT_STATE = {
    "last_api_call_timestamp": 0,
    "api_calls_count": 0,
    "successful_fetches_count": 0,
    "failed_fetches_count": 0,
    "last_successful_fetch": None
}

def load_config():
    """Load configuration primarily from environment variables, falling back to defaults"""
    # Start with default configuration
    config = DEFAULT_CONFIG.copy()
    
    # If config.json exists, load it as a fallback, but environment variables will override it
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                # Update config with saved values, but env vars will override these
                config.update(saved_config)
                logger.debug(f"Loaded fallback configuration from {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Store sensitive data in memory only, not in config.json
    runtime_config = config.copy()
    
    # API endpoint is a required configuration - without it, the app can't function
    if "ENDPOINT_URL" in os.environ:
        endpoint_url = os.getenv("ENDPOINT_URL")
        runtime_config["api_endpoint"] = endpoint_url
        logger.debug(f"Setting api_endpoint from environment: {endpoint_url}")
    elif "api_endpoint" not in runtime_config:
        # If we don't have an endpoint URL, set a default but log a warning
        logger.warning("No ENDPOINT_URL found in environment. Please set ENDPOINT_URL in .env file.")
        runtime_config["api_endpoint"] = "https://api.example.com/v1/data"
    
    # API description is optional - use a default if not provided
    if "API_DESCRIPTION" in os.environ:
        api_description = os.getenv("API_DESCRIPTION")
        runtime_config["api_description"] = api_description
        logger.debug(f"Setting api_description from environment: {api_description}")
    elif "api_description" not in runtime_config:
        runtime_config["api_description"] = "API"
    
    # Optional configuration from environment variables
    if "FETCH_INTERVAL_SECONDS" in os.environ:
        try:
            fetch_interval = int(os.getenv("FETCH_INTERVAL_SECONDS"))
            config["fetch_interval_seconds"] = fetch_interval
            runtime_config["fetch_interval_seconds"] = fetch_interval
            logger.debug(f"Setting fetch_interval_seconds from environment: {fetch_interval}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid FETCH_INTERVAL_SECONDS in environment: {e}")
    
    if "RATE_LIMIT_ENABLED" in os.environ:
        rate_limit = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
        config["rate_limit_enabled"] = rate_limit
        runtime_config["rate_limit_enabled"] = rate_limit
        logger.debug(f"Setting rate_limit_enabled from environment: {rate_limit}")
    
    # Save the public configuration to config.json for reference/fallback
    # Exclude sensitive data like API endpoints
    try:
        # Create a sanitized copy for storage - remove sensitive fields
        safe_config = {k: v for k, v in config.items() 
                      if k not in ["api_endpoint", "api_description", "API_KEY"]}
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(safe_config, f, indent=2)
        logger.debug(f"Saved safe configuration to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error saving config file: {e}")
    
    return runtime_config

def load_state():
    """Load state from state file or create with defaults if it doesn't exist"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                logger.debug(f"Loaded state from {STATE_FILE}")
                return state
        except Exception as e:
            logger.error(f"Error loading state file: {e}")
    
    # Initialize with default state
    state = DEFAULT_STATE.copy()
    save_state(state)
    logger.debug(f"Initialized default state")
    return state

def save_state(state):
    """Save current state to state file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def can_call_api(config, state):
    """Check if we're allowed to call the API based on rate limiting configuration"""
    if not config.get("rate_limit_enabled", True):
        return True
    
    # Always use fetch_interval for rate limiting
    min_time_between_calls = config.get("fetch_interval_seconds", 300)
    last_call_time = state.get("last_api_call_timestamp", 0)
    time_since_last_call = time.time() - last_call_time
    
    if time_since_last_call < min_time_between_calls:
        wait_time = min_time_between_calls - time_since_last_call
        logger.warning(f"Rate limit in effect. Need to wait {wait_time:.1f} more seconds before calling API")
        return False
    
    return True

def update_api_call_timestamp(state):
    """Update the timestamp of the last API call"""
    state["last_api_call_timestamp"] = time.time()
    state["api_calls_count"] += 1
    save_state(state)

def generate_sample_data():
    """Generate sample JSON data for testing"""
    logger.info("Generating sample data in TEST_MODE")
    
    # Current timestamp
    now = datetime.now()
    
    # Generate random sample data
    sample_data = {
        "timestamp": now.isoformat(),
        "request_id": f"req_{random.randint(10000, 99999)}",
        "status": "success",
        "data": {
            "items": []
        },
        "metadata": {
            "version": "1.0",
            "count": 10,
            "generated_at": now.isoformat(),
            "provider": "Sample Data Generator"
        }
    }
    
    # Generate some items
    for i in range(10):
        item = {
            "id": f"item_{i+1}",
            "value": round(random.uniform(0, 100), 2),
            "label": f"Sample Item {i+1}",
            "active": random.choice([True, False]),
            "category": random.choice(["A", "B", "C"]),
            "created_at": (now - timedelta(days=random.randint(0, 30))).isoformat()
        }
        sample_data["data"]["items"].append(item)
    
    # Add some statistics
    sample_data["statistics"] = {
        "min_value": min(item["value"] for item in sample_data["data"]["items"]),
        "max_value": max(item["value"] for item in sample_data["data"]["items"]),
        "avg_value": round(sum(item["value"] for item in sample_data["data"]["items"]) / len(sample_data["data"]["items"]), 2),
        "categories": {
            "A": len([item for item in sample_data["data"]["items"] if item["category"] == "A"]),
            "B": len([item for item in sample_data["data"]["items"] if item["category"] == "B"]),
            "C": len([item for item in sample_data["data"]["items"] if item["category"] == "C"])
        }
    }
    
    return sample_data

def create_backup(data):
    """Save a backup of the latest successful response"""
    try:
        # Add backup timestamp
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Save to backup file
        with open(BACKUP_FILE, "w") as f:
            json.dump(backup_data, f, indent=2)
        
        logger.debug(f"Saved backup of successful response to {BACKUP_FILE}")
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")

def fetch_and_cache(config, state):
    """Fetch data from the configured API endpoint and cache it"""
    # If in test mode, generate sample data
    if TEST_MODE:
        data = generate_sample_data()
        
        # Add metadata
        data["_meta"] = {
            "fetched_at": datetime.now().isoformat(),
            "source": "TEST_MODE",
            "is_sample_data": True
        }
        
        # Save to cache file
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
        
        # Create a backup of the successful response
        create_backup(data)
        
        # Update state
        state["last_successful_fetch"] = datetime.now().isoformat()
        state["successful_fetches_count"] += 1
        save_state(state)
        
        logger.info(f"Generated test data and cached successfully")
        return True
    
    # Only update the timestamp if we actually make an API call
    if can_call_api(config, state):
        update_api_call_timestamp(state)
        
        # Get API endpoint URL from config - runtime_config includes sensitive data
        api_endpoint = config.get("api_endpoint")
        
        # Fallback to environment variable if not in config
        if not api_endpoint and "ENDPOINT_URL" in os.environ:
            api_endpoint = os.getenv("ENDPOINT_URL")
        
        if not api_endpoint:
            logger.error("No API endpoint configured. Please set ENDPOINT_URL in .env file.")
            return False
            
        logger.info(f"Fetching new data from {api_endpoint}")
        
        # Check if we have an API key for authentication
        headers = {}
        if API_KEY:
            # Different APIs use different header names for API keys
            # We'll use the common Authorization header, but this might need to be adjusted
            headers["Authorization"] = f"Bearer {API_KEY}"
            logger.debug("Using API key for authentication")
        else:
            logger.debug("No API_KEY found in environment variables. Proceeding without authentication.")
        
        # Try to fetch the data with retries
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(api_endpoint, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    # Successfully fetched data
                    data = response.json()
                    
                    # Check if this data is different from what we already have
                    data_changed = True
                    if os.path.exists(CACHE_FILE):
                        try:
                            with open(CACHE_FILE, 'r') as f:
                                old_data = json.load(f)
                            
                            # Compare data without metadata
                            old_data_copy = old_data.copy()
                            if "_meta" in old_data_copy:
                                del old_data_copy["_meta"]
                            
                            new_data_copy = data.copy()
                            
                            # Convert to strings for comparison
                            old_str = json.dumps(old_data_copy, sort_keys=True)
                            new_str = json.dumps(new_data_copy, sort_keys=True)
                            
                            if old_str == new_str:
                                data_changed = False
                                logger.info("Fetched data is identical to cached data - no changes detected")
                        except Exception as e:
                            logger.warning(f"Could not compare with cached data: {e}")
                    
                    # Add metadata
                    data["_meta"] = {
                        "fetched_at": datetime.now().isoformat(),
                        "source": api_endpoint,
                        "status_code": response.status_code,
                        "cache_timestamp": datetime.now().isoformat(),
                        "changed": data_changed
                    }
                    
                    # Save to cache file
                    with open(CACHE_FILE, "w") as f:
                        json.dump(data, f)
                    
                    # Create a backup of the successful response
                    create_backup(data)
                    
                    # Update state
                    state["last_successful_fetch"] = datetime.now().isoformat()
                    state["successful_fetches_count"] += 1
                    save_state(state)
                    
                    # Get data size in bytes (approximate by converting to JSON string)
                    data_size = len(json.dumps(data))
                    
                    if data_changed:
                        logger.info(f"New data fetched and cached successfully. Size: {data_size} bytes")
                    else:
                        logger.info(f"Data refreshed (unchanged) and cached successfully. Size: {data_size} bytes")
                    
                    return True
                else:
                    logger.warning(f"API returned non-200 status code: {response.status_code}")
                    # Don't retry if we get a client error (4xx)
                    if 400 <= response.status_code < 500:
                        break
            except Exception as e:
                logger.error(f"Error fetching data (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            
            # If we get here, the attempt failed - wait before retrying
            if attempt < MAX_RETRIES - 1:  # Don't sleep after the last attempt
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
        
        # If we get here, all attempts failed
        state["failed_fetches_count"] += 1
        save_state(state)
        logger.error("Failed to fetch data after all retry attempts")
        return False
    else:
        # We can't call the API due to rate limiting
        logger.debug("Skipping API call due to rate limiting")
        return False

def calculate_next_run_time(config, state):
    """Calculate the time until the next API call, considering both cache refresh and rate limiting"""
    fetch_interval = config.get("fetch_interval_seconds", 300)
    
    # If rate limiting is enabled, also consider the time since last API call
    if config.get("rate_limit_enabled", True):
        last_call_time = state.get("last_api_call_timestamp", 0)
        time_since_last_call = time.time() - last_call_time
        
        # Use fetch_interval for rate limiting
        if time_since_last_call < fetch_interval:
            return max(fetch_interval, fetch_interval - time_since_last_call)
    
    return fetch_interval

def run():
    """Main run loop"""
    logger.info("Starting JSON cacher fetcher service")
    
    # On startup, try to copy the last backup to the cache file if the cache doesn't exist
    if not os.path.exists(CACHE_FILE) and os.path.exists(BACKUP_FILE):
        try:
            logger.info("No cache file found. Attempting to restore from backup.")
            with open(BACKUP_FILE, 'r') as src:
                backup_data = json.load(src)
                data = backup_data.get("data")
                
                # Add metadata to indicate this is from backup
                if data:
                    data["_meta"] = {
                        "restored_from_backup": True,
                        "original_timestamp": backup_data.get("timestamp"),
                        "restored_at": datetime.now().isoformat()
                    }
                    
                    with open(CACHE_FILE, 'w') as dest:
                        json.dump(data, dest)
                    logger.info("Successfully restored cache from backup")
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
    
    # Load initial configuration and state
    config = load_config()
    state = load_state()
    
    # Check if we need to wait due to rate limiting
    can_fetch = can_call_api(config, state)
    if not can_fetch:
        # Calculate time to wait
        fetch_interval = config.get("fetch_interval_seconds", 300)
        last_call_time = state.get("last_api_call_timestamp", 0)
        time_since_last_call = time.time() - last_call_time
        wait_time = max(0, fetch_interval - time_since_last_call)
        
        if wait_time > 0:
            logger.info(f"Will attempt first fetch in {wait_time:.1f} seconds due to rate limiting")
            time.sleep(wait_time)
            # Now we should be able to fetch
            fetch_and_cache(config, state)
    else:
        # We can fetch immediately on startup
        fetch_and_cache(config, state)
    
    while True:
        try:
            # Load configuration (might have been updated via API)
            config = load_config()
            
            # Load state (might have been updated via API or another process)
            state = load_state()
            
            # Calculate the time until next run
            wait_time = calculate_next_run_time(config, state)
            
            # Log the wait time at an appropriate level
            if wait_time > 60:
                logger.debug(f"Waiting {wait_time:.1f} seconds until next fetch")
            else:
                logger.debug(f"Waiting {wait_time:.1f} seconds until next fetch")
            
            # Sleep until next run
            time.sleep(wait_time)
            
            # Fetch and cache data from API
            fetch_and_cache(config, state)
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, exiting")
            break
        except Exception as e:
            logger.error(f"Unexpected error in run loop: {e}")
            # Sleep a bit before retrying to avoid rapid failure loops
            time.sleep(10)

if __name__ == "__main__":
    run()
