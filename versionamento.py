import streamlit as st
from github import Github, GithubException
import tempfile
import difflib

st.title("Versionamento e Envio de PBIT para GitHub")

# -----------------------------
# Upload de arquivos PBIT
# -----------------------------
st.header("Carregar versão atual do PBIT")
uploaded_file = st.file_uploader("Escolha o arquivo PBIT atual", type="pbit", key="current")

st.header("Carregar versão anterior do PBIT (opcional para comparação)")
previous_file = st.file_uploader("Escolha a versão anterior do PBIT", type="pbit", key="previous")

st.header("Configurações do GitHub")
repo_name = st.text_input("Repositório GitHub (usuario/repositorio)")
github_token = st.text_input("Token GitHub", type="password")
github_path = st.text_input("Caminho no repositório (ex: modelos/meu_modelo.pbit)")

# -----------------------------
# Função de comparação
# -----------------------------
def comparar_pbits(file_current, file_previous):
    """
    Compara dois arquivos PBIT linha a linha (como texto JSON dentro do DataModelSchema)
    Retorna uma lista de diferenças
    """
    import zipfile, json

    # Função interna para extrair JSON do DataModelSchema
    def extrair_schema(pbit_bytes):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(pbit_bytes)
            tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "r") as z:
            data = z.read("DataModelSchema").decode("utf-8")
        return data.splitlines()

    current_lines = extrair_schema(file_current.getvalue())
    previous_lines = extrair_schema(file_previous.getvalue())

    diff = list(difflib.unified_diff(previous_lines, current_lines, lineterm=''))
    return diff

# -----------------------------
# Função de envio para GitHub
# -----------------------------
def enviar_para_github(uploaded_file, repo_name, github_token, github_path):
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
            st.success(f"Arquivo atualizado com sucesso no GitHub: {github_path}")
        except GithubException:
            repo.create_file(
                path=github_path,
                message=f"Upload do arquivo {uploaded_file.name}",
                content=content
            )
            st.success(f"Arquivo enviado com sucesso para o GitHub: {github_path}")
        return True
    except GithubException as e:
        st.error(f"Erro ao criar/atualizar o arquivo no GitHub: {e}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado ao enviar para GitHub: {e}")
        return False

# -----------------------------
# Ações do usuário
# -----------------------------
if st.button("Comparar PBITs"):
    if uploaded_file and previous_file:
        diff = comparar_pbits(uploaded_file, previous_file)
        if not diff:
            st.success("Não foram encontradas diferenças entre os arquivos.")
        else:
            st.warning(f"Foram encontradas {len(diff)} linhas diferentes:")
            st.text("\n".join(diff[:1000]))  # mostra até 1000 linhas de diferença
    else:
        st.info("Envie os dois arquivos PBIT para comparar.")

if st.button("Enviar PBIT para GitHub"):
    enviar_para_github(uploaded_file, repo_name, github_token, github_path)
