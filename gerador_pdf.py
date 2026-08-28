"""
Módulo Gerador de PDF.
Objetivo: Receber uma lista de dicionários com os resultados do Simples Nacional 
e formatá-los numa tabela em um arquivo PDF profissional.
"""
from fpdf import FPDF

def exportar_para_pdf(lista_resultados, caminho_arquivo):
    """
    Cria um PDF em formato Paisagem (Landscape) com os dados extraídos.
    
    :param lista_resultados: Lista de dicionários com os dados do scraper.
    :param caminho_arquivo: Onde o PDF será salvo (ex: 'C:/relatorio.pdf').
    """
    print("[DEBUG] Iniciando a geração do PDF...")
    
    # Inicia o PDF em formato 'L' (Landscape/Paisagem), unidade em milímetros, tamanho A4
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Configura a fonte do Título
    pdf.set_font("Arial", style='B', size=16)
    # Cria uma célula centralizada para o título principal
    pdf.cell(277, 15, txt="Relatório de Consulta - Simples Nacional", ln=True, align='C')
    pdf.ln(5) # Pula uma pequena linha
    
    # ---------------------------------------------------------
    # CABEÇALHO DA TABELA
    # ---------------------------------------------------------
    pdf.set_font("Arial", style='B', size=10)
    
    # Definimos as larguras exatas de cada coluna em milímetros (Soma total ~277mm para A4 Paisagem)
    larguras = [35, 95, 45, 50, 52]
    cabecalhos = ["CNPJ", "Nome Empresarial", "Situação Atual", "Ev. Futuros (Simples)", "Ev. Futuros (SIMEI)"]
    
    # Loop para desenhar o cabeçalho
    for i in range(len(cabecalhos)):
        # border=1 desenha a borda da tabela, align='C' centraliza o texto
        pdf.cell(larguras[i], 10, txt=cabecalhos[i], border=1, align='C')
    
    pdf.ln() # Quebra a linha para começar a preencher os dados
    
    # ---------------------------------------------------------
    # PREENCHIMENTO DOS DADOS (LINHAS)
    # ---------------------------------------------------------
    pdf.set_font("Arial", size=9)
    
    for resultado in lista_resultados:
        # Se houve erro no CNPJ, podemos pular ou escrever o erro. Aqui vamos escrever tudo.
        cnpj = resultado.get("CNPJ", "")
        
        # Como o Nome Empresarial pode ser gigante, cortamos para caber na célula (ex: max 45 caracteres)
        nome = resultado.get("Nome Empresarial", "")[:45] 
        
        situacao = resultado.get("Situação", "")[:25]
        ev_simples = resultado.get("Eventos Simples", "")[:28]
        ev_simei = resultado.get("Eventos SIMEI", "")[:28]
        
        # Desenha a linha da tabela para esta empresa
        pdf.cell(larguras[0], 10, txt=cnpj, border=1, align='C')
        pdf.cell(larguras[1], 10, txt=nome, border=1, align='L') # Nome alinhado à esquerda
        pdf.cell(larguras[2], 10, txt=situacao, border=1, align='C')
        pdf.cell(larguras[3], 10, txt=ev_simples, border=1, align='C')
        pdf.cell(larguras[4], 10, txt=ev_simei, border=1, align='C')
        pdf.ln() # Pula para a próxima linha
        
    # Salva o arquivo no caminho escolhido pelo usuário
    pdf.output(caminho_arquivo)
    print(f"[DEBUG] PDF salvo com sucesso em: {caminho_arquivo}")