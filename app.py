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
    df = pd.read_pickle('/content/df_roles_chem_prop.pkl')

    # Очистка данных
    df['all_plants'] = df['all_plants'].fillna('')
    df['all_roles'] = df['all_roles'].fillna('')
    df['chebi'] = df['chebi'].fillna('')
    df['chembl'] = df['chembl'].fillna('')
    df['synonyms'] = df['synonyms'].fillna('')
    df['lipinski_pass'] = df['lipinski_pass'].fillna('')
    df['iupac'] = df['iupac'].fillna('')
    df['smiles'] = df['smiles'].fillna('')
    df['image_url'] = df['image_url'].fillna('')

    # Создаем списки для быстрого поиска
    df['roles_list'] = df['all_roles'].apply(
        lambda x: [a.strip() for a in str(x).split(',') if a.strip()]
    )
    df['plants_list'] = df['all_plants'].apply(
        lambda x: [p.strip() for p in str(x).split(',') if p.strip()]
    )

    return df

df = load_data()

# ================== БОКОВАЯ ПАНЕЛЬ ==================
st.sidebar.image("https://img.icons8.com/color/96/000000/plant-under-sun.png", width=80)
st.sidebar.title("🌿 Фитохимическая БД")
st.sidebar.markdown("---")

# Сбор всех уникальных ролей и растений для фильтров
all_roles = sorted(set([r for sublist in df['roles_list'] for r in sublist]))
all_plants = sorted(set([p for sublist in df['plants_list'] for p in sublist]))

# Фильтры в боковой панели
st.sidebar.subheader("🔍 Фильтры")

# Поиск по названию
search_term = st.sidebar.text_input("Поиск по названию", placeholder="Например: Quercetin")

# Фильтр по роли
selected_role = st.sidebar.selectbox(
    "Роль (Duke)",
    ["Все"] + all_roles[:50]
)

# Фильтр по растению
selected_plant = st.sidebar.selectbox(
    "Растение",
    ["Все"] + all_plants[:50]
)

# Статистика
st.sidebar.markdown("---")
st.sidebar.metric("Всего веществ", len(df))
st.sidebar.metric("Уникальных растений", len(all_plants))
st.sidebar.metric("Уникальных ролей", len(all_roles))

# ================== ФИЛЬТРАЦИЯ ==================
filtered_df = df.copy()

if search_term:
    filtered_df = filtered_df[
        filtered_df['name'].str.contains(search_term, case=False, na=False) |
        filtered_df['iupac'].str.contains(search_term, case=False, na=False) |
        filtered_df['synonyms'].str.contains(search_term, case=False, na=False)
    ]

if selected_role != "Все":
    filtered_df = filtered_df[
        filtered_df['roles_list'].apply(lambda x: selected_role in x)
    ]

if selected_plant != "Все":
    filtered_df = filtered_df[
        filtered_df['plants_list'].apply(lambda x: selected_plant in x)
    ]

# ================== ОСНОВНОЙ КОНТЕНТ ==================
st.title("🌿 База данных лекарственных растений РФ")
st.markdown(f"**Найдено веществ: {len(filtered_df)}**")

# Табы для разных представлений
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Карточки веществ",
    "📊 Статистика",
    "🕸️ Граф связей",
    "📈 Аналитика",
    "📐 Физико-химические свойства"
])

# ================== TAB 1: КАРТОЧКИ ==================
with tab1:
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
                        # Картинка соединения
                        if row['image_url']:
                            st.image(row['image_url'], use_column_width=True)

                        st.markdown(f"""
                        <div style="
                            border: 1px solid #ddd;
                            border-radius: 10px;
                            padding: 15px;
                            margin-bottom: 15px;
                            background: white;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            height: 280px;
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
                                <b>💊 Роли:</b> {', '.join(row['roles_list'][:3])}
                                {', ...' if len(row['roles_list']) > 3 else ''}
                            </p>
                            <p style="font-size: 0.85em;">
                                <b>⚗️ MW:</b> {row['MolecularWeight']:.2f} |
                                <b>XLogP:</b> {row['XLogP'] if pd.notna(row['XLogP']) else 'N/A'}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"Подробнее", key=f"btn_{row['InChIKey']}"):
                            st.session_state.selected_compound = row['InChIKey']
                            st.rerun()

# ================== TAB 2: СТАТИСТИКА ==================
with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Топ-20 ролей")
        all_roles_flat = [a for sublist in df['roles_list'] for a in sublist if a]
        role_counts = Counter(all_roles_flat).most_common(20)

        if role_counts:
            fig = px.bar(
                x=[c[1] for c in role_counts],
                y=[c[0] for c in role_counts],
                orientation='h',
                title="Самые частые роли",
                color=[c[1] for c in role_counts],
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

    # Тепловая карта корреляций ролей
    st.subheader("Корреляции ролей (топ-10)")
    top_roles = [act for act, _ in role_counts[:10]]
    co_occurrence = pd.DataFrame(0, index=top_roles, columns=top_roles)

    for _, row in df.iterrows():
        roles = row['roles_list']
        for a1 in roles:
            if a1 in top_roles:
                for a2 in roles:
                    if a2 in top_roles:
                        co_occurrence.loc[a1, a2] += 1

    fig = px.imshow(
        co_occurrence,
        text_auto=True,
        color_continuous_scale='RdBu_r',
        title="Совстречаемость ролей"
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

# ================== TAB 3: ГРАФ СВЯЗЕЙ ==================
with tab3:
    st.subheader("🕸️ Граф связей растений и веществ")

    sample_size = min(50, len(filtered_df))
    sample_df = filtered_df.sample(sample_size, random_state=42)

    G = nx.Graph()

    for _, row in sample_df.iterrows():
        compound_name = row['name']
        G.add_node(compound_name, type='compound')

        for plant in row['plants_list'][:3]:
            G.add_node(plant, type='plant')
            G.add_edge(compound_name, plant, weight=1)

        for role in row['roles_list'][:3]:
            G.add_node(role, type='role')
            G.add_edge(compound_name, role, weight=1)

    pos = nx.spring_layout(G, k=2, iterations=50)

    node_types = {'compound': 'blue', 'plant': 'green', 'role': 'red'}
    edge_traces = []
    node_traces = []

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
        title="Сеть: Вещество → Растение → Роль",
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

    with col1:
        avg_roles = df['roles_list'].apply(len).mean()
        st.metric("Среднее ролей на вещество", f"{avg_roles:.1f}")

    with col2:
        avg_plants = df['plants_list'].apply(len).mean()
        st.metric("Среднее растений на вещество", f"{avg_plants:.1f}")

    with col3:
        coverage = (df['roles_list'].apply(len) > 0).mean() * 100
        st.metric("Покрытие ролями", f"{coverage:.1f}%")

    st.subheader("Распределение количества ролей")
    roles_counts_dist = df['roles_list'].apply(len)
    fig = px.histogram(
        roles_counts_dist,
        nbins=20,
        title="Сколько ролей у веществ",
        labels={'value': 'Количество ролей', 'count': 'Число веществ'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ================== TAB 5: ФИЗИКО-ХИМИЧЕСКИЕ СВОЙСТВА ==================
with tab5:
    st.subheader("📐 Физико-химические свойства веществ")

    properties = [
        "MolecularWeight", "XLogP", "HBondDonorCount", "HBondAcceptorCount",
        "RotatableBondCount", "TPSA", "HeavyAtomCount", "Charge", "Complexity"
    ]

    # Выбор свойств для отображения
    selected_props = st.multiselect(
        "Выберите свойства для отображения",
        properties,
        default=properties
    )

    if selected_props:
        # Таблица с выбранными свойствами
        display_cols = ['name'] + selected_props
        display_df = filtered_df[display_cols].copy()
        display_df = display_df.rename(columns={
            'name': 'Название',
            'MolecularWeight': 'Мол. масса',
            'XLogP': 'XLogP',
            'HBondDonorCount': 'Доноры H-связей',
            'HBondAcceptorCount': 'Акцепторы H-связей',
            'RotatableBondCount': 'Вращаемые связи',
            'TPSA': 'TPSA',
            'HeavyAtomCount': 'Тяжёлые атомы',
            'Charge': 'Заряд',
            'Complexity': 'Сложность'
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            height=500
        )

        # Скачать таблицу
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Скачать таблицу свойств (CSV)",
            data=csv,
            file_name="physchem_properties.csv",
            mime="text/csv"
        )

        # Гистограммы распределения выбранных свойств
        st.subheader("Распределение выбранных свойств")
        n_cols = 2
        n_rows = (len(selected_props) + 1) // n_cols
        fig = make_subplots(
            rows=n_rows, cols=n_cols,
            subplot_titles=selected_props
        )

        for i, prop in enumerate(selected_props):
            r = i // n_cols + 1
            c = i % n_cols + 1
            fig.add_trace(
                go.Histogram(
                    x=filtered_df[prop].dropna(),
                    name=prop,
                    nbinsx=25
                ),
                row=r, col=c
            )

        fig.update_layout(
            height=300 * n_rows,
            showlegend=False,
            title_text="Распределение физико-химических свойств"
        )
        st.plotly_chart(fig, use_container_width=True)

# ================== ДЕТАЛЬНАЯ СТРАНИЦА КОМПОНЕНТА ==================
if 'selected_compound' in st.session_state:
    selected_inkey = st.session_state.selected_compound
    compound = df[df['InChIKey'] == selected_inkey].iloc[0]

    with st.expander(f"📄 Детальная информация: {compound['name']}", expanded=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            # Картинка
            if compound['image_url']:
                st.image(compound['image_url'], width=300)

            st.markdown(f"### {compound['name']}")
            st.markdown(f"**InChIKey:** `{compound['InChIKey']}`")
            st.markdown(f"**PubChem CID:** {compound['pubchem_cid']}")

            if compound['chebi']:
                st.markdown(f"**CHEBI:** {compound['chebi']}")
            if compound['chembl']:
                st.markdown(f"**ChEMBL:** {compound['chembl']}")
            if compound['iupac']:
                st.markdown(f"**IUPAC:** {compound['iupac']}")
            if compound['smiles']:
                st.markdown(f"**SMILES:** `{compound['smiles']}`")
            if compound['synonyms']:
                st.markdown(f"**Синонимы:** {compound['synonyms']}")

            # Физико-химические свойства
            st.markdown("### 📐 Физико-химические свойства")
            props_df = pd.DataFrame({
                'Свойство': [
                    'Молекулярная масса', 'XLogP', 'TPSA', 'Сложность',
                    'Заряд', 'Доноры H-связей', 'Акцепторы H-связей',
                    'Вращаемые связи', 'Тяжёлые атомы'
                ],
                'Значение': [
                    f"{compound['MolecularWeight']:.2f}",
                    compound['XLogP'] if pd.notna(compound['XLogP']) else 'N/A',
                    f"{compound['TPSA']:.2f}",
                    compound['Complexity'],
                    compound['Charge'],
                    compound['HBondDonorCount'],
                    compound['HBondAcceptorCount'],
                    compound['RotatableBondCount'],
                    compound['HeavyAtomCount']
                ]
            })
            st.table(props_df)

            if compound['lipinski_pass']:
                st.markdown(f"**Lipinski pass:** {compound['lipinski_pass']}")

        with col2:
            st.markdown("### 🌱 Растения")
            for plant in compound['plants_list']:
                st.markdown(f"- {plant}")

            st.markdown("### 💊 Роли")
            for role in compound['roles_list']:
                st.markdown(f"- {role}")

        if st.button("Закрыть", key="close_detail"):
            del st.session_state.selected_compound
            st.rerun()

# ================== ИНСТРУКЦИИ ==================
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Инструкция:**
1. Используйте фильтры слева
2. Нажмите "Подробнее" на карточке
3. Исследуйте статистику, граф и свойства
""")

# Кнопка для экспорта
if st.sidebar.button("📥 Экспорт отфильтрованных данных"):
    csv = filtered_df[['name', 'InChIKey', 'all_plants', 'all_roles']].to_csv(index=False)
    st.sidebar.download_button(
        label="Скачать CSV",
        data=csv,
        file_name="filtered_compounds.csv",
        mime="text/csv"
    )