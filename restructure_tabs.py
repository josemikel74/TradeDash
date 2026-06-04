import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the tabs list
tabs_old = """    tabs = st.tabs([
        "Dashboard Principal", 
        "Gráficos Interactivos", 
        "Agentes", 
        "Supervisor", 
        "Historial/Riesgo", 
        "Memoria y Evolución",
        "Gestión de Datos y Calibración de Memoria",
        "Configuración", 
        "Operación en Curso",
        "Filosofía Génesis",
        "📖 Acerca / Guía"
    ])"""

tabs_new = """    tabs = st.tabs([
        "Dashboard Principal", 
        "Gráficos Interactivos", 
        "Agentes", 
        "Memoria y Evolución",
        "Gestión de Datos y Calibración de Memoria",
        "Configuración", 
        "Operación en Curso",
        "Filosofía Génesis",
        "📖 Acerca / Guía"
    ])"""

content = content.replace(tabs_old, tabs_new)

# 2. Extract contents of tabs[3], tabs[4], tabs[6]
# Let's find their start indices using re or simple string search
idx_3 = content.find("    with tabs[3]:")
idx_4 = content.find("    with tabs[4]:")
idx_5 = content.find("    with tabs[5]:")
idx_6 = content.find("    with tabs[6]:")
idx_7 = content.find("    with tabs[7]:")
idx_8 = content.find("    with tabs[8]:")
idx_9 = content.find("    with tabs[9]:")
idx_10 = content.find("    with tabs[10]:")

if idx_3 == -1 or idx_4 == -1 or idx_5 == -1 or idx_6 == -1:
    print("Error finding tabs")
    import sys
    sys.exit(1)

content_3 = content[idx_3 + len("    with tabs[3]:"):idx_4]
content_4 = content[idx_4 + len("    with tabs[4]:"):idx_5]
content_6 = content[idx_6 + len("    with tabs[6]:"):idx_7]

# Let's strip them slightly if necessary, but preserving them is fine.
# We will construct new tab 4 from old tab 6 + old tab 3 + old tab 4
new_tab_4 = content_6 + "\n        st.divider()\n" + content_3 + "\n        st.divider()\n" + content_4

# We have to rebuild the file from 0-3... wait, tab[5] becomes tab[3], tab[6] becomes tab[4], etc.
part_before_3 = content[:idx_3]
content_5 = content[idx_5 + len("    with tabs[5]:"):idx_6]
content_7 = content[idx_7 + len("    with tabs[7]:"):idx_8]
content_8 = content[idx_8 + len("    with tabs[8]:"):idx_9]
content_9 = content[idx_9 + len("    with tabs[9]:"):idx_10]
content_10 = content[idx_10 + len("    with tabs[10]:"):]

new_content = (
    part_before_3 + 
    "    with tabs[3]:" + content_5 +
    "    with tabs[4]:" + new_tab_4 +
    "    with tabs[5]:" + content_7 +
    "    with tabs[6]:" + content_8 +
    "    with tabs[7]:" + content_9 +
    "    with tabs[8]:" + content_10
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done")
