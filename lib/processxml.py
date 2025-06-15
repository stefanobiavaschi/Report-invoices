from lib.utils import get_xml_from_p7m, load_xml_safe

import subprocess
import os
import shutil

import xml.etree.ElementTree as ET
import pandas as pd

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="logfile.log",         # <-- Qui verranno salvati i log
    filemode="w"                    # "w" sovrascrive il file ogni volta, "a" lo appende
)


class XMLProcessing:
    def __init__(self):
        # Nessun parametro richiesto, inizializzazione semplice
        self.logger = logging.getLogger(self.__class__.__name__)


    def process_xml(self,
                    input_dirs: list):
        """
        """
        for input_dir in input_dirs:
            parts = input_dir.split(os.sep)
            parts[-2] = "processed"
            output_dir_preprocess = os.sep.join(parts)
            parts[-2] = "df"
            output_dir_df = os.sep.join(parts[:-1])

            self._preprocess_xml(input_dir, output_dir_preprocess)

            df = self._extract_invoices(output_dir_preprocess, output_dir_df)
            df_details = self._extract_invoices_details(output_dir_preprocess, output_dir_df)
            self.logger.info(f"Processamento completato per: {input_dir}")


    def _preprocess_xml(self, input_dir, output_dir):
        """
        Estrae file XML da file .p7m oppure copia direttamente i file .xml,
        ignorando quelli che contengono '_MT_' nel nome.
        
        Args:
            input_dir (str): Percorso della cartella contenente i file di input.
            output_dir (str): Percorso della cartella dove salvare i file processati.
        """
        # Crea la cartella di destinazione se non esiste
        os.makedirs(output_dir, exist_ok=True)

        # Scorri tutti i file nella cartella di input
        for filename in os.listdir(input_dir):
            if "_MT_" in filename:
                continue  # Ignora i file metadati

            full_input_path = os.path.join(input_dir, filename)

            if filename.endswith(".xml.p7m"):
                # Rimuove .p7m per ottenere il nome del file XML di output
                output_filename = filename[:-4]
                full_output_path = os.path.join(output_dir, output_filename)
                try:
                    get_xml_from_p7m(full_input_path, full_output_path, logger=self.logger)
                    self.logger.info(f"✔ Estratto: {filename}")
                except subprocess.CalledProcessError:
                    self.logger.info(f"❌ Errore nell'estrazione di: {filename}")

            elif filename.endswith(".xml"):
                full_output_path = os.path.join(output_dir, filename)
                shutil.copy(full_input_path, full_output_path)
                self.logger.info(f"📄 Copiato: {filename}")

        self.logger.info("✅ Processing completato.")


    def _extract_invoices(self, input_folder, output_folder):
        def strip_ns(tag):
            return tag.split('}')[-1] if '}' in tag else tag

        dati = []

        for filename in os.listdir(input_folder):
            if filename.endswith(".xml"):
                file_path = os.path.join(input_folder, filename)
                try:
                    tree = load_xml_safe(file_path, logger=self.logger)
                    root = tree.getroot()

                    # Inizializzazione dei campi
                    record = {
                        "Nome_file": filename,
                        "IdPaese_Mittente": None,
                        "IdCodice_Mittente": None,
                        "Denominazione_Mittente": None,
                        "IdPaese_Destinatario": None,
                        "IdCodice_Destinatario": None,
                        "Denominazione_Destinatario": None,
                        "Importo_totale_doc": None,
                        "Data_Fattura": None,
                        "Nr_Fattura": None
                    }

                    # Estrazione Header
                    for elem in root.iter():
                        if strip_ns(elem.tag) == "FatturaElettronicaHeader":
                            # CedentePrestatore (mittente)
                            cedente = elem.find(".//{*}CedentePrestatore")
                            if cedente is not None:
                                id_fiscale = cedente.find(".//{*}IdFiscaleIVA")
                                denominazione = cedente.find(".//{*}Denominazione")
                                if id_fiscale is not None:
                                    id_paese = id_fiscale.find(".//{*}IdPaese")
                                    id_codice = id_fiscale.find(".//{*}IdCodice")
                                    if id_paese is not None:
                                        record["IdPaese_Mittente"] = id_paese.text
                                    if id_codice is not None:
                                        record["IdCodice_Mittente"] = id_codice.text
                                if denominazione is not None:
                                    record["Denominazione_Mittente"] = denominazione.text

                            # CessionarioCommittente (destinatario)
                            cessionario = elem.find(".//{*}CessionarioCommittente")
                            if cessionario is not None:
                                id_fiscale = cessionario.find(".//{*}IdFiscaleIVA")
                                denominazione = cessionario.find(".//{*}Denominazione")
                                if id_fiscale is not None:
                                    id_paese = id_fiscale.find(".//{*}IdPaese")
                                    id_codice = id_fiscale.find(".//{*}IdCodice")
                                    if id_paese is not None:
                                        record["IdPaese_Destinatario"] = id_paese.text
                                    if id_codice is not None:
                                        record["IdCodice_Destinatario"] = id_codice.text
                                if denominazione is not None:
                                    record["Denominazione_Destinatario"] = denominazione.text

                    # Estrazione ImportoTotaleDocumento
                    for elem in root.iter():
                        if strip_ns(elem.tag) == "ImportoTotaleDocumento":
                            record["Importo_totale_doc"] = elem.text
                            break  # ne basta uno

                    # Estrazione DatiGeneraliDocumento
                    dati_generali_doc = root.find(".//{*}DatiGeneraliDocumento")
                    if dati_generali_doc is not None:
                        data = dati_generali_doc.find(".//{*}Data")
                        numero = dati_generali_doc.find(".//{*}Numero")
                        if data is not None:
                            record["Data_Fattura"] = data.text
                        if numero is not None:
                            record["Nr_Fattura"] = numero.text

                    # Aggiungi riga al dataframe
                    dati.append(record)

                except ET.ParseError:
                    self.logger.error(f"Errore di parsing nel file: {filename}")

        # Creazione DataFrame e salvataggio
        df = pd.DataFrame(dati)
        input_folder_name = os.path.basename(os.path.normpath(input_folder))
        output_filename = f"{input_folder_name}_invoices.csv"
        output_path = os.path.join(output_folder, output_filename)
        df.to_csv(output_path, index=False)
        self.logger.info(f"File salvato in: {output_path}")
        return df


    def _extract_invoices_details(self, input_folder, output_folder):
        """
        Estrae i dettagli delle fatture da file XML e li salva in un DataFrame.
        
        Returns:
            pd.DataFrame: DataFrame contenente i dettagli delle fatture.
        """
        # Carica il file XML

        df_invoices_details = pd.DataFrame()

        for filename in os.listdir(input_folder):
            if filename.endswith(".xml"):
                file_path = os.path.join(input_folder, filename)
                try:
                    tree = load_xml_safe(file_path, logger=self.logger)
                    root = tree.getroot()

                    # Estrazione dei dati generali della fattura
                    dati_generali_doc = root.find(".//{*}DatiGeneraliDocumento")
                    data_fattura = None
                    nr_fattura = None

                    if dati_generali_doc is not None:
                        data = dati_generali_doc.find(".//{*}Data")
                        numero = dati_generali_doc.find(".//{*}Numero")
                        if data is not None:
                            data_fattura = data.text
                        if numero is not None:
                            nr_fattura = numero.text

                    # Lista per raccogliere le righe della fattura
                    righe_fattura = []

                    # Estrazione delle linee della fattura
                    for linea in root.findall(".//{*}DettaglioLinee"):
                        descrizione = linea.find(".//{*}Descrizione")
                        quantita = linea.find(".//{*}Quantita")
                        prezzo_unitario = linea.find(".//{*}PrezzoUnitario")
                        prezzo_totale = linea.find(".//{*}PrezzoTotale") 
                        iva = linea.find(".//{*}AliquotaIVA")

                        riga = {
                            "Data_Fattura": data_fattura,
                            "Nr_Fattura": nr_fattura,
                            "Descrizione": descrizione.text if descrizione is not None else None,
                            "Quantita": float(quantita.text) if quantita is not None else None,
                            "Prezzo_unit": float(prezzo_unitario.text) if prezzo_unitario is not None else None,
                            "Prezzo_tot": float(prezzo_totale.text) if prezzo_totale is not None else None,
                            "iva": float(iva.text) if iva is not None else None,

                        }
                        righe_fattura.append(riga)

                    # Creazione del DataFrame
                    df_fattura = pd.DataFrame(righe_fattura)

                    df_fattura['Prezzo_ivato'] = df_fattura['Prezzo_tot'] * (1 +  (df_fattura['iva'] / 100) )

                    df_invoices_details = pd.concat([df_invoices_details, df_fattura], ignore_index=True)


                except ET.ParseError:
                    self.logger.error(f"Errore di parsing nel file: {filename}")

        input_folder_name = os.path.basename(os.path.normpath(input_folder))
        output_filename = f"{input_folder_name}_invoices_details.csv"
        output_path = os.path.join(output_folder, output_filename)
        df_invoices_details.to_csv(output_path, index=False)
        self.logger.info(f"File salvato in: {output_path}")
        return df_invoices_details