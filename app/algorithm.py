import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from utils.map import *
from sklearn.preprocessing import MinMaxScaler
import os

    
def show():
    # Заголовок Streamlit
    st.title('Визуализация данных GeoJSON с помощью Folium')

    data_folder = 'data'

    # Выбор между проведением анализа и открытием существующей карты
    action = st.radio("Выберите действие:", ('Открыть существующую карту', 'Провести анализ'))

    if action == 'Открыть существующую карту':
        # Получаем список файлов из директории saved_maps
        map_files = os.listdir(os.path.join(data_folder, 'saved_maps'))
        map_name = st.selectbox('Выберите сохраненную карту:', map_files)
        if map_name:
            # Загрузите и отобразите выбранную сохраненную карту
            map_data = load_saved_map(os.path.join(data_folder, 'saved_maps', map_name))
            if map_data is not None:
                folium_static(map_data)
            else:
                st.error('Загрузка карты.')
        else:
            st.info('Выберите сохраненную карту из списка.')

    else:
        # Загрузка данных из файлов GeoJSON
        gdfs = {}
        
        geojson_files = [file for file in os.listdir(data_folder) if file.endswith('.geojson')]

        # Загрузка mun_obr_arctic.geojson всегда
        mun_obr_arctic_file = 'mun_obr_arctic.geojson'
        gdfs['mun_obr_arctic'] = gpd.read_file(os.path.join(data_folder, mun_obr_arctic_file))

        # Убрать mun_obr_arctic.geojson из списка geojson_files, чтобы он не предлагался к выбору
        geojson_files.remove(mun_obr_arctic_file)

        # Получаем список всех доступных сценариев
        scenario_names = sorted(list(scenarios.keys()))

        # Выбираем сценарий с помощью виджета multiselect
        selected_scenarios = st.selectbox('Выберите сценарии:', scenario_names)

        # Создаем пустой словарь для хранения выбранных слоев и их "связей"

        selected_geojson_files = scenarios[selected_scenarios]['layers']

        for file in selected_geojson_files:
            layer_name = os.path.splitext(file)[0]
            gdfs[layer_name] = gpd.read_file(os.path.join(data_folder, file))

        selected_layers = list(gdfs.keys())

        analysis_level = st.radio('Выберите уровень анализа:', ('Region', 'Arctic', 'Municipality'))

        # Определяем размер прогнозируемой области в зависимости от выбранного уровня анализа
        if analysis_level == 'Arctic':
            hex_size = 1.0
        elif analysis_level == 'Region':
            hex_size = 0.7
        elif analysis_level == 'Municipality':
            hex_size = 0.1

        from utils.styles import layer_styles

        updated_layer_styles = {}
        for layer_name, layer_params in layer_styles.items():
            updated_params = layer_params.copy()
            updated_params['lat_offset_range'] *= hex_size
            updated_params['lon_offset_range'] *= hex_size
            updated_layer_styles[layer_name] = updated_params
        layer_styles = updated_layer_styles


        button_agree = False

        region_mapping = {
            "Архангельская область (рекомендуется)": "Архангельская область",
            # Add more region mappings as needed
        }
        # Reverse the mapping to get user-friendly names from actual names
        region_reverse_mapping = {v: k for k, v in region_mapping.items()}
        # Get the set of region names from the DataFrame
        region_names = sorted(set(gdfs['mun_obr_arctic'].region.tolist()))
        # Convert region names to user-friendly names for the dropdown menu
        user_friendly_region_names = [region_reverse_mapping.get(region, region) for region in region_names]


        # Если выбран уровень анализа "Region" или "Municipality", предоставляем выбор региона
        if analysis_level in ('Region', 'Municipality'):
            region_names = sorted(set(gdfs['mun_obr_arctic'].region.tolist()))
            selected_region = st.selectbox('Выберите регион:', user_friendly_region_names)
            selected_region = region_mapping.get(selected_region, selected_region)

            # Если выбран уровень анализа "Municipality", предоставляем выбор муниципалитета
            selected_municipality = None
            if analysis_level == 'Municipality':
                municipalities = set(gdfs['mun_obr_arctic'][gdfs['mun_obr_arctic'].region == selected_region].NAME.tolist())
                selected_municipality = st.selectbox('Выберите муниципалитет:', municipalities)
            analysis_confirmed = True

        if selected_layers and not button_agree:
            if analysis_level == 'Arctic' or analysis_confirmed:
                # Применяем фильтр в зависимости от выбранного уровня анализа
                if analysis_level == 'Arctic':
                    filter_gdf = gdfs['mun_obr_arctic']
                elif analysis_level == 'Region':
                    filter_gdf = gdfs['mun_obr_arctic'][gdfs['mun_obr_arctic']['region'] == selected_region]
                else:
                    filter_gdf = gdfs['mun_obr_arctic'][gdfs['mun_obr_arctic']['NAME'] == selected_municipality]

            st.header('Отображение выбранной области на карте')

            # Create a Folium map centered on the Arctic region
            m_preproc = folium.Map(tiles="Stamen Terrain", location=[60, 50], zoom_start=3)            
            # Add GeoJSON data to the map with layer styling
            folium.GeoJson(
                filter_gdf,
                name='Область',
                style_function=lambda x: {
                    'color': layer_styles['mun_obr_arctic']['color']
                }
            ).add_to(m_preproc)

            # Add LayerControl to the map for selecting layers to display
            folium.LayerControl().add_to(m_preproc)

            # Display the map using Streamlit
            folium_static(m_preproc)

        # Кнопка для подтверждения выбора слоев
        if st.button('Подтвердить выбор слоев'):
            button_agree = True
            if not selected_geojson_files:
                st.warning("Выберите хотя бы один слой для анализа.")
                return
            hexagons = create_hexagons((10, 20, 175, 85), hex_size)
            hexagons = hexagons.to_crs(epsg=3857)
            hexagons = filter_hexagons(hexagons, filter=filter_gdf, level=analysis_level)
            hexagons = hexagons_analyse(hexagons, layers={layer:gdfs[layer] for layer in selected_layers if layer!='mun_obr_arctic'})
            hexagons = gpd.GeoDataFrame(hexagons, geometry='geometry')
            hexagons = hexagons.to_crs(epsg=4326)

            print(hexagons.columns)
            selected_layers = [col for col in hexagons.columns if col not in ['geometry', 'NAME']]
            total_counts = hexagons[selected_layers].copy()

            # Normalizing values from 0 to 10 for each column
            scaler = MinMaxScaler(feature_range=(0, 10))
            for col in selected_layers:
                total_counts['score_' + col] = scaler.fit_transform(total_counts[col].values.reshape(-1, 1))
                hexagons['score_' + col] = total_counts['score_' + col]  # Assigning the normalized values back to 'hexagons'

            # Dropping the original columns, keeping only the normalized ones
            hexagons = hexagons.drop(columns=selected_layers)
            hexagons['score'] = 0

            # Loop through the selected scenarios
            scenario = scenarios[selected_scenarios]
            scenario_layers = scenario['layers']
            scenario_connections = scenario['connections']

            print(selected_layers)
            # Apply scenario multipliers to the values in each column and sum them up
            for layer in scenario_layers:
                if layer.split('.')[0] in selected_layers:
                    hexagons['score'] += hexagons['score_' + layer.split('.')[0]] * scenario_connections[layer]


            m = folium.Map(tiles="Stamen Terrain", location=[60, 40], zoom_start=3)

            # Отображение гексагонов на карте
            
            hexagons = hexagons.sort_values(by='score', ascending=True)
            print(hexagons)
            hexagon_group = folium.FeatureGroup(name='Гексагоны')
            for _, row in hexagons.iterrows():
                print(row['score'])
                sc_h = row['score']
                color = get_color(sc_h, hexagons['score'].max(), hexagons['score'].min())
                popup_text = f"Муниципальный район: {row['NAME']} Score: {sc_h:.1f}"
                print(popup_text)
                folium.GeoJson(row.geometry,
                            style_function=lambda x, color=color: {'fillColor': color},
                            popup=folium.Popup(popup_text, parse_html=True)).add_to(hexagon_group)

            m.add_child(hexagon_group)

            # Получаем топ 10 гексагонов по сумме scaled_count
            hexagons = hexagons.sort_values(by='score', ascending=False)
            top_hexagons = hexagons.head(10)

            # Создаем группу для меток топ 10 гексагонов
            top_marker_group = folium.FeatureGroup(name='Рекомендуемые области для строительства')

            # Добавляем маркеры для каждой из топ 10 точек
            for _, row in top_hexagons.iterrows():
                lat = row['geometry'].centroid.y
                lon = row['geometry'].centroid.x
                popup_text = f"Муниципальный район: {row['NAME']} Score: {row['score']:.1f}"
                folium.Marker(location=[lat, lon],
                            popup=popup_text,
                            icon=folium.Icon(color='black', icon='info-sign')).add_to(top_marker_group)

            # Добавляем группу меток топ 10 гексагонов на карту
            m.add_child(top_marker_group)

            # Add the markers to the corresponding FeatureGroup
            marker_groups = {}
            for layer in selected_layers:
                # Create a separate FeatureGroup for the markers of each layer
                marker_groups[layer] = folium.FeatureGroup(name=f'Метки - {layer}', show=True)
                
                sorting_column = f'score_{layer}'

                top_hexagons_layer = hexagons.sort_values(by=sorting_column, ascending=False)
                for _, row in top_hexagons_layer.head(10).iterrows():
                    lat = row['geometry'].centroid.y
                    lon = row['geometry'].centroid.x
                    
                    # For mean layer, get the mean value
                    if f'mean_{layer}' in hexagons.columns:
                        count_layer = row[sorting_column]
                    else:
                        count_layer = int(row[sorting_column])  # Convert count or sum value to integer

                    # Apply a small random offset to the latitude and longitude based on the layer's offset range
                    lat_offset = layer_styles[layer]['lat_offset_range']
                    lon_offset = layer_styles[layer]['lon_offset_range']

                    lat += lat_offset
                    lon += lon_offset

                    popup_text = f"Муниципальный район\n sсore:{count_layer} {layer_styles[layer]['desc']}"
                    folium.Marker(
                        location=[lat, lon],
                        popup=popup_text,
                        icon=folium.Icon(color=layer_styles[layer]['color'], icon=layer_styles[layer]['icon'])
                    ).add_to(marker_groups[layer])

            for layer, marker_group in marker_groups.items():
                m.add_child(marker_group)

            # Add the layer control to the map
            folium.LayerControl().add_to(m)

            # Display the map using st.pydeck_chart
            folium_static(m)

            st.markdown("Топ районов по общему параметру 'score':")
            table_html = "<table><tr><th>Район</th><th>Общее количество</th><th>Широта</th><th>Долгота</th></tr>"
            for _, row in hexagons.sort_values(by='score', ascending=False).head(10).iterrows():
                lat = row['geometry'].centroid.y
                lon = row['geometry'].centroid.x
                table_html += f'<tr><td>{row["NAME"]}</td><td>{row["score"]:.1f}</td><td>{lat:.1f}</td><td>{lon:.1f}</td></tr>'
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)

            # Create a DataFrame with the top 10 rows for saving as CSV
            top_rows_df = hexagons.sort_values(by='score', ascending=False).head(10)
            # Add the latitude and longitude columns
            top_rows_df['Latitude'] = top_rows_df['geometry'].centroid.y
            top_rows_df['Longitude'] = top_rows_df['geometry'].centroid.x

            # Display the "Сохранить таблицу" button
            if st.button('Сохранить таблицу'):
                # Save the DataFrame as a CSV file
                csv_file = top_rows_df.to_csv(index=False)
                # Provide a link to download the CSV file
                st.download_button(label='Скачать таблицу', data=csv_file, file_name='top_rows_table.csv', mime='text/csv')
