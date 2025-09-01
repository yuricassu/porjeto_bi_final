import streamlit as st
import zipfile, json
import pandas as pd
import altair as alt
from io import BytesIO

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

    added_tables = set(new_tables) - set(old_tables)
    removed_tables = set(old_tables) - set(new_tables)
    report["added"].extend([f"Tabela adicionada: {t}" for t in added_tables])
    report["removed"].extend([f"Tabela removida: {t}" for t in removed_tables])

    for tname in set(old_tables) & set(new_tables):
        old_t, new_t = old_tables[tname], new_tables[tname]

        old_cols = {c["name"]: c for c in old_t.get("columns", [])}
        new_cols = {c["name"]: c for c in new_t.get("columns", [])}

        added_cols = set(new_cols) - set(old_cols)
        removed_cols = set(old_cols) - set(new_cols)
        report["added"].extend([f"Coluna adicionada em {tname}: {c}" for c in added_cols])
        report["removed"].extend([f"Coluna removida em {tname}: {c}" for c in removed_cols])

        for cname in set(old_cols) & set(new_cols):
            old_c, new_c = old_cols[cname], new_cols[cname]
            if old_c.get("description","") != new_c.get("description",""):
                report["modified"].append({
                    "tipo": "Coluna",
                    "tabela": tname,
                    "nome": cname,
                    "alteracao_tipo": "descrição",
                    "valor_antigo": old_c.get("description",""),
                    "valor_novo": new_c.get("description","")
                })
            if old_c.get("dataType","") != new_c.get("dataType",""):
                report["modified"].append({
                    "tipo": "Coluna",
                    "tabela": tname,
                    "nome": cname,
                    "alteracao_tipo": "tipo",
                    "valor_antigo": old_c.get("dataType",""),
                    "valor_novo": new_c.get("dataType","")
                })

        old_measures = {m["name"]: m for m in old_t.get("measures", [])}
        new_measures = {m["name"]: m for m in new_t.get("measures", [])}

        added_measures = set(new_measures) - set(old_measures)
        removed_measures = set(old_measures) - set(new_measures)
        report["added"].extend([f"Medida adicionada em {tname}: {m}" for m in added_measures])
        report["removed"].extend([f"Medida removida em {tname}: {m}" for m in removed_measures])

        for mname in set(old_measures) & set(new_measures):
            old_m, new_m = old_measures[mname], new_measures[mname]
            if old_m.get("expression","") != new_m.get("expression",""):
                report["modified"].append({
                    "tipo": "Medida",
                    "tabela": tname,
                    "nome": mname,
                    "alteracao_tipo": "DAX",
                    "valor_antigo": old_m.get("expression",""),
                    "valor_novo": new_m.get("expression","")
                })
            if old_m.get("description","") != new_m.get("description",""):
                report["modified"].append({
                    "tipo": "Medida",
                    "tabela": tname,
                    "nome": mname,
                    "alteracao_tipo": "descrição",
                    "valor_antigo": old_m.get("description",""),
                    "valor_novo": new_m.get("description","")
                })

    return report

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📊 Versionamento e Auditoria de PBIT")

pbit_file = st.file_uploader("📂 Carregue o PBIT Atual", type=["pbit"])
previous_pbit_file = st.file_uploader("📂 Carregue o PBIT Anterior (para comparação)", type=["pbit"])

if st.button("📌 Analisar") and pbit_file:
    new_model = carregar_data_model(pbit_file)

    if previous_pbit_file:
        old_model = carregar_data_model(previous_pbit_file)
        report = comparar_modelos(old_model, new_model)

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

        st.subheader("🔍 Relatório Detalhado")
        st.write("### Adicionados")
        st.write(report["added"] or "Nenhum")
        st.write("### Removidos")
        st.write(report["removed"] or "Nenhum")

        st.write("### Modificados")
        if report["modified"]:
            df_mod = pd.DataFrame(report["modified"])
            st.dataframe(df_mod, use_container_width=True)

            # -----------------------------
            # Gerar Excel formatado
            # -----------------------------
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Abas separadas
                pd.DataFrame(report["added"], columns=["Adicionados"]).to_excel(writer, sheet_name="Adicionados", index=False)
                pd.DataFrame(report["removed"], columns=["Removidos"]).to_excel(writer, sheet_name="Removidos", index=False)
                df_mod.to_excel(writer, sheet_name="Modificados", index=False)

                workbook = writer.book
                for sheet in writer.sheets.values():
                    for idx, col in enumerate(sheet.get_default_row_height() for _ in df_mod.columns):
                        sheet.set_column(idx, idx, 25)
                writer.save()
            output.seek(0)

            st.download_button(
                label="⬇️ Baixar relatório completo em Excel",
                data=output,
                file_name="Auditoria_PBIT.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    else:
        st.info("Nenhum PBIT anterior fornecido, apenas carregado o modelo atual.")


