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
3. Edit the `.env` file with your API endpoint:
   ```
   ENDPOINT_URL=https://your-api-endpoint.com/data
   ```
4. Access your cached data at:
   ```
   http://localhost:8000/data
   ```
   
   Note: The default port is 8000, but you can change it by setting the PORT environment variable:
   ```bash
   PORT=3000 ./start.sh
   ```

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
  - `config.json`: Runtime configuration (can be modified via API)
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
2. Create a `.env` file based on the `env.example` template:

    ```bash
    cp env.example .env
    ```

3. Edit the `.env` file with your configuration:

    ```
    # For APIs requiring authentication (or leave commented out if none needed)
    # API_KEY=your_api_key_here
    
    # Required: Your API endpoint URL
    ENDPOINT_URL=https://your-api-endpoint.com/v1/data
    
    # Optional: Change the API server port (default: 8000)
    PORT=8000
    ```

4. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

All configuration is managed through environment variables in the `.env` file. No need to manually edit any JSON files!

### Basic Configuration

```
# API Configuration
# For APIs requiring authentication (uncomment if needed):
# API_KEY=your_api_key_here

# API header style for authentication (default: bearer)
# Options: bearer, basic, x-access-token, or any custom header name
# API_HEADER_TYPE=bearer

# Required: Your API endpoint URL
ENDPOINT_URL=https://your-api-endpoint.com/v1/data

# Server configuration
PORT=8000  # Default API server port
```

### Advanced Configuration

```
# API description for logs and status
API_DESCRIPTION=My Weather API

# API header configuration
API_HEADER_TYPE=bearer  # Options: bearer, basic, x-access-token, or custom header name

# Fetcher configuration 
TEST_MODE=false  # Set to true to generate test data
FETCH_INTERVAL_SECONDS=300  # Cache refresh interval (5 min)

# Rate limiting
RATE_LIMIT_ENABLED=true
# The following is optional - if not set, the fetch interval will be used
MIN_TIME_BETWEEN_API_CALLS_SECONDS=300
```

The application saves your configuration to `config.json` for reference, but this file should not be committed to your repository (it's in the `.gitignore`).

For reference, here's the default configuration structure (also available in `config.example.json`):

```json
{
  "fetch_interval_seconds": 300,
  "rate_limit_enabled": true
}
```

#### About Cache Refresh and Rate Limiting

The application uses two key settings to control how often it refreshes data:

1. **fetch_interval_seconds**: How often the service attempts to refresh its cache (e.g., every 5 minutes)
2. **rate_limit_enabled**: Whether to enforce rate limiting on API calls (default: true)

When rate limiting is enabled but no `min_time_between_api_calls_seconds` is specified, the fetch interval is used for rate limiting as well. This simplifies configuration by allowing you to set just one interval.

If you need more control, you can explicitly set `min_time_between_api_calls_seconds` to a different value than your fetch interval. This is useful for APIs with strict rate limits.

These settings control the caching behavior and rate limiting. Your API endpoint and other settings should be defined in your `.env` file, not in config.json.

#### API Authentication Header Options

Different APIs require different authentication header formats. The `API_HEADER_TYPE` setting allows you to configure how your API key is sent with requests:

1. **bearer** (default): Sends the API key as `Authorization: Bearer your_api_key`
2. **basic**: Sends the API key as `Authorization: Basic your_api_key`
3. **x-access-token**: Sends the API key as `x-access-token: your_api_key`
4. **custom header name**: Uses the value directly as the header name (e.g., if you set `API_HEADER_TYPE=api-key`, it will use `api-key: your_api_key`)

Example for an API using custom token headers:
```
API_KEY=your_api_key
API_HEADER_TYPE=x-access-token
```

Example for a typical JWT-based API:
```
API_KEY=your_jwt_token
API_HEADER_TYPE=bearer
```

#### Security Considerations

For security reasons, sensitive information like your API endpoint URL is:
- Stored only in your `.env` file, not in config.json
- Kept in memory during runtime, not written to any configuration files
- Never committed to the repository (both `.env` and `config.json` are in .gitignore)

This approach prevents accidentally exposing your API keys or endpoints in your version control system.

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
