import pandas as pd
import numpy as np
import os

WAREHOUSE_DIM_PATH = os.path.join('warehouse', 'dim')

# --- Funciones de Creación de Dimensiones ---

def create_dim_calendar(raw_data):
    """
    Crea la dimensión de calendario a partir de todas las fechas de transacción.
    """
    
    # 1. Recolectar todas las fechas de hechos relevantes
    date_cols = [
        raw_data['sales_order']['order_date'],
        raw_data['web_session']['started_at'],
        raw_data['nps_response']['responded_at'],
    ]
    
    # Concatenar y convertir a datetime
    all_dates = pd.to_datetime(pd.concat(date_cols, ignore_index=True), errors='coerce')
    
    # Obtener fechas únicas
    unique_dates = all_dates.dt.normalize().unique()
    df_dates = pd.DataFrame(unique_dates, columns=['date'])
    df_dates['date'] = pd.to_datetime(df_dates['date'])
    df_dates.dropna(subset=['date'], inplace=True) # Eliminar fechas nulas
    
    # 2. Generar atributos de tiempo
    df_dates['date_id'] = df_dates['date'].dt.strftime('%Y%m%d').astype(int)
    df_dates['year'] = df_dates['date'].dt.year
    df_dates['month'] = df_dates['date'].dt.month
    df_dates['month_name'] = df_dates['date'].dt.strftime('%B')
    df_dates['day'] = df_dates['date'].dt.day
    df_dates['day_of_week'] = df_dates['date'].dt.dayofweek # 0=Lunes, 6=Domingo
    df_dates['week_of_year'] = df_dates['date'].dt.isocalendar().week.astype(int)
    df_dates['quarter'] = df_dates['date'].dt.quarter
    
    # Seleccionar y ordenar columnas
    dim_calendar = df_dates[[
        'date_id', 'date', 'year', 'quarter', 'month', 'month_name', 
        'day', 'day_of_week', 'week_of_year'
    ]].sort_values('date_id')
    
    output_path = os.path.join(WAREHOUSE_DIM_PATH, 'dim_calendar.csv')
    dim_calendar.to_csv(output_path, index=False)
    print(f"  -> dim_calendar creada en: {output_path}")
    
    return dim_calendar

def create_dim_customer(raw_data):
    """Crea la dimensión de clientes (PK: customer_id)."""
    df_customer = raw_data['customer'].copy()
    
    # Aplicar DDL y desnormalización (Concatenar nombres)
    df_customer['full_name'] = df_customer['first_name'].fillna('') + ' ' + df_customer['last_name'].fillna('')
    
    # Seleccionar solo las columnas finales para la dimensión
    dim_customer = df_customer[[
        'customer_id', 
        'email', 
        'full_name', 
        'phone', 
        'status', 
        'created_at' 
    ]].rename(columns={'created_at': 'signup_date'})
    
    output_path = os.path.join(WAREHOUSE_DIM_PATH, 'dim_customers.csv')
    dim_customer.to_csv(output_path, index=False)
    print(f"  -> dim_customers creada en: {output_path}")
    
    return dim_customer

def create_dim_product(raw_data):
    """Crea la dimensión de productos (PK: product_id), desnormalizando categoría."""
    df_prod = raw_data['product'].copy()
    df_cat = raw_data['product_category'][['category_id', 'name']].rename(
        columns={'name': 'category_name'}).copy()
    
    # Unir producto con categoría (Desnormalización)
    df_prod = pd.merge(df_prod, df_cat, on='category_id', how='left')
    
    dim_product = df_prod[['product_id', 'sku', 'name', 'list_price', 
                           'category_name', 'status', 'created_at']].rename(
                               columns={'name': 'product_name'})
    
    output_path = os.path.join(WAREHOUSE_DIM_PATH, 'dim_products.csv')
    dim_product.to_csv(output_path, index=False)
    print(f"  -> dim_products creada en: {output_path}")
    
    return dim_product

def create_dim_channel(raw_data):
    """Crea la dimensión de canales (PK: channel_id)."""
    df = raw_data['channel'].copy()
    
    dim_channel = df[['channel_id', 'code', 'name']].rename(
        columns={'code': 'channel_code', 'name': 'channel_name'})
    
    output_path = os.path.join(WAREHOUSE_DIM_PATH, 'dim_channels.csv')
    dim_channel.to_csv(output_path, index=False)
    print(f"  -> dim_channels creada en: {output_path}")
    
    return dim_channel

def create_dim_province(raw_data):
    """Crea la dimensión de provincias (PK: province_id)."""
    df = raw_data['province'].copy()
    
    dim_province = df[['province_id', 'name', 'code']].rename(
        columns={'name': 'province_name', 'code': 'province_code'})
    
    output_path = os.path.join(WAREHOUSE_DIM_PATH, 'dim_provinces.csv')
    dim_province.to_csv(output_path, index=False)
    print(f"  -> dim_provinces creada en: {output_path}")
    
    return dim_province

# --- Función Orquestadora ---

def create_all_dims(raw_data):
    """Orquesta la creación de todas las dimensiones y devuelve el diccionario."""
    dimensions = {}
    
    print("  - Creando dim_calendar...")
    dimensions['calendar'] = create_dim_calendar(raw_data)
    
    print("  - Creando dim_customers...")
    dimensions['customer'] = create_dim_customer(raw_data)
    
    print("  - Creando dim_products...")
    dimensions['product'] = create_dim_product(raw_data)
    
    print("  - Creando dim_channels...")
    dimensions['channel'] = create_dim_channel(raw_data)
    
    print("  - Creando dim_provinces...")
    dimensions['province'] = create_dim_province(raw_data)
    
    return dimensions