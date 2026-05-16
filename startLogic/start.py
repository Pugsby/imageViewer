import argparse
import os
import sys

argparse = argparse.ArgumentParser(description="Start the server. (It is reccomended to use start.sh/start.bat)")
argparse.add_argument("--windows", action="store_true", help="Start the application in Windows mode.")
argparse.add_argument("--linux", action="store_true", help="Start the application in Linux mode.")
args = argparse.parse_args()

windows = args.windows
linux = args.linux

if linux:
    breakSystemPackages = os.path.exists("/etc/arch-release")
    os.system("pip install -r requirements.txt" + (" --break-system-packages" if breakSystemPackages else ""))
elif windows:
    print("Please manually run 'pip install -r requirements.txt' in the command prompt to install the required packages. I don't wanna accidentally mess up ur pc.")

os.system("cd ./impData && python server.py")