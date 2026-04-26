# 🔐 Credentials, Configuration & Local vs Cloud Logging

## **TL;DR - Your Current Situation (No Cloud Providers)**

```env
# .env file for LOCAL LOGGING ONLY
APP_NAME=my-api
LOG_LEVEL=INFO
FILE_LOG_LEVEL=DEBUG
CLOUD_LOGGING_PROVIDERS=    # Empty = no cloud logging
```

```python
# Your code stays simple
from ai_service_kit.logging import setup_enhanced_logging, Logger

setup_enhanced_logging()  # One-time setup
Logger.info("This works perfectly without any cloud credentials!")
```

## **🎚️ Enable/Disable Control (Independent Systems)**

### **Local File Logging** (Always Available - No Credentials Needed)

```env
# Enable/disable local logging components
LOG_CONSOLE=true           # Console output on/off
FILE_LOG_LEVEL=DEBUG       # File logging level (empty = disable)
ERROR_FILE_LEVEL=ERROR     # Error file (empty = disable)
LOG_STRUCTURED=false       # Human-readable vs JSON
```

### **Cloud Logging** (Optional - Requires Credentials)

```env
# Global cloud toggle
CLOUD_LOGGING_PROVIDERS=               # Empty = ALL cloud disabled
CLOUD_LOGGING_PROVIDERS=aws,datadog    # Enable specific providers

# Per-provider toggles (double safety)
AWS_LOGGING_ENABLED=true
DATADOG_LOGGING_ENABLED=false
```

## **🔐 Credentials Required (Only for Cloud)**

### **AWS CloudWatch**

```env
# Credentials (choose one method)
AWS_ACCESS_KEY_ID=your-key              # Option 1: Environment variables
AWS_SECRET_ACCESS_KEY=your-secret
# OR use IAM roles (recommended in production)

# Configuration
AWS_LOG_GROUP=/my-api/production
AWS_REGION=us-east-1
AWS_LOGGING_LEVEL=ERROR                 # Only errors to CloudWatch (cost-effective)
```

**Package**: `pip install boto3`

### **Datadog**

```env
DATADOG_API_KEY=your-datadog-api-key
DATADOG_LOGGING_LEVEL=INFO              # Rich data for dashboards
```

**Package**: `pip install datadog`

### **Azure Monitor**

```env
AZURE_CONNECTION_STRING=InstrumentationKey=your-key
AZURE_LOGGING_LEVEL=ERROR
```

**Package**: `pip install applicationinsights`

### **Google Cloud**

```env
# Uses service account JSON or default credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_LOGGING_LEVEL=WARNING
```

**Package**: `pip install google-cloud-logging`

## **📊 Independent Log Levels**

Local and cloud logging have **completely separate** log level controls:

```env
# Local logging levels
LOG_LEVEL=WARNING           # Console shows WARNING+
FILE_LOG_LEVEL=DEBUG        # Files capture everything
ERROR_FILE_LEVEL=ERROR      # Error file gets errors only

# Cloud provider levels (independent)
AWS_LOGGING_LEVEL=ERROR     # Only errors to expensive CloudWatch
DATADOG_LOGGING_LEVEL=INFO  # Info+ to rich Datadog dashboards
AZURE_LOGGING_LEVEL=WARNING # Warnings to Azure alerting
```

## **✅ Yes, It Does Both!**

The system supports **simultaneous local + cloud logging** with independent configuration:

```env
# Example: Local files + AWS errors + Datadog everything
APP_NAME=my-api
FILE_LOG_LEVEL=DEBUG               # Local files get everything
LOG_LEVEL=WARNING                  # Console shows warnings+

CLOUD_LOGGING_PROVIDERS=aws,datadog
AWS_LOGGING_LEVEL=ERROR            # Only errors to CloudWatch (cost control)
DATADOG_LOGGING_LEVEL=INFO         # Rich data to Datadog

# Result:
# DEBUG → files only
# INFO → files + Datadog
# WARNING → files + Datadog + console
# ERROR → files + Datadog + console + CloudWatch
```

## **🚀 Common Configurations**

### **Development (Local Only)**

```env
APP_NAME=my-api
LOG_LEVEL=DEBUG
LOG_STRUCTURED=false
CLOUD_LOGGING_PROVIDERS=        # No cloud providers
```

### **Production Cost-Optimized**

```env
CLOUD_LOGGING_PROVIDERS=aws
AWS_LOGGING_LEVEL=ERROR         # Only errors to expensive CloudWatch
FILE_LOG_LEVEL=INFO             # Detailed local logs
```

### **Production Full Observability**

```env
CLOUD_LOGGING_PROVIDERS=aws,datadog
AWS_LOGGING_LEVEL=ERROR         # Errors for alerting
DATADOG_LOGGING_LEVEL=INFO      # Rich data for analysis
FILE_LOG_LEVEL=DEBUG            # Complete local logs
```

## **⚡ Graceful Fallbacks**

The system **never crashes** due to cloud issues:

- **Missing credentials** → Warning printed, cloud provider skipped
- **Missing packages** → Error message, continues with other providers
- **Network failures** → Error logged locally, continues operation
- **Invalid config** → Provider disabled, logs locally

Your application **always works** even if cloud providers fail!

## **🔧 Quick Start for Your Case**

Since you don't have cloud providers right now:

1. **Create .env file:**

```env
APP_NAME=my-api
LOG_LEVEL=INFO
FILE_LOG_LEVEL=DEBUG
CLOUD_LOGGING_PROVIDERS=
```

2. **Update your code (one time):**

```python
from ai_service_kit.logging import setup_enhanced_logging, Logger

setup_enhanced_logging()  # Replaces your old logging setup
```

3. **Use anywhere:**

```python
Logger.info("No __name__ needed!")
Logger.error("Goes to files + console + error file")
```

**Result**: Perfect local logging with rotation, structured JSON, error files, and the ability to add cloud providers later with **zero code changes** - just update your `.env` file!
