from typing import List, Dict, Any
import pandas as pd
from src.interfaces.repository_fetcher import RepositoryFetcher
from src.utils.output_formatter import RepositoryOutputFormatter

class RepositoryManager:
    def __init__(self, fetcher: RepositoryFetcher):
        self.fetcher = fetcher
        self.output = RepositoryOutputFormatter()
        # Definição das linguagens alvo da pesquisa
        self.target_languages = ["TypeScript", "Python", "JavaScript", "Java", "C#"]
    
    def fetch_poc_repositories(self, repos_per_lang: int = 20) -> List[Dict[str, Any]]:
        """
        Coordena a coleta de repositórios para cada uma das 5 linguagens.
        """
        all_collected_repos = []
        
        # Critérios de elegibilidade: 1k+ stars e criado antes de Março/2023
        base_criteria = "stars:>=1000 created:<2023-03-01 pushed:>2025-10-01 sort:stars-desc"
        
        for lang in self.target_languages:
            query_string = f"language:{lang} {base_criteria}"
            print(f"\n🔍 Buscando repositórios para a linguagem: [bold]{lang}[/bold]")
            
            # Chama o fetcher passando a query específica da linguagem
            repos = self.fetcher.fetch(
                query_string=query_string, 
                max_repos=repos_per_lang
            )
            all_collected_repos.extend(repos)
            
        return all_collected_repos
    
    def display_results(self, repos: List[Dict[str, Any]]) -> None:
        """
        Renderiza as tabelas bonitas no terminal usando o 'rich'.
        """
        if not repos:
            self.output.print_no_repos()
            return
        
        self.output.print_repositories(repos)
        self.output.print_summary(repos)
        self.output.print_completion(len(repos))
    
    def save_consolidated_data(self, repos: List[Dict[str, Any]], filename: str = "poc_repos.csv"):
        """
        Salva os resultados em CSV para análise posterior.
        """
        if not repos:
            return
        
        df = pd.DataFrame(repos)
        output_path = self.fetcher.data_dir / filename
        df.to_csv(output_path, index=False, encoding='utf-8')
        self.output.print_save_success(str(output_path))