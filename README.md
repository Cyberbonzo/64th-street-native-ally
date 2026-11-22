# 64th Street: A Detective Story no ROG Ally

Port Linux x86-64 da edição mundial do arcade da Jaleco. Os dois programas Motorola 68000, de jogo e de som, são traduzidos durante a compilação. O executável SDL2 e a biblioteca da placa são específicos de **64th Street**. A compilação usa a ROM do próprio jogador.

## Jogar no Ally

O atalho **64th Street: A Detective Story** está na coleção **[Unifideck] MICROSD**. A instalação fica em `Games/64thStreet-Native` no cartão BazziteSD. O jogo renderiza em 16:9 e ocupa a tela de 1920×1080 do Ally. O raster da placa foi ampliado de 256×224 para 342×224. A apresentação preserva a proporção dos pixels do arcade e a cadência de 56,19 Hz.

| Ação | ROG Ally | Teclado |
|---|---|---|
| Inserir crédito | View | 5 |
| Iniciar | Menu / Start | 1 ou Enter |
| Andar | Direcional ou analógico esquerdo | Setas |
| Atacar ou confirmar personagem | A | Z |
| Pular | B | X |
| Pausar ou continuar | Y | Esc |

O port mantém uma cópia do estado da partida em `saves/progress.s64`. Salva a cada 30 segundos de jogo, ao pausar e no encerramento normal. Na próxima abertura, um estado válido é carregado automaticamente.

## Compilar com sua ROM

Em Linux x86-64, a compilação usa Git, Python 3, GCC/G++, Make, patch, pkg-config e os arquivos de desenvolvimento do SDL2 e zlib. Com esses componentes disponíveis, execute na pasta deste projeto:

```sh
bash build.sh "/caminho/para/64street.zip"
```

O script também aceita o ZIP externo que contém `64street.zip`. Ele verifica os 13 chips da edição mundial pelo tamanho e CRC, obtém a revisão fixada do FBNeo e gera o código nativo localmente. A saída pronta para uso fica em `.work/dist/`. Execute `jogar.sh` ou adicione esse arquivo à Steam. Use `STREET64_WORK` para escolher outra pasta de compilação.

## Como funciona

O gerador combina os chips pares e ímpares de cada 68000, decodifica os programas e emite entradas x86-64 com operandos de extensão e destinos de instruções definidos durante a compilação. A biblioteca conserva os registradores, as interrupções e a temporização necessários ao código traduzido. O adaptador da placa usa o driver Mega System 1-C do FBNeo para a memória, vídeo, entradas e chips de áudio YM2151 e MSM6295. A interface SDL2 apresenta o resultado e lê os controles.

As ferramentas e adaptações estão neste repositório. As imagens dos chips e a biblioteca gerada a partir delas ficam na cópia privada do jogador. As condições de uso do código do FBNeo estão em [licenses/FBNeo.txt](licenses/FBNeo.txt). [Fontes dos dispositivos na revisão usada](https://github.com/finalburnneo/FBNeo/tree/61cd3ede225ec44b84011f7679db68123d72725d).

## Campo de visão 16:9

O renderizador lê mais colunas dos mapas de cenário e dos sprites. No começo da rua, a câmera mostra o cenário à frente; com o deslocamento da fase, ela passa a revelar as duas laterais. Os indicadores dos jogadores ficam próximos às extremidades, e o cronômetro permanece centralizado. As ilustrações fixas da história e os retratos da seleção mantêm as dimensões originais sobre o fundo do jogo.

O teste comparou duas execuções de 3.351 quadros com a mesma sequência de entradas. Na primeira fase foi possível conferir, no mesmo quadro, a silhueta original dos lutadores e o cenário adicional de ambos os lados. O áudio das duas execuções coincidiu byte a byte. A versão 16:9 também restaurou um save feito em 4:3 e mostrou o combate no porto.

## Verificação

No ROG Ally com Bazzite, o atalho da Steam abriu o executável Linux do microSD em uma janela fullscreen de 1920×1080. O SDL reconheceu o controle. O teste com entradas programadas passou por crédito, seleção de Rick e combate na primeira fase. A verificação automatizada de 70.000 quadros também exercitou os dois jogadores. As demais fases ainda precisam de verificação individual.

Em uma compilação limpa, a mesma sequência de 1.350 quadros reproduziu os mesmos hashes de vídeo e de áudio da compilação de teste. Um teste separado salvou no quadro 510, encerrou, reabriu e avançou 47 quadros. A imagem coincidiu byte a byte com a execução contínua até o quadro 557. O roteiro de teste da placa está em [tools/verify_board.py](tools/verify_board.py).

O inventário do ZIP interno foi produzido pelo REA 6.10.1, evidência `ev_3f5cf43851a478f6e0b58cd8357338664dd66076b2345b0199577b03d053f3bc`. O leitor ELF dessa versão não aceitou o Motorola 68000. Os vetores de reset foram verificados nos bytes dos chips intercalados: `0x6b8` no programa principal e `0x400` no programa de áudio.
