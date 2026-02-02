# Nanogence R&D Platform Walkthrough

## 1. Overview
This platform is a modular R&D data management system designed for Nanogence.
*   **Recipe Designer**: Create versioned recipes for C-S-H synthesis.
*   **Lab Notebook**: Log batches and QC measurements (PSD, pH, Solids).
*   **Results & Explorer**: Record performance (Strength) and visualize correlations.
*   **AI Predictor**: Real-time compressive strength estimations.

## 2. Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app/main.py
```

## 3. Features

### Recipe Designer & AI Prediction
- Define Ca/Si ratio, Molarity, and PCE content.
- See **Live Predictions** for 28-day strength in the sidebar as you adjust parameters.
- Retrain the AI by running: `python train_model_script.py`.

### Lab Notebook & QC
- Select a Recipe and start a new synthesis batch.
- Input Particle Size Distribution (PSD) data Before/After sonication.

### Results & Explorer
- Enter Compressive Strengths at multiple ages (12h, 16h, 1d, 2d, 28d).
- Use the **Explorer** to see scatter plots and statistical distributions of your data.

## 🛠️ How to Sync Changes to your Website
Your website on Streamlit Cloud is linked to your GitHub repository. To update it:

1.  **Modify** files locally (e.g., change titles or logic).
2.  **Test** locally with `streamlit run app/main.py`.
3.  **Push** to GitHub:
    ```bash
    git add .
    git commit -m "Updated lab platform"
    git push origin master
    ```
Streamlit Cloud will detect the push and update your live website automatically.

## 📂 Key Files
- `app/main.py`: App gateway.
- `app/ml_utils.py`: Prediction logic.
- `app/pages/`: Modular tool pages.
- `nanogence.db`: Database file.
- `seed_data.py`: Example data loader.
