import subprocess
import os
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt

import logging


def get_xml_from_p7m(file_p7m, output_xml, logger=None):

    if logger is None:
        logger = logging.getLogger(__name__)

    
    try:
        # Primo tentativo con openssl
        subprocess.run([
            "openssl", "smime", "-verify",
            "-inform", "DER",
            "-noverify",
            "-in", file_p7m,
            "-out", output_xml
        ], check=True)

    except subprocess.CalledProcessError:
        logger.warning("[!] Primo tentativo fallito: provo a estrarre a mano il contenuto XML.")

        with open(file_p7m, "rb") as f:
            content = f.read()

        # Cerca l'inizio del tag <?xml e taglia da lì
        start = content.find(b"<?xml")
        if start == -1:
            string_error = "Contenuto XML non trovato nel file .p7m"
            logger.error(string_error)
            raise ValueError(string_error)

        # Cerca il primo tag di chiusura valido tra i due candidati
        closing_tags = [b"</p:FatturaElettronica>", b"</FatturaElettronica>"]
        end = -1
        selected_tag = None

        for tag in closing_tags:
            pos = content.find(tag, start)  # Cerca dopo l'inizio dell'XML
            if pos != -1 and (end == -1 or pos < end):
                end = pos
                selected_tag = tag

        if end == -1:
            string_error = "Tag di chiusura </p:FatturaElettronica> non trovato nel file .p7m"
            logger.error(string_error)
            raise ValueError(string_error)

        xml_content = content[start:end] + selected_tag

        # Salva il contenuto su file
        with open(output_xml, "wb") as out:
            out.write(xml_content)

        logger.info("[✓] Estrazione manuale completata.")


def load_xml_safe(file_path, logger=None):

    if logger is None:
        logger = logging.getLogger(__name__)

    try:
        # Primo tentativo: parsing normale
        return ET.parse(file_path)
    except ET.ParseError:
        # Se fallisce, prova con lettura manuale del contenuto
        encodings_to_try = ["utf-8", "iso-8859-1", "windows-1252"]
        for enc in encodings_to_try:
            try:
                with open(file_path, "r", encoding=enc, errors="ignore") as f:
                    xml_content = f.read()

                # Rimuove caratteri non stampabili tranne \n e \t
                cleaned_content = ''.join(
                    c for c in xml_content if c.isprintable() or c in "\n\t"
                )

                return ET.ElementTree(ET.fromstring(cleaned_content))
            except ET.ParseError:
                continue  # Prova il prossimo encoding
            except Exception as e:
                raise e  # Altri errori gravi vanno sollevati
        raise ET.ParseError(f"Impossibile decodificare {file_path} con gli encoding provati.")
    

def plot_cake_mittente(df_invoices_details):
    """
    Crea un grafico a torta che mostra la distribuzione dell'importo pagato ai vari fornitori.
    """
    
    # Raggruppa e somma
    grouped = df_invoices_details.groupby('Denominazione_Mittente')['Prezzo_ivato'].sum()

    # Calcola le percentuali
    percent = grouped / grouped.sum()

    # Dividi in main e altri
    main = grouped[percent >= 0.02]
    other = grouped[percent < 0.02]
    main['Altro'] = other.sum()

    # Ordina dal più grande al più piccolo
    main = main.sort_values(ascending=False)

    # Crea le etichette tagliate a 20 caratteri
    labels = [label[:20] for label in main.index]

    # Palette colori
    colors = plt.get_cmap('tab20').colors
    n_colors = len(colors)
    n_slices = len(main)
    colors_to_use = [colors[i % n_colors] for i in range(n_slices)]

    # Grafico a torta
    plt.figure(figsize=(8, 8))
    plt.pie(main, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors_to_use)
    plt.title('Distribuzione dell importo pagato ai vari fornitori')
    plt.axis('equal')
    plt.tight_layout()
    plt.show()


def plot_hist_mittente(df_invoices_details, col_groupby='Denominazione_Mittente'):
    # Raggruppa e somma
    grouped = df_invoices_details.groupby(col_groupby)['Prezzo_ivato'].sum()

    # Calcola le percentuali per "Altro"
    percent = grouped / grouped.sum()

    # Dividi in main e altri
    main = grouped[percent >= 0.005]
    other = grouped[percent < 0.005]
    main['Altro'] = other.sum()

    # Ordina dal più grande al più piccolo
    main = main.sort_values(ascending=False)

    # Etichette accorciate a 20 caratteri
    labels = [label[:20] for label in main.index]

    # Crea l'istogramma
    plt.figure(figsize=(10, 6))
    plt.bar(labels, main, color='skyblue')
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Prezzo Ivato (somma assoluta)')
    plt.title('Importo Totale dell importo pagato ai vari fornitori')
    plt.tight_layout()
    plt.show()