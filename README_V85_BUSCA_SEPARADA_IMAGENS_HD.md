# V85 — Busca separada por jornal + imagens HD salvas separadamente

## Base confirmada
Patch preparado sobre a `main` confirmada em:

`4e6e35804bed954be6b1a4ec56a030b208e61118`

Essa base já contém a V84.

## 1. Selecionar jornal não inicia mais busca
Na V84, clicar numa linha da tabela chamava `download_current()` imediatamente. Isso fazia várias buscas ocultas começarem enquanto o usuário apenas alternava jornais para configurar usuário/senha.

Na V85:
- clicar em um jornal **somente seleciona**;
- nenhuma rede/download é iniciada pela seleção;
- a busca começa somente em **Iniciar busca / baixar edição**.

## 2. Status/progresso separado por jornal
Cada provedor passa a manter seu próprio status e estado de atividade.

Uma mensagem de Estadão não aparece mais enquanto O Globo estiver selecionado. Se uma busca continuar em segundo plano e o usuário mudar a seleção, a mensagem permanece associada ao jornal correto.

## 3. Valor — captura reforçada das páginas PressReader
O APK `tysudess/aplicativo-extrair-valor` encontrava recursos tanto pelo JavaScript quanto pela interceptação das requisições do WebView.

A V85 replica essa estratégia no Qt WebEngine:
- adiciona `QWebEngineUrlRequestInterceptor`;
- observa diretamente requisições do PressReader / `prcdn.co`;
- continua verificando `performance.getEntriesByType('resource')`;
- também verifica `img.currentSrc`, `img.src` e `srcset` do DOM;
- mantém a página do Chromium em estado ativo durante a busca;
- dá mais tempo para o viewer solicitar a imagem HD antes de concluir que a página não existe.

Isso corrige o principal ponto fraco da V84, que podia terminar com `0 páginas` mesmo quando o viewer havia carregado recursos por outra camada.

## 4. Imagens HD ficam salvas separadamente
No Valor, as páginas baixadas não ficam mais em pasta temporária apagada no final.

Estrutura esperada:

```text
JornaisDigitais/
  valor-economico/
    AAAA-MM-DD/
      paginas_hd/
        pagina-001.jpg
        pagina-002.jpg
        pagina-003.jpg
        ...
      valor-economico-AAAA-MM-DD.pdf
```

- JPEG permanece JPEG original;
- PNG/WebP/AVIF preservam o arquivo baixado;
- o PDF é montado depois usando as imagens completas;
- se uma etapa posterior falhar, as imagens que já foram baixadas são preservadas para diagnóstico/uso.

## 5. Outros jornais
Os adaptadores existentes de Correio Braziliense, Estado de Minas, Folha, Estadão, O Globo, A Tarde, GZH, Gazeta, NYT e Washington Post são preservados.

A V85 corrige a interferência entre as buscas e impede disparo automático ao selecionar. Ela não inventa um padrão de imagem genérico para todos os viewers, porque isso aumentaria o risco de salvar anúncios, logos ou documentos que não são páginas do jornal. A captura de imagens deve continuar sendo especializada por provider conforme identificarmos o padrão real de cada viewer.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/digital_newspapers/browser.py`
- `src/monitor_noticias/digital_newspapers/pressreader_hd.py`
- `src/monitor_noticias/digital_newspapers/providers.py`
- `src/monitor_noticias/ui/digital_newspapers_page.py`
- `tests/unit/test_digital_newspapers_v84.py`

### ADICIONAR
- `tests/unit/test_digital_newspapers_v85.py`
- `README_V85_BUSCA_SEPARADA_IMAGENS_HD.md`

## Workflow
**WORKFLOW: NÃO PRECISA ALTERAR**

## Validação local
- `py_compile` dos arquivos Python alterados: OK
- testes V84 + V85: `10 passed`
