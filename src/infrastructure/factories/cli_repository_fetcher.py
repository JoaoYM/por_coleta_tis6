import subprocess
import json
from typing import Any, Dict, Optional

from src.interfaces.repository_fetcher import BaseRepositoryFetcher

class CliRepositoryFetcher(BaseRepositoryFetcher):
    """
    Implementation that uses the 'gh' GitHub CLI binary
    to perform GraphQL requests.
    """
    
    def _execute_request(self, query: str, cursor: Optional[str]) -> Dict[str, Any]:
        
        cmd = [
            'gh', 'api', 'graphql',
            '-f', f'query={query}'
        ]

        if cursor:
            cmd.extend(['-f', f'cursor={cursor}'])
        else:
            cmd.extend(['-F', 'cursor=null']) # -F forces it to be treated as a real null value

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"errors": result.stderr.strip(), "data": None}

            return json.loads(result.stdout)
        except Exception as e:
            return {"errors": str(e), "data": None}