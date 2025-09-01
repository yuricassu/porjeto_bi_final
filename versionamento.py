import streamlit as st
import zipfile, json
import pandas as pd
import altair as alt

# -----------------------------
# Função para extrair DataModel do PBIT
# -----------------------------
def carregar_data_model(uploaded_file):
    with zipfile.ZipFile(uploaded_file, "r") as z:
        data_model = json.loads(z.read("DataModelSchema"))
    return data_model.get("model", {})

# -----------------------------
# Função para comparar dois modelos
# -----------------------------
def comparar_modelos(old_model, new_model):
    report = {"added": [], "removed": [], "modified": []}

    old_tables = {t["name"]: t for t in old_model.get("tables", [])}
    new_tables = {t["name"]: t for t in new_model.get("tables", [])}

    # Tabelas adicionadas/retiradas
    added_tables = set(new_tables) - set(old_tables)
    removed_tables = set(old_tables) - set(new_tables)
    report["added"].extend([f"Tabela adicionada: {t}" for t in added_tables])
    report["removed"].extend([f"Tabela removida: {t}" for t in removed_tables])

    # Tabelas existentes → checar colunas/medidas
    for tname in set(old_tables) & set(new_tables):
        old_t, new_t = old_tables[tname], new_tables[tname]

        old_cols = {c["name"]: c for c in old_t.get("columns", [])}
        new_cols = {c["name"]: c for c in new_t.get("columns", [])}

        # Colunas adicionadas/retiradas
        added_cols = set(new_cols) - set(old_cols)
        removed_cols = set(old_cols) - set(new_cols)
        report["added"].extend([f"Coluna adicionada em {tname}: {c}" for c in added_cols])
        report["removed"].extend([f"Coluna removida em {tname}: {c}" for c in removed_cols])

        # Colunas modificadas
        for cname in set(old_cols) & set(new_cols):
            old_c, new_c = old_cols[cname], new_cols[cname]
            changes = []
            if old_c.get("description","") != new_c.get("description",""):
                changes.append(f"descrição: '{old_c.get('description','')}' → '{new_c.get('description','')}'")
            if old_c.get("dataType","") != new_c.get("dataType",""):
                changes.append(f"tipo: {old_c.get('dataType','')} → {new_c.get('dataType','')}")
            if changes:
                report["modified"].append({
                    "tipo": "Coluna",
                    "tabela": tname,
                    "nome": cname,
                    "alteracoes": ", ".join(changes)
                })

        # Medidas adicionadas/retiradas/modificadas
        old_measures = {m["name"]: m for m in old_t.get("measures", [])}
        new_measures = {m["name"]: m for m in new_t.get("measures", [])}

        added_measures = set(new_measures) - set(old_measures)
        removed_measures = set(old_measures) - set(new_measures)
        report["added"].extend([f"Medida adicionada em {tname}: {m}" for m in added_measures])
        report["removed"].extend([f"Medida removida em {tname}: {m}" for m in removed_measures])

        for mname in set(old_measures) & set(new_measures):
            old_m, new_m = old_measures[mname], new_measures[mname]
            changes = []
            if old_m.get("expression","") != new_m.get("expression",""):
                changes.append(f"DAX alterado: '{old_m.get('expression','')}' → '{new_m.get('expression','')}'")
            if old_m.get("description","") != new_m.get("description",""):
                changes.append(f"descrição: '{old_m.get('description','')}' → '{new_m.get('description','')}'")
            if changes:
                report["modified"].append({
                    "tipo": "Medida",
                    "tabela": tname,
                    "nome": mname,
                    "alteracoes": ", ".join(changes)
                })

    return report

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📊 Versionamento e Auditoria de PBIT")

# Uploads
pbit_file = st.file_uploader("📂 Carregue o PBIT Atual", type=["pbit"])
previous_pbit_file = st.file_uploader("📂 Carregue o PBIT Anterior (para comparação)", type=["pbit"])

if st.button("📌 Analisar"):
    if pbit_file:
        new_model = carregar_data_model(pbit_file)
        if previous_pbit_file:
            old_model = carregar_data_model(previous_pbit_file)
            report = comparar_modelos(old_model, new_model)

            # -----------------------------
            # Dashboard Resumido
            # -----------------------------
            st.subheader("📊 Resumo de Alterações")
            df_summary = pd.DataFrame({
                "Categoria": ["Adicionados", "Removidos", "Modificados"],
                "Quantidade": [len(report["added"]), len(report["removed"]), len(report["modified"])]
            })
            chart = alt.Chart(df_summary).mark_bar().encode(
                x=alt.X('Categoria', sort=None),
                y='Quantidade',
                color='Categoria'
            ).properties(width=600, height=400, title="Resumo de Alterações no Modelo")
            st.altair_chart(chart)

            # -----------------------------
            # Relatório Detalhado
            # -----------------------------
            st.subheader("🔍 Relatório de Alterações Detalhado")
            st.write("### Adicionados")
            st.write(report["added"] or "Nenhum")
            st.write("### Removidos")
            st.write(report["removed"] or "Nenhum")

            st.write("### Modificados")
            if report["modified"]:
                df_mod = pd.DataFrame(report["modified"])
                # Destaque visual usando st.dataframe
                st.dataframe(df_mod, use_container_width=True)
            else:
                st.write("Nenhum")
        else:
            st.info("Nenhum PBIT anterior fornecido, apenas carregado o modelo atual.")
