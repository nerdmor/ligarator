# ligarator
Encontre a combinação mais barata de lojas para comprar suas cartas de Magic

## Descrição/objetivo
Um script em python que encontre a combinação mais barata de lojas para a compra de cartas de Magic entre cartas na LigaMagic. Utiliza solução linear de equações para encontrar o ponto mínimo entre as diferentes combinações de lojas.

## Requerimentos
* Python 3.5 (Testado apenas a partir desta versão)
* Google Ortools (No Windows, depende de Python x64 para ser utilizado)
* Outras bibliotecas Python (descritas em dependencies.txt)
* Uma conexão com a internet (duh)

## Limitações Conhecidas
* Não checa se o nome da carta está escrito corretamente
* Não leva em consideração estado da carta  (Se é pra ser barato, vale aquela AP)

## Como instalar
1. Tenha Python 3.5 ou superior instalado na sua máquina
	* Você pode baixar em [python.org](https://www.python.org/downloads/)
    * Se você está usando Windows, tenha certeza de instalar a versão x64
    * Prefica não instalar para todos os usuários (desmarque essa opção) se você não sabe abrir o console/terminal como administrador
2. Baixe os arquivos deste projeto todos para uma única pasta
3. Abra uma terminal na pasta onde os arquivos estão
    * No Windows 7 ou superior, o jeito mais fácil de fazer isso é:
        1. Abra a pasta onde os seus arquivos estão
        2. Segure shift e clique com o botão direito do mouse fora de qualquer ícone
        3. Solte o shift e clique na opção "Abrir janela do Console aqui" ou "Abrir janela do PowerShell aqui"
4. Instale as dependências do projeto
    * Elas estão no arquivo dependencies.txt
    * Caso você não saiba fazer isso, use a seguinte linha:
        ```
        pip install altgraph beautifulsoup4 bs4 certifi chardet future idna macholib ortools pefile pip protobuf requests six urllib3
        ```
    * No windows, use tambem:
        ```
        pip install pywin32
        ```
5. Tenha uma lista de cartas desejadassalva em um arquivo de texto
    * Uma linha por carta
    * Nomes escritos corretamente (o programa não checa). De preferência em inglês
    * No seguinte formato: [N] [NOME DA CARTA]
    * Exemplos:
        ```
        4 llanowar elves
        3 Giant Growth
        ```
5.1. Opcional: faça uma lista de lojas banidas
    * Edite o arquivo banned_stores.txt e coloque o nome das lojas de quem você não quer comprar, como aparecem na Liga, um nome por linha
    * Exemplos:
        ```
        nome loja 1
        nome loja 2
        ```
6. No terminal, execute o arquivo **ligarator.py**
    ```
    python ligarator.py
    ```
7. Siga as instruções na tela
    * O resultado pode demorar. Para não estressar o site, o script demora vários segundos entre cada carta. 
    * O cálculo de opções pode ser bastante intenso em recursos, dependendo das ofertas
    * Os resultados serão mostrados na tela e salvos na mesma pasta em que o arquivo com a sua wantlist estava.
