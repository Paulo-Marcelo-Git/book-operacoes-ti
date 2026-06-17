"""Localiza e baixa a planilha mais recente da pasta do Google Drive.

Usa Service Account (job headless). A pasta do Drive precisa estar COMPARTILHADA
com o e-mail da service account (acesso de leitor).
"""
import fnmatch
import io
from pathlib import Path

from . import config
from .logging_setup import get_logger

log = get_logger()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_path = config.BASE_DIR / config.GDRIVE_SA_JSON
    if not sa_path.exists():
        raise FileNotFoundError(
            f"Service account não encontrada em {sa_path}. "
            "Gere o JSON no Google Cloud e compartilhe a pasta do Drive com o e-mail dela."
        )
    creds = service_account.Credentials.from_service_account_file(str(sa_path), scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def baixar(destino_dir=None) -> Path:
    """Baixa o xlsx mais recente que casa com GDRIVE_FILE_PATTERN. Retorna o caminho local."""
    destino_dir = Path(destino_dir or config.OUTPUT_DIR)
    svc = _service()

    query = (f"'{config.GDRIVE_FOLDER_ID}' in parents "
             f"and mimeType='{XLSX_MIME}' and trashed=false")
    resp = svc.files().list(
        q=query, orderBy="modifiedTime desc",
        fields="files(id,name,modifiedTime)", pageSize=50,
    ).execute()

    arquivos = [f for f in resp.get("files", [])
                if fnmatch.fnmatch(f["name"], config.GDRIVE_FILE_PATTERN)]
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum .xlsx casando com '{config.GDRIVE_FILE_PATTERN}' na pasta do Drive."
        )

    alvo = arquivos[0]  # mais recente (orderBy modifiedTime desc)
    log.info("Arquivo selecionado: %s (modificado em %s)", alvo["name"], alvo["modifiedTime"])

    from googleapiclient.http import MediaIoBaseDownload
    destino = destino_dir / alvo["name"]
    req = svc.files().get_media(fileId=alvo["id"])
    with io.FileIO(destino, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    log.info("Planilha baixada: %s", destino)
    return destino
