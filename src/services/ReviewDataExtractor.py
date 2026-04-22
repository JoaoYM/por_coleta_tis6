import os
import time
import requests
import pandas as pd
import numpy as np
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
        
        # Carrega o token automaticamente do .env
        load_dotenv(dotenv_path=self.base_path / '.env')
        self.token = os.getenv("GITHUB_TOKEN")
        self.api_url = "https://api.github.com/graphql"

    def _get_query_content(self) -> str:
        """Lê o arquivo GraphQL do disco."""
        if not self.query_file.exists():
            raise FileNotFoundError(f"Arquivo de query não encontrado: {self.query_file}")
        return self.query_file.read_text(encoding="utf-8")

    def _is_human(self, author_login: str) -> bool:
        """Filtra bots via sufixo padrão e uma blacklist de ofensores conhecidos."""
        if not author_login:
            return False
            
        login_lower = author_login.lower()
        
        # Filtro 1: Padrão do GitHub
        if login_lower.endswith('[bot]'):
            return False
            
        # Filtro 2: Blacklist de automações famosas do ecossistema Open Source
        known_bots = {
            "dependabot", "dependabot-preview", "renovate", "snyk-bot", 
            "github-actions", "coveralls", "codecov", "greenkeeper", 
            "netlify", "vercel", "sonarcloud", "travis-ci"
        }
        
        return login_lower not in known_bots

    def extract_prs_from_csv(self, input_csv: str = "poc_repos_merged_filter.csv", start_date: str = "2026-01-01", end_date: str = "2026-02-28"):
        """Coordena a extração lendo os repositórios aprovados da Fase 1."""
        input_path = self.data_dir / input_csv
        if not input_path.exists():
            print(f"❌ Erro: Arquivo {input_csv} não encontrado na pasta data/")
            return

        df_repos = pd.read_csv(input_path)
        all_prs_data = []
        query_content = self._get_query_content()

        self.output.print_fetch_start("GraphQL PR Extractor", len(df_repos))

        for index, row in df_repos.iterrows():
            repo_name = row['name'] # Ex: 'facebook/react'
            # Monta a query de busca específica para este repositório e janela de tempo
            # O parâmetro -is:draft garante que pegaremos apenas PRs que nasceram prontos
            pr_query = f"repo:{repo_name} is:pr is:merged -is:draft merged:{start_date}..{end_date}"
            
            cursor = None
            has_next = True
            
            print(f"📡 Extraindo PRs de: {repo_name}...")
            
            while has_next:
                variables = {"prQuery": pr_query, "cursor": cursor}
                
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(self.api_url, json={"query": query_content, "variables": variables}, headers=headers)
                
                if response.status_code != 200:
                    print(f"❌ Erro na API para {repo_name}: HTTP {response.status_code}")
                    break
                    
                data = response.json()
                
                if 'errors' in data:
                    print(f"❌ Erro GraphQL no repo {repo_name}: {data['errors'][0].get('message', '')}")
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
        df_prs.to_csv(output_path, index=False, encoding='utf-8')
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
        
        # --- NOVO CÁLCULO DE LATÊNCIA (Descontando Finais de Semana) ---
        # 1. Pega as datas puras (sem hora) para contar os dias no calendário
        start_date = pr_created_at.date()
        end_date = first_review_date.date()
        
        # 2. Conta quantos dias úteis (seg-sex) existem entre a criação e a revisão
        business_days = np.busday_count(start_date, end_date)
        
        # 3. Calcula o tempo bruto total em segundos
        total_seconds = (first_review_date - pr_created_at).total_seconds()
        
        # 4. Encontra quantos dias de final de semana (sábado/domingo) passaram no meio
        calendar_days = (end_date - start_date).days
        weekend_days = calendar_days - business_days
        
        # 5. Desconta as horas do final de semana (cada dia = 24h = 86400s)
        business_seconds_penalty = weekend_days * 86400
        
        # 6. Latência final em horas úteis
        latency_hours = (total_seconds - business_seconds_penalty) / 3600
        
        # Proteção: Zera a latência caso a matemática de fuso horários gere números negativos
        latency_hours = max(0.0, latency_hours)
        
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