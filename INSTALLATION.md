# Installation Guide

## Prerequisites

Before running this backend, you need to install Node.js and npm.

### Installing Node.js

1. **Download Node.js:**
   - Go to [https://nodejs.org/](https://nodejs.org/)
   - Download the LTS (Long Term Support) version for Windows
   - Choose the Windows Installer (.msi) for your system architecture (x64 recommended)

2. **Install Node.js:**
   - Run the downloaded installer
   - Follow the installation wizard
   - Make sure to check the box that says "Automatically install the necessary tools"
   - Complete the installation

3. **Verify Installation:**
   Open a new PowerShell or Command Prompt window and run:
   ```bash
   node --version
   npm --version
   ```
   Both commands should return version numbers.

### Alternative: Using Node Version Manager (nvm) for Windows

If you prefer using nvm for Windows:

1. **Install nvm-windows:**
   - Download from [https://github.com/coreybutler/nvm-windows/releases](https://github.com/coreybutler/nvm-windows/releases)
   - Run the installer

2. **Install Node.js via nvm:**
   ```bash
   nvm install lts
   nvm use lts
   ```

## Project Setup

Once Node.js is installed:

1. **Navigate to the project directory:**
   ```bash
   cd "C:\Users\Apoorva Shetty\Documents\GitHub\reWise_backend"
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Or start the production server:**
   ```bash
   npm start
   ```

## Troubleshooting

### If npm is not recognized:
- Make sure Node.js is properly installed
- Restart your terminal/PowerShell after installation
- Check if Node.js is in your system PATH

### If you get permission errors:
- Run PowerShell as Administrator
- Or use the following command to set execution policy:
  ```bash
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### If you get network errors during npm install:
- Check your internet connection
- Try using a different npm registry:
  ```bash
  npm config set registry https://registry.npmjs.org/
  ```

## Testing the Installation

After successful installation and setup:

1. **Start the server:**
   ```bash
   npm run dev
   ```

2. **Test the health endpoint:**
   Open a browser or use curl:
   ```
   http://localhost:3000/health
   ```

3. **Test the search endpoint:**
   ```
   http://localhost:3000/search?term=javascript
   ```

You should see the server running and be able to access the endpoints successfully. 