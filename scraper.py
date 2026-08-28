"""
Módulo de Web Scraping usando Playwright.
Objetivo: Extração absoluta de Eventos Futuros contornando a violação de "Strict Mode"
e formatando corretamente os dados provenientes de tabelas HTML.
"""
import asyncio
import subprocess
import re
import os
import random
from playwright.async_api import async_playwright

async def processar_lote_cnpjs(cnpjs, fila_mensagens):
    # 1. Caminhos do Chrome e do Perfil Persistente
    caminho_chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(caminho_chrome):
        caminho_chrome = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
    caminho_perfil = r"C:\perfil_cdp_robo"
    
    print("[DEBUG] Iniciando o Chrome com Perfil Persistente (Anti-CAPTCHA via CDP)...")
    
    processo_chrome = subprocess.Popen([
        caminho_chrome,
        "--remote-debugging-port=9222",
        f"--user-data-dir={caminho_perfil}"
    ])
    
    await asyncio.sleep(4) # Tempo para o Chrome abrir a janela

    async with async_playwright() as p:
        try:
            print("[DEBUG] Conectando o Playwright ao Chrome físico...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            
            # NAVEGAÇÃO INICIAL ÚNICA
            print("[DEBUG] Acessando o portal do Simples Nacional pela primeira vez...")
            await page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/aplicacoes.aspx?id=21", timeout=60000)
            
            total = len(cnpjs)
            
            for index, cnpj_original in enumerate(cnpjs, start=1):
                print(f"\n[DEBUG] ---> Processando CNPJ {index}/{total}: {cnpj_original}")
                
                cnpj_limpo = re.sub(r'\D', '', cnpj_original)
                if not cnpj_limpo:
                    continue
                    
                try:
                    # Foca no Iframe
                    miolo_site = page.frame_locator('#frame')
                    campo_cnpj = miolo_site.locator('#Cnpj')
                    
                    try:
                        await campo_cnpj.wait_for(state="visible", timeout=15000)
                    except:
                        print("[DEBUG] Campo não encontrado. Restaurando a página inicial...")
                        await page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/aplicacoes.aspx?id=21", timeout=60000)
                        await campo_cnpj.wait_for(state="visible", timeout=45000)
                    
                    # ==========================================================
                    # Passo 2: LIMPEZA PROFUNDA E DIGITAÇÃO SEQUENCIAL
                    # ==========================================================
                    print("[DEBUG] Preparando o campo para digitação blindada...")
                    sucesso_digitacao = False
                    
                    for tentativa in range(5): 
                        await campo_cnpj.click(force=True)
                        await campo_cnpj.evaluate("node => node.value = ''") 
                        await page.wait_for_timeout(300)
                        await page.keyboard.press("Backspace") 
                        await page.wait_for_timeout(300) 
                        
                        print(f"[DEBUG] Digitando os números (Tentativa {tentativa + 1}/5)...")
                        await campo_cnpj.press_sequentially(cnpj_limpo, delay=250)
                        await page.wait_for_timeout(1000) 
                        
                        valor_na_tela = await campo_cnpj.input_value()
                        valor_na_tela_limpo = re.sub(r'\D', '', valor_na_tela)
                        
                        if valor_na_tela_limpo == cnpj_limpo:
                            print("[DEBUG] Digitação COMPLETA confirmada com sucesso!")
                            sucesso_digitacao = True
                            break
                        else:
                            print(f"[DEBUG] O site cortou números. Limpando e tentando de novo...")
                    
                    if not sucesso_digitacao:
                        raise Exception("Falha na digitação: o site rejeitou o CNPJ completo após 5 tentativas.")
                    # ==========================================================
                    
                    await page.wait_for_timeout(1000)
                    
                    # ==========================================================
                    # Passo 3: O CLIQUE COM PAUSA DRAMÁTICA
                    # ==========================================================
                    print("[DEBUG] Preparando para clicar em Consultar...")
                    botao_consultar = miolo_site.locator('button.btn-verde.h-captcha:has-text("Consultar")')
                    
                    await botao_consultar.hover()
                    tempo_pausa = random.randint(1500, 2500)
                    print(f"[DEBUG] Hesitando por {tempo_pausa/1000} segundos antes de clicar...")
                    await page.wait_for_timeout(tempo_pausa)
                    await botao_consultar.click(delay=random.randint(150, 350))
                    # ==========================================================
                    
                    # Passo 4: Aguardar resultados
                    print("[DEBUG] Aguardando resultados...")
                    await miolo_site.locator('.panel-body').first.wait_for(state="visible", timeout=60000) 
                    
                    # ==========================================================
                    # Passo 5: LEITURA ROBUSTA DOS DADOS E TABELAS
                    # ==========================================================
                    print("[DEBUG] Extraindo dados principais...")
                    nome_empresarial = await miolo_site.locator('.panel-body .spanValorVerde').nth(1).inner_text()
                    
                    painel_situacao = miolo_site.locator('.panel:has-text("Situação Atual")').last
                    situacao_texto = await painel_situacao.inner_text()
                    
                    data_optante = re.search(r"\d{2}/\d{2}/\d{4}", situacao_texto)
                    if data_optante:
                        situacao = data_optante.group()
                    else:
                        situacao = "Lucro Presumido ou Real"
                        
                    # 5.1 Expandir as "Mais informações"
                    try:
                        botao_mais_info = miolo_site.locator('text="Mais informações"')
                        if await botao_mais_info.count() > 0:
                            await botao_mais_info.first.click()
                            await page.wait_for_timeout(2000) # Tempo para a animação da gaveta abrir
                    except Exception as e:
                        print(f"[DEBUG] Botão de mais informações não clicado: {e}")
                    
                    # 5.2 Leitura Robusta: Eventos Simples Nacional
                    eventos_simples = "Não Existem"
                    try:
                        # O '.last' garante que pegamos a caixa exata e ignoramos o container gigante
                        painel_ev_simples = miolo_site.locator('.panel', has_text="Eventos Futuros (Simples Nacional)").last
                        if await painel_ev_simples.count() > 0:
                            # '.first' garante que pegamos apenas o corpo dessa caixa exata
                            corpo_simples = painel_ev_simples.locator('.panel-body').first
                            texto_bruto_simples = await corpo_simples.inner_text()
                            
                            if texto_bruto_simples.strip():
                                # Formata a tabela HTML: troca TABS (\t) por hífens e ENTERs (\n) por barras
                                txt_format = texto_bruto_simples.replace('\t', ' - ').replace('\n', ' | ')
                                # Remove o cabeçalho da tabela se ele vier junto, para ficar mais limpo
                                txt_format = txt_format.replace("Descrição do Evento - Data Efeito | ", "")
                                eventos_simples = txt_format.strip()
                    except Exception as e:
                        print(f"[DEBUG] Erro ao extrair Eventos Simples: {e}")
                        
                    # 5.3 Leitura Robusta: Eventos SIMEI
                    eventos_simei = "Não Existem"
                    try:
                        painel_ev_simei = miolo_site.locator('.panel', has_text="Eventos Futuros (SIMEI)").last
                        if await painel_ev_simei.count() > 0:
                            corpo_simei = painel_ev_simei.locator('.panel-body').first
                            texto_bruto_simei = await corpo_simei.inner_text()
                            
                            if texto_bruto_simei.strip():
                                txt_format = texto_bruto_simei.replace('\t', ' - ').replace('\n', ' | ')
                                txt_format = txt_format.replace("Descrição do Evento - Data Efeito | ", "")
                                eventos_simei = txt_format.strip()
                    except Exception as e:
                        print(f"[DEBUG] Erro ao extrair Eventos SIMEI: {e}")
                    # ==========================================================
                    
                    print(f"[DEBUG] Sucesso Absoluto! CNPJ: {cnpj_limpo} processado.")

                    resultado = {
                        "CNPJ": cnpj_original,
                        "Nome Empresarial": nome_empresarial.strip(),
                        "Situação": situacao,
                        "Eventos Simples": eventos_simples,
                        "Eventos SIMEI": eventos_simei,
                        "Status": "Sucesso",
                        "Index": index,
                        "Total": total
                    }
                    
                    # Passo 6: O SEGREDO DO LOTE (O Botão Voltar)
                    if index < total:
                        print("[DEBUG] Clicando em 'Voltar' para pesquisar a próxima empresa...")
                        botao_voltar = miolo_site.locator('a.btn-verde:has-text("Voltar")')
                        if await botao_voltar.count() > 0:
                            await botao_voltar.click()
                            await page.wait_for_timeout(2500) 
                        else:
                            print("[DEBUG] Botão voltar não encontrado, recarregando...")
                            await page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/aplicacoes.aspx?id=21")
                    
                except Exception as e:
                    print(f"[ERRO DEBUG] Falha no CNPJ {cnpj_original}. Erro: {str(e)}")
                    resultado = {
                        "CNPJ": cnpj_original,
                        "Nome Empresarial": "Erro de Execução/Captcha",
                        "Situação": "-",
                        "Eventos Simples": "-",
                        "Eventos SIMEI": "-",
                        "Status": "Erro",
                        "Index": index,
                        "Total": total
                    }
                    await page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/aplicacoes.aspx?id=21", timeout=60000)
                    
                fila_mensagens.put(resultado)
                
        except Exception as e_conexao:
            print(f"[ERRO FATAL] Falha ao conectar no Chrome via CDP: {e_conexao}")
            fila_mensagens.put({
                "CNPJ": "ERRO SISTEMA", "Nome Empresarial": "Feche as abas normais do Chrome e tente de novo.",
                "Situação": "-", "Eventos Simples": "-", "Eventos SIMEI": "-", "Status": "Erro",
                "Index": 0, "Total": len(cnpjs)
            })

        finally:
            print("[DEBUG] Encerrando processos e navegador...")
            if 'browser' in locals():
                await browser.close()
            processo_chrome.terminate()
            fila_mensagens.put("FIM")

def iniciar_scraper(cnpjs, fila_mensagens):
    asyncio.run(processar_lote_cnpjs(cnpjs, fila_mensagens))