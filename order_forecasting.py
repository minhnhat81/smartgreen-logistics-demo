import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt
import math

df = pd.read_csv('train.csv')  # Thay đường dẫn nếu cần
df['date'] = pd.to_datetime(df['date'])
df = df.groupby('date')['sales'].sum().reset_index()
df = df.rename(columns={'date': 'ds', 'sales': 'y'})

model = Prophet(daily_seasonality=True, yearly_seasonality=True)
model.fit(df)

future = model.make_future_dataframe(periods=30)
forecast = model.predict(future)

fig = model.plot(forecast)
plt.title('Dự báo nhu cầu đơn hàng')
plt.show()

current_inventory = 1000
forecast_next_7_days = forecast['yhat'].tail(7).sum()
if forecast_next_7_days > current_inventory:
    print(f"Cảnh báo: Tồn kho thấp! Dự báo sales 7 ngày: {forecast_next_7_days:.2f}. Cần tái đặt hàng.")
else:
    print("Tồn kho ổn định.")

holding_cost = 0.5
ordering_cost = 100
demand = forecast['yhat'].tail(30).sum()
optimal_qty = math.sqrt(2 * demand * ordering_cost / holding_cost)
print(f"Số lượng đặt hàng tối ưu (EOQ): {optimal_qty:.2f}")