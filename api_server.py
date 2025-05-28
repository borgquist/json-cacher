import os
import json
import logging
import time
import threading
import queue
from datetime import datetime
from flask import Flask, jsonify, request, redirect, Response
from flask_cors import CORS
from logger_config import configure_logging

# Configure logging with our central configuration
logger = configure_logging("api_server")

# Constants
CACHE_FILE = "cached_data.json"
STATE_FILE = "fetcher_state.json"
CONFIG_FILE = "config.json"
BACKUP_FILE = "last_successful_response.json"

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Disable Flask's default logging
app.logger.disabled = True

# SSE client management
sse_clients = []
sse_lock = threading.Lock()

def add_sse_client(client_queue):
    """Add a new SSE client"""
    with sse_lock:
        sse_clients.append(client_queue)

def remove_sse_client(client_queue):
    """Remove an SSE client"""
    with sse_lock:
        if client_queue in sse_clients:
            sse_clients.remove(client_queue)

def broadcast_notification(event_type, data):
    """Broadcast a notification to all connected SSE clients"""
    with sse_lock:
        disconnected_clients = []
        for client_queue in sse_clients:
            try:
                client_queue.put({
                    "event": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
            except:
                # Client is disconnected, mark for removal
                disconnected_clients.append(client_queue)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            sse_clients.remove(client)

def monitor_connection_status():
    """Background thread to monitor connection status changes"""
    last_status = None
    
    while True:
        try:
            state = load_state()
            current_status = state.get("connection_status", "unknown")
            
            # Check if status changed
            if last_status is not None and last_status != current_status:
                # Broadcast the status change
                broadcast_notification("connection_status_change", {
                    "status": current_status,
                    "previous_status": last_status,
                    "last_change": state.get("last_connection_change"),
                    "consecutive_failures": state.get("consecutive_failures", 0)
                })
                
                logger.info(f"Broadcasting connection status change: {last_status} -> {current_status}")
            
            last_status = current_status
            time.sleep(2)  # Check every 2 seconds
            
        except Exception as e:
            logger.error(f"Error in connection status monitor: {e}")
            time.sleep(5)  # Wait longer on error

# Start the background monitoring thread
monitor_thread = threading.Thread(target=monitor_connection_status, daemon=True)
monitor_thread.start()

def load_config():
    """Load configuration from config.json"""
    # Start with a default config
    config = {
        "fetch_interval_seconds": 300,
        "rate_limit_enabled": True,
        "port": 8000,
        "endpoint_url": "https://api.example.com/v1/data",
        "api_description": "API",
        "api_header_type": "bearer",
        "test_mode": False,
        "log_level": "INFO",
        "log_response_filter": ""
    }
    
    # If config.json exists, load settings from it
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                # Update config with saved values
                config.update(saved_config)
                logger.debug(f"Loaded configuration from {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    else:
        logger.warning(f"No {CONFIG_FILE} found. Using default configuration.")
        # Create default config file
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Created default config file at {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Error creating default config file: {e}")
    
    # For backwards compatibility, convert api_endpoint to endpoint_url if needed
    if "api_endpoint" in config and "endpoint_url" not in config:
        config["endpoint_url"] = config["api_endpoint"]
    
    return config

def load_state():
    """Load state from state file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                return state
        except Exception as e:
            logger.error(f"Error loading state file: {e}")
    
    # Default state if file doesn't exist
    return {
        "last_api_call_timestamp": 0,
        "api_calls_count": 0,
        "successful_fetches_count": 0,
        "failed_fetches_count": 0,
        "last_successful_fetch": None
    }

def get_backup_info():
    """Get information about the backup file"""
    if not os.path.exists(BACKUP_FILE):
        return None
    
    try:
        # Get file stats
        stats = os.stat(BACKUP_FILE)
        file_size = stats.st_size
        last_modified = stats.st_mtime
        
        # Get timestamp from backup file
        with open(BACKUP_FILE, 'r') as f:
            data = json.load(f)
            timestamp = data.get("timestamp")
        
        # Calculate age
        now = time.time()
        age_seconds = now - last_modified
        
        return {
            "file_size_bytes": file_size,
            "last_modified": datetime.fromtimestamp(last_modified).isoformat(),
            "timestamp": timestamp,
            "age_seconds": int(age_seconds),
            "age_hours": round(age_seconds / 3600, 1)
        }
    except Exception as e:
        logger.error(f"Error getting backup info: {e}")
        return None

def get_cached_data():
    """Get cached data from file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading cache file: {e}")
    
    # Try to load from backup if cache doesn't exist
    if os.path.exists(BACKUP_FILE):
        logger.info("Cache file not found, trying to use backup")
        try:
            with open(BACKUP_FILE, 'r') as f:
                backup_data = json.load(f)
                # Return the data from the backup
                return backup_data.get("data")
        except Exception as e:
            logger.error(f"Error reading backup file: {e}")
    
    return None

def save_config(config):
    """Save non-sensitive configuration to file"""
    try:
        # Create a sanitized copy for storage - remove sensitive fields
        safe_config = {k: v for k, v in config.items() 
                      if k not in ["api_endpoint", "api_description", "API_KEY"]}
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(safe_config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

@app.route('/')
def home():
    """Redirect to status page"""
    return redirect('/status')

@app.route('/data')
def get_data():
    """API endpoint to get the cached data"""
    # Log client requests with their IP address
    client_ip = request.remote_addr
    logger.info(f"Data requested by client {client_ip}")
    # Also print to console explicitly with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - API: Data requested by client {client_ip}")
    
    data = get_cached_data()
    if data:
        return jsonify(data)
    else:
        logger.warning(f"Request for /data from {client_ip} but no data available")
        return jsonify({"error": "No data available"}), 404

@app.route('/backup')
def get_backup():
    """API endpoint to get backup data"""
    # Log backup data requests with client IP
    client_ip = request.remote_addr
    logger.info(f"Backup data requested by client {client_ip}")
    # Also print to console with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - API: Backup data requested by client {client_ip}")
    
    if not os.path.exists(BACKUP_FILE):
        logger.warning(f"Request for /backup from {client_ip} but no backup available")
        return jsonify({"error": "No backup available"}), 404
    
    try:
        with open(BACKUP_FILE, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error reading backup file for client {client_ip}: {e}")
        return jsonify({"error": f"Failed to read backup: {str(e)}"}), 500

@app.route('/status')
def get_status():
    """API endpoint to get cacher status"""
    # Log status requests with client IP
    client_ip = request.remote_addr
    logger.info(f"Status requested by client {client_ip}")
    # Also print to console with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - API: Status requested by client {client_ip}")
    
    config = load_config()
    state = load_state()
    
    # Calculate time since last API call
    last_call_time = state.get("last_api_call_timestamp", 0)
    time_since_last_call = time.time() - last_call_time
    
    # Calculate next scheduled API call
    fetch_interval = config.get("fetch_interval_seconds", 300)
    next_call_seconds = max(0, fetch_interval - time_since_last_call)
    
    # Rate limiting info
    rate_limit_enabled = config.get("rate_limit_enabled", True)
    # Always use fetch_interval for rate limiting
    min_time_between_calls = fetch_interval
    rate_limit_seconds_remaining = max(0, min_time_between_calls - time_since_last_call) if rate_limit_enabled else 0
    
    # Get information about cached data
    cache_exists = os.path.exists(CACHE_FILE)
    cache_size = os.path.getsize(CACHE_FILE) if cache_exists else 0
    cache_age = 0
    
    if cache_exists:
        try:
            cache_mtime = os.path.getmtime(CACHE_FILE)
            cache_age = time.time() - cache_mtime
        except:
            pass
    
    # Get backup info
    backup_info = get_backup_info()
    
    # Get API description from config
    api_description = config.get("api_description", "API")
    api_endpoint = config.get("endpoint_url", "")
    
    status = {
        "version": "1.2.0",
        "api": {
            "description": api_description,
            "endpoint": api_endpoint
        },
        "state": {
            "last_api_call": datetime.fromtimestamp(last_call_time).isoformat() if last_call_time > 0 else None,
            "time_since_last_call_seconds": round(time_since_last_call),
            "next_call_seconds": round(next_call_seconds),
            "api_calls_count": state.get("api_calls_count", 0),
            "successful_fetches_count": state.get("successful_fetches_count", 0),
            "failed_fetches_count": state.get("failed_fetches_count", 0),
            "last_successful_fetch": state.get("last_successful_fetch"),
            "connection_status": state.get("connection_status", "unknown"),
            "last_connection_change": state.get("last_connection_change"),
            "consecutive_failures": state.get("consecutive_failures", 0)
        },
        "config": {
            "fetch_interval_seconds": fetch_interval,
            "rate_limit_enabled": rate_limit_enabled
        },
        "cache": {
            "exists": cache_exists,
            "size_bytes": cache_size,
            "age_seconds": round(cache_age)
        },
        "backup": backup_info
    }
    
    return jsonify(status)

@app.route('/events')
def events():
    """Server-Sent Events endpoint for real-time notifications"""
    client_ip = request.remote_addr
    logger.info(f"SSE connection established from client {client_ip}")
    # Also print to console with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - API: SSE connection established from client {client_ip}")
    
    def event_stream():
        client_queue = queue.Queue()
        add_sse_client(client_queue)
        
        try:
            # Send initial connection status
            state = load_state()
            initial_data = {
                "status": state.get("connection_status", "unknown"),
                "last_change": state.get("last_connection_change"),
                "consecutive_failures": state.get("consecutive_failures", 0)
            }
            yield f"event: connection_status\ndata: {json.dumps(initial_data)}\n\n"
            
            # Send periodic heartbeats and handle notifications
            while True:
                try:
                    # Check for new notifications (with timeout)
                    notification = client_queue.get(timeout=30)
                    event_name = notification["event"]
                    event_data = json.dumps(notification["data"])
                    yield f"event: {event_name}\ndata: {event_data}\n\n"
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
                except:
                    # Client disconnected
                    break
        finally:
            remove_sse_client(client_queue)
            logger.info(f"SSE connection closed for client {client_ip}")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} - API: SSE connection closed for client {client_ip}")
    
    return Response(event_stream(), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*',
                           'Access-Control-Allow-Headers': 'Cache-Control'})

@app.route('/config', methods=['GET', 'POST'])
def manage_config():
    """API endpoint to get/update configuration"""
    # Log configuration requests with client IP
    client_ip = request.remote_addr
    
    if request.method == 'GET':
        logger.info(f"Configuration requested by client {client_ip}")
        # Print to console with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} - API: Configuration requested by client {client_ip}")
        
        # Return only non-sensitive configuration
        config = load_config()
        safe_config = {k: v for k, v in config.items() 
                      if k not in ["api_endpoint", "api_description", "API_KEY"]}
        return jsonify(safe_config)
    
    elif request.method == 'POST':
        logger.info(f"Configuration update requested by client {client_ip}")
        # Print to console with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} - API: Configuration update requested by client {client_ip}")
        try:
            update_data = request.get_json()
            if not update_data:
                logger.warning(f"Empty configuration update from client {client_ip}")
                return jsonify({"error": "No data provided"}), 400
            
            # Load current config
            config = load_config()
            
            # Update configuration values
            if 'fetch_interval_seconds' in update_data:
                try:
                    interval = int(update_data['fetch_interval_seconds'])
                    if interval < 10:
                        return jsonify({"error": "fetch_interval_seconds must be at least 10 seconds"}), 400
                    config['fetch_interval_seconds'] = interval
                except (ValueError, TypeError):
                    return jsonify({"error": "fetch_interval_seconds must be an integer"}), 400
            
            if 'rate_limit_enabled' in update_data:
                config['rate_limit_enabled'] = bool(update_data['rate_limit_enabled'])
            
            # Don't allow updating sensitive config via API
            if 'endpoint_url' in update_data:
                logger.warning(f"Client {client_ip} attempted to update endpoint_url - rejected for security")
                return jsonify({"error": "Updating API endpoint via API is not allowed for security reasons"}), 403
            
            if 'api_description' in update_data:
                config['api_description'] = update_data['api_description']
            
            # Save updated config
            if save_config(config):
                logger.info(f"Configuration updated by client {client_ip}: {config}")
                
                # Return only non-sensitive configuration
                safe_config = {k: v for k, v in config.items() 
                              if k not in ["api_endpoint", "api_description", "API_KEY"]}
                return jsonify({"message": "Configuration updated successfully", "config": safe_config})
            else:
                logger.error(f"Failed to save configuration for client {client_ip}")
                return jsonify({"error": "Failed to save configuration"}), 500
            
        except Exception as e:
            logger.error(f"Error updating config from client {client_ip}: {e}")
            return jsonify({"error": f"Failed to update configuration: {str(e)}"}), 500

if __name__ == '__main__':
    config = load_config()
    port = config.get("port", 8000)
    logger.info(f"Starting API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 