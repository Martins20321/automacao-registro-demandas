# Automação de registro de demandas (Outlook → SharePoint)

Lê a caixa compartilhada do **Outlook clássico**, encontra as demandas concluídas ("Feito") de um
estagiário a partir de uma data, monta o registro de cada uma e entrega as linhas prontas para colar
na lista do SharePoint, **sempre com prévia e confirmação do operador antes do envio**.

---

## Passo a passo de uso (executável)

### Antes de começar (uma vez)

1. **Descompacte** `registro-demandas.zip` em uma pasta sua (por exemplo, `Documentos\registro-demandas`).
   Não execute de dentro do zip.
2. **Configure o `.env`** (valores do seu órgão). Se o responsável entregou o pacote com o `.env` pronto,
   pule este passo. Senão, copie `.env.example` para `.env` e preencha (veja a tabela em
   [Configuração](#configuração-env)).
3. Peça ao responsável a **lista oficial de estagiários** e salve em `config\estagiarios.csv`
   (colunas `nome,email`, nome **sem acento**, como aparece no SharePoint).
4. Tenha uma **chave da API do Groq** (gratuita, em https://console.groq.com/keys). O programa pede a
   chave na primeira execução, não a mostra na tela e a guarda só no seu computador (no `.env`).
5. Se o Windows avisar que o executável é de "editor desconhecido", clique em *Mais informações* >
   *Executar assim mesmo*. Isso acontece porque o programa não é assinado digitalmente.

### A cada execução

1. **Abra o Outlook clássico**, logado, com a caixa compartilhada visível no painel esquerdo.
   O "novo Outlook" e o Outlook na web **não funcionam**.
2. *(Recomendado)* **Exporte a lista do SharePoint**: na lista, clique em **Exportar > Exportar para
   CSV**. Serve para o programa não registrar uma demanda que já está lá.
3. Dê dois cliques em **`registro-demandas.exe`**.
4. Responda às perguntas:
   - **Seu e-mail institucional** (o mesmo da lista de estagiários);
   - **Seu nome completo**;
   - **Data inicial** (dd/mm/aaaa): o programa busca as demandas **suas** concluídas desde essa data.
5. Aguarde. Ele indexa o Outlook, identifica o dono de cada conversa pela **assinatura em imagem** e
   analisa com IA (cerca de 10 segundos por demanda).
6. Quando perguntar, informe o **caminho do CSV** exportado (pode arrastar o arquivo para a janela) ou
   aperte **ENTER** para pular. Sem o CSV, não há checagem de duplicidade.
7. **Confira a prévia.** Ela mostra, para cada demanda, exatamente o que será registrado:
   - `[OK]`: nada a verificar. `[REVISAR]`: leia os avisos marcados com `!`.
   - Para **editar**, digite o número da demanda, escolha o campo e informe o novo valor.
   - Para **remover**, digite `x` e o número (por exemplo, `x 3`).
   - Se uma demanda já existir na lista, o programa pergunta se deve registrar mesmo assim.
8. Quando estiver tudo certo, aperte **ENTER** e digite **`sim`** para confirmar.
9. As linhas **já ficam copiadas** e a lista abre no navegador (se `LISTA_URL` estiver no `.env`).
   Na lista do SharePoint:
   1. Clique em **Editar no modo de exibição de grade**.
   2. Clique na **primeira célula vazia da coluna Problema**.
   3. Pressione **Ctrl+V**.
   4. Confira e clique em **Sair do modo de grade** para salvar.
10. Aperte ENTER na janela do programa para fechá-la.

> **Dica para a colagem:** crie na lista uma vista com as colunas **na mesma ordem da saída**
> (Problema, Descrição do problema, Complexidade, Status, Atribuído a, Data de Abertura, Cliente,
> Sistema, Origem do chamado, Data de Conclusão) e filtre por datas recentes, para a linha vazia ficar
> à vista. O arquivo gerado **não tem cabeçalho**.

### Exemplos de comandos

Dois cliques no `.exe` basta. Para pular as perguntas, rode pelo terminal (PowerShell ou Prompt de Comando),
na pasta do programa:

```bash
# Tudo informado de uma vez, com checagem de duplicidade
registro-demandas.exe --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026 --lista-csv "C:\Users\Maria\Downloads\Atendimentos.csv"
```

```bash
# Só ver a prévia (não pergunta nada e não entrega)
registro-demandas.exe --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026 --so-previa
```

```bash
# Considerar só as conversas com a categoria da pessoa (mais rápido, menos completo)
registro-demandas.exe --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026 --so-categoria
```

```bash
# Procurar o primeiro e-mail da conversa até 180 dias antes da data inicial (padrão: 90)
registro-demandas.exe --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026 --margem-dias 180
```

| Opção | Para que serve |
|---|---|
| `--email`, `--nome`, `--desde` | Dados do operador e data inicial (dd/mm/aaaa). Se faltarem, o programa pergunta. |
| `--lista-csv "caminho"` | CSV exportado da lista, para evitar registro duplicado. |
| `--so-previa` | Gera e salva a prévia, sem perguntar e sem entregar. |
| `--so-categoria` | Não verifica pela assinatura as conversas sem a categoria da pessoa. |
| `--margem-dias N` | Quanto antes da data inicial procurar o primeiro e-mail da conversa. |

### Onde ficam os arquivos gerados

Na pasta `saida\` ao lado do executável: a prévia inicial, a prévia confirmada e o `.tsv` com as
linhas (o mesmo conteúdo que foi copiado), caso precise colar de novo.

### Entendendo o resultado

| Aparece | Significa |
|---|---|
| **Demanda registrada** | Pedido executado pela equipe (ativação de conta, alteração de página etc.). |
| **Esclarecimento** | Usuário perguntou e a equipe respondeu: também é registrado, com complexidade Baixa. |
| **Ignoradas** | Encaminhamentos à fábrica (usuário pediu a execução e a equipe só repassou) e perguntas sem resposta útil. Não são registradas, mas ficam listadas para você conferir. |
| **Falhas** | Conversas que a IA não conseguiu analisar. Registre à mão. |

### Problemas comuns

| Problema | O que fazer |
|---|---|
| "Faltam valores no arquivo .env" | Preencha os valores indicados no `.env` (veja [Configuração](#configuração-env)). |
| "Armazenamento '…' não encontrado" | A caixa compartilhada não está no perfil do Outlook clássico, ou o nome em `OUTLOOK_ARMAZENAMENTO` está diferente do painel do Outlook. |
| O programa parece parado | A leitura do Outlook e a IA levam alguns minutos. Se o Outlook mostrar um aviso de segurança, clique em permitir. |
| "limite de requisições do Groq" | É normal no plano gratuito: o programa espera e tenta de novo sozinho. |
| "não confere com o e-mail" | O nome ou o e-mail digitados diferem da lista `config\estagiarios.csv`. |
| Assinatura não reconhecida (`REVISAR`) | O OCR não leu o nome com segurança. Confira o responsável na prévia. |
| Chave do Groq errada | Edite a linha `GROQ_API_KEY` do `.env` (ou apague a linha) e rode de novo. |

---

## Configuração (.env)

Tudo que é específico do órgão fica no `.env` (que **não é versionado**), e não no código. Copie
`.env.example` para `.env` e preencha:

| Variável | Obrigatória | O que é |
|---|---|---|
| `OUTLOOK_ARMAZENAMENTO` | sim | Nome da caixa compartilhada **exatamente como aparece no painel esquerdo do Outlook clássico**. |
| `DOMINIO_INTERNO` | sim | Domínio dos e-mails internos, por exemplo `@orgao.gov.br`. Também reconhece o e-mail impresso na assinatura. |
| `CLIENTE_CONSULTAS_PUBLICAS` | sim | Cliente gravado para demandas **externas** de Consultas Públicas (pessoa/grupo reconhecido pelo SharePoint). |
| `CLIENTE_PORTAL_EXTERNO` | sim | Cliente gravado para demandas **externas** do portal. |
| `CATEGORIAS_IGNORADAS` | não | Categorias do Outlook que não são nome de estagiário, separadas por vírgula. |
| `LISTA_URL` | não | Endereço da lista; abre no navegador ao final da execução. |
| `GROQ_API_KEY` | não | Chave da IA. Se vazia, o programa pede na primeira execução e a grava aqui. |
| `GROQ_MODEL` | não | Modelo do Groq (padrão `openai/gpt-oss-120b`). |

---

## Como funciona

1. O operador informa e-mail, nome e a data inicial.
2. O programa reconstrói cada conversa (recebidas e enviadas) e identifica o responsável pela
   **assinatura em imagem** da resposta de conclusão (OCR local com Tesseract).
3. Uma IA (Groq) classifica a conversa e resume o pedido. Ela só recebe texto **anonimizado**
   (nomes viram `[PESSOA_n]` e voltam só localmente).
4. Regras fixas definem Cliente, Complexidade, Status, Origem e datas.
5. O programa mostra a prévia, permite editar, verifica duplicidade (CSV exportado da lista) e,
   após o "sim", copia as linhas para a área de transferência e abre a lista.

Colunas da saída: Problema, Descrição do problema, Complexidade, Status, Atribuído a, Data de Abertura,
Cliente, Sistema, Origem do chamado, Data de Conclusão.

## Desenvolvimento

Requisitos: Windows com Outlook clássico, Python 3.12 e
[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).

```bash
# 1. Ambiente e dependências
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt

# 2. Configuração (edite os dois arquivos criados)
copy .env.example .env
copy config\estagiarios.exemplo.csv config\estagiarios.csv

# 3. Executar
.venv\Scripts\python buscar_demandas.py
.venv\Scripts\python buscar_demandas.py --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026 --so-previa
```

Edite `config/estagiarios.csv` com a lista oficial. Esse arquivo e o `.env` **não são versionados**.

Testes (não precisam de Outlook nem de chave):

```bash
.venv\Scripts\python -m pytest
```

Gerar o executável (o resultado fica em `dist\registro-demandas\` e `dist\registro-demandas.zip`):

```bash
powershell -ExecutionPolicy Bypass -File empacotamento\construir_exe.ps1
```

Por padrão o pacote leva a lista de **exemplo** e só o `.env.example`. Para um pacote de **uso interno**
(com a sua lista real e o `.env` do órgão, sem a chave), use `-IncluirLista`; esse pacote **não deve
ser publicado**:

```bash
powershell -ExecutionPolicy Bypass -File empacotamento\construir_exe.ps1 -IncluirLista
```

## Estrutura

- `automacao/`: módulos (Outlook, assinatura/OCR, anonimização, IA, regras, prévia, duplicidade, entrega).
- `buscar_demandas.py`: programa principal (linha de comando).
- `tests/`: testes automatizados.
- `config/`: lista de estagiários (exemplo versionado, real ignorado).
- `empacotamento/`: construção do executável e instruções que acompanham o pacote.
- `tessdata/`: idioma português do Tesseract.

## Privacidade

Nada de e-mail, nomes ou imagens é versionado (`dados/`, `saida/`, `.env` e a lista real de estagiários
estão no `.gitignore`). A IA recebe apenas texto anonimizado, e a detecção de nomes é por regra, portanto
a conferência humana continua obrigatória.
