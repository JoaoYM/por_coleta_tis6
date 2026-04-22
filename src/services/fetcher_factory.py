from typing import Literal, Dict, Type
from src.interfaces.repository_fetcher import RepositoryFetcher
from src.infrastructure.factories.http_repository_fetcher import HttpRepositoryFetcher
from src.infrastructure.factories.cli_repository_fetcher import CliRepositoryFetcher

class RepositoryFetcherFactory:
    _FETCHERS: Dict[str, Type[RepositoryFetcher]] = {
        'http': HttpRepositoryFetcher,
        'cli': CliRepositoryFetcher,
    }

    @classmethod
    def create(cls, method: str) -> RepositoryFetcher:
        fetcher_class = cls._FETCHERS.get(method.lower())
        
        if not fetcher_class:
            available = list(cls._FETCHERS.keys())
            raise ValueError(f"Método '{method}' não suportado. Escolha entre: {available}")
        
        # Factory could resolve environment tokens or check dependencies before instantiation
        return fetcher_class()

    @classmethod
    def get_available_methods(cls):
        return list(cls._FETCHERS.keys())