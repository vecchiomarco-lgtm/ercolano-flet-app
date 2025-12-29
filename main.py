import os
import flet as ft
import sqlite3
import shutil
import subprocess
from datetime import datetime, date

# --- CONFIGURAZIONE AMBIENTE ---
DB_NAME = "concorsi_rita.db"
PDF_FOLDER = "bandi_pdf"

if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS concorsi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ente TEXT,
            descrizione TEXT,
            scadenza TEXT,
            link TEXT,
            nota TEXT,
            file_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "Monitor Concorsi L-26 - Rita"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1200
    page.window.height = 900
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO

    init_db()
    selected_files_paths = []

    # --- LOGICA APERTURA FILE ---
    def open_all_pdfs(file_paths_str):
        if not file_paths_str:
            return
        paths = file_paths_str.split(",")
        for p in paths:
            if os.path.exists(p):
                # Utilizziamo os.startfile su Windows per aprire con l'app predefinita
                os.startfile(p)

    # --- FUNZIONI DI SUPPORTO ---
    def delete_concorso(concorso_id):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM concorsi WHERE id=?", (concorso_id,))
        conn.commit()
        conn.close()
        load_concorsi()

    def save_concorso(e):
        if not ent_input.value or not scadenza_input.value:
            page.open(ft.SnackBar(ft.Text("Errore: Ente e Scadenza obbligatori!"), bgcolor=ft.Colors.RED_400))
            return

        saved_paths = []
        for path in selected_files_paths:
            filename = os.path.basename(path)
            dest = os.path.join(PDF_FOLDER, f"{int(datetime.now().timestamp())}_{filename}")
            shutil.copy(path, dest)
            saved_paths.append(dest)
        
        file_paths_str = ",".join(saved_paths)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO concorsi (ente, descrizione, scadenza, link, nota, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ent_input.value, desc_input.value, scadenza_input.value, link_input.value, nota_input.value, file_paths_str))
        conn.commit()
        conn.close()

        # Reset UI
        ent_input.value = desc_input.value = link_input.value = nota_input.value = ""
        scadenza_input.value = date.today().strftime("%Y-%m-%d")
        selected_files_paths.clear()
        file_info_text.value = "Nessun file selezionato"
        load_concorsi()

    def load_concorsi(e=None):
        concorsi_table.rows.clear()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM concorsi ORDER BY scadenza ASC")
        rows = cursor.fetchall()
        
        oggi = date.today()
        for r in rows:
            try:
                data_scadenza = datetime.strptime(r[3], "%Y-%m-%d").date()
                giorni_rimanenti = (data_scadenza - oggi).days
            except:
                giorni_rimanenti = 999
            
            is_urgent = 0 <= giorni_rimanenti <= 3
            row_bg = ft.Colors.RED_50 if is_urgent else None
            txt_color = ft.Colors.RED_900 if is_urgent else ft.Colors.BLACK

            concorsi_table.rows.append(
                ft.DataRow(
                    color=row_bg,
                    cells=[
                        ft.DataCell(ft.Text(f"{r[3]} ({giorni_rimanenti} gg)", color=txt_color, weight="bold" if is_urgent else "normal")),
                        ft.DataCell(ft.Text(r[1], color=txt_color, weight="w600")),
                        ft.DataCell(ft.Text(r[2], color=txt_color)),
                        ft.DataCell(ft.Text(r[5], width=200, size=12)),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(ft.Icons.LANGUAGE, tooltip="Apri Link", icon_color="blue", on_click=lambda _, l=r[4]: page.launch_url(l)),
                                ft.IconButton(ft.Icons.FILE_OPEN, tooltip="Apri Allegati", icon_color="orange", on_click=lambda _, p=r[6]: open_all_pdfs(p)),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Elimina", icon_color="red", on_click=lambda _, id=r[0]: delete_concorso(id)),
                            ])
                        ),
                    ]
                )
            )
        conn.close()
        page.update()

    # --- COMPONENTI DATA PICKER ---
    def on_date_change(e):
        if date_picker.value:
            scadenza_input.value = date_picker.value.strftime("%Y-%m-%d")
            page.update()

    date_picker = ft.DatePicker(
        on_change=on_date_change,
        first_date=datetime(2024, 1, 1),
        last_date=datetime(2030, 12, 31),
    )
    page.overlay.append(date_picker)

    # --- INTERFACCIA UTENTE (UI) ---
    ent_input = ft.TextField(label="Ente", expand=1)
    desc_input = ft.TextField(label="Descrizione", expand=1)
    scadenza_input = ft.TextField(label="Scadenza (AAAA-MM-GG)", width=200, read_only=True)
    link_input = ft.TextField(label="Link URL", expand=1)
    nota_input = ft.TextField(label="Nota Personale", multiline=True, min_lines=2, expand=1)
    file_info_text = ft.Text("Nessun PDF", color=ft.Colors.GREY_700)
    
    # 1. Definiamo la funzione che gestisce il risultato
    def handle_file_picker_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_files_paths.extend([f.path for f in e.files])
            file_info_text.value = f"{len(selected_files_paths)} file caricati"
            page.update()

    # 2. Creiamo il FilePicker (senza argomenti nelle parentesi per evitare l'errore)
    file_picker = ft.FilePicker()

    # 3. Assegniamo la funzione all'evento
    file_picker.on_result = handle_file_picker_result

    # 4. Aggiungiamo all'overlay
    page.overlay.append(file_picker)

    concorsi_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Scadenza")),
            ft.DataColumn(ft.Text("Ente")),
            ft.DataColumn(ft.Text("Cosa si tratta")),
            ft.DataColumn(ft.Text("Nota")),
            ft.DataColumn(ft.Text("Azioni")),
        ],
        rows=[]
    )

    # --- LAYOUT ---
    page.add(
        ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=35), ft.Text("Gestione Concorsi Rita", size=28, weight="bold")], alignment="center"),
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([ent_input, desc_input]),
                    ft.Row([
                        scadenza_input, # Questo deve avere read_only=True o False a tua scelta
                        ft.IconButton(
                            icon=ft.Icons.CALENDAR_MONTH, 
                            on_click=lambda _: page.open(date_picker), # Comando corretto per v0.28.3
                            tooltip="Scegli Data dal Calendario",
                            icon_color=ft.Colors.BLUE_700
                        ),
                        link_input
                    ]),
                    ft.Row([nota_input]),
                    ft.Row([
                        ft.ElevatedButton("Seleziona PDF", icon=ft.Icons.ATTACH_FILE, on_click=lambda _: file_picker.pick_files(allow_multiple=True)),
                        file_info_text,
                        ft.ElevatedButton("SALVA", icon=ft.Icons.SAVE, bgcolor=ft.Colors.BLUE_900, color="white", on_click=save_concorso, height=50),
                    ], alignment="spaceBetween")
                ])
            )
        ),
        ft.Divider(height=40),
        ft.Column([
            ft.Text("Elenco ordinato per scadenza:", weight="bold"),
            ft.Row([concorsi_table], scroll=ft.ScrollMode.ALWAYS)
        ], expand=True)
    )

    load_concorsi()

if __name__ == "__main__":
    import os
    # Render assegna la porta, se non la trova usa la 8080
    port = int(os.getenv("PORT", 8080))
    
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, 
        host="0.0.0.0", 
        port=port,
        # AGGIUNGI QUESTA RIGA SOTTO: è fondamentale per il cloud
        web_renderer=ft.WebRenderer.HTML
    )