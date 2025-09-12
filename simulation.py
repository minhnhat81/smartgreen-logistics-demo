import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import random
from scipy.stats import linregress

# Tạo đồ thị logistics
G = nx.Graph()
locations = ['Hanoi', 'HCMC', 'Da Nang', 'Hai Phong', 'Cai Mep Port',
             'Warehouse HN1', 'Warehouse HN2', 'Warehouse DN1', 'Warehouse HCMC1', 'Warehouse HCMC2']
G.add_nodes_from(locations)

# Cạnh với khoảng cách (km) và hệ số phát thải (kg CO2/km)
edges = [
    ('Hanoi', 'Hai Phong', {'distance': 100, 'emissions_factor': 0.2}),
    ('Hai Phong', 'Da Nang', {'distance': 650, 'emissions_factor': 0.2}),
    ('Da Nang', 'HCMC', {'distance': 850, 'emissions_factor': 0.2}),
    ('HCMC', 'Cai Mep Port', {'distance': 50, 'emissions_factor': 0.05}),
    ('Hanoi', 'Warehouse HN1', {'distance': 20, 'emissions_factor': 0.2}),
    ('Hanoi', 'Warehouse HN2', {'distance': 30, 'emissions_factor': 0.2}),
    ('Da Nang', 'Warehouse DN1', {'distance': 15, 'emissions_factor': 0.2}),
    ('HCMC', 'Warehouse HCMC1', {'distance': 10, 'emissions_factor': 0.05}),
    ('HCMC', 'Warehouse HCMC2', {'distance': 25, 'emissions_factor': 0.05}),
    ('Hanoi', 'HCMC', {'distance': 1700, 'emissions_factor': 0.15}),
    ('Warehouse HN1', 'Hai Phong', {'distance': 10, 'emissions_factor': 0.2}),
    ('Warehouse HCMC1', 'Cai Mep Port', {'distance': 5, 'emissions_factor': 0.05}),
]
G.add_edges_from(edges)

# Hàm tính chi phí tuyến đường
def path_cost(path):
    total_distance = 0
    total_emissions = 0
    for i in range(len(path) - 1):
        edge_data = G.get_edge_data(path[i], path[i+1])
        total_distance += edge_data['distance']
        total_emissions += edge_data['distance'] * edge_data['emissions_factor']
    return total_distance, total_emissions

# Tuyến truyền thống
traditional_path = ['Hanoi', 'Hai Phong', 'Da Nang', 'HCMC', 'Cai Mep Port']
trad_distance, trad_emissions = path_cost(traditional_path)

# Tuyến tối ưu hóa bằng A*
def emissions_heuristic(u, v):
    return 0  # Heuristic đơn giản
optimized_path = nx.astar_path(G, source='Hanoi', target='Cai Mep Port',
                               heuristic=emissions_heuristic, weight=lambda u, v, d: d['distance'] * d['emissions_factor'])
opt_distance, opt_emissions = path_cost(optimized_path)

# Tính tiết kiệm
distance_savings = (trad_distance - opt_distance) / trad_distance * 100
emissions_savings = (trad_emissions - opt_emissions) / trad_emissions * 100

# IoT simulation: 50 xe tải
num_trucks = 50
iot_fuel = np.random.normal(30, 5, num_trucks)  # Trước tối ưu
iot_fuel_opt = iot_fuel * (1 - 0.15)  # Sau tối ưu
iot_temp = np.random.normal(25, 5, num_trucks)
iot_humidity = np.random.normal(60, 10, num_trucks)

# AI Demand Forecasting: 24 tháng
time = np.arange(1, 25)
demand = 100 + 5 * time + np.random.normal(0, 20, 24)
slope, intercept, _, _, _ = linregress(time, demand)
forecast_month_25 = intercept + slope * 25

# Blockchain simulation: Log giao dịch
blockchain_log = []
for i in range(5):
    tx = {
        'id': i+1,
        'from': random.choice(locations),
        'to': random.choice(locations),
        'emissions': round(random.uniform(10, 200), 2),
        'status': 'Verified'
    }
    blockchain_log.append(tx)

# Reverse Logistics
recovery_rate = 0.3
total_packaging = 10000
recovered = total_packaging * recovery_rate
revenue_from_recovery = recovered * 5  # 5 triệu VND/tấn

# In kết quả
print("Traditional Route:", traditional_path)
print(f"Distance: {trad_distance:.2f} km, Emissions: {trad_emissions:.2f} kg CO2")
print("Optimized Route:", optimized_path)
print(f"Distance: {opt_distance:.2f} km, Emissions: {opt_emissions:.2f} kg CO2")
print(f"Savings: Distance {distance_savings:.2f}%, Emissions {emissions_savings:.2f}%")
print(f"IoT Data (Average): Fuel Before {iot_fuel.mean():.2f} L/100km, After {iot_fuel_opt.mean():.2f} L/100km")
print(f"Demand Forecast Month 25: {forecast_month_25:.2f} units")
print("Blockchain Log Sample:", blockchain_log[:3])
print(f"Reverse Logistics: Recovered {recovered:.0f} tons, Revenue {revenue_from_recovery:.0f} million VND")

# Vẽ biểu đồ
# Biểu đồ 1: Mạng lưới logistics
plt.figure(figsize=(10, 8))
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=500, font_size=8)
edge_labels = {(u, v): f"{d['distance']} km\n{d['emissions_factor']} kg/km" for u, v, d in G.edges(data=True)}
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6)
plt.title("Logistics Network in Vietnam")
plt.show()

# Biểu đồ 2: So sánh phát thải
plt.figure(figsize=(8, 5))
plt.bar(['Traditional', 'Optimized'], [trad_emissions, opt_emissions], color=['red', 'green'])
plt.ylabel("Emissions (kg CO2)")
plt.title("Emissions Comparison: Traditional vs Optimized Route")
plt.show()

# Biểu đồ 3: Dự báo nhu cầu
plt.figure(figsize=(8, 5))
plt.plot(time, demand, 'bo-', label='Historical Demand')
plt.plot(25, forecast_month_25, 'go', label='Forecast Month 25')
plt.xlabel("Month")
plt.ylabel("Demand (Units)")
plt.title("AI Demand Forecasting")
plt.legend()
plt.show()

# Biểu đồ 4: IoT Fuel Data
plt.figure(figsize=(8, 5))
plt.hist(iot_fuel, bins=10, alpha=0.5, label='Before Optimization', color='red')
plt.hist(iot_fuel_opt, bins=10, alpha=0.5, label='After Optimization', color='green')
plt.xlabel("Fuel Consumption (L/100km)")
plt.ylabel("Number of Trucks")
plt.title("IoT Fuel Data: Before vs After Optimization")
plt.legend()
plt.show()