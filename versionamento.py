import streamlit as st
import zipfile, json
from github import Github, GithubException

# -----------------------------
# Função para extrair DataModel do PBIT
# -----------------------------
def carregar_data_model(uploaded_file):
    uploaded_file.seek(0)
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
            if old_c.get("description","") != new_c.get("description",""):
                changes.append("descrição")
            if old_c.get("dataType","") != new_c.get("dataType",""):
                changes.append("tipo")
            if changes:
                report["modified"].append(f"Coluna modificada em {tname}.{cname}: {', '.join(changes)}")

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
                changes.append("DAX")
            if old_m.get("description","") != new_m.get("description",""):
                changes.append("descrição")
            if changes:
                report["modified"].append(f"Medida modificada em {tname}.{mname}: {', '.join(changes)}")

    return report

# -----------------------------
# Função para enviar arquivo para GitHub
# -----------------------------
def enviar_para_github(uploaded_file, repo_name, token, github_path):
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    # Garantir que o ponteiro do arquivo esteja no início
    uploaded_file.seek(0)
    content = uploaded_file.read()

    try:
        existing_file = repo.get_contents(github_path)
        repo.update_file(
            path=github_path,
            message=f"Atualizando {uploaded_file.name}",
            content=content,
            sha=existing_file.sha
        )
        return f"Arquivo atualizado no GitHub: {github_path}"
    except GithubException as e:
        if e.status == 404:
            repo.create_file(
                path=github_path,
                message=f"Enviando novo arquivo {uploaded_file.name}",
                content=content
            )
            return f"Arquivo enviado para GitHub: {github_path}"
        else:
            raise e

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📊 Versionamento e Auditoria de PBIT")

# Uploads
pbit_file = st.file_uploader("📂 Carregue o PBIT Atual", type=["pbit"])
previous_pbit_file = st.file_uploader("📂 Carregue o PBIT Anterior (para comparação)", type=["pbit"])

# GitHub inputs
st.subheader("💾 GitHub (opcional)")
github_token = st.text_input("Token", type="password")
github_repo = st.text_input("Repositório (user/repo)")
github_path = st.text_input("Caminho no repositório")

if st.button("📌 Analisar"):
    if pbit_file:
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
            st.write(report["modified"] or "Nenhum")
        else:
            st.info("Nenhum PBIT anterior fornecido, apenas carregado o modelo atual.")

        # Envio para GitHub
        if github_token and github_repo and github_path:
            msg = enviar_para_github(pbit_file, github_repo, github_token, github_path)
            st.success(msg)
