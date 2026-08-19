import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import networkx as nx
from collections import Counter
import re

# ================== НАСТРОЙКА СТРАНИЦЫ ==================
st.set_page_config(
    page_title="Фитохимическая база данных РФ",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== ЗАГРУЗКА ДАННЫХ ==================
@st.cache_data
def load_data():
    # Замените на ваш путь к файлу
    df = pd.read_pickle('sub_df_100.pkl')

    # Очистка данных
    df['all_plants'] = df['all_plants'].fillna('')
    df['chebi_roles'] = df['chebi_roles'].fillna('')
    df['activity'] = df['activity'].fillna('')

    # Создаем список активностей для быстрого поиска
    df['activities_list'] = df['activity'].apply(
        lambda x: [a.strip() for a in str(x).split(',') if a.strip()]
    )
    df['plants_list'] = df['all_plants'].apply(
        lambda x: [p.strip() for p in str(x).split(',') if p.strip()]
    )
    df['chebi_list'] = df['chebi_roles'].apply(
        lambda x: [r.strip() for r in str(x).split(';') if r.strip()]
    )

    return df

df = load_data()

# ================== БОКОВАЯ ПАНЕЛЬ ==================
st.sidebar.image("https://img.icons8.com/color/96/000000/plant-under-sun.png", width=80)
st.sidebar.title("🌿 Фитохимическая БД")
st.sidebar.markdown("---")

# Сбор всех уникальных активностей и растений для фильтров
all_activities = sorted(set([a for sublist in df['activities_list'] for a in sublist]))
all_plants = sorted(set([p for sublist in df['plants_list'] for p in sublist]))
all_chebi_roles = sorted(set([r for sublist in df['chebi_list'] for r in sublist]))

# Фильтры в боковой панели
st.sidebar.subheader("🔍 Фильтры")

# Поиск по названию
search_term = st.sidebar.text_input("Поиск по названию", placeholder="Например: Quercetin")

# Фильтр по активности
selected_activity = st.sidebar.selectbox(
    "Активность (Duke)",
    ["Все"] + all_activities[:50]  # Ограничим для скорости
)

# Фильтр по растению
selected_plant = st.sidebar.selectbox(
    "Растение",
    ["Все"] + all_plants[:50]
)

# Фильтр по CHEBI роли
selected_chebi = st.sidebar.selectbox(
    "CHEBI роль",
    ["Все"] + all_chebi_roles[:50]
)

# Статистика
st.sidebar.markdown("---")
st.sidebar.metric("Всего веществ", len(df))
st.sidebar.metric("Уникальных растений", len(all_plants))
st.sidebar.metric("Уникальных активностей", len(all_activities))

# ================== ФИЛЬТРАЦИЯ ==================
filtered_df = df.copy()

if search_term:
    filtered_df = filtered_df[
        filtered_df['name'].str.contains(search_term, case=False, na=False) |
        filtered_df['iupac'].str.contains(search_term, case=False, na=False)
    ]

if selected_activity != "Все":
    filtered_df = filtered_df[
        filtered_df['activities_list'].apply(lambda x: selected_activity in x)
    ]

if selected_plant != "Все":
    filtered_df = filtered_df[
        filtered_df['plants_list'].apply(lambda x: selected_plant in x)
    ]

if selected_chebi != "Все":
    filtered_df = filtered_df[
        filtered_df['chebi_list'].apply(lambda x: selected_chebi in x)
    ]

# ================== ОСНОВНОЙ КОНТЕНТ ==================
st.title("🌿 База данных лекарственных растений РФ")
st.markdown(f"**Найдено веществ: {len(filtered_df)}**")

# Табы для разных представлений
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Карточки веществ",
    "📊 Статистика",
    "🕸️ Граф связей",
    "📈 Аналитика"
])

# ================== TAB 1: КАРТОЧКИ ==================
with tab1:
    # Настройка отображения карточек
    cols_per_row = 3
    num_items = len(filtered_df)

    for i in range(0, num_items, cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            idx = i + j
            if idx < num_items:
                row = filtered_df.iloc[idx]

                with cols[j]:
                    with st.container():
                        st.markdown(f"""
                        <div style="
                            border: 1px solid #ddd;
                            border-radius: 10px;
                            padding: 15px;
                            margin-bottom: 15px;
                            background: white;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            height: 300px;
                            overflow-y: auto;
                        ">
                            <h4 style="margin-top: 0; color: #2c3e50;">{row['name']}</h4>
                            <p style="font-size: 0.9em; color: #7f8c8d;">
                                <b>InChIKey:</b> {row['InChIKey'][:20]}...
                            </p>
                            <p style="font-size: 0.85em;">
                                <b>🌱 Растения:</b> {', '.join(row['plants_list'][:3])}
                                {', ...' if len(row['plants_list']) > 3 else ''}
                            </p>
                            <p style="font-size: 0.85em;">
                                <b>💊 Активности:</b> {', '.join(row['activities_list'][:3])}
                                {', ...' if len(row['activities_list']) > 3 else ''}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Кнопка "Подробнее"
                        if st.button(f"Подробнее", key=f"btn_{row['InChIKey']}"):
                            st.session_state.selected_compound = row['InChIKey']
                            st.rerun()

# ================== TAB 2: СТАТИСТИКА ==================
with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Топ-20 активностей")
        # Собираем все активности
        all_acts = [a for sublist in df['activities_list'] for a in sublist if a]
        act_counts = Counter(all_acts).most_common(20)

        if act_counts:
            fig = px.bar(
                x=[c[1] for c in act_counts],
                y=[c[0] for c in act_counts],
                orientation='h',
                title="Самые частые активности",
                color=[c[1] for c in act_counts],
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Топ-20 растений")
        all_plants_flat = [p for sublist in df['plants_list'] for p in sublist if p]
        plant_counts = Counter(all_plants_flat).most_common(20)

        if plant_counts:
            fig = px.bar(
                x=[c[1] for c in plant_counts],
                y=[c[0] for c in plant_counts],
                orientation='h',
                title="Самые частые растения",
                color=[c[1] for c in plant_counts],
                color_continuous_scale='Plasma'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    # Тепловая карта корреляций активностей
    st.subheader("Корреляции активностей (топ-10)")
    # Берем топ-10 активностей и строим матрицу совстречаемости
    top_acts = [act for act, _ in act_counts[:10]]
    co_occurrence = pd.DataFrame(0, index=top_acts, columns=top_acts)

    for _, row in df.iterrows():
        acts = row['activities_list']
        for a1 in acts:
            if a1 in top_acts:
                for a2 in acts:
                    if a2 in top_acts:
                        co_occurrence.loc[a1, a2] += 1

    fig = px.imshow(
        co_occurrence,
        text_auto=True,
        color_continuous_scale='RdBu_r',
        title="Совстречаемость активностей"
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

# ================== TAB 3: ГРАФ СВЯЗЕЙ ==================
with tab3:
    st.subheader("🕸️ Граф связей растений и веществ")

    # Ограничим количество для производительности
    sample_size = min(50, len(filtered_df))
    sample_df = filtered_df.sample(sample_size, random_state=42)

    # Строим граф
    G = nx.Graph()

    # Добавляем узлы
    for _, row in sample_df.iterrows():
        compound_name = row['name']
        G.add_node(compound_name, type='compound')

        # Добавляем растения
        for plant in row['plants_list'][:3]:  # Ограничим для красоты
            G.add_node(plant, type='plant')
            G.add_edge(compound_name, plant, weight=1)

        # Добавляем активности
        for activity in row['activities_list'][:3]:
            G.add_node(activity, type='activity')
            G.add_edge(compound_name, activity, weight=1)

    # Визуализация графа
    pos = nx.spring_layout(G, k=2, iterations=50)

    # Создаем трассы для разных типов узлов
    node_types = {'compound': 'blue', 'plant': 'green', 'activity': 'red'}
    edge_traces = []
    node_traces = []

    # Рёбра
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_traces.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            showlegend=False
        ))

    # Узлы
    for node_type, color in node_types.items():
        nodes = [n for n, d in G.nodes(data=True) if d.get('type') == node_type]
        x = [pos[n][0] for n in nodes]
        y = [pos[n][1] for n in nodes]

        node_traces.append(go.Scatter(
            x=x, y=y,
            mode='markers+text',
            text=nodes,
            textposition="top center",
            marker=dict(size=15, color=color, line=dict(width=2, color='white')),
            name=node_type,
            hoverinfo='text',
            hovertext=nodes
        ))

    fig = go.Figure(data=edge_traces + node_traces)
    fig.update_layout(
        title="Сеть: Вещество → Растение → Активность",
        showlegend=True,
        height=700,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    st.plotly_chart(fig, use_container_width=True)

# ================== TAB 4: АНАЛИТИКА ==================
with tab4:
    st.subheader("📈 Аналитические инсайты")

    col1, col2, col3 = st.columns(3)

    # Метрики
    with col1:
        avg_activities = df['activities_list'].apply(len).mean()
        st.metric("Среднее активностей на вещество", f"{avg_activities:.1f}")

    with col2:
        avg_plants = df['plants_list'].apply(len).mean()
        st.metric("Среднее растений на вещество", f"{avg_plants:.1f}")

    with col3:
        coverage = (df['activities_list'].apply(len) > 0).mean() * 100
        st.metric("Покрытие активностями", f"{coverage:.1f}%")

    # Распределение
    st.subheader("Распределение количества активностей")
    act_counts_dist = df['activities_list'].apply(len)
    fig = px.histogram(
        act_counts_dist,
        nbins=20,
        title="Сколько активностей у веществ",
        labels={'value': 'Количество активностей', 'count': 'Число веществ'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ================== ДЕТАЛЬНАЯ СТРАНИЦА КОМПОНЕНТА ==================
# Проверяем, выбран ли компонент для детального просмотра
if 'selected_compound' in st.session_state:
    selected_inkey = st.session_state.selected_compound
    compound = df[df['InChIKey'] == selected_inkey].iloc[0]

    # Модальное окно с деталями
    with st.expander(f"📄 Детальная информация: {compound['name']}", expanded=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"### {compound['name']}")
            st.markdown(f"**InChIKey:** `{compound['InChIKey']}`")
            st.markdown(f"**PubChem CID:** {compound['pubchem_cid']}")
            st.markdown(f"**CHEBI:** {compound['chebi']}")
            st.markdown(f"**ChEMBL:** {compound['chembl']}")

            if compound['iupac']:
                st.markdown(f"**IUPAC:** {compound['iupac']}")

            if compound['smiles']:
                st.markdown(f"**SMILES:** `{compound['smiles']}`")

        with col2:
            st.markdown("### 🌱 Растения")
            for plant in compound['plants_list']:
                st.markdown(f"- {plant}")

            st.markdown("### 💊 Активности")
            for activity in compound['activities_list']:
                st.markdown(f"- {activity}")

            if compound['chebi_list']:
                st.markdown("### 🧪 CHEBI роли")
                for role in compound['chebi_list'][:5]:
                    st.markdown(f"- {role}")

        # Кнопка закрытия
        if st.button("Закрыть", key="close_detail"):
            del st.session_state.selected_compound
            st.rerun()

# ================== ИНСТРУКЦИИ ==================
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Инструкция:**
1. Используйте фильтры слева
2. Нажмите "Подробнее" на карточке
3. Исследуйте статистику и граф
""")

# Кнопка для экспорта
if st.sidebar.button("📥 Экспорт отфильтрованных данных"):
    csv = filtered_df[['name', 'InChIKey', 'all_plants', 'activity']].to_csv(index=False)
    st.sidebar.download_button(
        label="Скачать CSV",
        data=csv,
        file_name="filtered_compounds.csv",
        mime="text/csv"
    )
