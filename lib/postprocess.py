import pandas as pd
import glob
import os

def postprocess(data_string):
    """
    Funzione per eseguire il post-processing dei file CSV delle fatture.
    Unisce i dettagli delle fatture con le informazioni di base delle fatture.
    """
    # Percorso alla cartella che contiene i CSV
    folder_path = 'data/df' 

    # Trova tutti i file che terminano con _invoices.csv
    invoice_files = glob.glob(os.path.join(folder_path, '*_invoices.csv'))

    # Trova tutti i file che terminano con _invoices_details.csv
    invoice_details_files = glob.glob(os.path.join(folder_path, '*_invoices_details.csv'))

    # Leggi e concatena tutti i file in un unico DataFrame
    df_invoices = pd.concat([pd.read_csv(file) for file in invoice_files], ignore_index=True)
    df_invoices_details = pd.concat([pd.read_csv(file) for file in invoice_details_files], ignore_index=True)

    # Seleziona solo le colonne necessarie da df_invoices
    df_invoices_reduced = df_invoices[['Data_Fattura', 'Nr_Fattura', 'Denominazione_Mittente', 'IdCodice_Mittente']]

    # Esegui il merge
    df_invoices_details = df_invoices_details.merge(
        df_invoices_reduced,
        on=['Data_Fattura', 'Nr_Fattura'],
        how='left'
    )

    df_invoices['Mese_Fattura'] = pd.to_datetime(df_invoices['Data_Fattura']).dt.month
    df_invoices_details['Mese_Fattura'] = pd.to_datetime(df_invoices_details['Data_Fattura']).dt.month

    path = f'data/{data_string}_df_invoices_totali_per_fornitore.xlsx'
    path_details = f'data/{data_string}_df_invoices_details.xlsx'

    df_invoices_details.to_excel(path_details, index=False)
    df_invoices.to_excel(path, index=False)