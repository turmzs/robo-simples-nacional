# setup.py
import os

# Estrutura dos arquivos e seus conteúdos
arquivos = {
    "requirements.txt": """playwright==1.42.0
pandas==2.2.1
openpyxl==3.1.2
""",
    
    "scraper.py": '''"""
Módulo de Web Scraping usando Playwright.
Responsável por acessar o portal, consultar os CNPJs e retornar os dados.
"""
import asyncio
from playwright.async_api import async_playwright
import re

async def processar_lote_cnpjs(cnpjs, fila_mensagens):
    """
    Inicia o navegador e itera sobre a lista de CNPJs.
    """
    async with async_playwright() as p:
        # Lança o navegador em modo invisível (headless=True)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        total = len(cnpjs)
        
        for index, cnpj in enumerate(cnpjs, start=1):
            try:
                # 1. Navegar até a URL
                await page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/aplicacoes.aspx?id=21", timeout=60000)
                
                # NOTA: Os seletores abaixo (ex: '#Cnpj', '#btnConsultar') são exemplos. 
                # Você precisará inspecionar o site real para colocar os IDs corretos.
                
                # 2. Preencher o CNPJ e consultar
                await page.wait_for_selector('input[name="cnpj"]', timeout=10000) # Ajuste o seletor
                await page.fill('input[name="cnpj"]', cnpj)
                await page.click('button:has-text("Consultar")') # Ajuste o seletor
                
                # Aguarda o carregamento da página de resultados
                await page.wait_for_load_state('networkidle')
                
                # 3. Extrair dados primários
                # Ajuste os seletores conforme o HTML real do site
                nome_empresarial = await page.inner_text('.nome-empresarial', timeout=5000) 
                situacao_texto = await page.inner_text('.situacao-simples', timeout=5000)
                
                # 4. Regra de Negócio: Situação no Simples Nacional
                data_optante = re.search(r"\\d{2}/\\d{2}/\\d{4}", situacao_texto)
                if data_optante:
                    situacao = data_optante.group()
                else:
                    situacao = "Lucro Presumido ou Real"
                    
                # 5. Expansão de Conteúdo (Mais informações)
                try:
                    await page.click('text="Mais informações"', timeout=3000)
                    await page.wait_for_timeout(1000) # Aguarda animação de expansão
                except:
                    pass # Se não houver botão, segue em frente
                
                # 6. Extração de Eventos Futuros
                try:
                    eventos_simples = await page.inner_text('.eventos-futuros-simples', timeout=3000)
                except:
                    eventos_simples = "Não Existem"
                    
                try:
                    eventos_simei = await page.inner_text('.eventos-futuros-simei', timeout=3000)
                except:
                    eventos_simei = "Não Existem"
                
                # Monta o dicionário de resultado
                resultado = {
                    "CNPJ": cnpj,
                    "Nome Empresarial": nome_empresarial.strip(),
                    "Situação": situacao,
                    "Eventos Simples": eventos_simples.strip(),
                    "Eventos SIMEI": eventos_simei.strip(),
                    "Status": "Sucesso",
                    "Index": index,
                    "Total": total
                }
                
            except Exception as e:
                # Tratamento de erro para CNPJ falho
                resultado = {
                    "CNPJ": cnpj,
                    "Nome Empresarial": "Erro / Não Encontrado",
                    "Situação": "-",
                    "Eventos Simples": "-",
                    "Eventos SIMEI": "-",
                    "Status": "Erro",
                    "Index": index,
                    "Total": total
                }
                
            # Envia o resultado para a interface gráfica via Fila (Queue)
            fila_mensagens.put(resultado)
            
        await browser.close()
        fila_mensagens.put("FIM")

def iniciar_scraper(cnpjs, fila_mensagens):
    """
    Função ponte para rodar o asyncio loop em uma thread separada.
    """
    asyncio.run(processar_lote_cnpjs(cnpjs, fila_mensagens))
''',

    "main.py": '''"""
Interface Gráfica do Usuário (GUI) usando Tkinter.
Recebe os dados, inicia o scraper e exporta para Excel.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import pandas as pd
from scraper import iniciar_scraper

class AppSimplesNacional:
    def __init__(self, root):
        self.root = root
        self.root.title("Consulta Lote - Simples Nacional")
        self.root.geometry("900x600")
        
        self.fila = queue.Queue()
        self.dados_tabela = []
        self.thread_scraper = None
        
        self.criar_widgets()
        self.verificar_fila()

    def criar_widgets(self):
        # Frame Superior (Entrada de Dados)
        frame_top = tk.Frame(self.root)
        frame_top.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(frame_top, text="Lista de CNPJs (um por linha):").pack(anchor=tk.W)
        self.text_cnpjs = tk.Text(frame_top, height=5)
        self.text_cnpjs.pack(fill=tk.X, pady=5)
        
        btn_frame = tk.Frame(frame_top)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="Carregar Arquivo", command=self.carregar_arquivo).pack(side=tk.LEFT, padx=5)
        self.btn_iniciar = tk.Button(btn_frame, text="Iniciar Consulta", command=self.iniciar_consulta, bg="green", fg="white")
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)
        self.btn_exportar = tk.Button(btn_frame, text="Exportar para Excel", command=self.exportar_excel, state=tk.DISABLED)
        self.btn_exportar.pack(side=tk.RIGHT, padx=5)
        
        # Frame do Meio (Progresso)
        frame_mid = tk.Frame(self.root)
        frame_mid.pack(pady=5, padx=10, fill=tk.X)
        
        self.lbl_progresso = tk.Label(frame_mid, text="Aguardando...")
        self.lbl_progresso.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(frame_mid, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Frame Inferior (Tabela de Resultados)
        frame_bottom = tk.Frame(self.root)
        frame_bottom.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        colunas = ("cnpj", "nome", "situacao", "eventos_sn", "eventos_simei")
        self.tree = ttk.Treeview(frame_bottom, columns=colunas, show="headings")
        
        self.tree.heading("cnpj", text="CNPJ")
        self.tree.heading("nome", text="Nome Empresarial")
        self.tree.heading("situacao", text="Situação Simples")
        self.tree.heading("eventos_sn", text="Eventos Futuros (SN)")
        self.tree.heading("eventos_simei", text="Eventos Futuros (SIMEI)")
        
        self.tree.column("cnpj", width=120)
        self.tree.column("nome", width=200)
        self.tree.column("situacao", width=120)
        self.tree.column("eventos_sn", width=150)
        self.tree.column("eventos_simei", width=150)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
    def carregar_arquivo(self):
        """Lê um arquivo .txt e insere no Text box"""
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as file:
                self.text_cnpjs.delete("1.0", tk.END)
                self.text_cnpjs.insert(tk.END, file.read())
                
    def iniciar_consulta(self):
        texto = self.text_cnpjs.get("1.0", tk.END).strip()
        if not texto:
            messagebox.showwarning("Aviso", "Insira pelo menos um CNPJ.")
            return
            
        cnpjs = [c.strip() for c in texto.split('\\n') if c.strip()]
        
        # Reseta a interface
        self.tree.delete(*self.tree.get_children())
        self.dados_tabela.clear()
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_exportar.config(state=tk.DISABLED)
        self.progress_bar["maximum"] = len(cnpjs)
        self.progress_bar["value"] = 0
        
        # Inicia a Thread do Scraper
        self.thread_scraper = threading.Thread(target=iniciar_scraper, args=(cnpjs, self.fila))
        self.thread_scraper.daemon = True # Thread morre se o app fechar
        self.thread_scraper.start()
        
    def verificar_fila(self):
        """Verifica a cada 100ms se há novas mensagens do Scraper"""
        try:
            while not self.fila.empty():
                msg = self.fila.get_nowait()
                
                if msg == "FIM":
                    self.lbl_progresso.config(text="Consulta Finalizada!")
                    self.btn_iniciar.config(state=tk.NORMAL)
                    self.btn_exportar.config(state=tk.NORMAL)
                    messagebox.showinfo("Concluído", "Processamento finalizado com sucesso!")
                else:
                    # Atualiza a tabela
                    valores = (msg["CNPJ"], msg["Nome Empresarial"], msg["Situação"], msg["Eventos Simples"], msg["Eventos SIMEI"])
                    self.tree.insert("", tk.END, values=valores)
                    self.dados_tabela.append(valores)
                    
                    # Atualiza progresso
                    self.progress_bar["value"] = msg["Index"]
                    self.lbl_progresso.config(text=f"Processado {msg['Index']} de {msg['Total']}")
        except queue.Empty:
            pass
            
        # Continua verificando
        self.root.after(100, self.verificar_fila)
        
    def exportar_excel(self):
        """Exporta os dados armazenados para um arquivo Excel"""
        if not self.dados_tabela:
            return
            
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if filepath:
            df = pd.DataFrame(self.dados_tabela, columns=["CNPJ", "Nome Empresarial", "Situação Simples Nacional", "Eventos Futuros (Simples Nacional)", "Eventos Futuros (SIMEI)"])
            df.to_excel(filepath, index=False)
            messagebox.showinfo("Sucesso", f"Arquivo salvo em:\\n{filepath}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppSimplesNacional(root)
    root.mainloop()
'''
}

# Criando os arquivos no diretório atual
for nome_arquivo, conteudo in arquivos.items():
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo)
        
print("Estrutura do projeto criada com sucesso!")
print("Arquivos gerados: requirements.txt, scraper.py, main.py")