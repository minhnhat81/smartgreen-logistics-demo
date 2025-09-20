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
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route = []
        route_distance = 0
        route_times = []
        cumulative_time = 0
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(node)
            next_index = solution.Value(routing.NextVar(index))
            if next_index == index:
                break
            base_distance = distance_matrix[node][manager.IndexToNode(next_index)]
            traffic_multiplier, _ = get_traffic_status(
                df_locations['lat'].iloc[node], df_locations['lon'].iloc[node],
                df_locations['lat'].iloc[manager.IndexToNode(next_index)], df_locations['lon'].iloc[manager.IndexToNode(next_index)]
            )
            adjusted_distance = base_distance * traffic_multiplier
            route_distance += adjusted_distance
            segment_time = (adjusted_distance / speed_km_per_hour) * 60  # Chuyển đổi sang phút
            cumulative_time += segment_time
            route_times.append(cumulative_time)
            index = next_index
        route.append(manager.IndexToNode(index))
        routes.append(route)
        total_distance += route_distance
        route_details.append({
            'vehicle': vehicle_id + 1,
            'nodes': route,
            'distance': route_distance,
            'times': route_times
        })

    return routes, route_details, total_distance

# Load ABI
try:
    with open('contract_abi.json', 'r') as f:
        contract_abi = json.load(f)
except FileNotFoundError:
    contract_abi = []
    st.warning("Không tìm thấy contract_abi.json. Vui lòng thêm file.")

# Kiểm tra đăng nhập
authenticated, name = login()

if authenticated:
    st.sidebar.title(f"Chào {name}")
    st.sidebar.header("Giải Pháp Tối Ưu Giao Hàng")
    st.sidebar.write("""
    - Tắc nghẽn: Tái định tuyến động.
    - Thời tiết: Điều chỉnh ETA +20% khi mưa.
    - Thất bại: Xác thực địa chỉ, hẹn giao lại.
    """)

    # Tabs cho giao diện cá nhân hóa
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Nhập Đơn Hàng", "Tối Ưu Lộ Trình", "Cập Nhật Trạng Thái", "Xử Lý Thất Bại", "Báo Cáo Dashboard"])

    with tab1:
        st.subheader("Nhập Danh Sách Đơn Hàng")
        num_orders = st.number_input("Số lượng đơn hàng", min_value=1, max_value=20, value=5)
        orders_data = []
        for i in range(num_orders):
            st.write(f"Đơn hàng {i+1}:")
            order_id = st.text_input(f"ID đơn hàng {i+1}", key=f"id_{i}", value=f"order_{i+1}")
            address = st.text_input(f"Địa chỉ {i+1}", key=f"addr_{i}", value=f"10 Ngõ {i+1}, Quận 1, TP.HCM")
            lat = st.number_input(f"Vĩ độ {i+1}", key=f"lat_{i}", value=10.776 + np.random.uniform(-0.01, 0.01))
            lon = st.number_input(f"Kinh độ {i+1}", key=f"lon_{i}", value=106.700 + np.random.uniform(-0.01, 0.01))
            orders_data.append({'id': order_id, 'address': address, 'lat': lat, 'lon': lon})

        if st.button("Tạo Lộ Trình Tối Ưu"):
            if orders_data:
                num_points = len(orders_data) + 1  # +1 cho depot
                depot_lat, depot_lon = 10.776, 106.700
                points = [(depot_lat, depot_lon)] + [(order['lat'], order['lon']) for order in orders_data]
                # Tạo ma trận khoảng cách dựa trên tọa độ
                distance_matrix = np.zeros((num_points, num_points))
                for i in range(num_points):
                    for j in range(num_points):
                        if i != j:
                            lat1, lon1 = points[i]
                            lat2, lon2 = points[j]
                            distance_matrix[i][j] = calculate_distance(lat1, lon1, lat2, lon2)
                np.fill_diagonal(distance_matrix, 0)
                # Đảm bảo tất cả các giá trị đều dương và có kết nối
                for i in range(num_points):
                    for j in range(num_points):
                        if i != j and distance_matrix[i][j] == 0:
                            distance_matrix[i][j] = 1.0

                df_locations = pd.DataFrame({
                    'name': ['Depot'] + [order['id'] for order in orders_data],
                    'lat': [depot_lat] + [order['lat'] for order in orders_data],
                    'lon': [depot_lon] + [order['lon'] for order in orders_data]
                })

                # Debug dữ liệu
                st.write("Kích thước distance_matrix:", distance_matrix.shape)
                st.write("Số lượng địa điểm:", len(df_locations))
                st.write("Distance Matrix:", distance_matrix)

                try:
                    routes, route_details, total_distance = optimize_route(distance_matrix, df_locations)
                    st.session_state.routes = routes
                    st.session_state.route_details = route_details
                    st.session_state.total_distance = total_distance
                    st.session_state.orders_data = orders_data
                    st.session_state.df_locations = df_locations
                    st.session_state.distance_matrix = distance_matrix  # Lưu distance_matrix
                    st.success("Lộ trình tối ưu đã tạo!")
                except Exception as e:
                    st.error(f"Lỗi khi tạo lộ trình: {str(e)}")

    with tab2:
        st.subheader("Tối Ưu Lộ Trình")
        if 'routes' in st.session_state:
            routes = st.session_state.routes
            route_details = st.session_state.route_details
            total_distance = st.session_state.total_distance
            df_locations = st.session_state.df_locations
            distance_matrix = st.session_state.distance_matrix  # Lấy distance_matrix từ session_state
            st.write(f"Tổng khoảng cách: {total_distance:.1f} km")
            for detail in route_details:
                vehicle_id = detail['vehicle']
                st.write(f"### Xe {vehicle_id}")
                route_names = [df_locations['name'][i] for i in detail['nodes']]
                st.write(f"Lộ trình: {' -> '.join(route_names)}")
                for i, (node, time) in enumerate(zip(detail['nodes'][:-1], detail['times'])):
                    next_node = detail['nodes'][i + 1]
                    distance = distance_matrix[node][next_node] if node != next_node else 0
                    st.write(f"- Đến {df_locations['name'][next_node]}: {time:.1f} phút (Khoảng cách: {distance:.1f} km)")
                st.write(f"Tổng thời gian xe {vehicle_id}: {sum(detail['times']):.1f} phút")
                st.write(f"Tổng khoảng cách xe {vehicle_id}: {detail['distance']:.1f} km")
                st.write("---")

            # Bản đồ
            m = folium.Map(location=[10.776, 106.700], zoom_start=13)
            for i, loc in df_locations.iterrows():
                folium.Marker(
                    [loc['lat'], loc['lon']],
                    popup=f"{loc['name']}<br>ETA: {sum([t for d in route_details for t in d['times'] if i in d['nodes']]):.1f} phút",
                    icon=folium.Icon(color='red' if loc['name'] == 'Depot' else 'blue')
                ).add_to(m)
            for detail in route_details:
                points = [[df_locations['lat'][i], df_locations['lon'][i]] for i in detail['nodes']]
                color = 'blue' if detail['vehicle'] == 1 else 'red'
                folium.PolyLine(points, color=color, weight=2.5, popup=f"Xe {detail['vehicle']}: {sum(detail['times']):.1f} phút").add_to(m)
            folium_static(m)
        else:
            st.info("Vui lòng nhập đơn hàng ở tab trước.")

    with tab3:
        st.subheader("Cập Nhật Trạng Thái Giao Hàng")
        if 'orders_data' in st.session_state and 'df_locations' in st.session_state:
            orders = st.session_state.orders_data
            df_locations = st.session_state.df_locations
            for order in orders:
                order_id = order['id']
                st.write(f"Đơn hàng {order_id}:")
                # Lấy index của địa điểm từ df_locations
                location_index = df_locations[df_locations['name'] == order_id].index[0] if order_id in df_locations['name'].values else None
                # Sử dụng giá trị hiện tại từ session_state nếu có, nếu không dùng "Pending"
                current_status = st.session_state.get(f"status_{order_id}", "Pending")
                status = st.selectbox(f"Trạng thái {order_id}", ["Pending", "In Transit", "Delivered", "Failed - Customer Absent"], key=f"status_{order_id}", index=["Pending", "In Transit", "Delivered", "Failed - Customer Absent"].index(current_status))
                if st.button(f"Cập nhật vị trí và trạng thái {order_id} trên Blockchain", key=f"update_loc_{order_id}"):
                    try:
                        w3 = Web3(Web3.HTTPProvider(st.secrets["INFURA_URL"]))
                        contract = w3.eth.contract(address=st.secrets["CONTRACT_ADDRESS"], abi=contract_abi)
                        nonce = w3.eth.get_transaction_count(st.secrets["WALLET_ADDRESS"])
                        lat = order['lat'] if location_index is None else df_locations.loc[location_index, 'lat']
                        lon = order['lon'] if location_index is None else df_locations.loc[location_index, 'lon']
                        # Chuyển đổi lat và lon thành uint256 (nhân với 10^8 để giữ độ chính xác)
                        lat_uint = int(lat * 10**8)
                        lon_uint = int(lon * 10**8)
                        tx = contract.functions.updateOrderLocationAndStatus(order_id, lat_uint, lon_uint, status).build_transaction({
                            'from': st.secrets["WALLET_ADDRESS"],
                            'gas': 300000,
                            'gasPrice': w3.eth.gas_price,
                            'nonce': nonce,
                            'chainId': 11155111
                        })
                        signed_tx = w3.eth.account.sign_transaction(tx, st.secrets["PRIVATE_KEY"])
                        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                        st.success(f"Cập nhật vị trí và trạng thái thành công! Hash: {tx_hash.hex()}")
                        # Không gán lại st.session_state[f"status_{order_id}"] trực tiếp
                        # Thay vào đó, cập nhật bằng cách reload hoặc để widget tự xử lý
                    except Exception as e:
                        st.error(f"Lỗi cập nhật: {str(e)}")
        else:
            st.info("Vui lòng nhập đơn hàng ở tab trước.")

    with tab4:
        st.subheader("Xử Lý Thất Bại (Từ Chối/Hẹn Giao)")
        if 'orders_data' in st.session_state:
            order_id = st.selectbox("Chọn đơn hàng thất bại", [order['id'] for order in st.session_state.orders_data])
            address_input = st.text_input("Địa chỉ khách hàng", value=[o['address'] for o in st.session_state.orders_data if o['id'] == order_id][0])
            phone_number = st.text_input("Số điện thoại", value="0123456789")
            reschedule_time = st.date_input("Thời gian hẹn lại", value=datetime.now() + timedelta(days=1))
            if st.button("Xác Thực Và Xử Lý"):
                is_valid, status = validate_address(address_input)
                if is_valid:
                    st.success(f"Địa chỉ hợp lệ: {status}")
                    weather_status, weather_multiplier = get_weather()
                    eta_adjusted = 30 * weather_multiplier
                    message = send_appointment_notification(phone_number, eta_adjusted, order_id)
                    st.info(message)
                    st.write(f"Hẹn giao lại vào: {reschedule_time}")
                    # Tái tối ưu (giả lập)
                    st.session_state.routes = None  # Đánh dấu tái tối ưu
                    st.info("Lộ trình đã được tái tối ưu.")
                else:
                    st.warning(f"Địa chỉ không hợp lệ: {status}")
                    try:
                        w3 = Web3(Web3.HTTPProvider(st.secrets["INFURA_URL"]))
                        contract = w3.eth.contract(address=st.secrets["CONTRACT_ADDRESS"], abi=contract_abi)
                        nonce = w3.eth.get_transaction_count(st.secrets["WALLET_ADDRESS"])
                        tx = contract.functions.updateOrderStatus(order_id, "Failed - Rescheduled").build_transaction({
                            'from': st.secrets["WALLET_ADDRESS"],
                            'gas': 200000,
                            'gasPrice': w3.eth.gas_price,
                            'nonce': nonce,
                            'chainId': 11155111
                        })
                        signed_tx = w3.eth.account.sign_transaction(tx, st.secrets["PRIVATE_KEY"])
                        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                        st.success(f"Lý do thất bại lưu trên Blockchain. Hash: {tx_hash.hex()}")
                    except Exception as e:
                        st.error(f"Lỗi lưu Blockchain: {str(e)}")
        else:
            st.info("Vui lòng nhập đơn hàng ở tab trước.")

    with tab5:
        st.subheader("Báo Cáo Dashboard")
        if 'orders_data' in st.session_state:
            orders = st.session_state.orders_data
            # Giả lập dữ liệu báo cáo
            status_data = np.random.choice(["Delivered on Time", "Delayed", "Failed"], len(orders), p=[0.6, 0.3, 0.1])
            time_data = np.random.normal(25, 5, len(orders))
            eta_data = np.full(len(orders), 30)

            # Biểu đồ tròn
            fig1 = px.pie(values=[np.sum(status_data == "Delivered on Time"), np.sum(status_data == "Delayed"), np.sum(status_data == "Failed")],
                         names=["Đúng Giờ", "Chậm", "Thất Bại"], title="Tỷ Lệ Giao Hàng")
            st.plotly_chart(fig1)

            # Biểu đồ đường
            fig2 = go.Figure(data=[
                go.Scatter(x=[f"Đơn {i+1}" for i in range(len(time_data))], y=time_data, mode='markers+lines', name='Thời Gian Thực Tế'),
                go.Scatter(x=[f"Đơn {i+1}" for i in range(len(eta_data))], y=eta_data, mode='lines', name='ETA Dự Kiến', line=dict(dash='dash'))
            ])
            fig2.update_layout(title="Thời Gian Giao Hàng So Với Dự Kiến", yaxis_title="Thời gian (phút)")
            st.plotly_chart(fig2)

            st.write(f"Tổng đơn hàng: {len(orders)} | Đúng giờ: {np.sum(time_data <= eta_data)} ({100*np.sum(time_data <= eta_data)/len(orders):.1f}%) | Chậm: {np.sum(time_data > eta_data)}")
        else:
            st.info("Vui lòng nhập đơn hàng ở tab trước.")
