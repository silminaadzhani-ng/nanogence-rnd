# Deploying the Nanogence Platform

Since this is a **Streamlit** application, you have several fast ways to publish it as a website accessible to your team.

## Option 1: Streamlit Community Cloud (Fastest & Free)
Best for: Rapid sharing, small teams, testing.

1.  **Push to GitHub**:
    *   Initialize a git repo in this folder: `git init`, `git add .`, `git commit -m "Initial commit"`.
    *   Push this code to a new repository on your GitHub account.
2.  **Connect Streamlit**:
    *   Go to [share.streamlit.io](https://share.streamlit.io/).
    *   Log in with GitHub.
    *   Click **"New App"** -> Select your repository.
    *   Set **Main file path** to `app/main.py`.
    *   Click **Deploy**.
3.  **Result**: You get a public URL (e.g., `https://nanogence-platform.streamlit.app`) to share.

## Option 2: Docker / Internal Server (Secure & Private)
Best for: Corporate intranet, keeping data on-premise.

1.  **Build the Image**:
    ```bash
    docker build -t nanogence-platform .
    ```
2.  **Run the Container**:
    ```bash
    docker run -p 80:8501 nanogence-platform
    ```
3.  **Access**:
    *   The site will be available at `http://<your-server-ip>:80`.

## Important Note on Database
*   Currently, the app uses **SQLite** (`nanogence.db`), which is a file stored inside the app.
*   **For Cloud Deployment**: SQLite will reset every time the app restarts. You should switch back to **PostgreSQL** (as originally planned) for a persistent "Production" website.
*   **To switch to Postgres**:
    1.  Set up a hosted database (e.g., AWS RDS, Supabase, or Render).
    2.  Set the `DATABASE_URL` environment variable in your deployment settings to the Postgres connection string.
