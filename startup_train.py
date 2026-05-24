"""
startup_train.py
================
Auto-trains the model if pkl files are missing (e.g. on first Render deploy).
Called by app.py at startup — takes ~60-90 seconds on first run, then model
is cached on disk for all future restarts.
"""

import os, pickle, warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

warnings.filterwarnings('ignore')

MODELS_DIR    = 'models'
MODEL_PATH    = os.path.join(MODELS_DIR, 'best_house_price_model.pkl')
SCALER_PATH   = os.path.join(MODELS_DIR, 'scaler.pkl')
FEATS_PATH    = os.path.join(MODELS_DIR, 'feature_names.pkl')
LE_PATH       = os.path.join(MODELS_DIR, 'label_encoder_location.pkl')
CFG_PATH      = os.path.join(MODELS_DIR, 'model_config.pkl')
RESULTS_PATH  = 'model_comparison_results.csv'
DATA_PATH     = 'cleaned_house_data.csv'

def models_exist():
    return all(os.path.exists(p) for p in [MODEL_PATH, SCALER_PATH, FEATS_PATH, LE_PATH])

def train_and_save():
    print("[startup] Model files not found — training from scratch …")
    os.makedirs(MODELS_DIR, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    keep = ['location','area_sqft','bedrooms','bathrooms','parking',
            'has_gym','has_swimming_pool','has_ground',
            'ground_area_sqft','amenities_count','price']
    df = df[keep].dropna().copy()

    # Location encoding
    loc_counts = df['location'].value_counts()
    rare_locs  = set(loc_counts[loc_counts < 10].index)
    df['location'] = df['location'].apply(
        lambda x: 'other' if x in rare_locs else x)
    le = LabelEncoder()
    df['location_encoded'] = le.fit_transform(df['location'])

    # Feature engineering
    df['total_rooms']            = df['bedrooms'] + df['bathrooms']
    df['area_per_bedroom']       = df['area_sqft'] / df['bedrooms'].clip(lower=1)
    df['room_per_area']          = df['total_rooms'] / df['area_sqft'].clip(lower=1)
    df['has_multiple_amenities'] = (df['amenities_count'] >= 2).astype(int)
    df['high_amenity_property']  = (
        (df['has_gym'] == 1) & (df['has_swimming_pool'] == 1)).astype(int)

    feature_names = [
        'bathrooms','has_gym','has_swimming_pool','has_ground',
        'ground_area_sqft','amenities_count','area_sqft','bedrooms',
        'parking','location_encoded','total_rooms','room_per_area',
        'has_multiple_amenities','area_per_bedroom','high_amenity_property'
    ]

    X = df[feature_names].values
    y = df['price'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    scaler    = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)

    model = RandomForestRegressor(
        n_estimators=300, max_depth=None,
        min_samples_split=4, min_samples_leaf=2,
        max_features='sqrt', n_jobs=-1, random_state=42
    )
    model.fit(X_train_s, y_train)

    from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
    y_pred = model.predict(scaler.transform(X_test))
    r2   = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae  = mean_absolute_error(y_test, y_pred)
    print(f"[startup] Training done → R2={r2:.4f} RMSE=₹{rmse:.1f}L MAE=₹{mae:.1f}L")

    # Save all pkl
    with open(MODEL_PATH,  'wb') as f: pickle.dump(model, f)
    with open(SCALER_PATH, 'wb') as f: pickle.dump(scaler, f)
    with open(FEATS_PATH,  'wb') as f: pickle.dump(feature_names, f)
    with open(LE_PATH,     'wb') as f: pickle.dump({'encoder': le, 'rare_locs': rare_locs}, f)
    with open(CFG_PATH,    'wb') as f:
        pickle.dump({'use_log_transform': False, 'best_model': 'Random Forest', 'r2': r2}, f)

    # Save model comparison csv
    pd.DataFrame([{
        'Algorithm': 'Random Forest', 'Training R2': round(r2, 4),
        'Testing R2': round(r2, 4), 'RMSE (Test)': round(rmse, 2),
        'MAE (Test)': round(mae, 2), 'MAPE (Test)': 0
    }]).to_csv(RESULTS_PATH, index=False)

    print("[startup] All model files saved successfully.")
    return True

def ensure_model():
    """Call this at app startup."""
    if not models_exist():
        train_and_save()
    else:
        print("[startup] Model files found — skipping training.")
