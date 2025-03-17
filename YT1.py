import os
import re
import subprocess
import sys
import tkinter as tk
from threading import Thread
from tkinter import filedialog, messagebox, ttk
from io import BytesIO

import requests
import ttkbootstrap as tb
from PIL import Image, ImageTk
from colorama import init
from rich.console import Console
from svglib.svglib import svg2rlg
# from reportlab.graphics.renderPM import drawToPMImage

# Инициализация colorama для совместимости с Windows
init()

# Инициализация Rich для работы с цветами и форматированием
console = Console(force_terminal=True)

def sanitize_filename(filename):
    """Очищает имя файла от недопустимых символов."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[()\[\]{} ]', '_', filename)
    filename = re.sub(r'_+', '_', filename)
    return filename.strip('_')

def check_and_install_dependencies():
    """Проверка и установка необходимых зависимостей."""
    try:
        if not is_yt_dlp_installed():
            console.print("[yellow]yt-dlp не найден. Установка...[/yellow]")
            install_yt_dlp()

        required_packages = ["requests", "rich", "colorama", "Pillow", "svglib", "reportlab"]
        missing_packages = [pkg for pkg in required_packages if not is_package_installed(pkg)]
        if missing_packages:
            console.print(f"[yellow]Необходимо установить следующие пакеты: {', '.join(missing_packages)}[/yellow]")
            for pkg in missing_packages:
                install_python_package(pkg)

        console.print("[green]Все зависимости установлены.[/green]")
    except Exception as e:
        console.print(f"[red]Ошибка при проверке зависимостей: {str(e)}[/red]")
        sys.exit(1)

def is_yt_dlp_installed():
    """Проверка наличия yt-dlp."""
    try:
        subprocess.run(["yt-dlp", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_yt_dlp():
    """Установка yt-dlp."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
    except Exception as e:
        console.print(f"[red]Ошибка при установке yt-dlp: {str(e)}[/red]")
        sys.exit(1)

def is_package_installed(package_name):
    """Проверка наличия Python-пакета."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_python_package(package_name):
    """Установка Python-пакета."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True)
    except Exception as e:
        console.print(f"[red]Ошибка при установке пакета {package_name}: {str(e)}[/red]")
        sys.exit(1)

def list_available_formats(url):
    """Выводит список доступных форматов для скачивания."""
    result = subprocess.run(
        ["yt-dlp", "--cookies-from-browser", "firefox", "-F", url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Ошибка при получении форматов: {result.stderr}[/red]")
        console.print("[yellow]Убедитесь, что вы вошли в аккаунт YouTube в Firefox.[/yellow]")
        return []

    formats = result.stdout.splitlines()
    video_formats = []
    audio_formats = []

    for line in formats:
        if "video only" in line:
            video_formats.append(line)
        elif "audio only" in line:
            audio_formats.append(line)

    return formats, video_formats, audio_formats

def get_video_thumbnail(url):
    """Получает обложку видео."""
    result = subprocess.run(
        ["yt-dlp", "--cookies-from-browser", "firefox", "--get-thumbnail", url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Ошибка при получении обложки: {result.stderr}[/red]")
        return None

    thumbnail_url = result.stdout.strip()
    return thumbnail_url

def download_video_and_audio(url, output_dir, video_format_id, audio_format_id, concurrent_fragments, output_format):
    """Скачивает видео и аудио в выбранных форматах и объединяет их."""
    video_file = f"{output_dir}/video_temp.{video_format_id}"
    audio_file = f"{output_dir}/audio_temp.{audio_format_id}"

    try:
        # Скачиваем видео
        console.print(f"[green]Загрузка видео с форматом: {video_format_id}[/green]")
        subprocess.run(
            [
                "yt-dlp",
                "--cookies-from-browser",
                "firefox",
                url,
                "-f",
                video_format_id,
                "-o",
                video_file,
                "--concurrent-fragments",
                str(concurrent_fragments),
            ],
            check=True,
        )

        # Скачиваем аудио
        console.print(f"[green]Загрузка аудио с форматом: {audio_format_id}[/green]")
        subprocess.run(
            [
                "yt-dlp",
                "--cookies-from-browser",
                "firefox",
                url,
                "-f",
                audio_format_id,
                "-o",
                audio_file,
                "--concurrent-fragments",
                str(concurrent_fragments),
            ],
            check=True,
        )

        # Получаем название видео
        result = subprocess.run(
            ["yt-dlp", "--cookies-from-browser", "firefox", "--get-title", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]Ошибка при получении названия видео: {result.stderr}[/red]")
            return
        video_title = result.stdout.strip()

        # Очищаем название видео
        sanitized_title = sanitize_filename(video_title)

        # Формируем путь к выходному файлу
        output_file = f"{output_dir}/{sanitized_title}.{output_format}"

        # Объединяем видео и аудио
        console.print("[green]Объединение видео и аудио...[/green]")
        subprocess.run(
            ["ffmpeg", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "copy", output_file], check=True
        )

        # Удаляем временные файлы
        os.remove(video_file)
        os.remove(audio_file)
        console.print(f"[green]Видео успешно загружено и объединено: {output_file}[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Ошибка при загрузке или объединении: {e}[/red]")
    except KeyboardInterrupt:
        console.print("[yellow]Загрузка прервана пользователем.[/yellow]")

def start_download():
    """Запускает процесс загрузки видео и аудио."""
    url = url_entry.get().strip()
    output_dir = output_dir_entry.get().strip()
    video_format_id = video_format_var.get().split(" - ")[0].strip()
    audio_format_id = audio_format_var.get().split(" - ")[0].strip()
    concurrent_fragments = int(concurrent_fragments_var.get().strip())
    output_format = output_format_var.get().strip()

    if not url:
        messagebox.showerror("Ошибка", "Введите ссылку.")
        return
    if not output_dir:
        messagebox.showerror("Ошибка", "Выберите папку назначения.")
        return
    if not video_format_id or not audio_format_id:
        messagebox.showerror("Ошибка", "Выберите форматы видео и аудио.")
        return
    if not concurrent_fragments > 0:
        messagebox.showerror("Ошибка", "Количество потоков должно быть больше 0.")
        return

    download_thread = Thread(target=download_video_and_audio, args=(url, output_dir, video_format_id, audio_format_id, concurrent_fragments, output_format))
    download_thread.start()

def choose_directory():
    """Открывает диалоговое окно для выбора директории."""
    directory = filedialog.askdirectory()
    if directory:
        output_dir_entry.delete(0, tk.END)
        output_dir_entry.insert(0, directory)

def update_formats_and_thumbnail():
    """Обновляет списки форматов и загружает обложку видео."""
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Ошибка", "Введите ссылку.")
        return

    formats, video_formats, audio_formats = list_available_formats(url)
    if not formats:
        messagebox.showerror("Ошибка", "Не удалось получить список форматов.")
        return

    video_format_var.set("")
    audio_format_var.set("")
    video_format_menu["values"] = [f"{line.split()[0]} - {line.split()[2]} - {line.split()[3]} - {line.split()[4]} - {line.split()[-1]}" for line in video_formats]
    audio_format_menu["values"] = [f"{line.split()[0]} - {line.split()[2]} - {line.split()[3]} - {line.split()[4]} - {line.split()[-1]}" for line in audio_formats]

    thumbnail_url = get_video_thumbnail(url)
    if thumbnail_url:
        load_thumbnail(thumbnail_url)

def load_thumbnail(thumbnail_url):
    """Загружает и отображает обложку видео."""
    try:
        console.print(f"[yellow]Загружаем обложку с URL: {thumbnail_url}[/yellow]")

        response = requests.get(thumbnail_url, stream=True)
        response.raise_for_status()
        image = Image.open(response.raw)
        image = image.resize((int(root.winfo_width() * 0.8), int((root.winfo_width() * 0.8) * 9 / 16)), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        thumbnail_label.config(image=photo)
        thumbnail_label.image = photo
    except Exception as e:
        console.print(f"[red]Ошибка при загрузке или отображении обложки: {str(e)}[/red]")

def select_best_quality():
    """Выбирает наилучшее качество для видео и аудио."""
    if video_format_menu["values"]:
        video_format_var.set(video_format_menu["values"][0])
    if audio_format_menu["values"]:
        audio_format_var.set(audio_format_menu["values"][0])

if __name__ == "__main__":
    check_and_install_dependencies()

    # Инициализация Tkinter с использованием темы Material Design
    root = tb.Window(themename="darkly")
    root.title("YouTube Downloader")
    root.geometry("800x900")

    # Логотип YouTube
    # svg_response = requests.get("https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg")
    # drawing = svg2rlg(BytesIO(svg_response.content))
    # pil_image = drawToPMImage(drawing)
    # logo = pil_image.resize((80, 40), Image.LANCZOS)
    # logo_photo = ImageTk.PhotoImage(logo)
    # logo_label = ttk.Label(root, image=logo_photo)
    # logo_label.image = logo_photo
    # logo_label.pack(anchor="nw", padx=10, pady=5)

    url_label = ttk.Label(root, text="Ссылка:")
    url_label.pack(anchor="w", padx=10, pady=5)
    url_entry = ttk.Entry(root, width=80)
    url_entry.pack(padx=10, pady=5)

    output_dir_label = ttk.Label(root, text="Папка назначения:")
    output_dir_label.pack(anchor="w", padx=10, pady=5)
    output_dir_frame = ttk.Frame(root)
    output_dir_frame.pack(padx=10, pady=5, fill="x")
    output_dir_entry = ttk.Entry(output_dir_frame, width=60)
    output_dir_entry.pack(side="left", fill="x", expand=True)
    output_dir_button = ttk.Button(output_dir_frame, text="Выбрать", command=choose_directory)
    output_dir_button.pack(side="left", padx=5)

    video_format_id_label = ttk.Label(root, text="Видео формат:")
    video_format_id_label.pack(anchor="w", padx=10, pady=5)
    video_format_var = tk.StringVar()
    video_format_menu = ttk.Combobox(root, textvariable=video_format_var, width=80)
    video_format_menu.pack(padx=10, pady=5)

    audio_format_id_label = ttk.Label(root, text="Аудио формат:")
    audio_format_id_label.pack(anchor="w", padx=10, pady=5)
    audio_format_var = tk.StringVar()
    audio_format_menu = ttk.Combobox(root, textvariable=audio_format_var, width=80)
    audio_format_menu.pack(padx=10, pady=5)

    concurrent_fragments_label = ttk.Label(root, text="Количество потоков:")
    concurrent_fragments_label.pack(anchor="w", padx=10, pady=5)
    concurrent_fragments_var = tk.StringVar(value="4")
    concurrent_fragments_menu = ttk.Combobox(
        root, textvariable=concurrent_fragments_var, values=[str(i) for i in range(1, 11)], width=80
    )
    concurrent_fragments_menu.pack(padx=10, pady=5)

    output_format_label = ttk.Label(root, text="Формат выходного файла:")
    output_format_label.pack(anchor="w", padx=10, pady=5)
    output_format_var = tk.StringVar(value="mp4")
    output_format_menu = ttk.Combobox(root, textvariable=output_format_var, values=["mp4", "mkv", "avi", "webm"], width=80)
    output_format_menu.pack(padx=10, pady=5)

    update_button = ttk.Button(root, text="Обновить форматы и обложку", command=update_formats_and_thumbnail)
    update_button.pack(padx=10, pady=5)

    best_quality_button = ttk.Button(root, text="Лучшее качество", command=select_best_quality)
    best_quality_button.pack(padx=10, pady=5)

    download_button = ttk.Button(root, text="Скачать", command=start_download)
    download_button.pack(padx=10, pady=5)

    thumbnail_frame = ttk.Frame(root, width=int(root.winfo_width() * 0.8), height=int((root.winfo_width() * 0.8) * 9 / 16))
    thumbnail_frame.pack(padx=10, pady=10)
    thumbnail_label = ttk.Label(thumbnail_frame)
    thumbnail_label.pack(expand=True)

    root.mainloop()
