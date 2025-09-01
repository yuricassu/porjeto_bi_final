# -----------------------------
# Instalar dependências
# -----------------------------

import zipfile, json, re, io
import pandas as pd
import streamlit as st
from github import Github

# -----------------------------
# Funções auxiliares
# -----------------------------
DAX_REF_PATTERN = re.compile(r"'?([A-Za-z0-9_ ]+)'?\[([A-Za-z0-9_ ]+)\]")

def extract_table_column_refs_from_text(text):
    used = set()
    if not text:
        return used
    if isinstance(text, list):
        text = "\n".join(text)
    if not isinstance(text, str):
        return used
    for m in DAX_REF_PATTERN.finditer(text):
        if m.group(1) and m.group(2):
            used.add((m.group(1).strip(), m.group(2).strip()))
    return used

def load_model_json(pbit_file):
    with zipfile.ZipFile(pbit_file, "r") as z:
        return json.loads(z.read("DataModelSchema"))

def extract_model_info(model_json):
    tables = model_json.get("model", {}).get("tables", [])
    relationships = model_json.get("model", {}).get("relationships", [])
    measure_list = []
    for t in tables:
        tname = t["name"]
        for m in t.get("measures", []):
            expr = m.get("expression", "")
            if isinstance(expr, list):
                expr = "\n".join(expr)
            measure_list.append({"table": tname, "measure": m["name"], "expression": expr})
    return tables, relationships, measure_list

# -----------------------------
# Função de comparação
# -----------------------------
def compare_models(pbit1, pbit2):
    model1 = load_model_json(pbit1)
    model2 = load_model_json(pbit2)
    
    tables1, rels1, measures1 = extract_model_info(model1)
    tables2, rels2, measures2 = extract_model_info(model2)
    
    # Tabelas adicionadas ou removidas
    t1 = set([t["name"] for t in tables1])
    t2 = set([t["name"] for t in tables2])
    added_tables = t2 - t1
    removed_tables = t1 - t2
    
    # Medidas adicionadas ou removidas
    m1 = set([(m["table"], m["measure"]) for m in measures1])
    m2 = set([(m["table"], m["measure"]) for m in measures2])
    added_measures = m2 - m1
    removed_measures = m1 - m2
    
    # Relacionamentos
    r1 = set([(r["fromTable"], r["fromColumn"], r["toTable"], r["toColumn"]) for r in rels1])
    r2 = set([(r["fromTable"], r["fromColumn"], r["toTable"], r["toColumn"]) for r in rels2])
    added_rels = r2 - r1
    removed_rels = r1 - r2
    
    results = {
        "added_tables": pd.DataFrame(list(added_tables), columns=["table"]),
        "removed_tables": pd.DataFrame(list(removed_tables), columns=["table"]),
        "added_measures": pd.DataFrame(list(added_measures), columns=["table","measure"]),
        "removed_measures": pd.DataFrame(list(removed_measures), columns=["table","measure"]),
        "added_relationships": pd.DataFrame(list(added_rels), columns=["fromTable","fromColumn","toTable","toColumn"]),
        "removed_relationships": pd.DataFrame(list(removed_rels), columns=["fromTable","fromColumn","toTable","toColumn"])
    }
    
    return results

# -----------------------------
# Função de envio para GitHub
# -----------------------------
def enviar_para_github(file_path, repo_name, token, github_path):
    g = Github(token)
    repo = g.get_repo(repo_name)
    with open(file_path, "rb") as f:
        content = f.read()
    try:
        file = repo.get_contents(github_path)
        repo.update_file(file.path, f"Atualizando {file_path}", content, file.sha)
        return "Arquivo atualizado no GitHub!"
    except:
        repo.create_file(github_path, f"Enviando novo arquivo {file_path}", content)
        return "Arquivo enviado para GitHub!"

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🔎 Comparação de Modelos Power BI (.pbit)")

pbit_file1 = st.file_uploader("Upload do primeiro arquivo .pbit", type=["pbit"])
pbit_file2 = st.file_uploader("Upload do segundo arquivo .pbit", type=["pbit"])

if pbit_file1 and pbit_file2:
    st.info("Comparando modelos...")
    results = compare_models(pbit_file1, pbit_file2)
    
    st.success("✅ Comparação concluída!")
    
    # Mostrar resultados
    for k, df in results.items():
        st.subheader(k.replace("_", " ").title())
        st.dataframe(df)
    
    # Download do Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for sheet_name, df in results.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    st.download_button("📥 Baixar relatório Excel", data=output, file_name="Comparacao_Modelos.xlsx")
    
    # GitHub
    github_token = st.text_input("Token GitHub", type="password")
    github_repo = st.text_input("Repositório GitHub (usuario/repo)")
    github_path = st.text_input("Caminho dentro do repositório (ex: modelos/meu_modelo.pbit)")
    
    if st.button("📤 Enviar arquivo 2 para GitHub"):
        if github_token and github_repo and github_path:
            msg = enviar_para_github(pbit_file2.name, github_repo, github_token, github_path)
            st.success(msg)
        else:
            st.error("Preencha todos os campos do GitHub!")
