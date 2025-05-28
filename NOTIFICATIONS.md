# 🔔 JSON Cacher - Disconnection Notifications

This document explains how to receive real-time notifications when the JSON Cacher loses or regains connection to its data source.

## Overview

The JSON Cacher now provides real-time notifications about connection status changes using **Server-Sent Events (SSE)**. This allows your applications to:

- **Detect disconnections** immediately when the data source becomes unreachable
- **Handle reconnections** when the data source comes back online
- **Track connection health** with consecutive failure counts and timestamps
- **Implement graceful degradation** by switching to cached data during outages

## Connection Status Values

| Status | Description |
|--------|-------------|
| `connected` | ✅ Data source is reachable and responding |
| `disconnected` | ❌ Data source is unreachable (network error, timeout, HTTP error) |
| `unknown` | 🔄 Initial state before first connection attempt |

## API Endpoints

### 1. Status Endpoint (Polling)
```
GET /status
```

Returns current connection status in the response:

```json
{
  "state": {
    "connection_status": "connected",
    "last_connection_change": "2024-01-15T10:30:45.123Z",
    "consecutive_failures": 0,
    "last_successful_fetch": "2024-01-15T10:30:45.123Z"
  }
}
```

### 2. Events Endpoint (Real-time)
```
GET /events
```

Server-Sent Events stream for real-time notifications. See implementation examples below.

## Implementation Examples

### JavaScript (Browser)

```javascript
// Establish SSE connection
const eventSource = new EventSource('/events');

// Listen for connection status changes
eventSource.addEventListener('connection_status_change', function(event) {
    const data = JSON.parse(event.data);
    console.log('Connection status changed:', data);
    
    if (data.status === 'disconnected') {
        // Handle disconnection
        showDisconnectionWarning();
        switchToCachedData();
        console.warn(`Data source unreachable. Failures: ${data.consecutive_failures}`);
    } else if (data.status === 'connected') {
        // Handle reconnection
        hideDisconnectionWarning();
        refreshData();
        console.info('Data source connection restored!');
    }
});

// Handle initial connection status
eventSource.addEventListener('connection_status', function(event) {
    const data = JSON.parse(event.data);
    updateConnectionIndicator(data.status);
});

// Handle connection errors
eventSource.addEventListener('error', function(event) {
    console.error('SSE connection error:', event);
    if (eventSource.readyState === EventSource.CLOSED) {
        console.warn('SSE connection closed, attempting to reconnect...');
        // Implement reconnection logic if needed
    }
});

// Heartbeat events (optional - for connection health monitoring)
eventSource.addEventListener('heartbeat', function(event) {
    // Connection is alive - update last seen timestamp if needed
});
```

### Python (Client)

```python
import requests
import json
import sseclient  # pip install sseclient-py

def handle_connection_events():
    """Listen for connection status changes"""
    try:
        response = requests.get('http://localhost:8000/events', stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.event == 'connection_status_change':
                data = json.loads(event.data)
                
                if data['status'] == 'disconnected':
                    print(f"⚠️ Data source disconnected! Failures: {data['consecutive_failures']}")
                    # Handle disconnection - use cached data, show warnings, etc.
                    handle_disconnection(data)
                    
                elif data['status'] == 'connected':
                    print("✅ Data source reconnected!")
                    # Handle reconnection - refresh data, clear warnings, etc.
                    handle_reconnection(data)
                    
            elif event.event == 'connection_status':
                # Initial status
                data = json.loads(event.data)
                print(f"Initial connection status: {data['status']}")
                
    except Exception as e:
        print(f"Error listening for events: {e}")

def handle_disconnection(data):
    """Handle data source disconnection"""
    # Switch to cached data
    # Show user warnings
    # Log the issue
    pass

def handle_reconnection(data):
    """Handle data source reconnection"""
    # Refresh data from live source
    # Clear user warnings
    # Log the recovery
    pass
```

### Node.js (Server)

```javascript
const EventSource = require('eventsource');

const eventSource = new EventSource('http://localhost:8000/events');

eventSource.addEventListener('connection_status_change', (event) => {
    const data = JSON.parse(event.data);
    
    if (data.status === 'disconnected') {
        console.warn(`🔴 Data source disconnected: ${data.consecutive_failures} failures`);
        // Notify dependent services
        notifyServices('data_source_down', data);
    } else if (data.status === 'connected') {
        console.info('🟢 Data source reconnected');
        // Notify dependent services
        notifyServices('data_source_up', data);
    }
});

eventSource.addEventListener('error', (event) => {
    console.error('SSE connection error:', event);
});
```

## Event Data Structure

### Connection Status Change Event
```json
{
  "status": "disconnected",
  "previous_status": "connected", 
  "last_change": "2024-01-15T10:35:22.456Z",
  "consecutive_failures": 3
}
```

### Initial Connection Status Event
```json
{
  "status": "connected",
  "last_change": "2024-01-15T10:30:45.123Z",
  "consecutive_failures": 0
}
```

## Use Cases

### 1. Web Dashboard
Show a connection indicator and warning messages when the data source is unavailable:

```javascript
function updateConnectionIndicator(status) {
    const indicator = document.getElementById('connection-status');
    
    if (status === 'connected') {
        indicator.className = 'status-connected';
        indicator.textContent = '🟢 Live Data';
    } else if (status === 'disconnected') {
        indicator.className = 'status-disconnected';
        indicator.textContent = '🔴 Using Cached Data';
    }
}
```

### 2. Microservice Health Monitoring
Propagate connection status to other services:

```javascript
eventSource.addEventListener('connection_status_change', (event) => {
    const data = JSON.parse(event.data);
    
    // Update service registry
    updateServiceHealth('json-cacher', data.status === 'connected');
    
    // Send alerts if needed
    if (data.status === 'disconnected' && data.consecutive_failures >= 3) {
        sendAlert('JSON Cacher data source unreachable', data);
    }
});
```

### 3. Mobile App Offline Mode
Switch between live and cached data seamlessly:

```javascript
let useCache = false;

eventSource.addEventListener('connection_status_change', (event) => {
    const data = JSON.parse(event.data);
    useCache = (data.status === 'disconnected');
    
    // Update UI to show offline mode
    if (useCache) {
        showOfflineBanner();
    } else {
        hideOfflineBanner();
        refreshCurrentView();
    }
});
```

## Best Practices

1. **Graceful Degradation**: Always have a fallback to cached data when the source is disconnected
2. **User Communication**: Show clear indicators when using cached vs. live data
3. **Reconnection Handling**: Refresh data automatically when connection is restored
4. **Error Handling**: Implement proper error handling for SSE connection issues
5. **Resource Management**: Close SSE connections when no longer needed

## Troubleshooting

### SSE Connection Issues
- Ensure your client supports Server-Sent Events
- Check firewall/proxy settings that might block SSE
- Implement reconnection logic for network interruptions

### Missing Events
- Verify the JSON Cacher service is running
- Check that the `/events` endpoint is accessible
- Monitor console for JavaScript errors

### Performance Considerations
- SSE connections are lightweight but limit concurrent connections per browser
- Consider using WebSockets for high-frequency updates if needed
- Monitor memory usage in long-running applications

## Configuration

The notification system works automatically with your existing JSON Cacher configuration. No additional setup is required - just start listening to the `/events` endpoint.

### False Positive Reduction

To minimize false alarms, the system includes several safeguards:

#### 1. **Consecutive Failure Threshold**
The system requires multiple consecutive failures before marking the connection as disconnected (default: 3 failures).

```json
{
  "connection_failure_threshold": 3
}
```

#### 2. **Smart Error Classification**
Not all errors count toward disconnection:

**Temporary errors (don't count immediately):**
- Timeouts and connection timeouts
- SSL handshake issues
- HTTP 429 (rate limiting), 502, 503, 504 responses
- Temporary DNS resolution failures
- Network unreachable (brief)

**Persistent errors (count toward disconnection):**
- Connection refused
- Host not found / DNS resolution failure
- HTTP 4xx client errors (except 429)
- HTTP 5xx server errors (except 502, 503, 504)

#### 3. **Configurable Timeout**
Adjust the request timeout to match your API's typical response time:

```json
{
  "request_timeout_seconds": 30
}
```

### Configuration Options

Add these optional settings to your `config.json`:

```json
{
  "connection_failure_threshold": 3,
  "request_timeout_seconds": 30
}
```

Connection status is determined by:
- **HTTP response codes** (200 = connected, others = disconnected)
- **Network errors** (timeouts, DNS failures, etc.)
- **Request exceptions** (SSL errors, connection refused, etc.)

The system tracks consecutive failures and timestamps for detailed monitoring. 