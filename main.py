from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)
API_KEY = 'MJDSksW210iojZGUWQeDpLuCZHGGhT6N'
#http://127.0.0.1:5000/

# оординаты по названию города
def get_location_key(city_name):
    try:
        url = f"http://dataservice.accuweather.com/locations/v1/cities/search?apikey={API_KEY}&q={city_name}&language=ru"
        response = requests.get(url)
        print(f"Запрос LocationKey URL: {url}")
        print(f"Статус ответа: {response.status_code}")
        print(f"Ответ: {response.text}")
        # Проверяем статус ответа
        response.raise_for_status()
        data = response.json()
        if len(data) > 0:
            return data[0]['Key']
        else:
            return {"error": "Город не найден. Пожалуйста, проверьте правильность ввода."}

    # Обработка превышения лимита запросов
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 503:
            return {"error": "Превышен лимит запросов на сервере AccuWeather. Попробуйте позже."}
        return {"error": f"Ошибка HTTP: {http_err}"}

    # Общая ошибка запроса
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных о городе: {e}")
        return {"error": "Невозможно получить данные о городе."}


# Функция для получения данных о погоде по локации
def get_weather_data(location_key):
    try:
        forecast_url = f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}?apikey={API_KEY}&metric=true"
        forecast_response = requests.get(forecast_url)
        print(f"Запрос Forecast URL: {forecast_url}")
        print(f"Статус ответа: {forecast_response.status_code}")
        print(f"Ответ: {forecast_response.text}")
        # Проверяем статус ответа
        forecast_response.raise_for_status()
        return forecast_response.json()

    except requests.exceptions.HTTPError as http_err:
        if forecast_response.status_code == 503:
            return {"error": "Превышен лимит запросов на сервере AccuWeather. Попробуйте позже."}
        return {"error": f"Ошибка HTTP: {http_err}"}

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных о прогнозе: {e}")
        return {"error": "Невозможно получить данные о прогнозе. Введите города на русском языке с заглавной буквы."}


def process_weather_data(data):
    if data and 'DailyForecasts' in data:
        daily_forecast = data['DailyForecasts'][0]
        print(f"Daily Forecast: {daily_forecast}")
        temperature_max = daily_forecast['Temperature']['Maximum']['Value']
        temperature_min = daily_forecast['Temperature']['Minimum']['Value']
        average_temperature = (temperature_max + temperature_min) / 2

        rain_probability_day = 100 if daily_forecast['Day'].get('HasPrecipitation', False) else 0
        rain_probability_night = 100 if daily_forecast['Night'].get('HasPrecipitation', False) else 0
        average_rain_probability = (rain_probability_day + rain_probability_night) / 2

        wind_speed_day = daily_forecast['Day'].get('Wind', {}).get('Speed', {}).get('Value', 0)
        wind_speed_night = daily_forecast['Night'].get('Wind', {}).get('Speed', {}).get('Value', 0)
        average_wind_speed = (wind_speed_day + wind_speed_night) / 2

        weather_info = {
            'average_temperature': average_temperature,
            'average_wind_speed': average_wind_speed,
            'average_rain_probability': average_rain_probability,
        }
        print(f"Processed Weather Info: {weather_info}")
        return weather_info
    else:
        print("Invalid weather data received.")
        return "Не удалось получить данные о погоде."


# Функция для проверки благоприятности погодных условий
def check_bad_weather(temperature, wind_speed, rain_probability):
    if temperature < -20 or temperature > 35:
        return "Неблагоприятные условия: экстремальная температура."
    if wind_speed > 50:
        return "Неблагоприятные условия: сильный ветер."
    if rain_probability > 70:
        return "Неблагоприятные условия: высокая вероятность осадков."
    return "Погодные условия благоприятны."

@app.route('/weather_evaluation', methods=['GET'])
def weather_evaluation():
    # Пример данных
    evaluation = {
        'evaluation': "Погодные условия благоприятны",
        'temperature': "20 °C",
        'wind_speed': "5 км/ч",
        'rain_probability': "10%"
    }
    return jsonify(evaluation)

# Маршрут для отображения формы и обработки POST-запроса
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_city = request.form['start_city']
        end_city = request.form['end_city']
        # Получаем локацию для начальной и конечной точки
        start_location_key = get_location_key(start_city)
        end_location_key = get_location_key(end_city)

        if "error" in start_location_key:
            return render_template('index.html', error=start_location_key["error"])
        if "error" in end_location_key:
            return render_template('index.html', error=end_location_key["error"])

        # Данные о погоде для стартовой и финишной точки
        start_weather = get_weather_data(start_location_key)
        end_weather = get_weather_data(end_location_key)

        if "error" in start_weather:
            return render_template('index.html', error=start_weather["error"])
        if "error" in end_weather:
            return render_template('index.html', error=end_weather["error"])

        # Обрабатываем данные для начальной и конечной точки
        start_processed = process_weather_data(start_weather)
        end_processed = process_weather_data(end_weather)

        if isinstance(start_processed, str):
            return render_template('index.html', error=start_processed)
        if isinstance(end_processed, str):
            return render_template('index.html', error=end_processed)

        # Получаем оценки для начальной и конечной точки
        start_evaluation = check_bad_weather(start_processed['average_temperature'], start_processed['average_wind_speed'], start_processed['average_rain_probability'])
        end_evaluation = check_bad_weather(end_processed['average_temperature'], end_processed['average_wind_speed'], end_processed['average_rain_probability'])

        result = {
            'evaluation': f"{start_city}: {start_evaluation}, {end_city}: {end_evaluation}",
            'temperature': f"{start_city}: {start_processed['average_temperature']} °C, {end_city}: {end_processed['average_temperature']} °C",
            'wind_speed': f"{start_city}: {start_processed['average_wind_speed']} км/ч, {end_city}: {end_processed['average_wind_speed']} км/ч",
            'rain_probability': f"{start_city}: {start_processed['average_rain_probability']} %, {end_city}: {end_processed['average_rain_probability']} %"
        }

        return render_template('index.html', result=result)

    return render_template('index.html')


# Запуск Flask
if __name__ == '__main__':
    app.run(debug=True)
