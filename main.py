"""
Módulo Principal (Interface Gráfica)
Objetivo: Criar a tela do aplicativo, gerenciar a entrada de CNPJs,
iniciar o robô em segundo plano e exportar os resultados.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import pandas as pd # Para exportar para Excel

# Importamos as nossas próprias funções dos outros arquivos
from scraper import iniciar_scraper
from gerador_pdf import exportar_para_pdf

class SimplesNacionalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Robô Simples Nacional - Consulta Lote")
        self.root.geometry("900x600")
        
        # Variável para armazenar os resultados que o robô encontrar
        self.resultados_finais = []
        
        # A "Fila" (tubo de comunicação) entre o robô e a tela
        self.fila_mensagens = queue.Queue()

        self.criar_interface()

    def criar_interface(self):
        """Desenha todos os botões, caixas de texto e tabelas na tela."""
        # --- ÁREA DE ENTRADA DE DADOS ---
        frame_entrada = tk.Frame(self.root, pady=10)
        frame_entrada.pack(fill=tk.X, padx=10)

        tk.Label(frame_entrada, text="Cole os CNPJs abaixo (um por linha):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.caixa_texto_cnpjs = tk.Text(frame_entrada, height=5, width=40)
        self.caixa_texto_cnpjs.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
        
        self.btn_iniciar = tk.Button(frame_entrada, text="▶ Iniciar Consulta", bg="green", fg="white", font=("Arial", 10, "bold"), command=self.iniciar_consulta)
        self.btn_iniciar.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=10)

        # --- BARRA DE PROGRESSO E STATUS ---
        frame_status = tk.Frame(self.root)
        frame_status.pack(fill=tk.X, padx=10, pady=5)
        
        self.label_status = tk.Label(frame_status, text="Status: Aguardando...", fg="blue")
        self.label_status.pack(side=tk.LEFT)
        
        self.progresso = ttk.Progressbar(frame_status, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progresso.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

        # --- TABELA DE RESULTADOS (Treeview) ---
        frame_tabela = tk.Frame(self.root)
        frame_tabela.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        colunas = ("CNPJ", "Nome", "Situação", "Ev. Simples", "Ev. SIMEI")
        self.tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings")
        
        # Configuração dos cabeçalhos da tabela
        for col in colunas:
            self.tabela.heading(col, text=col)
            self.tabela.column(col, width=150, anchor=tk.CENTER)
            
        self.tabela.column("Nome", width=250, anchor=tk.W) # O nome precisa de mais espaço

        # Barra de rolagem para a tabela
        scrollbar = ttk.Scrollbar(frame_tabela, orient=tk.VERTICAL, command=self.tabela.yview)
        self.tabela.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tabela.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- ÁREA DE EXPORTAÇÃO ---
        frame_botoes = tk.Frame(self.root, pady=10)
        frame_botoes.pack(fill=tk.X, padx=10)

        self.btn_excel = tk.Button(frame_botoes, text="Salvar Excel", command=self.salvar_excel, state=tk.DISABLED)
        self.btn_excel.pack(side=tk.RIGHT, padx=5)

        self.btn_pdf = tk.Button(frame_botoes, text="Salvar PDF", command=self.salvar_pdf, state=tk.DISABLED)
        self.btn_pdf.pack(side=tk.RIGHT, padx=5)

    def iniciar_consulta(self):
        """Prepara os dados e inicia o robô em uma linha de trabalho paralela."""
        texto = self.caixa_texto_cnpjs.get("1.0", tk.END).strip()
        if not texto:
            messagebox.showwarning("Aviso", "Por favor, cole ao menos um CNPJ para iniciar.")
            return

        # Separa o texto em uma lista de linhas (ignorando linhas em branco)
        lista_cnpjs = [linha.strip() for linha in texto.split("\n") if linha.strip()]
        
        if not lista_cnpjs:
            return

        # Prepara a interface para o trabalho
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_excel.config(state=tk.DISABLED)
        self.btn_pdf.config(state=tk.DISABLED)
        self.tabela.delete(*self.tabela.get_children()) # Limpa a tabela antiga
        self.resultados_finais.clear()
        
        self.progresso["maximum"] = len(lista_cnpjs)
        self.progresso["value"] = 0
        self.label_status.config(text="Status: Iniciando navegador e verificando proteção...")

        # Inicia a Thread do robô (para não congelar a tela)
        # Passamos a lista de CNPJs e a fila de mensagens para ele falar conosco
        thread_robo = threading.Thread(target=iniciar_scraper, args=(lista_cnpjs, self.fila_mensagens))
        thread_robo.daemon = True # Garante que o robô fecha se fecharmos a janela
        thread_robo.start()

        # Inicia o "olheiro" que vai ficar a ler as mensagens do robô
        self.root.after(100, self.verificar_fila)

    def verificar_fila(self):
        """Verifica a cada 0.1 segundo se o robô mandou algum resultado."""
        try:
            # Puxa uma mensagem do tubo (se houver)
            mensagem = self.fila_mensagens.get_nowait()
            
            if mensagem == "FIM":
                # O robô avisou que terminou todo o lote
                self.label_status.config(text="Status: Consulta Finalizada com Sucesso!")
                self.btn_iniciar.config(state=tk.NORMAL)
                self.btn_excel.config(state=tk.NORMAL)
                self.btn_pdf.config(state=tk.NORMAL)
                messagebox.showinfo("Concluído", "Todas as consultas foram finalizadas.")
                return # Sai da função, não chama o after novamente
                
            elif isinstance(mensagem, dict):
                # O robô mandou o dicionário com os dados de uma empresa
                self.resultados_finais.append(mensagem)
                
                # Atualiza a tabela na tela
                valores = (
                    mensagem["CNPJ"],
                    mensagem["Nome Empresarial"],
                    mensagem["Situação"],
                    mensagem["Eventos Simples"],
                    mensagem["Eventos SIMEI"]
                )
                self.tabela.insert("", tk.END, values=valores)
                
                # Atualiza a barra de progresso
                self.progresso["value"] = mensagem["Index"]
                self.label_status.config(text=f"Status: Processado {mensagem['Index']} de {mensagem['Total']}")
                
        except queue.Empty:
            pass # A fila está vazia, o robô ainda está a pensar

        # Se não foi "FIM", agenda para olhar a fila de novo daqui a 100 milissegundos
        self.root.after(100, self.verificar_fila)

    def salvar_excel(self):
        """Exporta a lista de resultados guardada na memória para um arquivo .xlsx"""
        caminho = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Salvar Relatório Excel")
        if caminho:
            try:
                # Transforma a nossa lista de dicionários numa tabela do Pandas e salva
                df = pd.DataFrame(self.resultados_finais)
                # Removemos colunas técnicas (como Index e Total) antes de salvar
                colunas_para_remover = ["Index", "Total", "Status"]
                df = df.drop(columns=[col for col in colunas_para_remover if col in df.columns], errors='ignore')
                
                df.to_excel(caminho, index=False)
                messagebox.showinfo("Sucesso", "Arquivo Excel salvo com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar Excel:\n{str(e)}")

    def salvar_pdf(self):
        """Exporta a lista usando a função do nosso arquivo gerador_pdf.py"""
        caminho = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], title="Salvar Relatório PDF")
        if caminho:
            try:
                exportar_para_pdf(self.resultados_finais, caminho)
                messagebox.showinfo("Sucesso", "Arquivo PDF salvo com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar PDF:\n{str(e)}")


# Ponto de partida do programa
if __name__ == "__main__":
    janela_principal = tk.Tk()
    app = SimplesNacionalApp(janela_principal)
    janela_principal.mainloop()