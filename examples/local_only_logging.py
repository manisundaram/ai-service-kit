"""
Simple example for local file logging only - no cloud providers needed.

Perfect for development or when you don't have cloud provider credentials.
"""

import os
from ai_service_kit.logging import setup_enhanced_logging, Logger


def main():
    """Example showing local-only logging setup."""
    
    print("🏠 Setting up LOCAL FILE LOGGING ONLY...")
    print("-" * 50)
    
    # Configure for local files only
    os.environ.update({
        'APP_NAME': 'my-local-app',
        'LOG_LEVEL': 'INFO',
        'FILE_LOG_LEVEL': 'DEBUG',
        'LOG_STRUCTURED': 'false',  # Human-readable for development
        'LOG_CONSOLE': 'true',
        
        # The key: empty providers = NO cloud logging
        'CLOUD_LOGGING_PROVIDERS': '',  # This disables ALL cloud logging
    })
    
    # One line setup - reads all config from environment
    setup_enhanced_logging()
    
    print("✅ Logging configured for LOCAL FILES ONLY")
    print("   ➤ No API keys needed")
    print("   ➤ No cloud dependencies") 
    print("   ➤ No external network calls")
    print()
    
    # Test different log levels
    print("🔥 Testing log levels...")
    Logger.debug("Debug info (files only)")
    Logger.info("Important info (files + console)")
    Logger.warning("Something to watch (files + console)")
    Logger.error("Something went wrong! (files + console)")
    
    print("✅ Logging test completed")
    
    # Show what files were created
    logs_dir = "./logs"
    if os.path.exists(logs_dir):
        files = os.listdir(logs_dir)
        print(f"\n📁 Log files created in ./logs/:")
        for file in files:
            if file.startswith('my-local-app'):
                print(f"   ➤ {file}")


if __name__ == "__main__":
    main()
    
    print("\n" + "="*60)
    print("💡 YOUR SETUP FOR LOCAL-ONLY LOGGING")
    print("="*60)
    
    print("""
Copy this to your .env file:

    APP_NAME=my-api
    LOG_LEVEL=INFO
    FILE_LOG_LEVEL=DEBUG
    LOG_STRUCTURED=false
    CLOUD_LOGGING_PROVIDERS=

Then in your code:

    from ai_service_kit.logging import setup_enhanced_logging, Logger
    
    setup_enhanced_logging()  # One-time setup
    
    Logger.info("This goes to files + console")
    Logger.error("This also goes to error file")

That's it! No cloud credentials needed.
""")
    
    # Show an example of reading the log file
    print("📖 SAMPLE LOG FILE CONTENT:")
    print("-" * 30)
    try:
        with open("./logs/my-local-app.log", "r") as f:
            lines = f.readlines()[-3:]  # Last 3 lines
            for line in lines:
                print(f"   {line.rstrip()}")
    except FileNotFoundError:
        print("   (Log file not found - run the example first)")
    except Exception as e:
        print(f"   (Could not read log file: {e})")