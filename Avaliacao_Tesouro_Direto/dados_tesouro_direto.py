# Importação das bibliotecas
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import locale
import os
import telegram_send

#Define o diretório de trabalho
os.chdir('C:\\Users\\charlessodre\\Documents\\PastaVM\\Estudos\\Avaliacao_Tesouro_Direto')


## Define as funções genéricas
def removeSimboloMoeda(string):
    """ Remove Simbolo de moeda. """
    return string.strip().replace('R$', '')


def formataMoeda(valor, exibeSimbolo=False):
    """ Formata a exibição da moeda. """
    simbolo = None

    if exibeSimbolo:
        simbolo = 'C'

    return locale.currency(valor, grouping=True, symbol=simbolo)


def inverteSeparadorDecimal(string):
    """ Inverte o separador decimal. """
    string = str(string).replace(',', 'v')
    string = string.replace('.', ',')
    string = string.replace('v', '.')

    return string


def objToFloat(obj):
    """ Converte um objeto para float. """
    return locale.atof(removeSimboloMoeda(obj))

def formata_segundos_hhmmss(segundos):
    """ Define a função que retorna os segundos no formato hh:mm:ss. """
    return time.strftime('%H:%M:%S', time.gmtime(segundos))

def get_data_atual():
    """ Define a função que retorna data atual do sistema. """

    return time.strftime("%d/%m/%Y")


def get_data_hora_atual():
    """ Define a função que retorna a data e hora atual do sistema. """
    return time.strftime("%d/%m/%Y %H:%M:%S")


def cria_diretorio(path, recursivo=False):
    """ Define a Função para Cria um diretório, se não existir. """
    if not os.path.exists(path):
        if recursivo:
            os.makedirs(path)
        else:
            os.mkdir(path)

def salvaDataFrameArquivo(dataframe, path_arquivo):
    """ Salva os dados do dataframe no arquivo. Se o arquivo não existir será criado. """
    # if file does not exist write header 
    if not os.path.isfile(path_arquivo):
        dataframe.to_csv(path_arquivo, header='column_names', mode='a', sep=';', encoding='latin-1', decimal=',', index= False)
    else: # else it exists so append without writing the header
        dataframe.to_csv(path_arquivo, header=False, mode='a', sep=';', encoding='latin-1', decimal=',', index= False)
    
    
    
### Definição das funções epecificas.

#Sta o locale como BR.
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# url das informações dos títulos.
url_fonte = 'http://www.tesouro.fazenda.gov.br/tesouro-direto-precos-e-taxas-dos-titulos'


def getBeautifulSoup(url):
    """ Obtém BeautifulSoup da pagina. """

    #Define os Headers
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'}

    soup = None

    # Define a requisição da conexão
    con = requests.get(url, headers=headers)

    # Conectando da página
    # https://www.w3.org/Protocols/HTTP/1.1/draft-ietf-http-v11-spec-01#Status-Codes
    # Verifica o Status da Conexão. Status 200 conexão Ok.
    if con.status_code == 200:
        # Cria objeto BeautifulSoup com o conteúdo html da página
        soup = BeautifulSoup(con.content, "html.parser")

    return soup


def extraiInformacoesPagina(soup):
    """ Extrai as informações da pagina e retorna um dataframe dos pandas. """
    # Extraindo a tabela de Resgaste de Titulos
    tabela_resgate = soup.find('table', {'class': 'tabelaPrecoseTaxas sanfonado'})

    # Extrai o conteúdo do corpo da  tabela.
    body_tabela = tabela_resgate.find('tbody')

    # Extrai as linhas do cabeçalho da tabela.
    linhas_cabecalho_tabela = body_tabela.find_all('th')
    cabecalho_tabela_tratada = []

    for linha in linhas_cabecalho_tabela:
        cabecalho_tabela_tratada.append(linha.text.strip())

    # Extrai as linhas do restando corpo da tabela com os valores e descrições
    linhas_tabela = body_tabela.find_all(class_='camposTesouroDireto')
    linhas_tabela_tratada = []

    for linha in linhas_tabela:
        colunas = linha.find_all('td')
        colunas = [x.text.strip() for x in colunas]
        linhas_tabela_tratada.append(colunas)

    # Cria um dataframe com as linhas do corpo da tabela.
    df_titulos = pd.DataFrame(linhas_tabela_tratada)

    # Adiciona o cabeçalho da tabela no dataframe criado.
    df_titulos.columns = cabecalho_tabela_tratada

    return df_titulos


def converteTipoDadosDataFrame(dataframe):
    """Trata os tipos de dados das colunas"""

    #Converta Coluna "Vencimento" para data
    dataframe['Vencimento'] = pd.to_datetime(dataframe['Vencimento'])

    # Converte Coluna "Taxa de Rendimento (% a.a.)" para Float
    dataframe['Taxa de Rendimento (% a.a.)'] = dataframe['Taxa de Rendimento (% a.a.)'].apply(objToFloat)

    # Converte Coluna "Preço Unitário" para Float
    dataframe['Preço Unitário'] = dataframe['Preço Unitário'].apply(objToFloat)

    # Adiciona a coluna "Data Hora Registro" que informa a data e hora da coleta dos dados.
    dataframe['Data Hora Registro'] =  pd.to_datetime( get_data_hora_atual())
    
    
    
    return dataframe


# Taxa do imposto de renda aplicado.
def getTaxaIRPF():
    return  22.5

#Calcula o rendimento bruto, ainda sem os descontos.
def calculaRendimentoBruto(precoResgate, quantidadeCompra, valoInvestido):
    return (precoResgate *  quantidadeCompra) - valoInvestido
  
# Calcula o valor IRPF que será descontado.
def calculaValorIRPF(rendimentoBruto, taxa_IRPF):
    return rendimentoBruto * taxa_IRPF

# Calcula o rendimento após o desconto do IRPF
def calculaRendimentoDescontadoIRPF(rendimentoBruto, valorIRPF):
    return rendimentoBruto - valorIRPF

# Calcula o % do redimento  após o desconto do IRPF
def calculaPercentualRendimentoDescontadoIRPF(rendimentoDescontadoIRPF, valorIvestido):
    return rendimentoDescontadoIRPF / valorIvestido


def getTitulosCarteira():
    # Dados da planilha que contém a carteira de títulos.
    diretorio = 'base_dados'
    nome_arquivo = 'carteira_titulos_tesouro.xlsx'
    nome_aba_carteira = 'MinhaCarteiraTitulosTesouro'
     
    path_planilha_carteira = os.path.join(diretorio , nome_arquivo)
    
    # Importa os títulos da carteira
    df_carteira = pd.read_excel(path_planilha_carteira, sheet_name=nome_aba_carteira,header=1, usecols=[1,2,4,5,6,7,8,9] )
    
    return df_carteira
    


def joinDataframesTituloCarteira(df_titulos, df_carteira):
    # Faz o join dos dataframes
    df_merge = pd.merge(df_carteira, df_titulos, on='Título', how='left')
    
    #Remove as colunas que não serão usadas
    df_merge = df_merge.drop(columns = ['Tipo','Data de vencimento', 'Data Hora Registro', 'Taxa de Rendimento (% a.a.)','% Rentabilidade (a.a)'])
    
    # Renomeia algumas colunas do dataframe.
    df_merge.rename(index=str, columns={'Preço Unitário': 'Preço Resgate', 'Preço para investimento (R$)': 'Preço Compra' }, inplace=True)
    
    #Calcula a diferença entre o valor atual e valor pago
    df_merge['Preço Resgate menos Compra'] = df_merge['Preço Resgate'] - df_merge['Preço Compra']
    
    #Cria as colunas com os calculos de rendimentos
    df_merge['Rendimento Bruto']  = df_merge.apply(lambda col: calculaRendimentoBruto(col['Preço Resgate'],col['Quantidade Compra'],col['Valor Investido']), axis=1)
    df_merge['Valor IRPF (R$)'] = df_merge.apply(lambda col: calculaValorIRPF(col['Rendimento Bruto'],getTaxaIRPF()), axis=1)
    df_merge['Rendimento descontado IRPF (R$)'] = df_merge.apply(lambda col: calculaRendimentoDescontadoIRPF(col['Rendimento Bruto'], col['Valor IRPF (R$)']), axis=1)
    df_merge['Rendimento descontado IRPF %'] = df_merge.apply(lambda col: calculaPercentualRendimentoDescontadoIRPF(col['Rendimento descontado IRPF (R$)'] , col['Valor Investido']), axis=1)
    
    return df_merge



def getTitulosAnalise(nomeTitulo, df_merge):
    
    df_final = df_merge.loc[df_merge['Título'] == nomeTitulo]
    df_final.set_index(['Título', 'Data Compra'])
    
    return df_final
    

def enviaNotificacao(df_selecao_final):
    
    lista_msgs = []

    for index, row  in df_selecao_final.iterrows() : 
        nomeTitulo = row['Título']
        dataCompra = row['Data Compra']
        percRendimentodescontadoIRPF = row['Rendimento descontado IRPF %']
        valorRendimentodescontadoIRPF =row['Rendimento descontado IRPF (R$)']
        valorAtual = row['Preço Resgate']
        valorCompra =  row['Preço Compra']
        redimentoBruto = row['Rendimento Bruto']
        valorInvestido =  row['Valor Investido']
    
        mensagem = 'O título {0} comprado em {1:%d/%m/%Y} atingiu o % de Rendimento (descontado IRPF): {2:.2f}%. O Valor do Rendimento (descontado IRPF): R$ {3:.2f}. Valor atual: R$ {4:.2f}. Valor de compra: R$ {5:.2f}. Redimento Bruto: R$ {6:.2f}. Valor investido R$ {7:.2f} \n'.format( nomeTitulo, dataCompra ,percRendimentodescontadoIRPF,valorRendimentodescontadoIRPF, valorAtual, valorCompra, redimentoBruto, valorInvestido)
    
        lista_msgs.append(mensagem)
    
    for msg in lista_msgs:
        telegram_send.send(messages=[msg])
        #print(msg)



def verificaHorarioExecucao():
        
    horaInicio = 8 
    horaFim = 18
    
    hora_atual = int(time.strftime("%H"))
    
    return hora_atual >= horaInicio and hora_atual <= horaFim
       
# Função principal
def main():
    
    diretorio = 'base_dados'
    nome_arquivo = 'base_valores_titulos_tesouro.csv'  
    tituloAcompanhamento = 'Tesouro IPCA+ 2035'
    
    #Critérios para o envio da notificação
    taxaRendimento = 1.0
    valorDiferenca = 1.0
 
    cria_diretorio(diretorio)
    arquivo = os.path.join(diretorio , nome_arquivo)

    while True:
        
        if verificaHorarioExecucao():

            try:
                soap = getBeautifulSoup(url_fonte)

                if soap is not None:     
                    
                    df_titulos = extraiInformacoesPagina(soap)
                                         
                    df_titulos = converteTipoDadosDataFrame(df_titulos)        

                    df_carteira = getTitulosCarteira()
                        
                    df_merge = joinDataframesTituloCarteira(df_titulos, df_carteira)
                
                    df_final = getTitulosAnalise(tituloAcompanhamento, df_merge)

                    #Seleciona somente as linhas atingiram os critérios definidos.
                    df_selecao_final = df_final[ (df_final['Rendimento descontado IRPF %'] > taxaRendimento) & ( df_final['Preço Resgate menos Compra'] > valorDiferenca) ]

                    #Envia a notificação pelo Telegram
                    enviaNotificacao(df_selecao_final)
                               
                    salvaDataFrameArquivo(df_titulos, arquivo)
                
                    print('Dados Obtidos com sucesso.', get_data_hora_atual())
                
                else:
                    print('Falha o obter o soap.', get_data_hora_atual())

                
                time.sleep(3600)

            except:
                    print('Erro ao obter as informações da página. Hora: ',  get_data_hora_atual())
                    time.sleep(60)

        else:
            time.sleep(3600)
        


#Executa a função principal
main()


