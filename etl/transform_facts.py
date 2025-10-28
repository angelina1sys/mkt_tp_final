import pandas as pd
import os

WAREHOUSE_FACT_PATH = os.path.join('warehouse', 'fact')

def get_date_id(df, date_col):
    """Aplica formato de clave date_id (YYYYMMDD) a una columna de fechas."""
    # Convertir a datetime, normalizar a medianoche, formatear y convertir a INT
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.normalize()
    return df[date_col].dt.strftime('%Y%m%d').fillna(0).astype(int)

# --- Funciones de Creación de Hechos ---

def create_fact_sales(raw_data, dimensions):
    """Crea la tabla de hechos de ventas (granularidad: ítem)."""
    
    # 1. Unir ítems con cabecera de orden
    df_items = raw_data['sales_order_item'].copy()
    df_orders = raw_data['sales_order'][['order_id', 'order_date', 'customer_id', 
                                          'channel_id', 'status', 'total_amount', 
                                          'shipping_address_id']].copy()
    fact_sales = pd.merge(df_items, df_orders, on='order_id', how='left')

    # 2. Enlace Geográfico (Provincia de envío para KPI Ventas por Provincia)
    df_address = raw_data['address'][['address_id', 'province_id']].copy()
    
    fact_sales = pd.merge(
        fact_sales, 
        df_address, 
        left_on='shipping_address_id', 
        right_on='address_id', 
        how='left'
    ).rename(columns={'province_id': 'shipping_province_id'})
    
    # 3. Creación de Claves (PKs del Hecho y FKs)
    fact_sales['order_item_pk'] = fact_sales.index + 1 # PK del Hecho
    fact_sales['date_id'] = get_date_id(fact_sales, 'order_date')
    
    # 4. Seleccionar columnas finales
    final_cols = ['order_item_pk', 'date_id', 'order_id', 'customer_id', 'product_id', 
                  'channel_id', 'shipping_province_id', 'quantity', 'line_total', 
                  'total_amount', 'status']
    
    output_path = os.path.join(WAREHOUSE_FACT_PATH, 'fact_sales.csv')
    fact_sales[final_cols].to_csv(output_path, index=False)
    print(f"  -> fact_sales creada en: {output_path}")
    
def create_fact_nps(raw_data, dimensions):
    """Crea la tabla de hechos de respuesta NPS (Base para KPI de NPS)."""
    df_nps = raw_data['nps_response'].copy()
    
    df_nps['nps_pk'] = df_nps.index + 1 # PK del Hecho
    df_nps['date_id'] = get_date_id(df_nps, 'responded_at')
    
    # Lógica para categorizar la respuesta (Necesaria para el cálculo del NPS)
    def categorize_score(score):
        if score >= 9:
            return 'Promoter' # 9-10
        elif score >= 7:
            return 'Passive'  # 7-8
        else:
            return 'Detractor' # 0-6
            
    df_nps['nps_category'] = df_nps['score'].apply(categorize_score)
    
    final_cols = ['nps_pk', 'date_id', 'customer_id', 'channel_id', 'score', 'nps_category']
    
    output_path = os.path.join(WAREHOUSE_FACT_PATH, 'fact_nps.csv')
    df_nps[final_cols].to_csv(output_path, index=False)
    print(f"  -> fact_nps creada en: {output_path}")

def create_fact_web_session(raw_data, dimensions):
    """Crea la tabla de hechos de sesiones web (Base para KPI Usuarios Activos)."""
    df_session = raw_data['web_session'].copy()
    
    df_session['session_pk'] = df_session.index + 1 # PK del Hecho
    df_session['date_id'] = get_date_id(df_session, 'started_at')
    
    # Calcular duración de sesión (métrica opcional)
    df_session['started_at'] = pd.to_datetime(df_session['started_at'])
    df_session['ended_at'] = pd.to_datetime(df_session['ended_at'], errors='coerce')
    
    # Calculamos la duración en segundos
    df_session['duration_seconds'] = (df_session['ended_at'] - df_session['started_at']).dt.total_seconds().fillna(0).astype(int)
    
    final_cols = ['session_pk', 'date_id', 'customer_id', 'source', 'device', 'duration_seconds']
    
    output_path = os.path.join(WAREHOUSE_FACT_PATH, 'fact_web_session.csv')
    df_session[final_cols].to_csv(output_path, index=False)
    print(f"  -> fact_web_session creada en: {output_path}")
    
def create_fact_shipment(raw_data, dimensions):
    """
    Crea la tabla de hechos de envíos.
    Clave para la meta de 'reducir tiempos de entrega en Mendoza'.
    """
    df_shipment = raw_data['shipment'].copy()
    
    df_shipment['shipment_pk'] = df_shipment.index + 1 # PK del Hecho
    df_shipment['shipped_date_id'] = get_date_id(df_shipment, 'shipped_at')
    
    # 1. Unir con cabecera de orden para obtener la dirección de envío
    df_orders = raw_data['sales_order'][['order_id', 'shipping_address_id']].copy()
    df_shipment = pd.merge(df_shipment, df_orders, on='order_id', how='left')
    
    # 2. Unir con dirección para obtener la provincia de destino (Mendoza)
    df_address = raw_data['address'][['address_id', 'province_id']].copy()
    df_shipment = pd.merge(
        df_shipment, 
        df_address, 
        left_on='shipping_address_id', 
        right_on='address_id', 
        how='left'
    ).rename(columns={'province_id': 'shipping_province_id'})
    
    # 3. Calcular tiempo de entrega (métrica principal)
    df_shipment['shipped_at'] = pd.to_datetime(df_shipment['shipped_at'], errors='coerce')
    df_shipment['delivered_at'] = pd.to_datetime(df_shipment['delivered_at'], errors='coerce')
    
    # Calcula el tiempo de entrega en días (float)
    df_shipment['delivery_time_days'] = (df_shipment['delivered_at'] - df_shipment['shipped_at']).dt.total_seconds() / (60 * 60 * 24)
    
    final_cols = ['shipment_pk', 'shipped_date_id', 'order_id', 'shipping_province_id', 
                  'carrier', 'status', 'delivery_time_days']
    
    output_path = os.path.join(WAREHOUSE_FACT_PATH, 'fact_shipment.csv')
    df_shipment[final_cols].to_csv(output_path, index=False)
    print(f"  -> fact_shipment creada en: {output_path}")

# --- Función Orquestadora ---

def create_all_facts(raw_data, dimensions):
    """Orquesta la creación de todas las tablas de hechos."""
    
    print("  - Creando fact_sales...")
    create_fact_sales(raw_data, dimensions)
    
    print("  - Creando fact_nps...")
    create_fact_nps(raw_data, dimensions)
    
    print("  - Creando fact_web_session...")
    create_fact_web_session(raw_data, dimensions)
    
    print("  - Creando fact_shipment (Métrica de Logística)...")
    create_fact_shipment(raw_data, dimensions)