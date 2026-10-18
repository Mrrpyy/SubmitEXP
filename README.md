
# SubmitEXP

Gamified Canvas submission tracking browser extension.

SubmitEXP is a Chrome extension designed to reward students for submitting Canvas assignments early.

The project uses:
- React and TypeScript for the browser extension
- Python and FastAPI for the backend
- MySQL for database management
- Git and GitHub for version control

Screenshot processing and OCR are planned to run locally in the browser to protect user privacy.

**Current Status:** The extension can communicate with the backend and validate sample assignment metadata.

## Project Setup

These instructions use Windows PowerShell. Start in the main `SubmitEXP` project directory.

### Step 1: Set Up the Backend

Navigate to the backend directory:

```powershell
cd backend
```

Create a Python virtual environment:

```powershell
py -m venv .venv
```

Install the required Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the FastAPI backend server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The backend should be running at:

http://127.0.0.1:8000

Verify that backend is working:

http://127.0.0.1:8000/health

Expected:

```json
{
  "status": "ok"
}
```

API documentation:

http://127.0.0.1:8000/docs

Keep the backend terminal running while testing the extension.

### Step 2: Set Up the Chrome Extension

Open a second terminal and navigate to the extentsion dir from the project root:

```powershell
cd extension
```

Instal extension dependencies:

```powershell
npm ci
```

Build extension:

```powershell
npm run build
```

Creates the `dist` directory, has compiled extension.

### Step 3: Load the Extension in Chrome

1. Open Google Chrome.
2. Navigate to `chrome://extensions`.
3. Enable **Developer mode**.
4. Click **Load unpacked**.
5. Select the `SubmitEXP/extension/dist` folder.
6. Open SubmitEXP from the Chrome toolbar.

Whenever changes are made to the extension source code run:

```powershell
npm run build
```

Then reload the extension from `chrome://extensions`.

### Step 4: Test the Backend Connection

Make sure the FastAPI backend server is running.

1. Open the SubmitEXP extension popup.
2. Locate the backend connection section.
3. Click **Test API Connection**.
4. Verify that the request succeeds.

Expected:

```text
Metadata validated (not saved; no points awarded).
```

Confirms that the extension can communicate with the backend.

### Step 4: Verify the Database Connection

Restart backend server.

Open:

http://127.0.0.1:8000/health/database

Successful response confirms that the backend can communicate with MySQL.

## Running Tests

### Backend Tests

Navigate to the backend directory:

```powershell
cd backend
```

Run all backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Extension-to-Backend Integration Tests

To test the backend integration functionality:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_integration.py -v
```

These five tests verify:

1. The backend health endpoint works.
2. Valid assignment metadata is accepted.
3. Screenshot data is rejected.
4. Invalid submission types are rejected.
5. Chrome extension CORS requests are handled correctly.

Expected result:

```text
5 passed
```

Automated API tests don't require the backend server to be running separately.

### Extension Build Test

Navigate to the extension directory:

```powershell
cd extension
```

Run:

```powershell
npm run build
```

Successful build confirms that TypeScript project compiles and production bundle is generated

### Manual Extension Test

1. Start the backend server.
2. Build and reload the Chrome extension.
3. Open the extension popup.
4. Click **Test API Connection**.
5. Verify that metadata validation succeeds.

## Troubleshooting

### Missing Python Dependencies

If Python reports that a module such as `uvicorn` or `pytest` is missing, reinstall the backend dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Extension Cannot Connect to Backend

Verify that:

- The backend server is running.
- The backend is accessible at `http://127.0.0.1:8000`.
- The extension has been rebuilt.
- The extension has been reloaded in Chrome.

### Extension Changes Not Appearing

Rebuild the extension:

```powershell
npm run build
```

Then reload it from `chrome://extensions`.

### Database Connection Error

Verify that:

- MySQL is running.
- The `submitexp` database exists.
- The database tables have been created.
- The `.env` file contains the correct credentials.

## Configuration Management

This project uses Git and GitHub for configuration management.

### Branches

- `main` contains stable and reviewed code.
- `feature/*` branches are used for new features.
- `fix/*` branches are used for bug fixes.

### Development Workflow

1. Select or assign a project task.
2. Create a branch from `main`.
3. Develop and test the feature.
4. Commit changes with descriptive commit messages.
5. Push the branch to GitHub.
6. Create a pull request into `main`.
7. Have another team member review the pull request.
8. Resolve review comments.
9. Merge the approved changes into `main`.

### Files to Exclude from Commits

Do not commit:

- Python virtual environments (`.venv`)
- Node.js dependencies (`node_modules`)
- Environment files containing credentials (`.env`)
- Generated TypeScript build-cache files (`*.tsbuildinfo`)
- Generated extension build files (`dist`)

These files should be excluded using `.gitignore`.
