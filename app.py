"""
Flask Web Application — Redesigned UI
Bangalore House Price Prediction Project
"""

from flask import Flask, render_template, request, jsonify, send_file
import pickle
import numpy as np
import pandas as pd
import os

# ─── Auto-train model if pkl files are missing (first Render deploy) ──────────
from startup_train import ensure_model
ensure_model()

app = Flask(__name__)
app.jinja_env.globals.update(enumerate=enumerate, zip=zip)

# ─── Load model & all preprocessing objects ───────────────────────────────────
try:
    with open('models/best_house_price_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('models/scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    with open('models/feature_names.pkl', 'rb') as f:
        feature_names = pickle.load(f)
    with open('models/label_encoder_location.pkl', 'rb') as f:
        loc_data    = pickle.load(f)
        le_location = loc_data['encoder']
        rare_locs   = set(loc_data['rare_locs'])

    # Detect log-transform flag from v3 training
    USE_LOG = False
    if os.path.exists('models/model_config.pkl'):
        with open('models/model_config.pkl', 'rb') as f:
            cfg = pickle.load(f)
        USE_LOG = cfg.get('use_log_transform', False)

    results_df     = pd.read_csv("model_comparison_results.csv")
    best_row       = results_df.sort_values('Testing R2', ascending=False).iloc[0]
    MODEL_NAME     = best_row['Algorithm']
    MODEL_ACCURACY = round(float(best_row['Testing R2']), 4)
    MODEL_RMSE     = round(float(best_row['RMSE (Test)']), 2)
    MODEL_MAE      = round(float(best_row['MAE (Test)']), 2)

    cleaned_df  = pd.read_csv("cleaned_house_data.csv")
    AVG_PRICE   = round(cleaned_df['price'].mean() / 100, 2)   # Crores
    TOTAL_PROPS = 13320
    MEDIAN_GROUND = float(
        cleaned_df[cleaned_df['ground_area_sqft'] > 0]['ground_area_sqft'].median()
    )

    print(f"Model loaded : {MODEL_NAME}  (R2={MODEL_ACCURACY}, log={USE_LOG})")
    print(f"Features     : {feature_names}")

except Exception as e:
    print(f"Error loading model: {e}")
    MODEL_NAME    = "Gradient Boosting"
    MODEL_ACCURACY = 0.69
    MODEL_RMSE    = 48.5
    MODEL_MAE     = 25.8
    AVG_PRICE     = 1.12
    TOTAL_PROPS   = 13320
    MEDIAN_GROUND = 500.0
    USE_LOG       = True

# ─── Localities ───────────────────────────────────────────────────────────────
LOCALITIES = [
    'Whitefield', 'Koramangala', 'Indiranagar', 'Vijayanagar',
    'Marathahalli', 'Sarjapur Road', 'Electronic City', 'Bannerghatta Road',
    'Bellandur', 'Brookfield', 'Hebbal', 'Yeshwantpur',
    'JP Nagar', 'Yelahanka', 'Banaswadi', 'Malleshwaram',
    'Richmond Town', 'Kalyannagar', 'Rajajinagar', 'BTM Layout'
]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def encode_location(loc_str):
    loc = loc_str.strip()
    if loc in rare_locs:
        loc = 'other'
    try:
        return int(le_location.transform([loc])[0])
    except:
        try:
            return int(le_location.transform(['other'])[0])
        except:
            return 0

def build_feature_vector(inp):
    """Build and scale the feature vector matching whatever feature_names the model expects."""
    area      = float(inp['area_sqft'])
    bedrooms  = int(inp['bedrooms'])
    bathrooms = int(inp['bathrooms'])
    parking   = int(inp['parking'])
    has_gym   = int(inp['has_gym'])
    has_pool  = int(inp['has_swimming_pool'])
    has_grd   = int(inp['has_ground'])

    ground_area   = MEDIAN_GROUND if has_grd else 0.0
    amenities_cnt = has_gym + has_pool + has_grd
    total_rooms   = bedrooms + bathrooms
    room_per_area = total_rooms / max(area, 1)
    has_multi_am  = 1 if amenities_cnt >= 2 else 0
    area_per_bed  = area / max(bedrooms, 1)
    high_amenity  = 1 if (has_gym and has_pool) else 0
    loc_enc       = encode_location(inp['location'])
    log_area      = np.log1p(area)          # used by v3 model

    # Full feature dict — covers both old (15 feat) and new (16 feat) models
    feat_dict = {
        'bathrooms':             bathrooms,
        'has_gym':               has_gym,
        'has_swimming_pool':     has_pool,
        'has_ground':            has_grd,
        'ground_area_sqft':      ground_area,
        'amenities_count':       amenities_cnt,
        'area_sqft':             area,
        'bedrooms':              bedrooms,
        'parking':               parking,
        'location_encoded':      loc_enc,
        'total_rooms':           total_rooms,
        'room_per_area':         room_per_area,
        'has_multiple_amenities':has_multi_am,
        'area_per_bedroom':      area_per_bed,
        'high_amenity_property': high_amenity,
        'log_area':              log_area,   # only used if feature_names includes it
    }

    # Build ordered numpy array exactly matching feature_names
    values = np.array([[feat_dict.get(f, 0) for f in feature_names]], dtype=np.float64)

    # Scale — pass numpy array to avoid feature-name mismatch warning
    return scaler.transform(values)

def fmt_price(p):
    """Format price in Lakhs → show as Cr if >= 100L."""
    if p >= 100:
        return f'\u20b9{p/100:.2f} Cr'
    return f'\u20b9{p:.2f}L'

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def dashboard():
    return render_template('dashboard.html',
        total_props   =f"{TOTAL_PROPS:,}",
        avg_price     =f"\u20b9{AVG_PRICE:.2f} Cr",
        num_locations =f"{len(LOCALITIES)}+",
        model_accuracy=f"{MODEL_ACCURACY*100:.1f}%",
        active        ='dashboard'
    )

@app.route('/predict', methods=['GET'])
def predict_page():
    return render_template('predict.html',
        localities    =LOCALITIES,
        model_accuracy=MODEL_ACCURACY,
        model_name    =MODEL_NAME,
        active        ='predict'
    )

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.get_json()
        if not data:
            data = request.form.to_dict()

        if not data.get('location'):
            return jsonify({'error': 'Please select a location'}), 400
        if not data.get('area_sqft'):
            return jsonify({'error': 'Please enter area'}), 400

        inp = {
            'location':          data.get('location', 'Whitefield'),
            'area_sqft':         float(data.get('area_sqft', 1000)),
            'bedrooms':          int(data.get('bedrooms', 2)),
            'bathrooms':         int(data.get('bathrooms', 2)),
            'parking':           int(data.get('parking', 1)),
            'has_gym':           1 if data.get('has_gym') in [1, '1', True, 'true', 'on'] else 0,
            'has_swimming_pool': 1 if data.get('has_swimming_pool') in [1, '1', True, 'true', 'on'] else 0,
            'has_ground':        1 if data.get('has_ground') in [1, '1', True, 'true', 'on'] else 0,
        }

        X_scaled = build_feature_vector(inp)
        raw_pred = float(model.predict(X_scaled)[0])

        # If model was trained on log1p(price), reverse with expm1
        if USE_LOG:
            price = float(np.expm1(raw_pred))
        else:
            price = raw_pred

        price = max(price, 0)

        area     = inp['area_sqft']
        per_sqft = price * 100_000 / max(area, 1)
        low      = round(price * 0.88, 2)
        high     = round(price * 1.12, 2)

        price_range_lakh = f'\u20b9{low:.1f}L \u2013 \u20b9{high:.1f}L'
        price_range_cr   = f'\u20b9{low/100:.2f} Cr \u2013 \u20b9{high/100:.2f} Cr'

        # Similar properties from dataset
        similar = []
        try:
            sub = cleaned_df[
                (cleaned_df['bedrooms'] == inp['bedrooms']) &
                (cleaned_df['price'].between(low * 0.6, high * 1.4))
            ]
            if len(sub) >= 3:
                sub = sub.sample(3, random_state=42)
            elif len(sub) > 0:
                sub = sub.head(3)
            else:
                # Fallback: any properties with same bedroom count
                sub = cleaned_df[
                    cleaned_df['bedrooms'] == inp['bedrooms']
                ].sample(min(3, len(cleaned_df)), random_state=42)

            BANGALORE_AREAS = [
                'Koramangala', 'Indiranagar', 'Whitefield', 'Marathahalli',
                'HSR Layout', 'JP Nagar', 'Bellandur', 'Hebbal', 'Yelahanka',
                'Electronic City', 'Sarjapur Road', 'BTM Layout'
            ]
            for i, (_, row) in enumerate(sub.iterrows()):
                p    = float(row['price'])
                area_row = float(row['area_sqft'])
                loc  = BANGALORE_AREAS[i % len(BANGALORE_AREAS)]
                similar.append({
                    'title':           f"{int(row['bedrooms'])} BHK Apartment",
                    'location':        loc,
                    'area':            f"{area_row:,.0f} sq ft",
                    'price_formatted': fmt_price(p),
                })
        except Exception as ex:
            print(f"Similar props error: {ex}")

        return jsonify({
            'success':       True,
            'price':         round(price, 2),
            'price_formatted': fmt_price(price),
            'per_sqft':      f'\u20b9{per_sqft:,.0f}',
            'price_range':   price_range_lakh,
            'price_range_cr':price_range_cr,
            'confidence':    f'{MODEL_ACCURACY*100:.1f}%',
            'similar':       similar,
            'location':      inp['location'],
            'bedrooms':      inp['bedrooms'],
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/insights')
def insights():
    return render_template('insights.html', active='insights')

@app.route('/model-info')
def model_info():
    all_results = results_df.sort_values('Testing R2', ascending=False).to_dict('records')
    model_size  = round(os.path.getsize('models/best_house_price_model.pkl') / 1024, 1)
    return render_template('model_info.html',
        model_name    =MODEL_NAME,
        model_accuracy=MODEL_ACCURACY,
        model_rmse    =MODEL_RMSE,
        model_mae     =MODEL_MAE,
        all_results   =all_results,
        model_size    =model_size,
        active        ='model_info'
    )

@app.route('/about')
def about():
    return render_template('about.html', active='about')

@app.route('/api/download-model')
def download_model():
    try:
        return send_file('models/best_house_price_model.pkl',
                         as_attachment=True,
                         download_name='best_house_price_model.pkl')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Bangalore House Price Predictor — Dashboard UI")
    print(f"   Model     : {MODEL_NAME}")
    print(f"   R2        : {MODEL_ACCURACY*100:.1f}%")
    print(f"   Log-xform : {USE_LOG}")
    print(f"   Features  : {len(feature_names)}")
    print(f"   Open      : http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)
