import json
import streamlit as st
import folium
import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np
from streamlit_folium import folium_static
import pydeck as pdk
import pandas as pd


# Функция для загрузки сохраненной карты и отображения на карте
def load_saved_map(map_name):
    gdf = gpd.read_file(map_name)
    min_latitude = st.number_input('Минимальная широта', value=20.0, step=1.0)
    max_latitude = st.number_input('Максимальная широта', value=90.0, step=1.0)
    min_longitude = st.number_input('Минимальная долгота', value=35.0, step=1.0)
    max_longitude = st.number_input('Максимальная долгота', value=80.0, step=1.0)
    m = folium.Map(location=[(min_latitude + max_latitude) / 2, (min_longitude + max_longitude) / 2], zoom_start=4)

    folium.GeoJson(gdf, name='my_map').add_to(m)
    folium.LayerControl().add_to(m)

    folium_static(m)

# Функция для создания гексагонов внутри указанных границ
def create_hexagons(bounds, hex_size):
    minx, miny, maxx, maxy = bounds
    x_step = 2 * hex_size
    y_step = np.sqrt(3) * hex_size
    x_start = minx - x_step
    y_start = miny - y_step
    x_end = maxx + x_step
    y_end = maxy + y_step

    hexagons = []
    y = y_start
    row_count = 0
    while y < y_end:
        x = x_start + (0 if row_count % 2 == 0 else hex_size * (3/2))
        col_count = 0
        while x < x_end:
            if row_count % 2 == 0:
                y_offset = 0
            else:
                y_offset = hex_size * np.sqrt(3) / 2

            poly_coords = [
                (x + hex_size * np.cos(angle), y + hex_size * np.sin(angle))
                for angle in np.arange(0, 2 * np.pi, 2 * np.pi / 6)
            ]
            hexagon = Polygon(poly_coords)
            hexagons.append(hexagon)
            x += hex_size * 3
            col_count += 1
        y += hex_size * np.sqrt(3) / 2
        row_count += 1


    hexagons_gdf = gpd.GeoDataFrame(geometry=hexagons, crs='EPSG:4326')
    return hexagons_gdf

# Function to filter hexagons based on intersections with a GeoDataFrame
def filter_hexagons(hexagons, filter, level):
    if level == 'Arctic':
        # Фильтрация для всей Арктики
        joined_hexagons = gpd.sjoin(hexagons, filter, op='intersects')
    elif level == 'Region':
        # Фильтрация для выбранного региона
        joined_hexagons = gpd.sjoin(hexagons, filter, op='intersects')
    elif level == 'Municipality':
        # Фильтрация для выбранного муниципалитета (оставляем только 1 муниципалитет)
        joined_hexagons = gpd.sjoin(hexagons, filter, op='intersects')
    joined_hexagons = joined_hexagons[~joined_hexagons.duplicated('geometry')].reset_index(drop=True)[['geometry', 'NAME']]
    return joined_hexagons
def filter_hexagons(hexagons, filter, level):
    joined_hexagons = gpd.sjoin(hexagons, filter, op='intersects')
    joined_hexagons = joined_hexagons[~joined_hexagons.duplicated('geometry')].reset_index(drop=True)[['geometry', 'NAME']]  # Добавляем столбец 'NAME' с названиями муниципалитетов
    return joined_hexagons

# Function to count valuable resources occurrences within each hexagon
def hexagons_analyse(hexagons, layers):
    # Создаем геометрию точек для каждого слоя и объединяем в единый GeoDataFrame
    points_list = []
    for layer_name, layer_gdf in layers.items():
        if layer_name in ['buildings']:
            layer_gdf['layer_name'] = layer_name
            layer_gdf = layer_gdf[['layer_name', 'geometry', 'year']]
            layer_gdf = layer_gdf[layer_gdf.year>0]
            points_gdf = layer_gdf.explode()
            points_list.append(points_gdf)
        elif layer_name in ['base_obl_people_3000']:
            layer_gdf['layer_name'] = layer_name
            layer_gdf = layer_gdf[['layer_name', 'geometry', 'people']]
            points_gdf = layer_gdf.explode()
            points_list.append(points_gdf)
        else:
            layer_gdf['layer_name'] = layer_name
            layer_gdf = layer_gdf[['layer_name', 'geometry']]
            points_gdf = layer_gdf.explode()
            points_list.append(points_gdf) 
        
    points_gdf_all = pd.concat(points_list, ignore_index=True)
    # Выполняем пространственное объединение, чтобы получить точки в каждом гексагоне
    joined_gdf = gpd.sjoin(hexagons, points_gdf_all)

    mean_g = joined_gdf[['geometry', 'layer_name', 'year', 'people', 'NAME']].groupby(['geometry', 'NAME', 'layer_name']).mean().reset_index()
    mean_g = mean_g.set_index('geometry')[['year', 'NAME']].dropna()
    mean_g.columns = ['buildings', 'NAME']


    sum_g = joined_gdf[['geometry', 'layer_name', 'year', 'people', 'NAME']].groupby(['geometry', 'NAME', 'layer_name']).sum().reset_index()
    sum_g = sum_g.set_index('geometry')[['people', 'NAME']].dropna()
    sum_g.columns = ['base_obl_people_3000', 'NAME']


    #size_g = size_g[[i for i in size_g.columns if i not in ['year', 'people']]]
    size_g = joined_gdf[['geometry', 'layer_name', 'NAME']].groupby(['geometry', 'NAME', 'layer_name']).size().reset_index(name='count')
    size_g = size_g.pivot(index='geometry', columns='layer_name', values='count')
    print(size_g)
    size_g = size_g[[i for i in size_g.columns if i not in ['buildings', 'base_obl_people_3000']]]
    print(size_g)

    pivot_all = pd.concat([mean_g, sum_g, size_g])
    pivot_all = pivot_all.reset_index()
    print(pivot_all)
    merged_df = pivot_all.merge(hexagons, on='geometry', how='outer').fillna(0)

    merged_df.drop(columns='NAME_x', inplace=True)
    merged_df.rename(columns={'NAME_y': 'NAME'}, inplace=True)

    # Опционально, чтобы убрать дубликаты колонок с суффиксами "_x" и "_y"
    merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
    sorted_df = merged_df.sort_values(by=list(merged_df.columns.difference(['geometry'])), ascending=False)

    # Удалите дубликаты строк после первого встречания по столбцу 'geometry'
    final_df = sorted_df.drop_duplicates(subset='geometry', keep='first')

    for col in final_df.columns.tolist():
        if (final_df[col] == 0).all():
        # Если все значения равны 0, то удалите данную колонку из DataFrame
            final_df.drop(columns=col, inplace=True)
    print(final_df)
    print(final_df.describe())
    
    return final_df


    
# Функция для получения цвета в зависимости от значения
def get_color(value, max_c, min_c):
    min_value = min_c
    max_value = max_c  # Максимальное значение числа полезных ископаемых (по вашему усмотрению)
    norm_value = (value - min_value) / (max_value - min_value)
    r = int(255 * (1 - norm_value))
    g = int(255 * norm_value)
    b = 0  # Since we always want blue component to be 0
    return f'#{r:02X}{g:02X}{b:02X}'


def update_map_coordinates(lat, lon):
    map_center = [lat, lon]
    map.pydeck_view = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=6,
        max_zoom=16,
        pitch=0,
        bearing=0,
    )
    map.pydeck_layers[0].data = hexagons.to_json()

scenarios = {
        "Размещение образовательного учреждения": {
            "layers": ["objects_education.geojson", "base_obl_people_3000.geojson", "buildings.geojson", "slow_roads_lines.geojson"],
            "connections": {
                "objects_education.geojson": -1,
                "base_obl_people_3000.geojson": 2,
                "buildings.geojson": 1.5,
                "slow_roads_lines.geojson": 1
            }
        },
        "Размещение медицинского учреждения": {
            "layers": ["objects_zdrav.geojson", "base_obl_people_3000.geojson", "buildings.geojson", "slow_roads_lines.geojson"],
            "connections": {
                "objects_zdrav.geojson": -1,
                "base_obl_people_3000.geojson": 2,
                "buildings.geojson": 1.5,
                "slow_roads_lines.geojson":1
            }
        },
        "Туристический объект": {
            "layers": ["objects_tourism.geojson", "buildings.geojson", "base_obl_people_3000.geojson", "slow_roads_lines.geojson", "polezn_iskop.geojson"],
            "connections": {
                "objects_tourism.geojson": 2.5,
                "buildings.geojson": -1,
                "base_obl_people_3000.geojson": 1.5,
                "slow_roads_lines.geojson" : -1,
                "polezn_iskop.geojson": -0.5
                
            }
        },
        "Объект промышленности": {
            "layers": ["polezn_iskop.geojson", "base_obl_people_3000.geojson", "buildings.geojson", "objects_tourism.geojson", "slow_roads_lines.geojson"],
            "connections": {
                "polezn_iskop.geojson": 3,
                "base_obl_people_3000.geojson": 1,
                "buildings.geojson": 1.5,
                "objects_tourism.geojson": -1,
                "slow_roads_lines.geojson": -2,
            }
        },
        "Строительство новых районов": {
            "layers": ["slow_roads_lines.geojson", "buildings.geojson", "base_obl_people_3000.geojson", "objects_education.geojson", "objects_zdrav.geojson"],
            "connections": {
                "slow_roads_lines.geojson": -1,
                "buildings.geojson": -3,
                "base_obl_people_3000.geojson": 2,
                "objects_education.geojson": 1,
                "objects_zdrav.geojson": 1,

            }
        }
    }