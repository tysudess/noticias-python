# V74 - Editor PDF com largura igual à capa padrão

## Correção solicitada

Todas as páginas do PDF exportado passam a ter **exatamente a mesma largura física da capa padrão**.

A capa não é redimensionada para acompanhar a matéria. É a matéria que passa a usar a largura da capa.

## Exemplo confirmado no PDF enviado

Antes:

- capa: `298,8 pt` de largura;
- matéria: `561,6 pt` de largura.

Depois:

- capa: `298,8 pt`;
- matéria: `298,8 pt`;
- altura da matéria: proporcional ao original (`~472,717 pt` no exemplo).

## Qualidade

A correção não reduz a resolução:

- JPEG original continua sem recompressão quando possível;
- imagens não sofrem downsample;
- páginas PDF sem transformação continuam vetoriais;
- altura é calculada pela proporção original;
- não há achatamento nem esticamento.

O que muda é somente o **tamanho físico da página dentro do PDF**.

## Arquivo para substituir

`src/monitor_noticias/ui/pdf_export_quality_fix.py`

## Teste novo

`tests/unit/test_pdf_width_equals_cover_v74.py`

## Windows e Ubuntu

A correção é compartilhada entre as duas versões.

## WORKFLOW

NÃO PRECISA ALTERAR.
