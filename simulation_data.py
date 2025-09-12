import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Tạo 15 điểm giao hàng (tọa độ giả quanh TP.HCM)
locations = [
    {"name": "Depot", "lat": 10.776, "lon": 106.700},  # Quận 1
    {"name": "Customer1", "lat": 10.780, "lon": 106.705},
    {"name": "Customer2", "lat": 10.775, "lon": 106.710},
    {"name": "Customer3", "lat": 10.790, "lon": 106.695},
    {"name": "Customer4", "lat": 10.785, "lon": 106.702},
    {"name": "Customer5", "lat": 10.770, "lon": 106.698},
    {"name": "Customer6", "lat": 10.782, "lon": 106.715},
    {"name": "Customer7", "lat": 10.788, "lon": 106.708},
    {"name": "Customer8", "lat": 10.773, "lon": 106.703},
    {"name": "Customer9", "lat": 10.779, "lon": 106.697},
    {"name": "Customer10", "lat": 10.787, "lon": 106.712},
    {"name": "Customer11", "lat": 10.774, "lon": 106.706},
    {"name": "Customer12", "lat": 10.781, "lon": 106.701},
    {"name": "Customer13", "lat": 10.776, "lon": 106.709},
    {"name": "Customer14", "lat": 10.783, "lon": 106.704},
]

# Ma trận khoảng cách (km, giả lập)
np.random.seed(42)
num_locations = len(locations)
distance_matrix = np.random.randint(1, 10, size=(num_locations, num_locations))
distance_matrix = (distance_matrix + distance_matrix.T) // 2  # Đối xứng
np.fill_diagonal(distance_matrix, 0)

# Dữ liệu time-series cho ETA (365 ngày)
start_date = datetime(2024, 1, 1)
dates = [start_date + timedelta(days=i) for i in range(365)]
delivery_times = np.random.normal(30, 5, 365) + np.sin(np.arange(365)/365*2*np.pi)*10  # Phút, có mùa vụ
weather = np.random.choice(['Sunny', 'Rainy'], size=365, p=[0.7, 0.3])  # Giả lập thời tiết
weather_effect = np.where(weather == 'Rainy', 1.2, 1.0)  # Mưa tăng 20% thời gian
delivery_times *= weather_effect

# Lưu dữ liệu time-series
df_time_series = pd.DataFrame({
    'date': dates,
    'delivery_time': delivery_times,
    'weather': weather
})
df_time_series.to_csv('train.csv', index=False)

# Lưu dữ liệu vị trí và khoảng cách
df_locations = pd.DataFrame(locations)
df_locations.to_csv('locations.csv', index=False)
pd.DataFrame(distance_matrix, columns=[loc['name'] for loc in locations], index=[loc['name'] for loc in locations]).to_csv('distance_matrix.csv')
print("Dữ liệu giả lập đã tạo: train.csv, locations.csv, distance_matrix.csv")