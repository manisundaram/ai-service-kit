"""
Complete guide to credentials, enable/disable flags, and local vs cloud logging.

This example demonstrates all the configuration options for controlling
logging destinations independently.
"""

import os
import time
from ai_service_kit.logging import setup_enhanced_logging, Logger


def demonstrate_logging_scenarios():
    """Demonstrate different logging scenarios."""
    
    print("🔥 Testing different log levels...")
    Logger.debug("This is a debug message")       # Files only (if FILE_LOG_LEVEL=DEBUG)
    Logger.info("This is an info message")        # Files + some cloud providers
    Logger.warning("This is a warning message")   # Files + console + most cloud providers  
    Logger.error("This is an error message")      # Everything (all destinations)
    
    print("✅ Log test completed")


def main():
    """Main demonstration function."""
    
    print("="*80)
    print("🎛️  LOGGING CONFIGURATION SCENARIOS")
    print("="*80)
    
    print("\n📋 SCENARIO 1: LOCAL FILES ONLY (No Cloud)")
    print("-" * 50)
    
    # Local files only - no cloud providers
    os.environ.update({
        'APP_NAME': 'local-only-demo',
        'LOG_LEVEL': 'INFO',
        'FILE_LOG_LEVEL': 'DEBUG',
        'LOG_CONSOLE': 'true',
        'CLOUD_LOGGING_PROVIDERS': '',  # Empty = no cloud logging
    })
    
    setup_enhanced_logging()
    demonstrate_logging_scenarios()
    
    print("\n📤 SCENARIO 2: CLOUD + LOCAL (Fake credentials for demo)")
    print("-" * 50)
    
    # Enable cloud logging with fake credentials (will fail gracefully)
    os.environ.update({
        'APP_NAME': 'cloud-demo',
        'CLOUD_LOGGING_PROVIDERS': 'aws,datadog',
        
        # AWS settings (will fail without real credentials)
        'AWS_LOGGING_ENABLED': 'true',
        'AWS_LOGGING_LEVEL': 'ERROR',
        'AWS_LOG_GROUP': '/demo/logs',
        
        # Datadog settings (will fail without real API key)
        'DATADOG_LOGGING_ENABLED': 'true', 
        'DATADOG_LOGGING_LEVEL': 'INFO',
        'DATADOG_API_KEY': 'fake-api-key-for-demo',
    })
    
    setup_enhanced_logging()  # Will warn about missing credentials
    demonstrate_logging_scenarios()


if __name__ == "__main__":
    main()
    
    print("\n" + "="*80)
    print("📝 CREDENTIALS & CONFIGURATION SUMMARY")
    print("="*80)
    
    print("""
🔐 CREDENTIALS REQUIRED:

AWS CloudWatch:
    - AWS_ACCESS_KEY_ID & AWS_SECRET_ACCESS_KEY (environment variables)
    - OR use IAM roles (recommended in production)
    - boto3 package: pip install boto3

Azure Monitor: 
    - AZURE_CONNECTION_STRING (from Application Insights)
    - applicationinsights package: pip install applicationinsights

Google Cloud:
    - GOOGLE_APPLICATION_CREDENTIALS (service account JSON file path)
    - OR default credentials (gcloud auth application-default login)
    - google-cloud-logging package: pip install google-cloud-logging

Datadog:
    - DATADOG_API_KEY (from Datadog dashboard)
    - datadog package: pip install datadog

🎚️  ENABLE/DISABLE FLAGS:

Global Cloud Logging:
    CLOUD_LOGGING_PROVIDERS=""              # Disable ALL cloud logging
    CLOUD_LOGGING_PROVIDERS="aws,datadog"   # Enable specific providers

Per-Provider Control:  
    AWS_LOGGING_ENABLED=false              # Disable AWS even if listed
    DATADOG_LOGGING_ENABLED=true           # Enable Datadog
    
Local File Logging (Always Available):
    LOG_CONSOLE=false                      # Disable console output
    FILE_LOG_LEVEL=""                      # Disable file logging
    ERROR_FILE_LEVEL=""                    # Disable error file

📊 INDEPENDENT LOG LEVELS:

Local Logging:
    LOG_LEVEL=WARNING          # Console shows WARNING+
    FILE_LOG_LEVEL=DEBUG       # Files get DEBUG+ 
    ERROR_FILE_LEVEL=ERROR     # Error file gets ERROR+

Cloud Logging (Per Provider):
    AWS_LOGGING_LEVEL=ERROR         # Only errors to CloudWatch  
    DATADOG_LOGGING_LEVEL=INFO      # Info+ to Datadog
    AZURE_LOGGING_LEVEL=WARNING     # Warning+ to Azure
    GCP_LOGGING_LEVEL=ERROR         # Errors to Google Cloud

🚀 QUICK SETUPS:

Development (Local Only):
    CLOUD_LOGGING_PROVIDERS=""
    LOG_LEVEL=DEBUG
    LOG_STRUCTURED=false
    
Production (Cost-Optimized):
    CLOUD_LOGGING_PROVIDERS="aws"
    AWS_LOGGING_LEVEL=ERROR        # Only errors to expensive CloudWatch
    FILE_LOG_LEVEL=INFO            # Detailed local logs
    
Production (Full Observability):
    CLOUD_LOGGING_PROVIDERS="aws,datadog"  
    AWS_LOGGING_LEVEL=ERROR        # Errors for alerts
    DATADOG_LOGGING_LEVEL=INFO     # Rich data for analysis
""")
    
    print("\n🔧 FILES TO CHECK:")
    print("- logs/ directory (local files)")
    print("- Cloud provider dashboards (if configured)")
    print("- Console output (if LOG_CONSOLE=true)")
    
    # Show what files were created
    try:
        import os
        logs_dir = "./logs"
        if os.path.exists(logs_dir):
            files = os.listdir(logs_dir)
            print(f"\n📁 Local log files created: {', '.join(files)}")
    except Exception:
        pass