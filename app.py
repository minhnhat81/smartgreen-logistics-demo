import streamlit as st
import pandas as pd
import numpy as np
from prophet import Prophet
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import folium
from streamlit_folium import folium_static
from web3 import Web3
import json
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime, timedelta
from math import sqrt

# Tắt log CmdStanPy
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

# Dữ liệu người dùng cố định cho mô phỏng đăng nhập
USERS = {
    "deliveryman": {"name": "Delivery Man", "password": "password123"}
}

# Hàm mô phỏng đăng nhập
def login():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
        st.session_state['name'] = None
        st.session_state['username'] = None

    if not st.session_state['authenticated']:
        with st.form("login_form"):
            username = st.text_input("Tên người dùng")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("Đăng nhập")

            if submit:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state['authenticated'] = True
                    st.session_state['name'] = USERS[username]["name"]
                    st.session_state['username'] = username
                    st.success(f"Đăng nhập thành công! Chào {st.session_state['name']}")
                    st.rerun()
                else:
                    st.error("Tên người dùng hoặc mật khẩu không đúng")

    return st.session_state['authenticated'], st.session_state['name']

# Hàm tính khoảng cách Euclidean
def calculate_distance(lat1, lon1, lat2, lon2):
    return max(1.0, sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 100)  # Đảm bảo giá trị dương

# Hàm lấy thời tiết thực thời gian
def get_weather(city="Ho Chi Minh City"):
    api_key = st.secrets.get("OPENWEATHERMAP_KEY", "YOUR_OPENWEATHERMAP_KEY")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
    try:
        response = requests.get(url).json()
        weather = response['weather'][0]['main']
        if weather == "Rain":
            return "Rainy", 1.2  # Tăng ETA 20%
        return "Sunny", 1.0
    except:
        return "Sunny", 1.0

# Hàm giả lập tắc nghẽn giao thông
def get_traffic_status(from_lat, from_lon, to_lat, to_lon):
    if np.random.random() < 0.2:
        return 1.3, "Traffic Jam"
    return 1.0, "Normal"

# Hàm xác thực địa chỉ
def validate_address(address):
    if np.random.random() < 0.8:
        return True, "Valid"
    return False, "Invalid - Please confirm"

# Hàm thông báo lịch hẹn
def send_appointment_notification(phone, eta, order_id):
    message = f"Đơn hàng {order_id}: Dự kiến giao lúc {eta} phút. Vui lòng có mặt!"
    return f"SMS sent to {phone}: {message}"

# Hàm tối ưu lộ trình
def optimize_route(distance_matrix, df_locations, num_vehicles=1, depot=0, speed_km_per_hour=20):
    # Kiểm tra dữ liệu
    if distance_matrix.shape[0] != distance_matrix.shape[1]:
        raise ValueError("distance_matrix phải là ma trận vuông!")
    if len(distance_matrix) != len(df_locations):
        raise ValueError("Số lượng địa điểm không khớp!")
    if np.any(distance_matrix < 0) or np.any(np.isnan(distance_matrix)):
        raise ValueError("distance_matrix chứa giá trị âm hoặc NaN!")
    if num_vehicles > len(distance_matrix) - 1:
        raise ValueError("Số xe không được vượt quá số địa điểm trừ depot!")

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        base_distance = distance_matrix[from_node][to_node]
        if base_distance <= 0:
            return 1  # Giá trị mặc định nếu khoảng cách không hợp lệ
        traffic_multiplier, _ = get_traffic_status(
            df_locations['lat'].iloc[from_node], df_locations['lon'].iloc[from_node],
            df_locations['lat'].iloc[to_node], df_locations['lon'].iloc[to_node]
        )
        adjusted_distance = base_distance * traffic_multiplier
        return max(1, int(adjusted_distance))  # Đảm bảo giá trị dương và nguyên

    routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(distance_callback))

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(search_parameters)

    if solution is None:
        raise ValueError("Không tìm thấy giải pháp tối ưu! Kiểm tra dữ liệu hoặc giảm số lượng xe.")

    routes = []
    route_details = []
    total_distance = 0
    for vehicle_id in range(num
