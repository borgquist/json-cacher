# JSON Cacher

A dedicated caching service for external API data. This service:

1. Fetches data from any API at configurable intervals
2. Stores the data in a local cache file
3. Serves the cached data through a local API endpoint
4. Maintains a backup of the latest successful response
5. Enforces rate limiting for API calls between restarts

This approach solves API rate limiting issues during development and provides uninterrupted access to external data.

## Getting Started

1. Clone this repository
2. Run the start script (it will create the necessary files and install dependencies):
   ```bash
   ./start.sh
   ```
3. Edit the `config.json` file with your API endpoint:
   ```json
   {
     "endpoint_url": "https://your-api-endpoint.com/data",
     "fetch_interval_seconds": 300,
     "rate_limit_enabled": true
   }
   ```
4. Access your cached data at:
   ```
   http://localhost:8000/data
   ```
   
   Note: The default port is 8000, but you can change it in the config.json file.

## Architecture

- `fetcher.py`: Polls the external API at regular intervals and caches the JSON response
- `api_server.py`: Provides local API endpoints to access the cached data
- `config.json`: Stores configuration settings that persist between restarts
- `start.sh`: Helper script to run both services with one command
- Docker support: `Dockerfile`, `docker-compose.yml`, and `docker-entrypoint.sh` for containerized deployment
- Backup: The latest successful response is stored in `last_successful_response.json`

## File Organization

- **Core Code**:
  - `fetcher.py`: Data retrieval service
  - `api_server.py`: API endpoint server
  
- **Configuration**:
  - `env.example`: Template for environment variables
  - `.env`: Your actual environment variables (not tracked in git)
  - `config.json`: Your actual configuration settings (not tracked in git)
  - `config.example.json`: Example configuration structure (for reference)
  
- **Data Files**:
  - `cached_data.json`: The current cached data
  - `last_successful_response.json`: Backup data in case of API failure
  - `fetcher_state.json`: State tracking for rate limiting
  
- **Startup & Deployment**:
  - `start.sh`: Script to run both services
  - `Dockerfile`: Container definition
  - `docker-compose.yml`: Multi-service container setup
  - `docker-entrypoint.sh`: Docker container startup script
  - `.dockerignore`: Files excluded from Docker builds

- **Logs**:
  - `fetcher.log`: Logs from the fetcher service
  - `api_server.log`: Logs from the API server

## Setup

1. Clone this repository
2. Create a `config.json` file based on the `config.example.json` template:

    ```bash
    cp config.example.json config.json
    ```

3. Edit the `config.json` file with your configuration:

    ```json
    {
      "endpoint_url": "https://your-api-endpoint.com/v1/data",
      "port": 8000,
      "fetch_interval_seconds": 300
    }
    ```

4. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

All configuration is managed through the `config.json` file. Each instance of the application can have its own configuration file.

### Basic Configuration

```json
{
  "endpoint_url": "https://your-api-endpoint.com/v1/data",
  "port": 8000,
  "fetch_interval_seconds": 300,
  "rate_limit_enabled": true
}
```

### Advanced Configuration

```json
{
  "endpoint_url": "https://your-api-endpoint.com/v1/data",
  "api_description": "My Weather API",
  "api_header_type": "bearer",
  "port": 8000,
  "log_level": "INFO",
  "log_response_filter": "data.metadata.version",
  "test_mode": false,
  "fetch_interval_seconds": 300,
  "rate_limit_enabled": true
}
```

For reference, a template configuration structure is available in `config.example.json`.

#### About Cache Refresh and Rate Limiting

The application uses two key settings to control how often it refreshes data:

1. **fetch_interval_seconds**: How often the service attempts to refresh its cache (e.g., every 5 minutes)
2. **rate_limit_enabled**: Whether to enforce rate limiting on API calls (default: true)

When rate limiting is enabled, the fetch interval is used for rate limiting as well. This simplifies configuration by allowing you to set just one interval.

#### API Authentication Header Options

Different APIs require different authentication header formats. The `api_header_type` setting allows you to configure how your API key is sent with requests:

1. **bearer** (default): Sends the API key as `Authorization: Bearer your_api_key`
2. **basic**: Sends the API key as `Authorization: Basic your_api_key`
3. **x-access-token**: Sends the API key as `x-access-token: your_api_key`
4. **custom header name**: Uses the value directly as the header name (e.g., if you set `api_header_type=api-key`, it will use `api-key: your_api_key`)

Example for an API using custom token headers:
```json
{
  "api_key": "your_api_key",
  "api_header_type": "x-access-token"
}
```

Example for a typical JWT-based API:
```json
{
  "api_key": "your_jwt_token",
  "api_header_type": "bearer"
}
```

#### Response Logging Filter

The `log_response_filter` option allows you to extract and log specific parts of API responses without flooding your logs with the entire response body. This is particularly useful for debugging or monitoring specific data points.

You can use two types of filters:

1. **JSON path**: Extract a specific field using dot notation
   ```json
   { "log_response_filter": "data.items.0.id" }
   ```

2. **Regex pattern**: Extract using a regular expression
   ```json
   { "log_response_filter": "\"id\":\"([^\"]+)\"" }
   ```

Examples:
- `data.metadata.version` - Extract the version field from the metadata object
- `items[0].status` - Get the status of the first item in the items array
- `"total_count":(\d+)` - Extract the total count value using a regex pattern

The filtered results will appear in your logs, making it easier to track specific data points without needing to inspect the entire response.

## Running the Service

### Method 1: Run Directly with Python

You need to run two processes:

```bash
# Terminal 1 - Data Fetcher
python fetcher.py

# Terminal 2 - API Server
python api_server.py
```

### Method 2: Using the Start Script

The repository includes a startup script that launches both services:

```bash
# Run both services with one command
./start.sh
```

The script automatically:
- Detects whether to use `python` or `python3` on your system
- Creates and activates a virtual environment if one doesn't exist
- Installs required dependencies if they're missing
- Creates `.env` and `config.json` from examples if they don't exist
- Runs both the fetcher and API server
- Adapts to different environments (local, server, Docker)

### Method 3: Using a Process Manager (Recommended for Production)

```bash
# Install PM2 with npm if you don't have it
npm install -g pm2

# Start both processes
pm2 start fetcher.py --name "json-fetcher"
pm2 start api_server.py --name "json-api" --interpreter python

# Make them start on boot
pm2 save
pm2 startup
```

## Using the Cached API

### Get the cached data

```
GET http://localhost:8000/data
```

The port can be changed by setting the PORT environment variable before starting the service.

### Check cache and rate limit status

```
GET http://localhost:8000/status
```

### View current configuration

```
GET http://localhost:8000/config
```

### Update configuration

```
POST http://localhost:8000/config
Content-Type: application/json

{
  "fetch_interval_seconds": 600,
  "rate_limit_enabled": true
}
```

### Get the backup data

```
GET http://localhost:8000/backup
```
