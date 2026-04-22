import os
import requests
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any, Optional
# Mantendo a herança da sua interface original
from src.interfaces.repository_fetcher import BaseRepositoryFetcher

class HttpRepositoryFetcher(BaseRepositoryFetcher):
    def __init__(self, token: Optional[str] = None):
        super().__init__()
        env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)
        
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_url = "https://api.github.com/graphql"

    def _execute_request(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa a chamada GraphQL passando variáveis dinâmicas (como a queryString).
        """
        if not self.token:
            return {"errors": "GITHUB_TOKEN não configurado", "data": None}

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query, "variables": variables},
                headers=headers
            )
            
            if response.status_code != 200:
                return {"errors": f"HTTP {response.status_code}", "data": None}
                
            return response.json()
            
        except Exception as e:
            return {"errors": str(e), "data": None}

    def _parse_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adaptado para capturar metadados de rede e filtros de elegibilidade[cite: 116].
        """
        return {
            "name": node.get('nameWithOwner', 'N/A'), # 'owner/repo' para chamadas futuras
            "url": node.get('url', ''),
            "stargazerCount": node.get('stargazerCount', 0),
            "createdAt": node.get('createdAt', ''),
            "pushedAt": node.get('pushedAt', ''),
            # Filtro inicial: Total de PRs e Contribuidores
            "total_prs": (node.get('pullRequests') or {}).get('totalCount', 0),
            "contributor_count": (node.get('mentionableUsers') or {}).get('totalCount', 0),
        }