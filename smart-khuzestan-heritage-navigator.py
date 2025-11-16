import pandas as pd
import random
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from imblearn.over_sampling import SMOTE
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import unicodedata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import psycopg2
from psycopg2 import Error
from sqlalchemy import create_engine
import streamlit as st
import folium
from streamlit_folium import st_folium
import arabic_reshaper
from bidi.algorithm import get_display
from sklearn.metrics import accuracy_score

#  تنظیمات اولیه و فونت فارسی
random.seed(42)
np.random.seed(42)

current_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(current_dir, "Vazir-Regular.ttf")

if os.path.exists(font_path):
    persian_font = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = persian_font.get_name()
    plt.rcParams['axes.unicode_minus'] = False
    st.success("فونت فارسی با موفقیت لود شد.")
else:
    st.error(f"فایل Vazir-Regular.ttf پیدا نشد!\nمسیر جستجو: {font_path}")
    plt.rcParams['font.family'] = 'sans-serif'

def persian_text(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

#  اتصال به PostgreSQL
DB_HOST = "localhost"
DB_NAME = "tourism23_db"
DB_USER = "postgres"
DB_PASS = "1234567890" #پسورد خود را وارد کنید
DB_PORT = "5432"

def create_database():
    try:
        conn = psycopg2.connect(host=DB_HOST, database="postgres", user=DB_USER, password=DB_PASS, port=DB_PORT)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {DB_NAME}")
        cur.close()
        conn.close()
    except Error as e:
        st.error(f"خطا در ایجاد دیتابیس: {e}")
        st.stop()

def connect_db():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
    except Error as e:
        st.error(f"اتصال به دیتابیس ناموفق: {e}")
        st.stop()

create_database()


archaeology_sites = [
    "چغازنبیل", "شوش", "هفت‌تپه", "سازه‌های آبی شوشتر", "قلعه شوش", "آرامگاه دانیال نبی",
    "کاخ آپادانا شوش", "اشکفت سلمان", "کول فرح", "چغا تپه", "تپه گلگیر", "ایوان کرخه",
    "قدمگاه صاحب الزمان", "پامنار", "زراس", "شیمن", "باجول", "سوسن", "مهرویان", "تاریشا"
]


handicraft_shops = [
    "بازار عبدالحمید (اهواز)", "کارگاه قلم‌زنی دزفول", "صنایع دستی حصیربافی شادگان", 
    "کارگاه کپوبافی اهواز", "عبابافی بختیاری", "گیوه‌بافی دزفول", "گلیم‌بافی بهبهان",
    "نمد مالی بختیاری", "محرق‌کاری اهواز", "خراطی دزفول", "ورشوسازی اهواز", "میناکاری اهواز",
    "کلوچه محلی دزفول", "حلوا خرمایی اهواز", "گیوه تخت بهبهان"
]

season_weights = {"spring": 1.5, "summer": 1.3, "autumn": 1.0, "winter": 0.8}
FUEL_COST_PER_KM = 0.5

#  داده‌های کامل با لوکیشن‌های واقعی (سود تصادفی)
data = [
    # باستانی
    {"name": "چغازنبیل", "spring_profit": 500, "summer_profit": 450, "autumn_profit": 400, "winter_profit": 300, "total_profit": 1650, "latitude": 32.0083, "longitude": 48.5250},
    {"name": "شوش", "spring_profit": 480, "summer_profit": 430, "autumn_profit": 380, "winter_profit": 280, "total_profit": 1570, "latitude": 32.1892, "longitude": 48.2543},
    {"name": "هفت‌تپه", "spring_profit": 400, "summer_profit": 360, "autumn_profit": 320, "winter_profit": 250, "total_profit": 1330, "latitude": 32.0500, "longitude": 48.5000},
    {"name": "سازه‌های آبی شوشتر", "spring_profit": 520, "summer_profit": 470, "autumn_profit": 420, "winter_profit": 320, "total_profit": 1730, "latitude": 32.0456, "longitude": 48.8567},
    {"name": "قلعه شوش", "spring_profit": 350, "summer_profit": 310, "autumn_profit": 280, "winter_profit": 220, "total_profit": 1160, "latitude": 32.1903, "longitude": 48.2469},
    {"name": "آرامگاه دانیال نبی", "spring_profit": 380, "summer_profit": 340, "autumn_profit": 300, "winter_profit": 240, "total_profit": 1260, "latitude": 32.1905, "longitude": 48.2439},
    {"name": "کاخ آپادانا شوش", "spring_profit": 450, "summer_profit": 410, "autumn_profit": 360, "winter_profit": 260, "total_profit": 1480, "latitude": 32.1890, "longitude": 48.2450},
    {"name": "اشکفت سلمان", "spring_profit": 320, "summer_profit": 290, "autumn_profit": 260, "winter_profit": 200, "total_profit": 1070, "latitude": 32.0000, "longitude": 49.0000},
    {"name": "کول فرح", "spring_profit": 340, "summer_profit": 310, "autumn_profit": 270, "winter_profit": 210, "total_profit": 1130, "latitude": 32.0100, "longitude": 49.0100},
    {"name": "چغا تپه", "spring_profit": 280, "summer_profit": 250, "autumn_profit": 220, "winter_profit": 170, "total_profit": 920, "latitude": 32.2000, "longitude": 48.3000},
    {"name": "تپه گلگیر", "spring_profit": 300, "summer_profit": 270, "autumn_profit": 240, "winter_profit": 190, "total_profit": 1000, "latitude": 32.0500, "longitude": 48.8500},
    {"name": "ایوان کرخه", "spring_profit": 360, "summer_profit": 320, "autumn_profit": 290, "winter_profit": 230, "total_profit": 1200, "latitude": 32.0000, "longitude": 48.6000},
    {"name": "قدمگاه صاحب الزمان", "spring_profit": 290, "summer_profit": 260, "autumn_profit": 230, "winter_profit": 180, "total_profit": 960, "latitude": 32.0400, "longitude": 48.8600},
    {"name": "پامنار", "spring_profit": 310, "summer_profit": 280, "autumn_profit": 250, "winter_profit": 200, "total_profit": 1040, "latitude": 32.0300, "longitude": 48.8700},
    {"name": "زراس", "spring_profit": 270, "summer_profit": 240, "autumn_profit": 210, "winter_profit": 160, "total_profit": 880, "latitude": 31.8000, "longitude": 49.5000},
    {"name": "شیمن", "spring_profit": 260, "summer_profit": 230, "autumn_profit": 200, "winter_profit": 150, "total_profit": 840, "latitude": 31.9000, "longitude": 49.4000},
    {"name": "باجول", "spring_profit": 280, "summer_profit": 250, "autumn_profit": 220, "winter_profit": 170, "total_profit": 920, "latitude": 32.1000, "longitude": 48.4000},
    {"name": "سوسن", "spring_profit": 320, "summer_profit": 290, "autumn_profit": 260, "winter_profit": 200, "total_profit": 1070, "latitude": 32.3000, "longitude": 48.1000},
    {"name": "مهرویان", "spring_profit": 340, "summer_profit": 310, "autumn_profit": 270, "winter_profit": 210, "total_profit": 1130, "latitude": 32.1800, "longitude": 48.2600},
    {"name": "تاریشا", "spring_profit": 300, "summer_profit": 270, "autumn_profit": 240, "winter_profit": 190, "total_profit": 1000, "latitude": 32.0000, "longitude": 49.0000},
    
    # صنایع دستی
    {"name": "بازار عبدالحمید (اهواز)", "spring_profit": 280, "summer_profit": 330, "autumn_profit": 220, "winter_profit": 150, "total_profit": 980, "latitude": 31.3183, "longitude": 48.6693},
    {"name": "کارگاه قلم‌زنی دزفول", "spring_profit": 240, "summer_profit": 290, "autumn_profit": 190, "winter_profit": 130, "total_profit": 850, "latitude": 32.3831, "longitude": 48.4236},
    {"name": "صنایع دستی حصیربافی شادگان", "spring_profit": 220, "summer_profit": 270, "autumn_profit": 180, "winter_profit": 120, "total_profit": 790, "latitude": 30.6500, "longitude": 48.6667},
    {"name": "کارگاه کپوبافی اهواز", "spring_profit": 200, "summer_profit": 250, "autumn_profit": 160, "winter_profit": 110, "total_profit": 720, "latitude": 31.3183, "longitude": 48.6706},
    {"name": "عبابافی بختیاری", "spring_profit": 260, "summer_profit": 310, "autumn_profit": 210, "winter_profit": 140, "total_profit": 920, "latitude": 31.5000, "longitude": 49.0000},
    {"name": "گیوه‌بافی دزفول", "spring_profit": 230, "summer_profit": 280, "autumn_profit": 190, "winter_profit": 130, "total_profit": 830, "latitude": 32.3800, "longitude": 48.4200},
    {"name": "گلیم‌بافی بهبهان", "spring_profit": 210, "summer_profit": 260, "autumn_profit": 170, "winter_profit": 110, "total_profit": 750, "latitude": 30.6000, "longitude": 50.2500},
    {"name": "نمد مالی بختیاری", "spring_profit": 250, "summer_profit": 300, "autumn_profit": 200, "winter_profit": 140, "total_profit": 890, "latitude": 31.7000, "longitude": 49.3000},
    {"name": "محرق‌کاری اهواز", "spring_profit": 220, "summer_profit": 270, "autumn_profit": 180, "winter_profit": 120, "total_profit": 790, "latitude": 31.3200, "longitude": 48.6800},
    {"name": "خراطی دزفول", "spring_profit": 240, "summer_profit": 290, "autumn_profit": 200, "winter_profit": 140, "total_profit": 870, "latitude": 32.3900, "longitude": 48.4300},
    {"name": "ورشوسازی اهواز", "spring_profit": 260, "summer_profit": 310, "autumn_profit": 210, "winter_profit": 150, "total_profit": 930, "latitude": 31.3100, "longitude": 48.6600},
    {"name": "میناکاری اهواز", "spring_profit": 280, "summer_profit": 330, "autumn_profit": 220, "winter_profit": 160, "total_profit": 990, "latitude": 31.3300, "longitude": 48.6900},
    {"name": "کلوچه محلی دزفول", "spring_profit": 190, "summer_profit": 240, "autumn_profit": 160, "winter_profit": 100, "total_profit": 690, "latitude": 32.3700, "longitude": 48.4100},
    {"name": "حلوا خرمایی اهواز", "spring_profit": 200, "summer_profit": 250, "autumn_profit": 170, "winter_profit": 110, "total_profit": 730, "latitude": 31.3000, "longitude": 48.6500},
    {"name": "گیوه تخت بهبهان", "spring_profit": 210, "summer_profit": 260, "autumn_profit": 180, "winter_profit": 120, "total_profit": 770, "latitude": 30.5900, "longitude": 50.2400}
]

locations_df = pd.DataFrame(data)

try:
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            name VARCHAR(255) PRIMARY KEY,
            spring_profit FLOAT, summer_profit FLOAT, autumn_profit FLOAT, winter_profit FLOAT,
            total_profit FLOAT, latitude FLOAT, longitude FLOAT
        );
    """)
    for _, row in locations_df.iterrows():
        cur.execute("""
            INSERT INTO locations VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING;
        """, (row['name'], row['spring_profit'], row['summer_profit'], row['autumn_profit'],
              row['winter_profit'], row['total_profit'], row['latitude'], row['longitude']))
    conn.commit()
except Error as e:
    st.error(f"خطا در ذخیره داده‌ها: {e}")
    st.stop()
finally:
    cur.close()
    conn.close()

try:
    engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    locations_df = pd.read_sql("SELECT * FROM locations", engine)
except Exception as e:
    st.error(f"خطا در خواندن دیتابیس: {e}")
    st.stop()


def distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def solve_tsp(coords):
    if len(coords) < 2:
        return list(range(len(coords)))
    n = len(coords)
    matrix = [[0 if i == j else int(distance_km(*coords[i], *coords[j]) * 1000) for j in range(n)] for i in range(n)]
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)
    def distance_callback(i, j):
        return matrix[manager.IndexToNode(i)][manager.IndexToNode(j)]
    transit = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)
    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(search)
    if solution:
        path = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            path.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        return path
    return list(range(n))

def create_random_path(max_distance=200, max_locations=6):
    arch_count = random.randint(2, min(4, len(archaeology_sites)))
    hand_count = random.randint(2, min(3, len(handicraft_shops)))
    if arch_count + hand_count > max_locations:
        hand_count = max_locations - arch_count
    selected_arch = random.sample(archaeology_sites, arch_count)
    selected_hand = random.sample(handicraft_shops, hand_count)
    path = selected_arch + selected_hand
    coords = []
    for n in path:
        loc = locations_df.loc[locations_df['name'] == n, ['latitude', 'longitude']]
        if not loc.empty:
            coords.append(loc.values[0].tolist())
        else:
            return None
    tsp_order = solve_tsp(coords)
    path = [path[i] for i in tsp_order]
    coords = [coords[i] for i in tsp_order]
    distances = [distance_km(*coords[i], *coords[i+1]) for i in range(len(coords)-1)] if len(coords) > 1 else [0]
    total_distance = sum(distances)
    if total_distance > max_distance:
        return None

    def calc_season(sites, season):
        return sum(locations_df.loc[locations_df['name']==s, f'{season}_profit'].values[0] * season_weights[season] * random.uniform(0.4, 1.6) for s in sites)

    arch_spring = calc_season(selected_arch, 'spring')
    arch_summer = calc_season(selected_arch, 'summer')
    arch_autumn = calc_season(selected_arch, 'autumn')
    arch_winter = calc_season(selected_arch, 'winter')
    hand_spring = calc_season(selected_hand, 'spring')
    hand_summer = calc_season(selected_hand, 'summer')
    hand_autumn = calc_season(selected_hand, 'autumn')
    hand_winter = calc_season(selected_hand, 'winter')

    arch_total = arch_spring + arch_summer + arch_autumn + arch_winter
    hand_total = hand_spring + hand_summer + hand_autumn + hand_winter
    total_profit = arch_total + hand_total
    total_profit_adjusted = total_profit - int(total_distance) - int(total_distance * FUEL_COST_PER_KM)
    return {
        "arch_sites_count": len(selected_arch), "handicrafts_count": len(selected_hand),
        "total_profit": total_profit, "total_distance": round(total_distance, 2),
        "total_profit_adjusted": total_profit_adjusted,
        "path": path
    }


@st.cache_data
def load_data():
    train_paths = [p for p in [create_random_path() for _ in range(1000)] if p]
    test_paths = []
    for _ in range(300):
        p = create_random_path()
        if p:
            p['total_profit'] *= random.uniform(0.4, 1.6)
            p['total_distance'] *= random.uniform(0.6, 1.4)
            p['total_profit_adjusted'] = p['total_profit'] - int(p['total_distance']) - int(p['total_distance'] * FUEL_COST_PER_KM)
            test_paths.append(p)
    return pd.DataFrame(train_paths), pd.DataFrame(test_paths)

train_df, test_df = load_data()

feature_cols = ["arch_sites_count", "handicrafts_count", "total_profit", "total_distance"]

high_threshold = np.percentile(train_df['total_profit_adjusted'], 75)
medium_threshold = np.percentile(train_df['total_profit_adjusted'], 50)
train_df['category'] = train_df['total_profit_adjusted'].apply(
    lambda x: "بالا" if x >= high_threshold else "متوسط" if x >= medium_threshold else "پایین"
)
test_df['category'] = test_df['total_profit_adjusted'].apply(
    lambda x: "بالا" if x >= high_threshold else "متوسط" if x >= medium_threshold else "پایین"
)

X_train, y_train = train_df[feature_cols], train_df["category"]
X_test, y_test = test_df[feature_cols], test_df["category"]

smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

param_grid = {'n_estimators': [20], 'max_depth': [2], 'min_samples_split': [30, 40], 'min_samples_leaf': [15, 20]}
clf_year = RandomForestClassifier(random_state=42, class_weight='balanced')
grid_year = GridSearchCV(clf_year, param_grid, cv=5, n_jobs=-1)
grid_year.fit(X_train_res, y_train_res)
best_clf_year = grid_year.best_estimator_

seasonal_data = []
for _, row in train_df.iterrows():
    path = row['path']
    for season_key, weight in season_weights.items():
        profit_season = 0
        for site in path:
            if site in locations_df['name'].values:
                profit_season += locations_df.loc[locations_df['name']==site, f'{season_key}_profit'].values[0] * weight
        seasonal_data.append({
            "arch_sites_count": row['arch_sites_count'],
            "handicrafts_count": row['handicrafts_count'],
            "total_profit": profit_season,
            "total_distance": row['total_distance']
        })

seasonal_df = pd.DataFrame(seasonal_data)
high_season = np.percentile(seasonal_df['total_profit'], 75)
medium_season = np.percentile(seasonal_df['total_profit'], 50)
seasonal_df['category_season'] = seasonal_df['total_profit'].apply(
    lambda x: "بالا" if x >= high_season else "متوسط" if x >= medium_season else "پایین"
)

X_train_s, y_train_s = seasonal_df[feature_cols], seasonal_df["category_season"]
X_train_s_res, y_train_s_res = smote.fit_resample(X_train_s, y_train_s)

clf_season = RandomForestClassifier(random_state=42, class_weight='balanced')
grid_season = GridSearchCV(clf_season, param_grid, cv=5, n_jobs=-1)
grid_season.fit(X_train_s_res, y_train_s_res)
best_clf_season = grid_season.best_estimator_


y_train_pred_year = best_clf_year.predict(X_train_res)
train_accuracy_year = accuracy_score(y_train_res, y_train_pred_year)
y_test_pred_year = best_clf_year.predict(X_test)
test_accuracy_year = accuracy_score(y_test, y_test_pred_year)

st.markdown("---")
st.success(f"**دقت آموزشی (سود کل): {train_accuracy_year:.1%}**")
st.success(f"**دقت تست (سود کل): {test_accuracy_year:.1%}**")


st.set_page_config(page_title="میراث خوزستان", layout="wide")
st.title("میراث‌یاب هوشمند خوزستان")

col1, col2, col3 = st.columns(3)
with col1:
    user_arch = st.multiselect("مکان‌های باستانی", archaeology_sites, default=["چغازنبیل", "شوش"])
with col2:
    user_hand = st.multiselect("صنایع دستی", handicraft_shops, default=["بازار عبدالحمید (اهواز)"])
with col3:
    season_options = ["بهار", "تابستان", "پاییز", "زمستان"]
    selected_season = st.selectbox("فصل سفر", season_options, index=0)

if st.button("تحلیل مسیر"):
    if not user_arch and not user_hand:
        st.error("حداقل یک مکان انتخاب کنید.")
    else:
        path = user_arch + user_hand
        coords = [locations_df.loc[locations_df['name'] == n, ['latitude', 'longitude']].values[0].tolist() for n in path]
        tsp_order = solve_tsp(coords)
        path = [path[i] for i in tsp_order]
        coords = [coords[i] for i in tsp_order]

        season_avg = sum(season_weights.values()) / 4
        arch_total_year = sum(locations_df.loc[locations_df['name']==s, 'total_profit'].values[0] * season_avg for s in user_arch)
        hand_total_year = sum(locations_df.loc[locations_df['name']==h, 'total_profit'].values[0] * season_avg for h in user_hand)
        total_profit_year = arch_total_year + hand_total_year

        season_map = {"بهار": "spring", "تابستان": "summer", "پاییز": "autumn", "زمستان": "winter"}
        season_key = season_map[selected_season]
        season_weight = season_weights[season_key]
        arch_total_season = sum(locations_df.loc[locations_df['name']==s, f'{season_key}_profit'].values[0] * season_weight for s in user_arch)
        hand_total_season = sum(locations_df.loc[locations_df['name']==h, f'{season_key}_profit'].values[0] * season_weight for h in user_hand)
        total_profit_season = arch_total_season + hand_total_season

        distances = [distance_km(*coords[i], *coords[i+1]) for i in range(len(coords)-1)] if len(coords) > 1 else [0]
        total_distance = sum(distances)
        fuel_cost = int(total_distance * FUEL_COST_PER_KM)
        total_profit_season_adjusted = total_profit_season - int(total_distance) - fuel_cost

        user_features_year = pd.DataFrame([[len(user_arch), len(user_hand), total_profit_year, total_distance]], columns=feature_cols)
        pred_year = best_clf_year.predict(user_features_year)[0]
        user_features_season = pd.DataFrame([[len(user_arch), len(user_hand), total_profit_season, total_distance]], columns=feature_cols)
        pred_season = best_clf_season.predict(user_features_season)[0]

        m = folium.Map(location=[31.8, 48.5], zoom_start=9, tiles="OpenStreetMap")
        folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)
        for i, (lat, lng) in enumerate(coords):
            color = "red" if path[i] in handicraft_shops else "blue"
            folium.Marker(
                [lat, lng],
                popup=f"<b>{path[i]}</b><br>سود: {locations_df.loc[locations_df['name']==path[i], 'total_profit'].values[0]:,.0f}",
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)
        map_key = f"map_{hash(''.join(path))}_{random.randint(1,1000)}"
        st_folium(m, width=700, height=500, key=map_key, returned_objects=[], use_container_width=True)

        st.success(f"**سود کل (۴ فصل): {total_profit_year:,.0f}** → **دسته: {pred_year}**")
        st.success(f"**سود {selected_season}: {total_profit_season:,.0f}** → **دسته: {pred_season}**")
        st.info(f"**مسیر بهینه:** {' → '.join(path)} | **فاصله:** {total_distance:.1f} km")

        try:
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS results;")
            cur.execute("""
                CREATE TABLE results (
                    id SERIAL PRIMARY KEY,
                    arch_count INT,
                    hand_count INT,
                    profit_year FLOAT,
                    profit_season FLOAT,
                    distance FLOAT,
                    adjusted_profit FLOAT,
                    category_year TEXT,
                    category_season TEXT,
                    season TEXT,
                    path TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                INSERT INTO results (arch_count, hand_count, profit_year, profit_season, distance, adjusted_profit, category_year, category_season, season, path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (len(user_arch), len(user_hand), total_profit_year, total_profit_season, total_distance, total_profit_season_adjusted, pred_year, pred_season, selected_season, " → ".join(path)))
            conn.commit()
            st.success("نتایج در دیتابیس ذخیره شد.")
        except Error as e:
            st.error(f"ذخیره نشد: {e}")
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

st.caption("چهارمین جشنواره بین‌المللی چندرسانه‌ای میراث فرهنگی – بخش میراث دیجیتال")


st.sidebar.markdown("---")
st.sidebar.markdown("## smart Khuzestan heritage navigator")
st.sidebar.markdown("- Iran")
st.sidebar.markdown("- **city:** Khuzestan")


