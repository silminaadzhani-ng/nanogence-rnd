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

## ⚠️ Crucial: Data Persistence Warning
*   **Default Mode**: The app uses **SQLite** (`nanogence.db`).
*   **On Streamlit Cloud**: The filesystem is **ephemeral**. Every time the app reloads or sleeps, the `.db` file is deleted and you lose your data.
*   **The Solution**: Use a shared persistent database (PostgreSQL).

## Option 2: Docker Compose (Full Stack - Recommended)
This is the best way to run the app with a **persistent** database on a server.

1.  **Run with one command**:
    ```bash
    docker-compose up -d
    ```
2.  **Why this works**: It starts both the App and a Postgres Database. The data is saved in a Docker Volume (`pgdata`) which survives restarts.

## How to use an External Database (Cloud)
If you are using Streamlit Cloud and want to keep your data:
1.  **Create a Postgres DB** (e.g., on [Neon](https://neon.tech/) or [Supabase](https://supabase.com/)).
2.  **Add Secret**: In the Streamlit Cloud dashboard, go to **Settings -> Secrets** and add:
    ```toml
    DATABASE_URL = "postgresql://USER:PASSWORD@HOST:PORT/DBNAME"
    ```
3.  **Restart App**: The platform will now save all data to the cloud database instead of a local file.
