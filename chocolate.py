import os
import re
import threading
import json  # Importando json para la gestión de configuración
import shutil
from tkinter import Tk, StringVar, filedialog
from ttkbootstrap import ttk, Style
from ttkbootstrap.constants import *
from bs4 import BeautifulSoup, Comment
from PIL import Image, ImageTk  # Importando PIL para mejor soporte de imágenes

# =========================
# DEFINICIÓN DE EXTENSIONES
# =========================
# Extensiones de archivos de imagen que se copiarán y se mostrarán en el Markdown.
IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg"
]

# Otras extensiones excluidas (no se copiarán imágenes de estos tipos).
EXCLUDED_EXTENSIONS = [
    ".exe",
    ".pdf",
    ".pkl"
    # Agrega o elimina extensiones según tus necesidades
]

# Definir la ruta para el archivo de configuración
CONFIG_FILE = 'config.json'
FRONT_COVER_FILE = 'front_cover.json'  # Nombre del archivo JSON para la portada

def load_config():
    """
    Carga la configuración desde el archivo config.json.
    Retorna un diccionario con las claves 'last_source' y 'last_target'.
    Si el archivo no existe o está mal formado, retorna valores por defecto.
    """
    if not os.path.exists(CONFIG_FILE):
        return {"last_source": "", "last_target": ""}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except Exception as e:
        print(f"Error al cargar el archivo de configuración: {e}")
        return {"last_source": "", "last_target": ""}

def save_config(source, target):
    """
    Guarda las rutas de origen y destino usadas por última vez en el archivo config.json.
    """
    config = {
        "last_source": source,
        "last_target": target
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error al guardar el archivo de configuración: {e}")

def filtrar_directorios(dirs):
    """
    Filtra y elimina los directorios que comienzan con un punto.

    Args:
        dirs (list): Lista de nombres de directorios.
    """
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
        # La portada se agregará posteriormente
        f.write("# Estructura del Proyecto\n\n")
        for root, dirs, files in os.walk(ruta):
            filtrar_directorios(dirs)

            relative_path = os.path.relpath(root, ruta)
            if relative_path == '.':
                level = 0
            else:
                level = relative_path.count(os.sep) + 1
            indent = '    ' * level

            carpeta = os.path.basename(root)
            if carpeta:
                f.write(f"{indent}- **🗀  {carpeta}/**\n")

            for file in files:
                if not file.startswith('.'):
                    file_indent = '    ' * (level + 1)
                    f.write(f"{file_indent}- 🗋  {file}\n")

def extraer_docstring(file_path):
    """
    Extrae el docstring o comentarios iniciales de un archivo según su tipo,
    excluyendo archivos en directorios ocultos y manejando exclusiones de extensión.
    Si el archivo es de imagen, se retorna una cadena vacía para evitar que se muestre [excluded].

    Args:
        file_path (str): Ruta completa del archivo.

    Returns:
        str: Contenido del docstring/comentario si se encuentra, de lo contrario, una cadena vacía
             o '[excluded]' si está en la lista de exclusiones (no aplicable a imágenes).
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # Si el archivo es una imagen, no se extrae docstring
    if ext in IMAGE_EXTENSIONS:
        return ""
    # Si el archivo tiene una extensión en la lista de excluidos, retornar [excluded]
    if ext in EXCLUDED_EXTENSIONS:
        return "[excluded]"

    doc = ""
    partes = file_path.split(os.sep)
    if any(part.startswith('.') for part in partes):
        return doc

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if ext == '.py':
            match = re.match(r'^\s*(?:\'\'\'|\"\"\")([\s\S]*?)(?:\'\'\'|\"\"\")', content, re.DOTALL)
            if match:
                doc = match.group(1).strip()
            else:
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
                content = re.sub(r'<\?php\s*', '', content, flags=re.IGNORECASE)
            multiline_match = re.search(r'/\*([\s\S]*?)\*/', content)
            if multiline_match:
                doc = multiline_match.group(1).strip()
            else:
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
        elif ext in ['.html', '.htm']:
            soup = BeautifulSoup(content, 'html.parser')
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            if comments:
                doc = comments[0].strip()
                print(f"Comentario HTML extraído de {file_path}:\n{doc}\n")
            else:
                print(f"No se encontró comentario en {file_path}.")
        else:
            pass

    except Exception as e:
        print(f"Error al procesar el archivo {file_path}: {e}")

    return doc

def copy_file_to_media(source_file, archivo_md):
    """
    Copia el archivo source_file a la carpeta "media" ubicada en el directorio del archivo_md.
    Si el archivo ya existe, se agrega un sufijo para evitar colisiones.

    Args:
        source_file (str): Ruta completa del archivo fuente.
        archivo_md (str): Ruta del archivo Markdown de salida (para determinar la carpeta destino).

    Returns:
        str: Nombre del archivo copiado (relativo a la carpeta "media").
    """
    target_dir = os.path.dirname(archivo_md)
    media_dir = os.path.join(target_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    base = os.path.basename(source_file)
    dest = os.path.join(media_dir, base)
    counter = 1
    orig_name, orig_ext = os.path.splitext(base)
    while os.path.exists(dest):
        dest = os.path.join(media_dir, f"{orig_name}_{counter}{orig_ext}")
        counter += 1
    try:
        shutil.copy2(source_file, dest)
    except Exception as e:
        print(f"Error al copiar {source_file} a {dest}: {e}")
    return os.path.basename(dest)

def agregar_docstrings_markdown(ruta, archivo_salida):
    """
    Agrega docstrings/comentarios de los archivos al documento Markdown,
    excluyendo directorios ocultos y manejando exclusiones de extensión.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write("\n# Documentación de Archivos\n\n")
        for root, dirs, files in os.walk(ruta):
            filtrar_directorios(dirs)

            for file in files:
                if file.startswith('.'):
                    continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, ruta)

                # Extraer docstring (o [excluded])
                doc = extraer_docstring(file_path)
                # Si no hay docstring y no es [excluded], pasamos
                if doc == "":
                    continue

                # Convertir saltos de línea en Markdown
                doc = doc.replace('\n', '  \n')

                f.write(f"## {relative_path}\n\n")
                f.write(f"{doc}\n\n")

def agregar_codigo_markdown(ruta, archivo_salida):
    """
    Agrega el código de cada archivo al documento Markdown dentro de bloques de código,
    excluyendo directorios ocultos y manejando exclusiones de extensión.
    Para archivos de imagen se copia el archivo a la carpeta "media" y se inserta la imagen en Markdown.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write("\n# Código de Archivos\n\n")
        for root, dirs, files in os.walk(ruta):
            filtrar_directorios(dirs)

            for file in files:
                if file.startswith('.'):
                    continue
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                ext = ext.lower().lstrip('.')
                relative_path = os.path.relpath(file_path, ruta)

                # Si es un archivo de imagen, copiarlo y mostrar la imagen en Markdown.
                if f".{ext}" in IMAGE_EXTENSIONS:
                    dest_filename = copy_file_to_media(file_path, archivo_salida)
                    f.write(f"## {relative_path}\n\n")
                    f.write(f"![{file}](media/{dest_filename})\n\n")
                # Si es un archivo excluido (no imagen), se escribe [excluded].
                elif f".{ext}" in EXCLUDED_EXTENSIONS:
                    f.write(f"## {relative_path}\n\n")
                    f.write("[excluded]\n\n")
                else:
                    lang_map = {
                        'py': 'python',
                        'js': 'javascript',
                        'php': 'php',
                        'css': 'css',
                        'html': 'html',
                        'htm': 'html',
                    }
                    lang = lang_map.get(ext, '')
                    try:
                        with open(file_path, 'r', encoding='utf-8') as code_file:
                            code_content = code_file.read()

                        f.write(f"## {relative_path}\n\n")
                        f.write(f"```{lang}\n")
                        f.write(f"{code_content}\n")
                        f.write("```\n\n")

                    except Exception as e:
                        print(f"Error al leer el archivo {file_path}: {e}")

def cargar_front_cover(ruta_carpeta):
    """
    Carga los datos de la portada desde front_cover.json si existe,
    de lo contrario, crea un archivo con valores por defecto.

    Args:
        ruta_carpeta (str): Ruta de la carpeta de origen.

    Returns:
        dict: Diccionario con los datos de la portada.
    """
    front_cover_path = os.path.join(ruta_carpeta, FRONT_COVER_FILE)
    if not os.path.exists(front_cover_path):
        # Crear un archivo con valores por defecto
        front_cover_data = {
            "title": "Título del Documento",
            "subtitle": "Subtítulo del Documento",
            "revision": "0",
            "author": "Autor",
            "logo": ""  # Campo para el logo
        }
        try:
            with open(front_cover_path, 'w', encoding='utf-8') as f:
                json.dump(front_cover_data, f, indent=4)
            print(f"Archivo {FRONT_COVER_FILE} creado con valores por defecto.")
        except Exception as e:
            print(f"Error al crear {FRONT_COVER_FILE}: {e}")
    else:
        try:
            with open(front_cover_path, 'r', encoding='utf-8') as f:
                front_cover_data = json.load(f)
            print(f"Datos de portada cargados desde {FRONT_COVER_FILE}.")
        except Exception as e:
            print(f"Error al cargar {FRONT_COVER_FILE}: {e}")
            front_cover_data = {
                "title": "Título del Documento",
                "subtitle": "Subtítulo del Documento",
                "revision": "0",
                "author": "Autor",
                "logo": ""  # Campo para el logo
            }
    return front_cover_data

def guardar_front_cover(ruta_carpeta, data):
    """
    Guarda los datos de la portada en front_cover.json.

    Args:
        ruta_carpeta (str): Ruta de la carpeta de origen.
        data (dict): Diccionario con los datos de la portada.
    """
    front_cover_path = os.path.join(ruta_carpeta, FRONT_COVER_FILE)
    try:
        with open(front_cover_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Datos de portada guardados en {FRONT_COVER_FILE}.")
    except Exception as e:
        print(f"Error al guardar {FRONT_COVER_FILE}: {e}")

def generar_portada_markdown(data, ruta_carpeta, archivo_salida):
    """
    Genera la sección de portada en Markdown con los datos proporcionados.
    Si se especifica un logo y éste existe en la carpeta del proyecto, se copia a la carpeta "media"
    y se inserta la imagen en el Markdown.

    Args:
        data (dict): Diccionario con los datos de la portada.
        ruta_carpeta (str): Ruta de la carpeta de origen.
        archivo_salida (str): Ruta del archivo Markdown de salida.

    Returns:
        str: Cadena de texto en Markdown con la portada.
    """
    portada_md = (
        f"# {data.get('title', 'Título del Documento')}\n\n"
        f"## {data.get('subtitle', 'Subtítulo del Documento')}\n\n"
        f"**Revisión:** {data.get('revision', '0')}\n\n"
    )
    
    # Si hay un logo, copiarlo a la carpeta media y agregar la imagen en Markdown
    logo = data.get('logo', "").strip()
    if logo:
        logo_path = os.path.join(ruta_carpeta, logo)
        if os.path.exists(logo_path):
            dest_filename = copy_file_to_media(logo_path, archivo_salida)
            portada_md += f"![Logo](media/{dest_filename})\n\n"
        else:
            portada_md += f"**Logo:** {logo}\n\n"
    
    portada_md += (
        f"**Autor:** {data.get('author', 'Autor')}\n\n"
        f"---\n\n"
    )
    return portada_md

def agregar_portada_markdown(ruta_carpeta, archivo_salida):
    """
    Agrega la portada al inicio del archivo Markdown.

    Args:
        ruta_carpeta (str): Ruta de la carpeta de origen.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    front_cover_data = cargar_front_cover(ruta_carpeta)
    portada_md = generar_portada_markdown(front_cover_data, ruta_carpeta, archivo_salida)
    try:
        with open(archivo_salida, 'r+', encoding='utf-8') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(portada_md + content)
        print("Portada agregada al archivo Markdown.")
    except Exception as e:
        print(f"Error al agregar la portada al archivo Markdown: {e}")

def procesar(carpeta, archivo_md, actualizar_label):
    """
    Ejecuta las fases del procesamiento y actualiza la etiqueta de estado,
    excluyendo directorios ocultos. Maneja también el caso de extensiones excluidas.

    Args:
        carpeta (str): Ruta de la carpeta a analizar.
        archivo_md (str): Nombre del archivo Markdown de salida.
        actualizar_label (function): Función para actualizar la etiqueta de estado.
    """
    try:
        listar_estructura_markdown(carpeta, archivo_md)
        agregar_portada_markdown(carpeta, archivo_md)
        actualizar_label("Estructura del proyecto y portada generadas.")

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
    # Cargar configuración
    config = load_config()

    # Configuración de la ventana principal
    root = Tk()
    root.title("Generador de Estructura Markdown")
    root.geometry("800x800")  # Aumentar altura para los nuevos campos
    style = Style(theme='cosmo')  # Usando el tema "cosmo"

    # Variables para almacenar las rutas
    ruta_carpeta = StringVar(value=config.get("last_source", ""))
    ruta_archivo = StringVar(value=config.get("last_target", ""))

    # Variables para la portada
    titulo_var = StringVar()
    subtitulo_var = StringVar()
    revision_var = StringVar()
    autor_var = StringVar()
    logo_var = StringVar()  # Variable para el logo

    # Funciones para seleccionar carpetas y archivos
    def seleccionar_carpeta():
        """
        Abre un diálogo para seleccionar una carpeta, iniciando desde la última carpeta seleccionada.
        Carga o crea el archivo front_cover.json y actualiza los campos de portada.
        """
        initial_dir = ruta_carpeta.get() if ruta_carpeta.get() else os.getcwd()
        carpeta = filedialog.askdirectory(initialdir=initial_dir)
        if carpeta:
            ruta_carpeta.set(carpeta)
            save_config(carpeta, ruta_archivo.get())
            # Cargar o crear front_cover.json
            front_cover_data = cargar_front_cover(carpeta)
            titulo_var.set(front_cover_data.get("title", ""))
            subtitulo_var.set(front_cover_data.get("subtitle", ""))
            revision_var.set(front_cover_data.get("revision", ""))
            autor_var.set(front_cover_data.get("author", ""))
            logo_var.set(front_cover_data.get("logo", ""))  # Cargar el logo

    def seleccionar_archivo():
        """
        Abre un diálogo para seleccionar un archivo de salida, iniciando desde la última carpeta utilizada.
        Una vez seleccionado, se crea (si no existen) la carpeta de destino y la subcarpeta "media".
        """
        if ruta_archivo.get():
            initial_dir = os.path.dirname(ruta_archivo.get()) or os.getcwd()
        elif ruta_carpeta.get():
            initial_dir = ruta_carpeta.get()
        else:
            initial_dir = os.getcwd()

        archivo = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md")]
        )
        if archivo:
            ruta_archivo.set(archivo)
            # Crear la carpeta destino (si no existe) y la subcarpeta "media"
            os.makedirs(os.path.dirname(archivo), exist_ok=True)
            media_folder = os.path.join(os.path.dirname(archivo), "media")
            os.makedirs(media_folder, exist_ok=True)
            save_config(ruta_carpeta.get(), archivo)

    # Función para actualizar la etiqueta de estado
    def actualizar_label(texto):
        estado_var.set(texto)
        root.update_idletasks()

    # Función para guardar los datos de la portada cuando se modifican
    def guardar_portada(*args):
        if not ruta_carpeta.get():
            return  # No hay carpeta seleccionada
        data = {
            "title": titulo_var.get(),
            "subtitle": subtitulo_var.get(),
            "revision": revision_var.get(),
            "author": autor_var.get(),
            "logo": logo_var.get()
        }
        guardar_front_cover(ruta_carpeta.get(), data)

    # Diseño de la UI
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill=BOTH, expand=True)

    # Añadir el logo en la parte superior
    logo_path = 'chocolate.png'  # Asegúrate de que chocolate.png esté en el mismo directorio que el script
    if os.path.exists(logo_path):
        try:
            # Abrir la imagen y ajustar el tamaño si es necesario
            image = Image.open(logo_path)
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS  # Para versiones anteriores a Pillow 10.0.0
            image = image.resize((300, 300), resample)
            logo = ImageTk.PhotoImage(image)
            logo_label = ttk.Label(frame, image=logo)
            logo_label.image = logo  # Mantener referencia para evitar recolección de basura
            logo_label.grid(row=0, column=0, columnspan=4, pady=(0, 10))
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
    else:
        print(f"{logo_path} no encontrado. Continuando sin logo.")

    # Selección de carpeta de origen
    carpeta_label = ttk.Label(frame, text="Carpeta de Origen:")
    carpeta_label.grid(row=1, column=0, sticky=W, pady=5)

    carpeta_entry = ttk.Entry(frame, textvariable=ruta_carpeta, width=50)
    carpeta_entry.grid(row=1, column=1, pady=5, padx=5, columnspan=2, sticky=W)

    carpeta_button = ttk.Button(frame, text="Seleccionar Carpeta", command=seleccionar_carpeta)
    carpeta_button.grid(row=1, column=3, pady=5, padx=5)

    # Selección de archivo de salida
    archivo_label = ttk.Label(frame, text="Archivo de Salida (.md):")
    archivo_label.grid(row=2, column=0, sticky=W, pady=5)

    archivo_entry = ttk.Entry(frame, textvariable=ruta_archivo, width=50)
    archivo_entry.grid(row=2, column=1, pady=5, padx=5, columnspan=2, sticky=W)

    archivo_button = ttk.Button(frame, text="Seleccionar Archivo", command=seleccionar_archivo)
    archivo_button.grid(row=2, column=3, pady=5, padx=5)

    # Separador
    separator = ttk.Separator(frame, orient=HORIZONTAL)
    separator.grid(row=3, column=0, columnspan=4, sticky="ew", pady=10)

    # Campos para la portada
    portada_label = ttk.Label(frame, text="Portada del Documento", font=("Helvetica", 16, "bold"))
    portada_label.grid(row=4, column=0, columnspan=4, pady=10)

    # Título
    titulo_label = ttk.Label(frame, text="Título:")
    titulo_label.grid(row=5, column=0, sticky=E, pady=5)

    titulo_entry = ttk.Entry(frame, textvariable=titulo_var, width=50)
    titulo_entry.grid(row=5, column=1, pady=5, padx=5, columnspan=3, sticky=W)

    # Subtítulo
    subtitulo_label = ttk.Label(frame, text="Subtítulo:")
    subtitulo_label.grid(row=6, column=0, sticky=E, pady=5)

    subtitulo_entry = ttk.Entry(frame, textvariable=subtitulo_var, width=50)
    subtitulo_entry.grid(row=6, column=1, pady=5, padx=5, columnspan=3, sticky=W)

    # Número de Revisión
    revision_label = ttk.Label(frame, text="Número de Revisión:")
    revision_label.grid(row=7, column=0, sticky=E, pady=5)

    revision_entry = ttk.Entry(frame, textvariable=revision_var, width=50)
    revision_entry.grid(row=7, column=1, pady=5, padx=5, columnspan=3, sticky=W)

    # Autor
    autor_label = ttk.Label(frame, text="Autor:")
    autor_label.grid(row=8, column=0, sticky=E, pady=5)

    autor_entry = ttk.Entry(frame, textvariable=autor_var, width=50)
    autor_entry.grid(row=8, column=1, pady=5, padx=5, columnspan=3, sticky=W)

    # Logo
    logo_label_ui = ttk.Label(frame, text="Logo (nombre archivo):")
    logo_label_ui.grid(row=9, column=0, sticky=E, pady=5)

    logo_entry = ttk.Entry(frame, textvariable=logo_var, width=50)
    logo_entry.grid(row=9, column=1, pady=5, padx=5, columnspan=3, sticky=W)

    # Asociar las variables de la portada con la función de guardado
    titulo_var.trace_add('write', guardar_portada)
    subtitulo_var.trace_add('write', guardar_portada)
    revision_var.trace_add('write', guardar_portada)
    autor_var.trace_add('write', guardar_portada)
    logo_var.trace_add('write', guardar_portada)

    # Botón para iniciar el proceso
    procesar_button = ttk.Button(
        frame,
        text="Iniciar Proceso",
        command=lambda: iniciar_proceso(
            ruta_carpeta.get(),
            ruta_archivo.get(),
            actualizar_label
        )
    )
    procesar_button.grid(row=10, column=1, pady=20)

    # Etiqueta para mostrar el estado
    estado_var = StringVar()
    estado_var.set("Esperando para iniciar...")
    estado_label = ttk.Label(frame, textvariable=estado_var, bootstyle="info")
    estado_label.grid(row=11, column=0, columnspan=4, pady=10)

    # Ajuste de columnas
    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(2, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main()
