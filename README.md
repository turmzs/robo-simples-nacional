# 🤖 Robô Simples Nacional - Consulta Lote (Anti-CAPTCHA)

Um aplicativo desktop desenvolvido em Python (Tkinter + Playwright) para automatizar consultas em lote no portal do Simples Nacional da Receita Federal do Brasil.

O grande diferencial deste projeto é a sua **Arquitetura Anti-Detecção**. Ele utiliza a técnica de Sequestro de Sessão via CDP (Chrome DevTools Protocol) com Perfil Persistente, permitindo contornar as severas proteções de comportamento de robô (hCaptcha/Cloudflare) do governo.

## ✨ Funcionalidades

- **Consulta em Lote:** Processa dezenas ou centenas de CNPJs de forma contínua.
- **Bypass de Proteção (CDP):** Utiliza o Google Chrome físico do usuário na porta 9222, salvando um perfil persistente em `C:\perfil_cdp_robo`.
- **Dinâmica de Digitação (Keystroke Dynamics):** Simulação de digitação humana com pausas aleatórias e limpeza profunda de campos via JavaScript para evitar erros na máscara do site.
- **Interface Gráfica (GUI):** Tela amigável construída com `tkinter`, exibição de resultados em tempo real (Treeview) e barra de progresso.
- **Multithreading:** O scraper roda em segundo plano através de Threads e fila de mensagens (`queue`), não congelando a interface gráfica.
- **Exportação Dupla:** Gera relatórios em `.xlsx` (usando Pandas) e `.pdf` (usando FPDF em formato paisagem).

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Interface:** Tkinter
- **Web Scraping:** Playwright (async)
- **Manipulação de Dados:** Pandas
- **Geração de PDF:** FPDF
- **Gerenciador de Pacotes:** `uv` (Recomendado para ultra-velocidade)

## 🚀 Como instalar e executar

### 1. Pré-requisitos

- Python instalado na máquina.
- Google Chrome padrão instalado.
- Ferramenta `uv` instalada globalmente (`pip install uv`).

### 2. Configurando o Ambiente Virtual

Clone este repositório e abra o terminal na pasta do projeto:

```bash
# Cria o ambiente virtual
uv venv

# Ativa o ambiente virtual (Windows)
.venv\Scripts\activate
