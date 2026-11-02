import subprocess
import sys
import os

def main():
    print("Starting German Course Helper...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\nStopping app...")
    except Exception as e:
        print(f"Error starting app: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()