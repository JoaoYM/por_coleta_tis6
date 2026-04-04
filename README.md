# 📦 Laboratório 02 - Coletor de Métricas Java & Análise Estática

Uma ferramenta de automação desenvolvida em Python para coletar dados dos 1.000 repositórios **Java** mais populares do GitHub e automatizar a extração de métricas de qualidade de software utilizando a ferramenta de análise estática [CK](https://github.com/mauricioaniche/ck).

Este projeto é referente à entrega **Lab02S01** da disciplina de Laboratório de Experimentação de Software.

## ✨ Funcionalidades

- **Coleta de Dados:** Busca os top-1.000 repositórios Java ordenados por popularidade (estrelas).
- **Múltiplos Métodos de Coleta:** Suporte para uso da API Direta (GraphQL via HTTP) ou integração com o binário local do GitHub CLI (`gh`).
- **Automação de Análise Estática:** Realiza o clone automatizado (shallow clone) de repositórios listados e executa o `ck.jar` para extrair métricas de qualidade de produto (CBO, DIT, LCOM, LOC).
- **Exportação Flexível:** Salva os dados processados em arquivos `.csv` e `.json` para análises futuras.
- **Tratamento de Falhas:** Limpeza garantida de arquivos temporários e tratamento robusto de *timeouts* e paginação da API do GitHub.

## 📋 Pré-requisitos

Certifique-se de ter as seguintes ferramentas instaladas no seu sistema:

- **Python 3.8+**
- **Git** (para realizar os clones automatizados)
- **Java (JDK/JRE 11+)** (necessário para executar a ferramenta CK)
- [GitHub CLI (gh)](https://cli.github.com/) *(Opcional, mas recomendado para o método CLI)*

## 🚀 Como Configurar

1. **Clone este repositório** para a sua máquina local.
2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
3.  **Instale as dependências:**
    
    Bash
    
    ```
    pip install -r requirements.txt
    
    ```
    
4.  **Configuração de Autenticação:**
    
    -   Crie uma cópia do arquivo `.env.example` e renomeie para `.env`.
        
    -   Adicione o seu _Personal Access Token_ do GitHub: `GITHUB_TOKEN=seu_token_aqui`
        
5.  **Configuração do CK:**
    
    -   Obtenha ou compile o arquivo `ck.jar` contendo suas dependências.
        
    -   Coloque o arquivo `ck.jar` na **raiz** do projeto (mesmo nível do diretório `src/`).
        

## 💻 Como Usar

Execute a aplicação como um módulo Python a partir da raiz do projeto, utilizando a flag `--csv` para garantir a geração do arquivo que a automação precisa ler:

Bash

```
python -m src.app --csv

```

Um menu interativo será exibido no terminal:

-   **Opções [1] e [2]:** Coletam a lista dos repositórios Java e geram o arquivo `data/repos.csv`.
    
-   **Opção [3]:** Lê o arquivo gerado, clona o primeiro repositório da lista de forma temporária e executa a análise do CK, gerando os relatórios de qualidade (`class.csv`, `method.csv`, etc.) na pasta `data/ck_results/`.
    

## 🏗️ Arquitetura e Padrões de Projeto

A base de código foi estruturada visando extensibilidade e manutenção, utilizando princípios **SOLID** e os seguintes _Design Patterns_:

-   **Factory Method:** (`RepositoryFetcherFactory`) Instancia o método de coleta correto com base na escolha do usuário sem acoplar a lógica de criação.
    
-   **Strategy:** As classes de _fetchers_ implementam a interface `BaseRepositoryFetcher`, permitindo que a lógica de negócio execute requisições sem se importar se está usando HTTP puro ou o CLI.
    
-   **Facade:** (`RepositoryManager`) Oculta a complexidade da orquestração entre a coleta de dados, padronização e exibição/exportação no terminal.