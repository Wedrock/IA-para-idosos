import google.generativeai as genai

SYSTEM_INSTRUCTION = (
    "Você é um assistente de tecnologia extremamente paciente, amigável e "
    "muito didático, especializado em ajudar idosos que têm dificuldade em "
    "usar celulares e aplicativos. "
    "Suas respostas devem ser dadas em passos curtos, usando linguagem simples "
    "e evitando jargões técnicos. Lembre-se que o usuário é um idoso que "
    "pode não saber termos como 'interface', 'widget', 'cache', 'app', 'download', "
    "ou 'clicar' (prefira 'tocar' ou 'apertar'). "
    "Responda com empatia e sempre pergunte se o usuário conseguiu realizar o passo antes de sugerir o próximo."
)


def main():
    assistente_falante = True
    ligar_microfone = True

    genai.configure(api_key="AIzaSyBTUjOg7wL6_7k951vDxg424IMxmdbcmNY")
    model = genai.GenerativeModel(
        'gemini-2.5-flash', 
        system_instruction=SYSTEM_INSTRUCTION 
    )
    chat = model.start_chat(history=[])

    if assistente_falante:
        import pyttsx3
        engine = pyttsx3.init()

        voices = engine.getProperty('voices')
        engine.setProperty('rate', 180) 

        print("\nLista de Vozes - Verifique o número\n")
        for indice, vozes in enumerate(voices):  
            print(indice, vozes.name)
        voz = 0
        engine.setProperty('voice', voices[voz].id)

    if ligar_microfone:
        import speech_recognition as sr  
        r = sr.Recognizer()
        mic = sr.Microphone()

    bem_vindo = "# Bem Vindo ao assistente com IA para idosos #"
    print("")
    print(len(bem_vindo) * "#")
    print(bem_vindo)
    print(len(bem_vindo) * "#")
    print("###   Digite 'desligar' para encerrar    ###")
    print("")

    while True:
        if ligar_microfone:
            with mic as fonte:
                r.adjust_for_ambient_noise(fonte)
                print("Fale alguma coisa (ou diga 'desligar')")
                audio = r.listen(fonte)
                print("Enviando para reconhecimento")
                try:
                    texto = r.recognize_google(audio, language="pt-BR")
                    print("Você disse: {}".format(texto))
                except sr.UnknownValueError: 
                    print("Não entendi o que você disse. Por favor, repita.")
                    texto = ""
                except Exception as e:
                    print("Ocorreu um erro no microfone. Erro:", e)
                    texto = ""
        else:
            texto = input("Escreva sua mensagem (ou #sair): ")

        if not texto:
            continue

        if texto.lower() == "desligar" or texto.lower() == "#sair":  
            break

        try:
            response = chat.send_message(texto)
            print("Gemini:", response.text, "\n")

            if assistente_falante:
                engine.say(response.text)
                engine.runAndWait()

        except Exception as e:
            erro_msg = "Desculpe, a conexão com o assistente falhou. Verifique sua chave de acesso ('sua-api-key') ou sua conexão com a internet. Erro: {}".format(
                e)
            print(erro_msg)
            if assistente_falante:
                engine.say("Desculpe, a conexão com o assistente falhou. Por favor, tente novamente mais tarde.")
                engine.runAndWait()

    print("Encerrando Chat")


if __name__ == '__main__':

    main()