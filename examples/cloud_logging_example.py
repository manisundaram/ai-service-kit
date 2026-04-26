"""
Real-world example of using ai-service-kit cloud logging.

This example shows how to set up logging that sends:
- DEBUG/INFO logs to files
- WARNING+ logs to console
- ERROR logs to AWS CloudWatch  
- INFO+ logs to Datadog

All configured via .env file - no code changes needed!
"""

import os
from ai_service_kit.logging import setup_enhanced_logging, Logger


def example_business_logic():
    """Example business logic with different log levels."""
    
    Logger.debug("Starting data processing pipeline")  # Files only
    Logger.info("Processing 1000 records")             # Files + Datadog
    Logger.warning("Cache miss, falling back to DB")   # Files + Datadog + Console
    Logger.error("Database connection failed!")        # Everything + CloudWatch


def main():
    """Example main function showing setup and usage."""
    
    # Option 1: Auto-configure from .env file (recommended)
    print("🚀 Setting up logging from environment...")
    setup_enhanced_logging()
    
    # That's it! All logging destinations are now configured based on your .env file
    
    # Use logging throughout your application
    Logger.info("Application started")
    
    try:
        example_business_logic()
        Logger.info("Business logic completed successfully")
    except Exception as e:
        Logger.error(f"Application error: {e}", exc_info=True)
    
    Logger.info("Application finished")


if __name__ == "__main__":
    # For this example, set up some environment variables
    # (In real usage, these would be in your .env file)
    
    example_env = {
        'APP_NAME': 'demo-api',
        'APP_ENV': 'production', 
        'LOG_LEVEL': 'WARNING',          # Console shows warnings+
        'FILE_LOG_LEVEL': 'DEBUG',       # Files get everything
        'LOG_STRUCTURED': 'true',        # JSON for production
        
        # Cloud logging (commented out to avoid requiring credentials)
        # 'CLOUD_LOGGING_PROVIDERS': 'aws,datadog',
        # 'AWS_LOGGING_ENABLED': 'true',
        # 'AWS_LOGGING_LEVEL': 'ERROR',   # Only errors to expensive CloudWatch
        # 'DATADOG_LOGGING_ENABLED': 'true', 
        # 'DATADOG_LOGGING_LEVEL': 'INFO', # Rich data to Datadog
    }
    
    # Temporarily set environment variables for demo
    for key, value in example_env.items():
        os.environ[key] = value
    
    # Run the example
    main()
    
    print("\n" + "="*60)
    print("💡 CLOUD LOGGING SETUP")
    print("="*60)
    print("To enable cloud logging, add to your .env file:")
    print()
    print("# Send errors to AWS CloudWatch")
    print("CLOUD_LOGGING_PROVIDERS=aws")
    print("AWS_LOGGING_ENABLED=true")  
    print("AWS_LOGGING_LEVEL=ERROR")
    print("AWS_LOG_GROUP=/my-api/production")
    print("AWS_REGION=us-east-1")
    print()
    print("# Send info+ to Datadog") 
    print("DATADOG_LOGGING_ENABLED=true")
    print("DATADOG_LOGGING_LEVEL=INFO")
    print("DATADOG_API_KEY=your-api-key")
    print()
    print("That's it! No code changes needed.")
    print("Your logs will automatically flow to all configured destinations.")