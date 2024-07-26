
import subprocess
import sys

def install_dependencies():
    """
    Installs necessary Python packages for the QGIS plugin.
    """
    # List of required packages
    required_packages = [
        'pandas',
        'geopandas',
        'mariadb', 
        'psycopg2-binary'
    ]

    # Install each package
    for package in required_packages:
        try:
            # Check if the package is already installed
            subprocess.check_call([sys.executable, '-m', 'pip', 'show', package])
            print(f"Package '{package}' is already installed.")
        except subprocess.CalledProcessError:
            # If not installed, attempt to install it
            try:
                print(f"Installing package '{package}'...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"Package '{package}' installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install package '{package}'. Error: {e}")

if __name__ == "__main__":
            install_dependencies()