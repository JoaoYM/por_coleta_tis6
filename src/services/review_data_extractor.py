import os
import time
import requests
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from src.utils.output_formatter import RepositoryOutputFormatter

class ReviewDataExtractor:
    def __init__(self):
        # Configuração de caminhos e variáveis de ambiente
        self.base_path = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_path / "data"
        self.query_file = self.base_path / "src" / "infrastructure" / "graphql" / "pr_query.graphql"
        self.output = RepositoryOutputFormatter()
        
        load_dotenv(dotenv_path=self.base_path / '.env')
        self.token = os.getenv("GITHUB_TOKEN")
        self.api_url = "https://api.github.com/graphql"

    def _get_query_content(self) -> str:
        """Lê o arquivo GraphQL do disco."""
        if not self.query_file.exists():
            raise FileNotFoundError(f"Arquivo de query não encontrado: {self.query_file}")
        return self.query_file.read_text(encoding="utf-8")

    def _is_human(self, author_login: str) -> bool:
        """Filtra interações de bots com base no sufixo padrão do GitHub."""
        if not author_login:
            return False
        return not author_login.lower().endswith('[bot]')

    def extract_prs_from_csv(self, input_csv: str = "poc_repos_merged_filter.csv", start_date: str = "2026-01-01", end_date: str = "2026-02-28"):
        """Coordena a extração lendo os repositórios aprovados da Fase 1."""
        input_path = self.data_dir / input_csv
        if not input_path.exists():
            self.output.print_error("CSV de repositórios não encontrado!")
            return

        df_repos = pd.read_csv(input_path)
        all_prs_data = []
        query_content = self._get_query_content()

        self.output.print_fetch_start("GraphQL PR Extractor", len(df_repos))

        for index, row in df_repos.iterrows():
            repo_name = row['name'] # Ex: 'facebook/react'
            # Monta a query de busca específica para este repositório e janela de tempo
            pr_query = f"repo:{repo_name} is:pr is:merged merged:{start_date}..{end_date}"
            
            cursor = None
            has_next = True
            
            while has_next:
                variables = {"prQuery": pr_query, "cursor": cursor}
                
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(self.api_url, json={"query": query_content, "variables": variables}, headers=headers)
                
                if response.status_code != 200:
                    self.output.print_error(f"Erro na API para {repo_name}: HTTP {response.status_code}")
                    break
                    
                data = response.json()
                
                if 'errors' in data:
                    self.output.print_error(f"Erro GraphQL no repo {repo_name}")
                    break
                    
                search_results = data['data']['search']
                
                # Processamento e filtragem de bots
                for edge in search_results.get('edges', []):
                    pr_node = edge.get('node')
                    if not pr_node: continue
                    
                    author_data = pr_node.get('author')
                    author_login = author_data.get('login') if author_data else None
                    
                    if not self._is_human(author_login):
                        continue
                        
                    pr_info = self._process_pr_node(repo_name, pr_node, author_login)
                    if pr_info:
                        all_prs_data.append(pr_info)

                page_info = search_results.get('pageInfo', {})
                has_next = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                
                time.sleep(0.5) # Proteção básica de Rate Limit

        # Salvamento dos dados estruturados
        output_path = self.data_dir / "poc_prs_extracted.csv"
        df_prs = pd.DataFrame(all_prs_data)
        df_prs.to_csv(output_path, index=False)
        self.output.print_save_success(str(output_path))

    def _process_pr_node(self, repo_name: str, pr_node: Dict[str, Any], author_login: str) -> Dict[str, Any]:
        """Extrai as métricas de tempo e esforço para as variáveis dependentes da pesquisa."""
        pr_created_at = pd.to_datetime(pr_node.get('createdAt'))
        
        human_reviews = []
        human_comments_count = 0
        
        # Filtra revisões oficiais feitas por humanos
        for review in pr_node.get('reviews', {}).get('nodes', []):
            if not review or not review.get('author'): continue
            reviewer_login = review['author'].get('login')
            if self._is_human(reviewer_login) and reviewer_login != author_login:
                human_reviews.append({
                    "reviewer": reviewer_login,
                    "date": pd.to_datetime(review['createdAt'])
                })
                
        # Conta comentários de discussão (Filtro de Ruído)
        for comment in pr_node.get('comments', {}).get('nodes', []):
            if not comment or not comment.get('author'): continue
            commenter_login = comment['author'].get('login')
            if self._is_human(commenter_login):
                human_comments_count += 1
                
        # Se não houve revisão externa humana, descartamos (Critério da Metodologia)
        if not human_reviews:
            return None
            
        # Ordena para pegar a primeira resposta
        human_reviews.sort(key=lambda x: x['date'])
        first_review_date = human_reviews[0]['date']
        
        # Cálculo do Time to First Review (em horas)
        latency_hours = (first_review_date - pr_created_at).total_seconds() / 3600
        
        # O revisor principal será o que fez a primeira revisão oficial
        primary_reviewer = human_reviews[0]['reviewer']

        return {
            "repository": repo_name,
            "pr_number": pr_node.get('number'),
            "author": author_login,
            "primary_reviewer": primary_reviewer,
            "first_review_latency_hours": round(latency_hours, 2),
            "discussion_volume": len(human_reviews) + human_comments_count
        }