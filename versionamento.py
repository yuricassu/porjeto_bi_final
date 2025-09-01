import streamlit as st
import zipfile, json
from github import Github, GithubException
from git import Repo
import tempfile
import os

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
            changes = []
            if old_c.get("description","") != new_c.get("description",""):
                changes.append("descrição")
            if old_c.get("dataType","") != new_c.get("dataType",""):
                changes.append("tipo")
            if changes:
                report["modified"].append(f"Coluna modificada em {tname}.{cname}: {', '.join(changes)}")

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
# Função para enviar arquivo grande via Git + LFS
# -----------------------------
def enviar_para_github_lfs(uploaded_file, repo_url, branch="main", commit_msg=None):
    if not uploaded_file or not repo_url:
        st.warning("Forneça o arquivo e a URL do repositório Git.")
        return

    commit_msg = commit_msg or f"Atualizando {uploaded_file.name}"

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "repo")
        try:
            repo = Repo.clone_from(repo_url, repo_path, branch=branch)
        except:
            st.info("Repositório já clonado ou não existe localmente, tentando abrir...")
            repo = Repo(repo_path)
            repo.git.checkout(branch)
            repo.remotes.origin.pull()

        # Salvar arquivo
        file_path = os.path.join(repo_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        # Adicionar ao Git, commit e push
        repo.git.add(file_path)
        repo.index.commit(commit_msg)
        repo.remotes.origin.push()

    st.success(f"✅ Arquivo {uploaded_file.name} enviado com sucesso via Git + LFS!")

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📊 Versionamento e Auditoria de PBIT")

# Uploads
pbit_file = st.file_uploader("📂 Carregue o PBIT Atual", type=["pbit"])
previous_pbit_file = st.file_uploader("📂 Carregue o PBIT Anterior (para comparação)", type=["pbit"])

# GitHub inputs
st.subheader("💾 GitHub (opcional) - Use Git + LFS para arquivos grandes")
github_repo_url = st.text_input("URL do repositório Git (HTTPS ou SSH)")
branch = st.text_input("Branch", value="main")

if st.button("📌 Analisar e Enviar"):
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

        # Envio para GitHub via LFS
        if github_repo_url:
            enviar_para_github_lfs(pbit_file, github_repo_url, branch)
