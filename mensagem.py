import os
import sys
import time
import re
import tempfile
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# --- NOVAS IMPORTAÇÕES PARA ÁUDIO ---
try:
    import speech_recognition as sr
    from gtts import gTTS
    import pygame

    HAVE_AUDIO = True
except ImportError:
    HAVE_AUDIO = False
    print("AVISO: Bibliotecas de áudio não encontradas.")
    print("Instale com: pip install SpeechRecognition gTTS pygame pyaudio")
    print("O modo de voz será desativado, funcionando apenas texto.\n")

# 1. Configuração de Ambiente e Segurança
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERRO CRÍTICO: Chave de API não encontrada.")
    print("Certifique-se de ter criado o arquivo .env com a variável GEMINI_API_KEY")
    input("Pressione Enter para sair...")
    sys.exit()

genai.configure(api_key=api_key)

# 2. Configuração do Modelo e Persona
SYSTEM_INSTRUCTION = (
    "Você é um assistente de tecnologia extremamente paciente, amigável e "
    "muito didático, especializado em ajudar idosos que têm dificuldade em "
    "usar celulares e aplicativos. "
    "Suas respostas devem ser dadas em passos curtos, usando linguagem simples "
    "e evitando jargões técnicos. Lembre-se que o usuário é um idoso que "
    "pode não saber termos como 'interface', 'widget', 'cache', 'app', 'download', "
    "ou 'clicar' (prefira 'tocar' ou 'apertar'). "
    "Responda com empatia e sempre pergunte se o usuário conseguiu realizar o passo antes de sugerir o próximo."
    "Seja breve nas respostas faladas."
)

generation_config = {
    "temperature": 0.4,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

# --- DETECÇÃO AUTOMÁTICA DE MODELO ---
print("Conectando ao Google para verificar modelos...")
model_name = None

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            if 'flash' in m.name:
                model_name = m.name
                break
            elif 'gemini-pro' in m.name:
                model_name = m.name

    if not model_name:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_name = m.name
                break
except Exception:
    pass

if not model_name:
    model_name = 'gemini-1.5-flash'

print(f"Modelo selecionado: {model_name}")

model = genai.GenerativeModel(
    model_name=model_name,
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config=generation_config
)

# 3. Inicialização da Interface Rica
console = Console()


# --- FUNÇÕES DE VOZ ---

def limpar_markdown(texto):
    """Remove caracteres especiais do Markdown para a leitura ficar limpa."""
    # Remove negrito (** ou __)
    texto = re.sub(r'\*\*(.*?)\*\*', r'\1', texto)
    texto = re.sub(r'__(.*?)__', r'\1', texto)
    # Remove itálico (* ou _)
    texto = re.sub(r'\*(.*?)\*', r'\1', texto)
    # Remove cabeçalhos (##)
    texto = re.sub(r'#+\s?', '', texto)
    return texto


def falar_mensagem(texto):
    """Converte texto em áudio e reproduz."""
    if not HAVE_AUDIO:
        return

    try:
        texto_limpo = limpar_markdown(texto)

        # Cria o áudio em um arquivo temporário
        tts = gTTS(text=texto_limpo, lang='pt')

        # Usa tempfile para garantir que o arquivo seja único e não dê erro de permissão
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)  # Fecha o descritor de arquivo de baixo nível

        tts.save(path)

        # Inicializa o mixer do pygame se não estiver rodando
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        # Aguarda terminar de falar
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        # Tenta limpar o arquivo (pode falhar no Windows se ainda estiver 'lockado', então ignoramos erro)
        try:
            os.remove(path)
        except:
            pass

    except Exception as e:
        console.print(f"[dim red]Erro ao tentar falar: {e}[/dim red]")


def ouvir_microfone():
    """Escuta o microfone e retorna o texto falado."""
    if not HAVE_AUDIO:
        return None

    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        # Ajuste de ruído ambiente
        console.print("[dim]Ajustando ruído ambiente... aguarde.[/dim]")
        recognizer.adjust_for_ambient_noise(source, duration=1)

        console.print("\n[bold green]🎤 PODE FALAR AGORA...[/bold green]")
        try:
            # Timeout: espera 5 segundos por fala. Phrase_time_limit: corta se falar por mais de 10s
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)

            console.print("[dim]Processando áudio...[/dim]")
            texto = recognizer.recognize_google(audio, language='pt-BR')
            console.print(f"[green]Você disse:[/green] {texto}")
            return texto

        except sr.WaitTimeoutError:
            console.print("[yellow]Não ouvi nada.[/yellow]")
            return None
        except sr.UnknownValueError:
            console.print("[yellow]Não entendi o que foi dito.[/yellow]")
            return None
        except Exception as e:
            console.print(f"[red]Erro no microfone: {e}[/red]")
            return None


# --- LOOP PRINCIPAL ---

def main():
    chat = model.start_chat(history=[])

    console.print(Panel.fit(
        "[bold cyan]Assistente de Voz para Terceira Idade[/bold cyan]\n"
        "Fale ou digite sua dúvida.\n"
        "[dim]Diga 'sair' ou digite para encerrar.[/dim]",
        title="Bem-vindo", border_style="green"
    ))

    # Mensagem de boas vindas falada
    falar_mensagem("Olá! Sou seu assistente virtual. Como posso ajudar hoje?")

    while True:
        texto_usuario = None

        # 1. Tenta ouvir primeiro (se tiver áudio ativado)
        if HAVE_AUDIO:
            console.print(
                "\n[bold yellow]Escolha:[/bold yellow] [1] Falar no Microfone  [2] Digitar (ou aguarde para falar)")
            opcao = input("> ")  # Se o usuário apertar Enter vazio, tenta ouvir

            if opcao == "" or opcao == "1":
                texto_usuario = ouvir_microfone()

        # 2. Se não ouviu nada ou usuário quis digitar
        if not texto_usuario:
            console.print("\n[bold yellow]Digite sua dúvida:[/bold yellow]")
            texto_usuario = input("> ")

        # Verifica comandos de saída
        if texto_usuario.lower() in ["sair", "tchau", "encerrar", "desligar"]:
            msg_final = "Foi um prazer ajudar! Até logo."
            console.print(f"[bold green]{msg_final}[/bold green]")
            falar_mensagem(msg_final)
            break

        if not texto_usuario.strip():
            continue

        # 3. Envia para o Gemini
        try:
            with console.status("[bold green]Pensando na resposta...[/bold green]", spinner="dots"):
                response = chat.send_message(texto_usuario)

            # 4. Mostra e Fala a resposta
            console.print("\n[bold cyan]Assistente:[/bold cyan]")
            console.print(Markdown(response.text))
            console.print("-" * 50, style="dim")

            # Fala a resposta em voz alta
            falar_mensagem(response.text)

        except Exception as e:
            console.print(f"[bold red]Erro de conexão:[/bold red] {e}")


if __name__ == "__main__":
    main()