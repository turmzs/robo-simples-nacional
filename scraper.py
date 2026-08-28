"""
Módulo de Web Scraping usando Playwright.
Objetivo: Blindagem contra instabilidades e lentidões do servidor da Receita Federal.
Implementa um loop de re-tentativas por CNPJ e recarregamento forçado de página.
"""
import asyncio
import subprocess
import re
import os
import random
from playwright.async_api import async_playwright

async def processar_lote_cnpjs(cnpjs, fila_mensagens):
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
    
    await asyncio.sleep(4)

    async with async_playwright() as p:
        try:
            print("[DEBUG] Conectando o Playwright ao Chrome físico...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            
            url_portal = "https://www8.receita.fazenda.gov.br/SimplesNacional/aplicacoes.aspx?id=21"
            print("[DEBUG] Acessando o portal do Simples Nacional...")
            await page.goto(url_portal, timeout=90000)
            
            total = len(cnpjs)
            
            for index, cnpj_original in enumerate(cnpjs, start=1):
                print(f"\n[DEBUG] ---> Processando CNPJ {index}/{total}: {cnpj_original}")
                
                cnpj_limpo = re.sub(r'\D', '', cnpj_original)
                if not cnpj_limpo:
                    continue
                
                sucesso_cnpj = False
                resultado = None
                max_tentativas_cnpj = 2  # Dá até 2 chances para cada CNPJ se o site falhar/atrasar
                
                for tentativa_cnpj in range(1, max_tentativas_cnpj + 1):
                    try:
                        print(f"[DEBUG] Tentativa {tentativa_cnpj}/{max_tentativas_cnpj} para o CNPJ: {cnpj_limpo}")
                        
                        miolo_site = page.frame_locator('#frame')
                        campo_cnpj = miolo_site.locator('#Cnpj')
                        
                        # Verifica se o campo do CNPJ está pronto na tela
                        try:
                            await campo_cnpj.wait_for(state="visible", timeout=15000)
                        except:
                            print("[DEBUG] Formulário não respondeu. Recarregando a página do portal...")
                            await page.goto(url_portal, timeout=90000)
                            await campo_cnpj.wait_for(state="visible", timeout=45000)

                        # DIGITAÇÃO HUMANIZADA
                        await campo_cnpj.click(force=True)
                        await campo_cnpj.evaluate("node => node.value = ''") 
                        await page.wait_for_timeout(300)
                        await page.keyboard.press("Backspace") 
                        await page.wait_for_timeout(300) 
                        
                        await campo_cnpj.press_sequentially(cnpj_limpo, delay=200)
                        await page.wait_for_timeout(800) 
                        
                        valor_na_tela = await campo_cnpj.input_value()
                        if re.sub(r'\D', '', valor_na_tela) != cnpj_limpo:
                            print("[DEBUG] Máscara do site falhou. Tentando reescrever...")
                            await campo_cnpj.evaluate("node => node.value = ''")
                            await campo_cnpj.press_sequentially(cnpj_limpo, delay=250)

                        await page.wait_for_timeout(800)
                        
                        # CLIQUE EM CONSULTAR
                        botao_consultar = miolo_site.locator('button.btn-verde.h-captcha:has-text("Consultar")')
                        await botao_consultar.hover()
                        await page.wait_for_timeout(random.randint(1000, 2000))
                        await botao_consultar.click(delay=150)
                        
                        # AGUARDAR RESULTADOS (TIMEOUT AMPLIADO PARA 90 SEGUNDOS)
                        print("[DEBUG] Aguardando resposta do servidor da Receita Federal...")
                        await miolo_site.locator('.panel-body').first.wait_for(state="visible", timeout=90000) 
                        
                        # EXTRAÇÃO DOS DADOS
                        print("[DEBUG] Extraindo Razão Social e Situação...")
                        nome_empresarial = await miolo_site.locator('.panel-body .spanValorVerde').nth(1).inner_text()
                        
                        painel_situacao = miolo_site.locator('.panel:has-text("Situação Atual")').last
                        situacao_texto = await painel_situacao.inner_text()
                        
                        data_optante = re.search(r"\d{2}/\d{2}/\d{4}", situacao_texto)
                        if data_optante:
                            situacao = data_optante.group()
                        else:
                            situacao = "Lucro Presumido ou Real"
                            
                        # EXPANSÃO E EXTRAÇÃO DE EVENTOS FUTUROS
                        try:
                            btn_mais_info = miolo_site.locator('#btnMaisInfo')
                            if await btn_mais_info.count() > 0 and await btn_mais_info.is_visible():
                                await btn_mais_info.click()
                                await page.wait_for_timeout(2000)
                        except Exception as e_info:
                            print(f"[DEBUG] Aviso ao expandir 'Mais Informações': {e_info}")
                        
                        eventos_simples = "Não Existem"
                        try:
                            painel_ev_simples = miolo_site.locator('.panel', has_text="Eventos Futuros (Simples Nacional)").last
                            if await painel_ev_simples.count() > 0:
                                corpo_simples = painel_ev_simples.locator('.panel-body').first
                                await corpo_simples.wait_for(state="visible", timeout=4000)
                                texto_simples = await corpo_simples.inner_text()
                                if texto_simples.strip():
                                    txt_fmt = texto_simples.replace('\t', ' - ').replace('\n', ' | ')
                                    eventos_simples = txt_fmt.replace("Descrição do Evento - Data Efeito | ", "").strip()
                        except Exception:
                            pass
                            
                        eventos_simei = "Não Existem"
                        try:
                            painel_ev_simei = miolo_site.locator('.panel', has_text="Eventos Futuros (SIMEI)").last
                            if await painel_ev_simei.count() > 0:
                                corpo_simei = painel_ev_simei.locator('.panel-body').first
                                await corpo_simei.wait_for(state="visible", timeout=4000)
                                texto_simei = await corpo_simei.inner_text()
                                if texto_simei.strip():
                                    txt_fmt = texto_simei.replace('\t', ' - ').replace('\n', ' | ')
                                    eventos_simei = txt_fmt.replace("Descrição do Evento - Data Efeito | ", "").strip()
                        except Exception:
                            pass
                        
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
                        
                        sucesso_cnpj = True
                        print(f"[DEBUG] Sucesso no CNPJ {cnpj_limpo} na tentativa {tentativa_cnpj}!")
                        
                        # NAVEGAÇÃO DE RETORNO
                        if index < total:
                            botao_voltar = miolo_site.locator('a.btn-verde:has-text("Voltar")')
                            if await botao_voltar.count() > 0:
                                await botao_voltar.click()
                                await page.wait_for_timeout(2000)
                            else:
                                await page.goto(url_portal, timeout=90000)
                        
                        break  # Concluiu com sucesso, sai do loop de re-tentativas do CNPJ
                        
                    except Exception as e_tentativa:
                        print(f"[DEBUG] Instabilidade no site durante o CNPJ {cnpj_limpo} (Tentativa {tentativa_cnpj}): {e_tentativa}")
                        # Em caso de erro/atraso, força a recarga da URL principal para limpar o estado do site
                        await page.goto(url_portal, timeout=90000)
                        await page.wait_for_timeout(2000)
                
                # Se após todas as tentativas o site ainda falhou para esse CNPJ:
                if not sucesso_cnpj:
                    resultado = {
                        "CNPJ": cnpj_original,
                        "Nome Empresarial": "Erro de Indisponibilidade do Site",
                        "Situação": "-",
                        "Eventos Simples": "-",
                        "Eventos SIMEI": "-",
                        "Status": "Erro",
                        "Index": index,
                        "Total": total
                    }
                    
                fila_mensagens.put(resultado)
                
        except Exception as e_conexao:
            print("[ERRO FATAL] Falha de Conexão CDP:", e_conexao)
            fila_mensagens.put({
                "CNPJ": "ERRO SISTEMA", 
                "Nome Empresarial": "Feche as abas normais do Chrome e tente de novo.",
                "Situação": "-", 
                "Eventos Simples": "-", 
                "Eventos SIMEI": "-", 
                "Status": "Erro",
                "Index": 0, 
                "Total": len(cnpjs)
            })

        finally:
            print("[DEBUG] Encerrando processos...")
            if 'browser' in locals():
                await browser.close()
            processo_chrome.terminate()
            fila_mensagens.put("FIM")

def iniciar_scraper(cnpjs, fila_mensagens):
    asyncio.run(processar_lote_cnpjs(cnpjs, fila_mensagens))