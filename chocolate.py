import os
import re
import threading
from tkinter import Tk, StringVar, filedialog, END
from ttkbootstrap import ttk, Style
from ttkbootstrap.constants import *

def filtrar_directorios(dirs):
    """
    Filtra y elimina los directorios que comienzan con un punto.

    Args:
        dirs (list): Lista de nombres de directorios.
    """
    # Modifica la lista en su lugar para excluir directorios que comienzan con '.'
    dirs[:] = [d for d in dirs if not d.startswith('.')]

def listar_estructura_markdown(ruta, archivo_salida):
    """
    Genera la estructura del directorio en formato Markdown con listas desordenadas,
    excluyendo directorios ocultos.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write("# Estructura del Proyecto\n\n")
        for root, dirs, files in os.walk(ruta):
            # Filtrar directorios ocultos
            filtrar_directorios(dirs)

            # Calcular el nivel de profundidad
            relative_path = os.path.relpath(root, ruta)
            if relative_path == '.':
                level = 0
            else:
                level = relative_path.count(os.sep) + 1
            indent = '    ' * level  # 4 espacios por nivel de indentación

            # Escribir el nombre de la carpeta
            carpeta = os.path.basename(root)
            if carpeta:  # Evitar escribir una línea vacía para la ruta raíz si es necesario
                f.write(f"{indent}- **🗀  {carpeta}/**\n")

            # Escribir los archivos dentro de la carpeta, excluyendo los de directorios ocultos
            for file in files:
                if not file.startswith('.'):  # Opcional: también puedes excluir archivos ocultos
                    file_indent = '    ' * (level + 1)
                    f.write(f"{file_indent}- 🗋  {file}\n")


def extraer_docstring(file_path):
    """
    Extrae el docstring o comentarios iniciales de un archivo según su tipo,
    excluyendo archivos en directorios ocultos.

    Args:
        file_path (str): Ruta completa del archivo.

    Returns:
        str: Contenido del docstring/comentario si se encuentra, de lo contrario, una cadena vacía.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    doc = ""

    # Excluir archivos en directorios ocultos
    partes = file_path.split(os.sep)
    if any(part.startswith('.') for part in partes):
        return doc

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if ext == '.py':
            # Extraer cadenas triple comillas al inicio del archivo
            match = re.match(r'^\s*(?:\'\'\'|\"\"\")([\s\S]*?)(?:\'\'\'|\"\"\")', content, re.DOTALL)
            if match:
                doc = match.group(1).strip()
            else:
                # Intentar extraer comentarios de una línea al inicio
                comments = []
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("#"):
                        comments.append(line.lstrip("#").strip())
                    elif not line:
                        continue
                    else:
                        break
                if comments:
                    doc = "\n".join(comments)
        elif ext in ['.js', '.php', '.css']:
            if ext == '.php':
                # Eliminar la etiqueta de apertura <?php antes de buscar comentarios
                content = re.sub(r'<\?php\s*', '', content, flags=re.IGNORECASE)
            # Extraer comentarios multilínea /* */ al inicio del archivo
            multiline_match = re.match(r'^\s*/\*([\s\S]*?)\*/', content, re.DOTALL)
            if multiline_match:
                doc = multiline_match.group(1).strip()
            else:
                # Extraer comentarios de una línea // al inicio del archivo
                comments = []
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("//"):
                        comments.append(line.lstrip("//").strip())
                    elif not line:
                        continue
                    else:
                        break
                if comments:
                    doc = "\n".join(comments)
        elif ext == '.html':
            # Extraer comentarios <!-- --> al inicio del archivo
            match = re.match(r'^\s*<!--([\s\S]*?)-->', content, re.DOTALL)
            if match:
                doc = match.group(1).strip()
        else:
            # Tipos de archivo no soportados
            pass

    except Exception as e:
        print(f"Error al procesar el archivo {file_path}: {e}")

    return doc


def agregar_docstrings_markdown(ruta, archivo_salida):
    """
    Agrega docstrings/comentarios de los archivos al documento Markdown,
    excluyendo directorios ocultos.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write("\n# Documentación de Archivos\n\n")
        for root, dirs, files in os.walk(ruta):
            # Filtrar directorios ocultos
            filtrar_directorios(dirs)

            for file in files:
                if file.startswith('.'):
                    continue  # Opcional: también puedes excluir archivos ocultos
                file_path = os.path.join(root, file)
                doc = extraer_docstring(file_path)
                if doc:
                    # Crear una ruta relativa para el encabezado
                    relative_path = os.path.relpath(file_path, ruta)
                    f.write(f"## {relative_path}\n\n")
                    f.write(f"{doc}\n\n")


def agregar_codigo_markdown(ruta, archivo_salida):
    """
    Agrega el código de cada archivo al documento Markdown dentro de bloques de código,
    excluyendo directorios ocultos.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write("\n# Código de Archivos\n\n")
        for root, dirs, files in os.walk(ruta):
            # Filtrar directorios ocultos
            filtrar_directorios(dirs)

            for file in files:
                if file.startswith('.'):
                    continue  # Opcional: también puedes excluir archivos ocultos
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                ext = ext.lower().lstrip('.')

                # Mapeo de extensiones a lenguajes para resaltado de sintaxis
                lang_map = {
                    'py': 'python',
                    'js': 'javascript',
                    'php': 'php',
                    'css': 'css',
                    'html': 'html',
                    'htm': 'html',
                    # Añade más extensiones y lenguajes si es necesario
                }

                lang = lang_map.get(ext, '')  # Si no se encuentra, no se especifica el lenguaje

                try:
                    with open(file_path, 'r', encoding='utf-8') as code_file:
                        code_content = code_file.read()

                    # Crear una ruta relativa para el encabezado
                    relative_path = os.path.relpath(file_path, ruta)
                    f.write(f"## {relative_path}\n\n")
                    f.write(f"```{lang}\n")
                    f.write(f"{code_content}\n")
                    f.write("```\n\n")

                except Exception as e:
                    print(f"Error al leer el archivo {file_path}: {e}")


def procesar(carpeta, archivo_md, actualizar_label):
    """
    Ejecuta las tres fases del procesamiento y actualiza la etiqueta de estado,
    excluyendo directorios ocultos.

    Args:
        carpeta (str): Ruta de la carpeta a analizar.
        archivo_md (str): Nombre del archivo Markdown de salida.
        actualizar_label (function): Función para actualizar la etiqueta de estado.
    """
    try:
        listar_estructura_markdown(carpeta, archivo_md)
        actualizar_label("Estructura del proyecto generada.")

        agregar_docstrings_markdown(carpeta, archivo_md)
        actualizar_label("Docstrings/comentarios agregados.")

        agregar_codigo_markdown(carpeta, archivo_md)
        actualizar_label("Código de archivos agregado.")

        actualizar_label(f"Proceso completado. Archivo generado: {archivo_md}")
    except Exception as e:
        actualizar_label(f"Error: {e}")


def iniciar_proceso(carpeta, archivo_md, actualizar_label):
    """
    Inicia el procesamiento en un hilo separado para mantener la UI responsiva.

    Args:
        carpeta (str): Ruta de la carpeta a analizar.
        archivo_md (str): Nombre del archivo Markdown de salida.
        actualizar_label (function): Función para actualizar la etiqueta de estado.
    """
    hilo = threading.Thread(target=procesar, args=(carpeta, archivo_md, actualizar_label))
    hilo.start()


def main():
    # Configuración de la ventana principal
    root = Tk()
    root.title("Generador de Estructura Markdown")
    root.geometry("700x350")
    style = Style(theme='cosmo')  # Usando el tema "clear"

    # Variables para almacenar las rutas
    ruta_carpeta = StringVar()
    ruta_archivo = StringVar()

    # Funciones para seleccionar carpetas y archivos
    def seleccionar_carpeta():
        carpeta = filedialog.askdirectory()
        if carpeta:
            ruta_carpeta.set(carpeta)

    def seleccionar_archivo():
        archivo = filedialog.asksaveasfilename(defaultextension=".md",
                                               filetypes=[("Markdown files", "*.md")])
        if archivo:
            ruta_archivo.set(archivo)

    # Función para actualizar la etiqueta de estado
    def actualizar_label(texto):
        estado_var.set(texto)
        root.update_idletasks()

    # Diseño de la UI
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill=BOTH, expand=True)

    # Selección de carpeta de origen
    carpeta_label = ttk.Label(frame, text="Carpeta de Origen:")
    carpeta_label.grid(row=0, column=0, sticky=W, pady=5)

    carpeta_entry = ttk.Entry(frame, textvariable=ruta_carpeta, width=50)
    carpeta_entry.grid(row=0, column=1, pady=5, padx=5)

    carpeta_button = ttk.Button(frame, text="Seleccionar Carpeta", command=seleccionar_carpeta)
    carpeta_button.grid(row=0, column=2, pady=5)

    # Selección de archivo de salida
    archivo_label = ttk.Label(frame, text="Archivo de Salida (.md):")
    archivo_label.grid(row=1, column=0, sticky=W, pady=5)

    archivo_entry = ttk.Entry(frame, textvariable=ruta_archivo, width=50)
    archivo_entry.grid(row=1, column=1, pady=5, padx=5)

    archivo_button = ttk.Button(frame, text="Seleccionar Archivo", command=seleccionar_archivo)
    archivo_button.grid(row=1, column=2, pady=5)

    # Botón para iniciar el proceso
    procesar_button = ttk.Button(frame, text="Iniciar Proceso",
                                 command=lambda: iniciar_proceso(
                                     ruta_carpeta.get(),
                                     ruta_archivo.get(),
                                     actualizar_label
                                 ))
    procesar_button.grid(row=2, column=1, pady=20)

    # Etiqueta para mostrar el estado
    estado_var = StringVar()
    estado_var.set("Esperando para iniciar...")
    estado_label = ttk.Label(frame, textvariable=estado_var, bootstyle="info")
    estado_label.grid(row=3, column=0, columnspan=3, pady=10)

    # Ajuste de columnas
    frame.columnconfigure(1, weight=1)

    root.mainloop()


if __name__ == "__main__":
        main()
