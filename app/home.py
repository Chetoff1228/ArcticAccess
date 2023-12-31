import streamlit as st

def show():
    # Информация о проекте ArcticAccess и преимуществах
    st.subheader('Проект Arctic Access')
    st.write('Мы команда Ikanam и наш проект постарается изменить нашу жизнь к лучшему.')
    st.write('Проект Arctic Access - это инновационный сервис, разработанный для оптимизации размещения городских объектов с учетом транспортной доступности в Арктической зоне.')
    st.write('Мы используем алгоритмы машинного обучения и продвинутый анализ данных, чтобы определить оптимальное местоположение объектов и предоставить вам визуализацию карты регионов и городов в удобном для вас формате.')
    st.write('Здесь вы можете производить анализ и управление вашими урбанистическими картами в формате GeoJSON.')

    # Вставка изображения из Google Диска через Google Drive Viewer
    img_id = '1EjiWvfJOEJpixQSpHpKoAt8N-3IJX6x5'  # Замените на идентификатор вашего изображения
    img_url = f'https://drive.google.com/uc?export=view&id={img_id}'
    st.image(img_url, caption='Проект Arctic Access', use_column_width=True)