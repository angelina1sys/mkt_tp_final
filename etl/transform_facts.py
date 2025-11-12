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
    df_orders = raw_data['sales_order'].copy()
    fact_sales = pd.merge(df_items, df_orders, on='order_id', how='left', suffixes=('_item', '_order'))

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
    
    
    output_path = os.path.join(WAREHOUSE_FACT_PATH, 'fact_sales_order_item.csv')
    fact_sales.to_csv(output_path, index=False)
    print(f"  -> fact_sales_order_item creada en: {output_path}")


def create_fact_payment(raw_data, dimensions):
    """
    Crea la tabla de hechos de pago, usando la tabla RAW 'payment'.
    PK: payment_pk, FK: order_id, date_id (paid_at).
    """
    df_payment = raw_data['payment'].copy()
    
    df_payment['payment_pk'] = df_payment.index + 1 # PK del Hecho
    df_payment['date_id'] = get_date_id(df_payment, 'paid_at') # Derivado de paid_at
    
    final_cols = ['payment_pk', 'date_id', 'order_id', 'method', 'status', 'amount', 'transaction_ref']
    
    output_path = os.path.join(WAREHOUSE_FACT_PATH, 'fact_payment.csv')
    df_payment[final_cols].to_csv(output_path, index=False)
    print(f"  -> fact_payment creada en: {output_path}")
    
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

def create_fact_sales_order(raw_data, dimensions):
    """
    Crea la tabla de hechos de cabecera de pedidos (granularidad: orden), 
    reemplazando shipping_address_id por la FK shipping_province_id.
    """
    
    
    # 1. Cargar datos base y asegurar una copia
    df_sales_order = raw_data['sales_order'].copy()
    
    # --- PASO DE UNIÓN: Crear el Enlace de Provincia ---
    
    # 1.1. Obtener la tabla address de RAW
    df_address = raw_data['address'][['address_id', 'province_id']].copy()
    
    # 1.2. Unir df_sales_order con address usando shipping_address_id
    # Se añade la columna 'province_id' a la tabla de hechos.
    df_sales_order = pd.merge(
        df_sales_order,
        df_address,
        left_on='shipping_address_id',
        right_on='address_id',
        how='left'
    )
    
    # 1.3. Renombrar la columna obtenida para el DW
    df_sales_order.rename(columns={'province_id': 'shipping_province_id'}, inplace=True)
    
    # 2. Creación de Claves Foráneas (Time)
    # Asumo que get_date_id está definida en tu script
    df_sales_order['date_id'] = get_date_id(df_sales_order, 'order_date')
    
    # 3. Selección de Columnas Finales
    final_cols = [
        'order_id',                  # PK / Dimensión Degenerada
        'customer_id',               # FK
        'channel_id',                # FK
        'store_id',                  # FK
        'order_date', 
        'date_id',                   # FK a dim_calendar
        'billing_address_id',        # Atributo/FK original (se mantiene)
        'shipping_province_id',      # NUEVA FK a dim_province
        'status', 
        'currency_code', 
        'subtotal', 
        'tax_amount', 
        'shipping_fee', 
        'total_amount'               # Métrica clave
    ]
    
    # NOTA: Debemos eliminar la columna 'shipping_address_id' original y 'address_id' del merge.
    # El merge anterior ya dejó 'shipping_province_id' en df_sales_order.
    
    fact_sales = df_sales_order[final_cols].copy()
    
    # 4. Carga
    output_path = os.path.join(WAREHOUSE_FACT_PATH, 'fact_sales_order.csv')
    fact_sales.to_csv(output_path, index=False)
    print(f"  -> fact_sales_order (Header Granularity) creada con FK de Provincia en: {output_path}")

# --- Función Orquestadora ---

def create_all_facts(raw_data, dimensions):
    """Orquesta la creación de todas las tablas de hechos."""
    
    print("  - Creando fact_sales (Header Granularity)...")
    create_fact_sales(raw_data, dimensions)

    print("  - Creando fact_sales_order...")
    create_fact_sales_order(raw_data, dimensions)

    print("  - Creando fact_payment (Nueva)...")
    create_fact_payment(raw_data, dimensions)
    
    print("  - Creando fact_nps...")
    create_fact_nps(raw_data, dimensions)
    
    print("  - Creando fact_web_session...")
    create_fact_web_session(raw_data, dimensions)
    
    print("  - Creando fact_shipment (Métrica de Logística)...")
    create_fact_shipment(raw_data, dimensions)