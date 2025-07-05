# Installation Guide

## Prerequisites

Before running this backend, you need to install Python 3.8 or higher.

### Installing Python

1. **Download Python:**
   - Go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - Download the latest Python version for Windows
   - Choose the Windows Installer (.exe) for your system architecture (x64 recommended)

2. **Install Python:**
   - Run the downloaded installer
   - **Important:** Check the box that says "Add Python to PATH"
   - Choose "Install Now" for standard installation
   - Complete the installation

3. **Verify Installation:**
   Open a new PowerShell or Command Prompt window and run:
   ```bash
   python --version
   pip --version
   ```
   Both commands should return version numbers.

### Alternative: Using Microsoft Store

You can also install Python from the Microsoft Store:
1. Open Microsoft Store
2. Search for "Python"
3. Install the latest version (e.g., "Python 3.11")

## Project Setup

Once Python is installed:

1. **Navigate to the project directory:**
   ```bash
   cd "C:\Users\Apoorva Shetty\Documents\GitHub\reWise_backend"
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the development server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Or start the production server:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

5. **Or run directly with Python:**
   ```bash
   python main.py
   ```

## Troubleshooting

### If python is not recognized:
- Make sure Python is properly installed
- Restart your terminal/PowerShell after installation
- Check if Python is in your system PATH

### If pip is not recognized:
- Python 3.4+ should include pip by default
- Try using: `python -m pip install -r requirements.txt`

### If you get permission errors:
- Run PowerShell as Administrator
- Or use the following command to set execution policy:
  ```bash
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### If you get network errors during pip install:
- Check your internet connection
- Try using a different pip index:
  ```bash
  pip install -r requirements.txt -i https://pypi.org/simple/
  ```

### If uvicorn is not found:
- Make sure you've installed the requirements:
  ```bash
  pip install -r requirements.txt
  ```
- Or install uvicorn directly:
  ```bash
  pip install uvicorn[standard]
  ```

## Testing the Installation

After successful installation and setup:

1. **Start the server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test the root endpoint:**
   Open a browser or use curl:
   ```
   http://localhost:8000/
   ```

3. **Test the search endpoint:**
   ```
   http://localhost:8000/search?term=javascript
   ```

4. **View API documentation:**
   ```
   http://localhost:8000/docs
   ```

You should see the server running and be able to access the endpoints successfully.

## Virtual Environment (Recommended)

For better dependency management, consider using a virtual environment:

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Deactivate when done:**
   ```bash
   deactivate
   ``` 