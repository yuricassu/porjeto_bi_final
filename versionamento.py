# -----------------------------
# Instalar dependências (apenas se necessário)
# -----------------------------
# !pip install streamlit PyGithub pandas openpyxl xlsxwriter

import streamlit as st
import pandas as pd
import zipfile
import json
import re
from github import Github, GithubException

# -----------------------------
# Funções auxiliares para auditoria
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

def audit_model(pbit_file):
    results = {
        "unused_columns": [],
        "duplicate_measures": [],
        "missing_descriptions": [],
        "orphan_tables": []
    }

    with zipfile.ZipFile(pbit_file, "r") as z:
        model_json = json.loads(z.read("DataModelSchema"))

    tables = model_json.get("model", {}).get("tables", [])
    relationships = model_json.get("model", {}).get("relationships", [])

    measure_list = []
    used_in_measures = set()

    for t in tables:
        tname = t["name"]
        for c in t.get("columns", []):
            cname = c["name"]
            desc = c.get("description", "")
            if not desc:
                results["missing_descriptions"].append((tname, cname))
        for m in t.get("measures", []):
            mname = m["name"]
            expr = m.get("expression", "") or ""
            if isinstance(expr, list):
                expr = "\n".join(expr)
            desc = m.get("description", "")
            measure_list.append({"table": tname, "measure": mname, "expression": expr, "desc": desc})
            used_in_measures |= extract_table_column_refs_from_text(expr)
            if not desc:
                results["missing_descriptions"].append((tname, mname))

    for t in tables:
        tname = t["name"]
        for c in t.get("columns", []):
            cname = c["name"]
            from_list = [(r.get("fromTable"), r.get("fromColumn")) for r in relationships]
            to_list = [(r.get("toTable"), r.get("toColumn")) for r in relationships]
            if (tname, cname) not in used_in_measures and \
               (tname, cname) not in from_list and \
               (tname, cname) not in to_list:
                results["unused_columns"].append((tname, cname))

    expr_map = {}
    for m in measure_list:
        expr = m["expression"] or ""
        norm_expr = expr.strip().replace(" ", "").lower()
        if norm_expr in expr_map:
            results["duplicate_measures"].append((expr_map[norm_expr], m))
        else:
            expr_map[norm_expr] = m

    related_tables = set([r["fromTable"] for r in relationships] + [r["toTable"] for r in relationships])
    for t in tables:
        if t["name"] not in related_tables:
            results["orphan_tables"].append(t["name"])

    results_df = {
        "unused_columns": pd.DataFrame(results["unused_columns"], columns=["table", "column"]),
        "duplicate_measures": pd.DataFrame([
            {"table1": m1["table"], "measure1": m1["measure"], 
             "table2": m2["table"], "measure2": m2["measure"], 
             "expression": m1["expression"]}
            for m1, m2 in results["duplicate_measures"]
        ]),
        "missing_descriptions": pd.DataFrame(results["missing_descriptions"], columns=["table", "name"]),
        "orphan_tables": pd.DataFrame(results["orphan_tables"], columns=["table"])
    }

    return results_df, tables, measure_list

# -----------------------------
# Função para envio ao GitHub
# -----------------------------
def enviar_para_github_streamlit(uploaded_file, repo_name, github_token, github_path):
    if uploaded_file is None:
        st.error("Nenhum arquivo foi carregado.")
        return False

    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)
    except GithubException as e:
        st.error(f"Erro ao acessar o repositório: {e}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return False

    try:
        content = uploaded_file.getvalue()

        try:
            existing_file = repo.get_contents(github_path)
            repo.update_file(
                path=github_path,
                message=f"Atualização do arquivo {uploaded_file.name}",
                content=content,
                sha=existing_file.sha
            )
            st.success(f"Arquivo atualizado no GitHub: {github_path}")
        except GithubException:
            repo.create_file(
                path=github_path,
                message=f"Upload do arquivo {uploaded_file.name}",
                content=content
            )
            st.success(f"Arquivo enviado ao GitHub: {github_path}")

        return True

    except GithubException as e:
        st.error(f"Erro ao criar/atualizar o arquivo no GitHub: {e}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado ao enviar para GitHub: {e}")
        return False

# -----------------------------
# Interface Streamlit
# -----------------------------
st.title("Versionamento e Auditoria de PBIT")

uploaded_file = st.file_uploader("Selecione o arquivo PBIT", type="pbit")

if uploaded_file:
    st.write(f"Arquivo carregado: {uploaded_file.name}")

    # Auditoria básica
    if st.button("Executar Auditoria"):
        results_df, tables, measures = audit_model(uploaded_file)
        st.write("### Resultado da Auditoria")
        for key, df in results_df.items():
            st.write(f"**{key}**")
            st.dataframe(df)

    # Envio para GitHub
    st.write("---")
    st.write("### Enviar para GitHub")
    repo_name = st.text_input("Repositório GitHub (usuario/repositorio)")
    github_token = st.text_input("Token GitHub", type="password")
    github_path = st.text_input("Caminho no repositório (ex: modelos/meu_modelo.pbit)")

    if st.button("Enviar para GitHub"):
        enviar_para_github_streamlit(uploaded_file, repo_name, github_token, github_path)
