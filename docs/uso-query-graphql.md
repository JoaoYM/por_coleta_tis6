# Uso da Query GraphQL

Este documento descreve como executar a consulta [`src/query.graphql`](../src/query.graphql) para coletar dados dos repositórios mais populares do GitHub, utilizando o **GitHub CLI (`gh`)** ou uma **requisição HTTP genérica**.

---

## Sobre a query

A query busca repositórios com mais de 1.000 estrelas, ordenados por estrelas decrescente, coletando os campos necessários para as questões de pesquisa RQ01–RQ06.

A consulta aceita um parâmetro de paginação opcional:

| Variável  | Tipo     | Descrição                                          |
|-----------|----------|----------------------------------------------------|
| `$cursor` | `String` | Cursor de paginação (`endCursor` da página anterior). Omitir na primeira requisição. |

Cada página retorna **25 repositórios**. Para coletar os 1.000 repositórios são necessárias **40 requisições** sequenciais.

> **Por que 25 por página?**  
> A combinação de 4 conexões aninhadas (releases, pullRequests, openIssues, closedIssues) por repositório consome muitos recursos no servidor do GitHub. Valores acima de ~40 retornam HTTP 502. O limite de 25 garante estabilidade.

---

## 1. GitHub CLI (`gh`)

### Pré-requisitos

```bash
# Verifique se o gh está instalado e autenticado
gh auth status
```

### Primeira página (sem cursor)

```bash
gh api graphql -F query=@src/query.graphql
```

### Páginas seguintes (com cursor)

Extraia o `endCursor` da resposta anterior e passe-o com `-f cursor=`:

```bash
gh api graphql -F query=@src/query.graphql -f cursor=<CURSOR>
```

### Saída esperada

```json
{
  "data": {
    "search": {
      "pageInfo": {
        "endCursor": "Y3Vyc29yOjI1",
        "hasNextPage": true
      },
      "edges": [
        {
          "node": {
            "name": "build-your-own-x",
            "url": "https://github.com/codecrafters-io/build-your-own-x",
            "createdAt": "2018-05-09T12:03:18Z",
            "updatedAt": "2026-02-22T23:22:39Z",
            "primaryLanguage": { "name": "Markdown" },
            "releases": { "totalCount": 0 },
            "pullRequests": { "totalCount": 155 },
            "openIssues": { "totalCount": 232 },
            "closedIssues": { "totalCount": 653 }
          }
        }
      ]
    }
  }
}
```