import streamlit as st
from github import Github, GithubException

def enviar_para_github_streamlit(uploaded_file, repo_name, github_token, github_path):
    """
    Envia um arquivo (PBIT) para um repositório GitHub a partir do Streamlit.

    Parameters:
    - uploaded_file: arquivo do Streamlit (st.file_uploader)
    - repo_name: str, no formato 'usuario/repositorio'
    - github_token: str, token com permissão repo/public_repo
    - github_path: str, caminho no repositório (ex: 'modelos/meu_modelo.pbit')
    """
    if uploaded_file is None:
        st.error("Nenhum arquivo foi carregado.")
        return False

    try:
        # Conectar ao GitHub
        g = Github(github_token)
        repo = g.get_repo(repo_name)
    except GithubException as e:
        st.error(f"Erro ao acessar o repositório: {e}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return False

    try:
        # Ler conteúdo do arquivo
        content = uploaded_file.getvalue()  # bytes

        # Verifica se o arquivo já existe
        try:
            existing_file = repo.get_contents(github_path)
            # Atualiza o arquivo existente
            repo.update_file(
                path=github_path,
                message=f"Atualização do arquivo {uploaded_file.name}",
                content=content,
                sha=existing_file.sha
            )
            st.success(f"Arquivo atualizado com sucesso no GitHub: {github_path}")
        except GithubException:
            # Cria novo arquivo
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
