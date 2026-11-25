# Registro de Demandas (Outlook → SharePoint)

Programa com janelas que lê a caixa compartilhada do **Outlook clássico**, encontra as demandas
concluídas ("Feito") de um estagiário a partir de uma data, monta o registro de cada uma e deixa as
linhas prontas para colar na lista do SharePoint, **sempre com prévia e confirmação antes do envio**.

---

## Baixar e instalar

1. Abra a página **Releases** deste repositório (barra lateral direita do GitHub) e, na versão mais
   recente, baixe **`Registro-de-Demandas.zip`** (em *Assets*).
2. **Extraia** o zip em uma pasta sua (por exemplo, em Documentos). Não execute de dentro do zip.
3. Dê dois cliques em **`Registro de Demandas.exe`**. Não precisa instalar nada.
   - Se o Windows avisar sobre "editor desconhecido": *Mais informações* > *Executar assim mesmo*.
     O aviso aparece porque o programa não é assinado digitalmente.

Na pasta extraída há só três itens: o programa (`Registro de Demandas.exe`), o `LEIA-ME.txt` e a pasta
`_internal` (arquivos do programa, não mexa).

## Primeiro uso (uma vez)

O programa abre sozinho a tela **Configurações**. Preencha:

| Campo | O que é |
|---|---|
| Nome da caixa compartilhada | Exatamente como aparece no painel esquerdo do Outlook clássico. |
| E-mail da caixa | Opcional. Só preencha se a caixa **não** aparecer como uma conta própria no Outlook (aberta apenas por permissão). |
| Domínio dos e-mails internos | Por exemplo `@orgao.gov.br`. |
| Cliente de demandas externas de Consultas Públicas | Pessoa/grupo que o SharePoint reconhece pelo nome. |
| Cliente de demandas externas do portal | Idem, para o portal. |
| Endereço da lista do SharePoint | Opcional. Se informado, o botão "Abrir a lista" aparece no final. |
| Categorias a ignorar | Opcional. Categorias do Outlook que não são nome de estagiário. |
| Chave da API do Groq | Grátis em https://console.groq.com/keys. Fica só no seu computador. |

Clique em **Editar lista de estagiários** e informe nome e e-mail de cada pessoa (o nome pode ter
acento: o programa compara ignorando isso).
Clique em **Testar instalação** para conferir o OCR, a lista, a chave e o acesso ao Outlook.
Ao salvar, o programa reabre sozinho.

## Usar a cada vez

1. Abra o **Outlook clássico**, com a caixa compartilhada visível no painel esquerdo.
   O "novo Outlook" e o Outlook na web **não funcionam**.
2. *(Recomendado)* Na lista do SharePoint, use **Exportar > Exportar para CSV**, para o programa não
   registrar uma demanda que já está lá.
3. No programa, informe **seu e-mail**, **seu nome** e a **data inicial**, selecione o CSV e clique em
   **Buscar minhas demandas**. Aguarde alguns minutos (cerca de 10 segundos por demanda).
4. Na **prévia**, confira cada demanda:
   - **OK**: nada a verificar. **REVISAR** (linha amarela): leia o aviso abaixo da tabela.
   - **JÁ EXISTE**: já está na lista; vem desmarcada. Clique em *Incluir esta demanda* se quiser mesmo.
   - Para **editar**, clique na demanda, altere os campos e clique em *Aplicar alterações*.
   - Para **excluir** da entrega, clique em *Não incluir esta demanda*.
   - As abas **Ignoradas** e **Falhas** mostram o que ficou de fora e por quê.
5. Clique em **Confirmar e copiar para o SharePoint**. As linhas ficam copiadas.
6. Na lista do SharePoint: **Editar no modo de exibição de grade**, clique na **primeira célula vazia da
   coluna Problema** e pressione **Ctrl+V**. Confira e clique em **Sair do modo de grade**.

> **Dica:** crie na lista uma vista com as colunas **na mesma ordem da saída** (Problema, Descrição do
> problema, Complexidade, Status, Atribuído a, Data de Abertura, Cliente, Sistema, Origem do chamado,
> Data de Conclusão) e filtre por datas recentes, para a linha vazia ficar à vista.

### Entendendo o resultado

| Aparece | Significa |
|---|---|
| **Para registrar** | Pedido executado pela equipe ou esclarecimento respondido (este sempre com complexidade Baixa). |
| **Ignoradas** | Encaminhamentos à fábrica (o usuário pediu a execução e a equipe só repassou) e perguntas sem resposta útil. |
| **Falhas** | Conversas que a IA não conseguiu analisar. Registre à mão. |

### Problemas comuns

| Problema | O que fazer |
|---|---|
| Aviso "Armazenamento … não encontrado" | A mensagem lista as caixas que o Outlook encontrou: copie o nome exato de uma delas para Configurações. Se a caixa só aparecer por permissão (sem ser uma conta própria no painel), preencha também o **e-mail da caixa** em Configurações. |
| "Verifique se o Outlook clássico está aberto" | Abra o Outlook clássico (o novo Outlook não serve) e tente de novo. |
| Parece parado | A leitura do Outlook e a IA levam alguns minutos. Se o Outlook pedir permissão de acesso, clique em permitir. |
| Limite de requisições do Groq | Normal no plano gratuito: o programa espera e tenta de novo sozinho. |
| "não confere com o e-mail" | O nome ou o e-mail diferem da lista de estagiários (Configurações > Editar lista). |
| Assinatura não reconhecida (REVISAR) | O OCR não leu o nome com segurança. Confira o responsável. |
| Erro inesperado | O detalhe fica em `saida\erro.log` (botão *Pasta dos arquivos*). |

Os dados ficam em `%APPDATA%\RegistroDemandas` (configuração, lista de estagiários e arquivos gerados).
Para desinstalar, apague a pasta do programa e, se quiser, essa pasta de dados.

---

## Publicar para download (para quem mantém o projeto)

1. **Crie o repositório** no GitHub: nome sugerido `automacao-registro-demandas`, **privado**.
2. **Envie o código** (na pasta do projeto):

```bash
git init
git add .
git status
git commit -m "Primeira versão"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/automacao-registro-demandas.git
git push -u origin main
```

   Confira o `git status` antes do commit: não pode aparecer `.env`, `dados/`, `saida/`, `dist/`,
   `build/` nem `config/estagiarios.csv` (todos estão no `.gitignore`).

3. **Gere o pacote**:

```bash
powershell -ExecutionPolicy Bypass -File empacotamento\construir_exe.ps1
```

   O resultado é `dist\Registro-de-Demandas.zip`.

4. **Publique a versão**: no GitHub, *Releases* > *Draft a new release*, crie a tag `v1.0.0`, arraste o
   `Registro-de-Demandas.zip` para *Assets* e clique em *Publish release*. Quem tiver acesso ao
   repositório baixa o zip na página de Releases. Em repositório privado, só colaboradores baixam:
   adicione as pessoas em *Settings* > *Collaborators*.

Para nova versão, repita os passos 3 e 4 com outra tag (`v1.0.1`).

**Pacote interno (opcional):** `-IncluirLista` gera um zip que já leva a lista real de estagiários e as
configurações do órgão (sem a chave), copiadas no primeiro uso. **Não publique esse zip no GitHub**:
compartilhe por um canal interno.

```bash
powershell -ExecutionPolicy Bypass -File empacotamento\construir_exe.ps1 -IncluirLista
```

---

## Linha de comando (opcional)

A mesma lógica roda no terminal, útil para testes e automação:

```bash
# Tudo informado de uma vez, com checagem de duplicidade
.venv\Scripts\python buscar_demandas.py --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026 --lista-csv "C:\Users\Maria\Downloads\Atendimentos.csv"

# Só ver a prévia (não pergunta nada e não entrega)
.venv\Scripts\python buscar_demandas.py --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026 --so-previa
```

| Opção | Para que serve |
|---|---|
| `--email`, `--nome`, `--desde` | Dados do operador e data inicial (dd/mm/aaaa). Se faltarem, o programa pergunta. |
| `--lista-csv "caminho"` | CSV exportado da lista, para evitar registro duplicado. |
| `--so-previa` | Gera e salva a prévia, sem perguntar e sem entregar. |
| `--so-categoria` | Não verifica pela assinatura as conversas sem a categoria da pessoa. |
| `--margem-dias N` | Quanto antes da data inicial procurar o primeiro e-mail da conversa (padrão 90). |

## Como funciona

1. O operador informa e-mail, nome e a data inicial.
2. O programa reconstrói cada conversa (recebidas e enviadas) e identifica o responsável pela
   **assinatura em imagem** da resposta de conclusão (OCR local com Tesseract).
3. Uma IA (Groq) classifica a conversa e resume o pedido. Ela só recebe texto **anonimizado**
   (nomes viram `[PESSOA_n]` e voltam só localmente).
4. Regras fixas definem Cliente, Complexidade, Status, Origem e datas.
5. O programa mostra a prévia, permite editar, verifica duplicidade e, após a confirmação, copia as
   linhas para a área de transferência.

Colunas da saída: Problema, Descrição do problema, Complexidade, Status, Atribuído a, Data de Abertura,
Cliente, Sistema, Origem do chamado, Data de Conclusão.

## Desenvolvimento

Requisitos: Windows com Outlook clássico, Python 3.12 e
[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).

```bash
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env
copy config\estagiarios.exemplo.csv config\estagiarios.csv
.venv\Scripts\python registro_demandas.py
```

Edite `.env` e `config/estagiarios.csv` (não são versionados). Testes (não precisam de Outlook nem de chave):

```bash
.venv\Scripts\python -m pytest
```

Verificação da instalação sem abrir janela (grava `saida\autoteste.txt`):

```bash
.venv\Scripts\python registro_demandas.py --autoteste
```

## Estrutura

- `registro_demandas.py`: programa com janelas. `buscar_demandas.py`: versão em terminal.
- `automacao/`: módulos (interface, fluxo, Outlook, assinatura/OCR, anonimização, IA, regras, prévia,
  duplicidade, entrega, configuração).
- `tests/`: testes automatizados.
- `config/`: lista de estagiários (exemplo versionado, real ignorado).
- `empacotamento/`: construção do programa e instruções que acompanham o pacote.
- `tessdata/`: idioma português do Tesseract.

## Privacidade

Nada de e-mail, nomes ou imagens é versionado (`dados/`, `saida/`, `.env` e a lista real de estagiários
estão no `.gitignore`). A IA recebe apenas texto anonimizado, e a detecção de nomes é por regra, portanto
a conferência humana continua obrigatória.
