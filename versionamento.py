import streamlit as st
import zipfile, json
from github import Github, GithubException

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
# Função para enviar arquivo para GitHub (robusta)
# -----------------------------
def enviar_para_github_streamlit(uploaded_file, repo_name, token, github_path):
    if not uploaded_file or not repo_name or not token or not github_path:
        st.warning("Preencha todos os campos de GitHub (token, repositório e caminho).")
        return

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
    except GithubException as e:
        st.error(f"Erro ao acessar o repositório: {e.data.get('message', str(e))}")
        return
    except Exception as e:
        st.error(f"Erro inesperado ao conectar ao GitHub: {str(e)}")
        return

    try:
        uploaded_file.seek(0)
        content = uploaded_file.read()
        # Verifica se o arquivo já existe
        existing_file = repo.get_contents(github_path)
        # Atualiza arquivo existente
        repo.update_file(
            path=github_path,
            message=f"Atualizando {uploaded_file.name}",
            content=content,
            sha=existing_file.sha
        )
        st.success(f"Arquivo atualizado com sucesso: {github_path}")
    except GithubException as e:
        if e.status == 404:
            # Arquivo não existe → criar
            try:
                repo.create_file(
                    path=github_path,
                    message=f"Enviando novo arquivo {uploaded_file.name}",
                    content=content
                )
                st.success(f"Arquivo enviado com sucesso: {github_path}")
            except GithubException as e2:
                st.error(f"Erro ao criar arquivo: {e2.data.get('message', str(e2))}")
        elif e.status == 403:
            st.error("Erro de permissão: verifique o token e o acesso ao repositório.")
        else:
            st.error(f"Erro GitHub: {e.data.get('message', str(e))}")
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")

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
            enviar_para_github_streamlit(pbit_file, github_repo, github_token, github_path)

