import plotly.graph_objects as go
import networkx as nx
import numpy as np
import random

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

# Tọa độ 3D giả lập (x, y: vị trí địa lý; z: phát thải trung bình)
coords = {
    'Hanoi': (0, 1000, 50), 'Hai Phong': (100, 950, 40), 'Da Nang': (50, 500, 45),
    'HCMC': (100, 0, 60), 'Cai Mep Port': (120, -50, 30),
    'Warehouse HN1': (10, 980, 35), 'Warehouse HN2': (-10, 970, 35),
    'Warehouse DN1': (60, 510, 30), 'Warehouse HCMC1': (90, 10, 25),
    'Warehouse HCMC2': (110, 20, 25)
}

# IoT: Nhiên liệu (L/100km) để xác định kích thước nút
num_trucks = 50
iot_fuel = np.random.normal(30, 5, num_trucks)
iot_fuel_opt = iot_fuel * (1 - 0.15)  # Giảm 15% sau tối ưu
node_sizes = {loc: np.mean(iot_fuel_opt) / 2 for loc in locations}

# Hàm tính chi phí tuyến
def path_cost(path):
    total_distance = 0
    total_emissions = 0
    for i in range(len(path) - 1):
        edge_data = G.get_edge_data(path[i], path[i+1])
        total_distance += edge_data['distance']
        total_emissions += edge_data['distance'] * edge_data['emissions_factor']
    return total_distance, total_emissions

# Tuyến truyền thống và tối ưu
traditional_path = ['Hanoi', 'Hai Phong', 'Da Nang', 'HCMC', 'Cai Mep Port']
trad_distance, trad_emissions = path_cost(traditional_path)

def emissions_heuristic(u, v):
    return 0
optimized_path = nx.astar_path(G, 'Hanoi', 'Cai Mep Port', heuristic=emissions_heuristic,
                              weight=lambda u, v, d: d['distance'] * d['emissions_factor'])
opt_distance, opt_emissions = path_cost(optimized_path)

# Dữ liệu cho biểu đồ 3D
x_nodes = [coords[loc][0] for loc in locations]
y_nodes = [coords[loc][1] for loc in locations]
z_nodes = [coords[loc][2] for loc in locations]
node_text = [f"{loc}<br>Fuel: {node_sizes[loc]:.2f} L/100km" for loc in locations]

# Cạnh truyền thống
x_trad, y_trad, z_trad = [], [], []
for i in range(len(traditional_path) - 1):
    x_trad.extend([coords[traditional_path[i]][0], coords[traditional_path[i+1]][0], None])
    y_trad.extend([coords[traditional_path[i]][1], coords[traditional_path[i+1]][1], None])
    z_trad.extend([coords[traditional_path[i]][2], coords[traditional_path[i+1]][2], None])

# Cạnh tối ưu
x_opt, y_opt, z_opt = [], [], []
for i in range(len(optimized_path) - 1):
    x_opt.extend([coords[optimized_path[i]][0], coords[optimized_path[i+1]][0], None])
    y_opt.extend([coords[optimized_path[i]][1], coords[optimized_path[i+1]][1], None])
    z_opt.extend([coords[optimized_path[i]][2], coords[optimized_path[i+1]][2], None])

# Reverse Logistics
x_reverse = [coords['HCMC'][0], coords['Hanoi'][0]]
y_reverse = [coords['HCMC'][1], coords['Hanoi'][1]]
z_reverse = [coords['HCMC'][2], coords['Hanoi'][2]]

# Vẽ biểu đồ 3D
fig = go.Figure()

# Vẽ nút
fig.add_trace(go.Scatter3d(
    x=x_nodes, y=y_nodes, z=z_nodes, mode='markers+text',
    marker=dict(size=[node_sizes[loc] for loc in locations], color='lightblue', opacity=0.8),
    text=node_text, textposition='top center', name='Locations'
))

# Vẽ cạnh truyền thống
fig.add_trace(go.Scatter3d(
    x=x_trad, y=y_trad, z=z_trad, mode='lines',
    line=dict(color='red', width=3), name='Traditional Route'
))

# Vẽ cạnh tối ưu
fig.add_trace(go.Scatter3d(
    x=x_opt, y=y_opt, z=z_opt, mode='lines',
    line=dict(color='green', width=3), name='Optimized Route'
))

# Vẽ reverse logistics
fig.add_trace(go.Scatter3d(
    x=x_reverse, y=y_reverse, z=z_reverse, mode='lines+markers',
    line=dict(color='purple', width=2, dash='dash'),
    marker=dict(size=5, symbol='circle'), name='Reverse Logistics'
))

# Thêm chú thích văn bản trong không gian 3D
fig.add_trace(go.Scatter3d(
    x=[coords['HCMC'][0]], y=[coords['HCMC'][1]], z=[coords['HCMC'][2] + 5],  # Dịch lên để dễ thấy
    mode='text', text=['Reverse Flow Start'], textposition='top center',
    textfont=dict(size=12, color='purple'), name='Reverse Annotation'
))

# Cập nhật bố cục
fig.update_layout(
    title="3D Simulation of Smart Green Logistics Ecosystem in Vietnam",
    scene=dict(
        xaxis_title="X (Relative Position)",
        yaxis_title="Y (Relative Position)",
        zaxis_title="Emissions (kg CO2)",
        aspectmode='manual', aspectratio=dict(x=1, y=2, z=0.5)
    ),
    showlegend=True
)

# In kết quả
print("Traditional Route:", traditional_path)
print(f"Distance: {trad_distance:.2f} km, Emissions: {trad_emissions:.2f} kg CO2")
print("Optimized Route:", optimized_path)
print(f"Distance: {opt_distance:.2f} km, Emissions: {opt_emissions:.2f} kg CO2")
print(f"Savings: Distance {(trad_distance - opt_distance) / trad_distance * 100:.2f}%, "
      f"Emissions {(trad_emissions - opt_emissions) / trad_emissions * 100:.2f}%")

# Lưu biểu đồ dưới dạng HTML
fig.write_html("logistics_3d_simulation.html")
fig.show()