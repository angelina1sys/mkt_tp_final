import pandas as pd
import os
from etl.transform_dims import create_all_dims
from etl.transform_facts import create_all_facts

# Rutas de los directorios
RAW_PATH = 'RAW'
WAREHOUSE_PATH = 'warehouse'

def main():
    print("Iniciando Proceso ETL (Extract, Transform, Load) para EcoBottle...")
    
    # 1. Asegurar directorios de salida
    os.makedirs(os.path.join(WAREHOUSE_PATH, 'dim'), exist_ok=True)
    os.makedirs(os.path.join(WAREHOUSE_PATH, 'fact'), exist_ok=True)
    
    # 2. Extracción: Cargar todos los CSVs
    raw_data = load_raw_data()
    
    # 3. Transformación y Carga de DIMENSIONES
    # Esta función debe generar y guardar dim_customer, dim_product, dim_calendar, etc.
    print("--> Creando Tablas de Dimensiones...")
    dimensions = create_all_dims(raw_data)
    
    # 4. Transformación y Carga de HECHOS
    # Esta función debe generar y guardar fact_sales, fact_nps, fact_web_session.
    print("--> Creando Tablas de Hechos...")
    create_all_facts(raw_data, dimensions)
    
    print("Proceso ETL Finalizado. Data Warehouse listo en el directorio 'warehouse/'.")

def load_raw_data():
    """Carga todos los archivos CSV del directorio RAW."""
    raw_data = {}
    print(f"Leyendo datos desde: {RAW_PATH}")
    for filename in os.listdir(RAW_PATH):
        if filename.endswith('.csv'):
            # Usa el nombre del archivo sin extensión como clave (ej. 'customer', 'sales_order')
            table_name = filename.replace('.csv', '')
            file_path = os.path.join(RAW_PATH, filename)
            
            # Nota: Considerar el tipo de dato de las columnas para evitar errores de lectura.
            raw_data[table_name] = pd.read_csv(file_path)
            # print(f"Cargada tabla: {table_name}")
            
    return raw_data

if __name__ == '__main__':
    main()