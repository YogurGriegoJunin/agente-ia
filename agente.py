import json
import urllib.request
import subprocess
import os
import shlex
import sys

# --- CONFIGURACIÓN ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3" 
MAX_HISTORY_CHARS = 4000

# --- HERRAMIENTAS ---
def tool_execute_command(command):
    try:
        args = shlex.split(command)
        result = subprocess.check_output(args, stderr=subprocess.STDOUT, text=True)
        return f"Resultado:\n{result}"
    except Exception as e:
        return f"Error: {str(e)}"

def tool_read_file(file_path):
    try:
        return open(os.path.normpath(file_path), 'r', encoding='utf-8').read()
    except Exception as e:
        return f"Error: {str(e)}"

def tool_list_dir(path):
    try:
        p = os.path.normpath(path)
        if not os.path.isdir(p): return "No es un directorio."
        entries = os.listdir(p)
        return "\n".join([f"[{'DIR' if os.path.isdir(os.path.join(p, e)) else 'FILE'}] {e}" for e in entries])
    except Exception as e:
        return f"Error: {str(e)}"

def tool_write_file(arg):
    try:
        if "|" not in arg: return "Error: Use formato ruta|contenido"
        path, content = arg.split("|", 1)
        with open(os.path.normpath(path), 'w', encoding='utf-8') as f:
            f.write(content)
        return "Archivo escrito con éxito."
    except Exception as e:
        return f"Error: {str(e)}"

TOOLS = {
    "execute_command": tool_execute_command,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "list_dir": tool_list_dir
}

# --- NÚCLEO ---
def call_ollama(prompt):
    data = {"model": MODEL_NAME, "prompt": prompt, "stream": False}
    try:
        req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), 
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())['response']
    except Exception as e:
        return f"Error de conexión: {str(e)}"

def run_agent(user_input):
    system_prompt = (
        "Eres un agente profesional. RESPONDE SOLO con PENSAM_AMIENTO, ACCIÓN o FINALIZADO.\n"
        "REGLA: Si sabes la respuesta por tu conocimiento, usa FINALIZADO directamente.\n"
        "REGLA: Si usas una herramienta, usa ACCIÓN y DETENTE. No alucines pasos.\n"
        "Formato:\n1. PENSAMIENTO: <razonamiento>\n2. ACCIÓN: <tool> | <arg>\n3. FINALIZADO: <respuesta>\n"
        "Tools: execute_command, read_file, write_file, list_dir"
    )
    history = f"{system_prompt}\n\nUsuario: {user_input}\n"
    print(f"\n[Agente Iniciado]\n" + "-"*20)

    for step in range(10):
        print(f"\n[Paso {step+1}/10]")
        if len(history) > MAX_HISTORY_CHARS:
            history = system_prompt + "\n\n" + history[-(MAX_HISTORY_CHARS-100):]
        
        response = call_ollama(history)
        print(f"Agente: {response}")

        if "FINALIZADO" in response:
            print("\n✅ Tarea completada."); break
        
        action_found = False
        for line in response.split('\n'):
            if "ACCIÓN:" in line:
                try:
                    _, action_part = line.split("ACCIÓN:", 1)
                    tool_name, tool_arg = [i.strip() for i in action_part.split("|", 1)]
                    print(f"Ejecutando: {tool_name}('{tool_arg}')")
                    if tool_name in TOOLS:
                        obs = TOOLS[tool_name](tool_arg)
                        print(f"Observación: {obs[:100]}...")
                        history += f"\n{response}\nObservación: {obs}"
                        action_found = True
                    else:
                        history += f"\n{response}\nObservación: Error, tool no existe."
                        action_found = True
                except:
                    history += f"\n{response}\nObservación: Error en formato de acción."
                    action_found = True
                break
        
        if not action_found:
            print("❌ Error: Sin acción o finalización válida."); break
    else:
        print("\n🛑 Límite de pasos alcanzado.")

if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else input("Tarea: ")
    run_agent(task)
