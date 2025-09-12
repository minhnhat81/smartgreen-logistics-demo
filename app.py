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
import logging

# Tắt log CmdStanPy
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

st.title("SmartGreenLogistics: Giao Hàng Chặng Cuối Thông Minh - Nâng Cấp")

# Sidebar: Giải Pháp Cho Vấn Đề Khảo Sát
st.sidebar.header("Giải Pháp Cho Vấn Đề Khảo Sát")
st.sidebar.write("""
- **Tắc nghẽn giao thông**: Tái định tuyến động với API Google Maps Traffic (giả lập).
- **Thời tiết mưa/ngập**: API OpenWeatherMap, overlay ngập, điều chỉnh ETA.
- **Tỷ lệ thất bại**: Xác thực địa chỉ, thông báo lịch hẹn, minh bạch Blockchain.
""")


# Hàm lấy thời tiết thực thời gian
def get_weather(city="Ho Chi Minh City"):
    api_key = "YOUR_OPENWEATHERMAP_KEY"  # Thay bằng key của bạn
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
    try:
        response = requests.get(url).json()
        weather = response['weather'][0]['main']
        if weather == "Rain":
            return "Rainy", 1.2  # Tăng ETA 20%
        return "Sunny", 1.0
    except:
        return "Sunny", 1.0  # Mặc định


# Hàm giả lập tắc nghẽn giao thông
def get_traffic_status(from_lat, from_lon, to_lat, to_lon):
    if np.random.random() < 0.2:
        return 1.3, "Traffic Jam"  # Tăng 30%
    return 1.0, "Normal"


# Hàm xác thực địa chỉ
def validate_address(address):
    if np.random.random() < 0.8:
        return True, "Valid"
    return False, "Invalid - Please confirm"


# Hàm thông báo lịch hẹn (giả lập)
def send_appointment_notification(phone, eta, order_id):
    message = f"Đơn hàng {order_id}: Dự kiến giao lúc {eta} phút. Vui lòng có mặt!"
    return f"SMS sent to {phone}: {message}"


# Upload dữ liệu
st.subheader("Tải Dữ Liệu")
time_series_file = st.file_uploader("Tải file time-series (train.csv)", type="csv")
locations_file = st.file_uploader("Tải file vị trí (locations.csv)", type="csv")
distance_file = st.file_uploader("Tải file khoảng cách (distance_matrix.csv)", type="csv")

if time_series_file and locations_file and distance_file:
    try:
        # Load dữ liệu
        df_time = pd.read_csv(time_series_file)
        df_locations = pd.read_csv(locations_file)
        distance_matrix = pd.read_csv(distance_file, index_col=0).values

        required_time_cols = ['date', 'delivery_time', 'weather']
        required_loc_cols = ['name', 'lat', 'lon']
        if not all(col in df_time.columns for col in required_time_cols):
            st.error(f"train.csv cần các cột: {required_time_cols}")
        elif not all(col in df_locations.columns for col in required_loc_cols):
            st.error(f"locations.csv cần các cột: {required_loc_cols}")
        elif distance_matrix.shape[0] != len(df_locations):
            st.error("Kích thước distance_matrix.csv không khớp với locations.csv")
        else:
            # Bước 1: Dự báo ETA với Prophet
            st.subheader("Dự Báo Thời Gian Giao Hàng (ETA)")
            df_time['date'] = pd.to_datetime(df_time['date'], errors='coerce')
            df_time = df_time[['date', 'delivery_time']].rename(columns={'date': 'ds', 'delivery_time': 'y'})
            df_time = df_time.dropna()

            if df_time.empty:
                st.error("Dữ liệu time-series rỗng sau xử lý.")
            else:
                model = Prophet(daily_seasonality=True, yearly_seasonality=True, interval_width=0.95)
                model.fit(df_time)
                future = model.make_future_dataframe(periods=30)
                forecast = model.predict(future)

                st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(30))

                # ETA cơ bản từ dự báo
                today = pd.to_datetime("2025-09-12 13:48:00")  # Thời gian hiện tại
                eta_base = forecast[forecast['ds'] == today]['yhat'].iloc[0] if not forecast[
                    forecast['ds'] == today].empty else 30.0

            # Bước 2: Tối ưu lộ trình với OR-Tools (nâng cấp ETA theo đoạn)
            st.subheader("Lộ Trình Giao Hàng Tối Ưu")
            num_vehicles = 2
            depot = 0
            manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot)
            routing = pywrapcp.RoutingModel(manager)


            def distance_callback(from_index, to_index):
                base_distance = distance_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]
                traffic_multiplier, traffic_status = get_traffic_status(
                    df_locations['lat'][manager.IndexToNode(from_index)],
                    df_locations['lon'][manager.IndexToNode(from_index)],
                    df_locations['lat'][manager.IndexToNode(to_index)],
                    df_locations['lon'][manager.IndexToNode(to_index)]
                )
                adjusted_distance = base_distance * traffic_multiplier
                return int(adjusted_distance * 1000)


            routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(distance_callback))

            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            solution = routing.SolveWithParameters(search_parameters)

            if solution:
                routes = []
                route_details = []
                total_distance = 0
                for vehicle_id in range(num_vehicles):
                    index = routing.Start(vehicle_id)
                    route = []
                    route_distance = 0
                    route_times = []
                    while not routing.IsEnd(index):
                        node = manager.IndexToNode(index)
                        route.append(node)
                        next_index = solution.Value(routing.NextVar(index))
                        base_distance = distance_matrix[node][manager.IndexToNode(next_index)]
                        traffic_multiplier, traffic_status = get_traffic_status(
                            df_locations['lat'][node], df_locations['lon'][node],
                            df_locations['lat'][manager.IndexToNode(next_index)],
                            df_locations['lon'][manager.IndexToNode(next_index)]
                        )
                        adjusted_distance = base_distance * traffic_multiplier
                        route_distance += adjusted_distance
                        # Tính ETA cho đoạn: 20 km/h (tốc độ xe máy), điều chỉnh thời tiết
                        weather_status, weather_multiplier = get_weather()
                        segment_time = (adjusted_distance / 20) * 60 * weather_multiplier  # Phút
                        route_times.append(segment_time)
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

                # Hiển thị chi tiết lộ trình
                st.write(f"Tổng khoảng cách (điều chỉnh tắc nghẽn): {total_distance:.1f} km")
                for detail in route_details:
                    route_names = [df_locations['name'][i] for i in detail['nodes']]
                    st.write(f"Xe {detail['vehicle']}: {' -> '.join(route_names)}")
                    total_time = sum(detail['times'])
                    st.write(f"Khoảng cách: {detail['distance']:.1f} km, Tổng thời gian: {total_time:.1f} phút")
                    for i, (time, node) in enumerate(zip(detail['times'], detail['nodes'][:-1])):
                        next_node = detail['nodes'][i + 1]
                        base_dist = distance_matrix[node][next_node]
                        st.write(
                            f"Đoạn {df_locations['name'][node]} -> {df_locations['name'][next_node]}: {time:.1f} phút ({base_dist:.1f} km)")

                # Vẽ bản đồ
                m = folium.Map(location=[10.776, 106.700], zoom_start=13)
                for i, loc in df_locations.iterrows():
                    folium.Marker(
                        [loc['lat'], loc['lon']],
                        popup=f"{loc['name']}<br>Thời tiết: {weather_status}",
                        icon=folium.Icon(color='red' if loc['name'] == 'Depot' else 'blue')
                    ).add_to(m)
                for detail in route_details:
                    route = detail['nodes']
                    points = [[df_locations['lat'][i], df_locations['lon'][i]] for i in route]
                    color = 'blue' if detail['vehicle'] == 1 else 'red'
                    for i in range(len(route) - 1):
                        segment = [points[i], points[i + 1]]
                        base_dist = distance_matrix[route[i]][route[i + 1]]
                        traffic_multiplier, traffic_status = get_traffic_status(
                            df_locations['lat'][route[i]], df_locations['lon'][route[i]],
                            df_locations['lat'][route[i + 1]], df_locations['lon'][route[i + 1]]
                        )
                        adjusted_dist = base_dist * traffic_multiplier
                        segment_time = (adjusted_dist / 20) * 60 * weather_multiplier
                        folium.PolyLine(
                            segment,
                            color=color if traffic_status == "Normal" else "orange",
                            weight=2.5,
                            popup=f"Xe {detail['vehicle']}<br>Khoảng cách: {adjusted_dist:.1f} km<br>Thời gian: {segment_time:.1f} phút<br>Tắc nghẽn: {traffic_status}"
                        ).add_to(m)
                folium_static(m)

            # Bước 3: Xử lý tỷ lệ thất bại
            st.subheader("Xử Lý Tỷ Lệ Giao Hàng Thất Bại")
            address_input = st.text_input("Nhập địa chỉ khách hàng", value="10 Ngõ 5, Quận 1")
            phone_number = st.text_input("Số điện thoại khách hàng", value="0123456789")
            if st.button("Xác Thực Địa Chỉ Và Gửi Thông Báo"):
                is_valid, status = validate_address(address_input)
                if is_valid:
                    st.success(f"Địa chỉ hợp lệ: {status}")
                    message = send_appointment_notification(phone_number, total_time, "order_123")
                    st.info(message)
                else:
                    st.warning(f"Địa chỉ không hợp lệ: {status}. Vui lòng xác nhận.")
                    st.info("Lưu lý do thất bại trên Blockchain.")

            # Bước 4: IoT giả lập
            st.subheader("IoT: Vị Trí Xe Thời Gian Thực")
            current_positions = [
                {'vehicle': 1, 'lat': 10.776 + np.random.uniform(-0.005, 0.005),
                 'lon': 106.700 + np.random.uniform(-0.005, 0.005)},
                {'vehicle': 2, 'lat': 10.776 + np.random.uniform(-0.005, 0.005),
                 'lon': 106.700 + np.random.uniform(-0.005, 0.005)}
            ]
            st.write("Vị trí xe hiện tại:", pd.DataFrame(current_positions))

            # Bước 5: Blockchain
            st.subheader("Blockchain: Minh Bạch Trạng Thái Đơn Hàng")
            try:
                with open('contract_abi.json', 'r') as f:
                    contract_abi = json.load(f)
                st.success(f"ABI loaded thành công! Số hàm: {len(contract_abi)}")
            except FileNotFoundError:
                st.error("Không tìm thấy contract_abi.json.")
                contract_abi = []
            except json.JSONDecodeError as e:
                st.error(f"Lỗi JSON: {str(e)}.")
                contract_abi = []

            infura_url = st.text_input("Infura URL",
                                       value="https://sepolia.infura.io/v3/ff6bb90076814174b5e96431aadd8b61")
            contract_address = st.text_input("Contract Address", value="0xFdd34AeD38B79Cd7e68F960fBa231C4126C629f6")
            private_key = st.text_input("Private Key", value="", type="password")
            wallet_address = st.text_input("Wallet Address", value="0xeEBCb81b354F95f00f0f1B43044e72327Ac9E308")

            if private_key and contract_abi:
                try:
                    w3 = Web3(Web3.HTTPProvider(infura_url))
                    if not w3.is_connected():
                        st.error("Không kết nối Infura.")
                    else:
                        st.success("Kết nối Infura thành công!")
                        contract = w3.eth.contract(address=contract_address, abi=contract_abi)

                        order_id = st.text_input("Nhập Order ID", value="order_123")
                        status = st.selectbox("Cập nhật trạng thái",
                                              ["Pending", "In Transit", "Delivered", "Failed - Customer Absent"])
                        if st.button("Cập nhật Blockchain"):
                            nonce = w3.eth.get_transaction_count(wallet_address)
                            tx = contract.functions.updateOrderStatus(order_id, status).build_transaction({
                                'from': wallet_address,
                                'gas': 200000,
                                'gasPrice': w3.eth.gas_price,
                                'nonce': nonce,
                                'chainId': 11155111
                            })
                            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
                            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                            st.success(f"Transaction hash: {tx_hash.hex()}")

                        if st.button("Tra cứu trạng thái"):
                            order_info = contract.functions.getOrderStatus(order_id).call()
                            st.write(f"Order ID: {order_info[0]}, Status: {order_info[1]}, Timestamp: {order_info[2]}")
                except Exception as e:
                    st.error(f"Lỗi Blockchain: {str(e)}")
            else:
                st.warning("Vui lòng nhập Private Key và đảm bảo contract_abi.json.")
    except Exception as e:
        st.error(f"Lỗi xử lý: {str(e)}")