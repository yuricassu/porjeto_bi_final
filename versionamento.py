import streamlit as st
import zipfile, json
import pandas as pd
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

        # Colunas modificadas (descrição ou tipo)
        for cname in set(old_cols) & set(new_cols):
            old_c, new_c = old_cols[cname], new_cols[cname]
            changes = []
            old_val = {}
            new_val = {}
            if old_c.get("description","") != new_c.get("description",""):
                changes.append("descrição")
                old_val["description"] = old_c.get("description","")
                new_val["description"] = new_c.get("description","")
            if old_c.get("dataType","") != new_c.get("dataType",""):
                changes.append("tipo")
                old_val["dataType"] = old_c.get("dataType","")
                new_val["dataType"] = new_c.get("dataType","")
            if changes:
                report["modified"].append({
                    "item": f"Coluna {tname}.{cname}",
                    "alteracoes": ", ".join(changes),
                    "versao_antiga": old_val,
                    "versao_nova": new_val
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
            old_val = {}
            new_val = {}
            if old_m.get("expression","") != new_m.get("expression",""):
                changes.append("DAX")
                old_val["expression"] = old_m.get("expression","")
                new_val["expression"] = new_m.get("expression","")
            if old_m.get("description","") != new_m.get("description",""):
                changes.append("descrição")
                old_val["description"] = old_m.get("description","")
                new_val["description"] = new_m.get("description","")
            if changes:
                report["modified"].append({
                    "item": f"Medida {tname}.{mname}",
                    "alteracoes": ", ".join(changes),
                    "versao_antiga": old_val,
                    "versao_nova": new_val
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
    if not pbit_file:
        st.warning("Carregue o PBIT atual.")
    else:
        new_model = carregar_data_model(pbit_file)
        if previous_pbit_file:
            old_model = carregar_data_model(previous_pbit_file)
            report = comparar_modelos(old_model, new_model)

            st.subheader("🔍 Relatório de Alterações")

            st.write("### Adicionados")
            st.write(report["added"] or "Nenhum")

            st.write("### Removidos")
            st.write(report["removed"] or "Nenhum")

            st.write("### Modificados")
            if report["modified"]:
                df_mod = pd.DataFrame([
                    {
                        "Item": m["item"],
                        "Alterações": m["alteracoes"],
                        "Versão Antiga": str(m["versao_antiga"]),
                        "Versão Nova": str(m["versao_nova"])
                    }
                    for m in report["modified"]
                ])
                st.dataframe(df_mod)
            else:
                st.write("Nenhum item modificado.")

            # -----------------------------
            # Exportar para Excel
            # -----------------------------
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                pd.DataFrame(report["added"], columns=["Adicionados"]).to_excel(writer, sheet_name="Adicionados", index=False)
                pd.DataFrame(report["removed"], columns=["Removidos"]).to_excel(writer, sheet_name="Removidos", index=False)
                if report["modified"]:
                    df_mod.to_excel(writer, sheet_name="Modificados", index=False)
                workbook = writer.book

                # Ajuste de largura das colunas
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    df = df_mod if sheet_name == "Modificados" else pd.DataFrame(report[sheet_name.lower()], columns=[sheet_name])
                    for idx, col in enumerate(df.columns):
                        max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(idx, idx, max_len)

            output.seek(0)
            st.download_button(
                label="⬇️ Baixar relatório completo em Excel",
                data=output,
                file_name="Auditoria_PBIT.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Nenhum PBIT anterior fornecido, apenas carregado o modelo atual.")

