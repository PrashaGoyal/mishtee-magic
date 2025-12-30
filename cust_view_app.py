import gradio as gr
import requests
import pandas as pd
from supabase import create_client, Client

# --- 1. ASSETS & CREDENTIALS ---
SUPABASE_URL = "https://ezydpnzbumnxxyqkidss.supabase.co"
SUPABASE_KEY = "sb_publishable_uk3J6PW9JPK-E93dpsukIg_jydFl_6N"
LOGO_URL = "https://github.com/PrashaGoyal/mishtee-magic/blob/main/mishTee_logo.png?raw=true"
STYLE_URL = "https://raw.githubusercontent.com/PrashaGoyal/mishtee-magic/refs/heads/main/style.py"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch and execute style.py to get 'mishtee_css'
try:
    style_response = requests.get(STYLE_URL)
    style_namespace = {}
    exec(style_response.text, {}, style_namespace)
    mishtee_css = style_namespace.get("mishtee_css", "")
except Exception as e:
    mishtee_css = ""
    print(f"CSS Load Error: {e}")

# --- 2. LOGIC FUNCTIONS ---

def get_customer_portal_data(phone_number):
    """Retrieves personalized greeting and order history."""
    if not phone_number or not phone_number.startswith('9'):
        return "Please enter a valid mobile number starting with 9.", pd.DataFrame()

    # Fetch Customer Name
    cust_res = supabase.table("customers").select("full_name").eq("phone", phone_number).execute()
    
    if not cust_res.data:
        return "Welcome to MishTee-Magic! Please visit a store to register.", pd.DataFrame()

    name = cust_res.data[0]['full_name']
    greeting = f"### Namaste, {name} ji! \n#### Great to see you again."

    # Fetch Order History with related Product/Store data
    order_res = supabase.table("orders")\
        .select("order_id, order_date, status, qty_kg, order_value_inr, products(sweet_name), stores(location_name)")\
        .eq("cust_phone", phone_number)\
        .order("order_date", desc=True)\
        .execute()

    if not order_res.data:
        return greeting, pd.DataFrame(columns=["No orders found yet."])

    # Format Dataframe
    df = pd.json_normalize(order_res.data)
    column_mapping = {
        "order_id": "Order ID",
        "order_date": "Date",
        "status": "Status",
        "qty_kg": "Qty (kg)",
        "order_value_inr": "Total (₹)",
        "products.sweet_name": "Item",
        "stores.location_name": "Store"
    }
    orders_df = df[list(column_mapping.keys())].rename(columns=column_mapping)
    return greeting, orders_df

def get_trending_products():
    """Retrieves the top 4 best-selling products."""
    res = supabase.table("orders").select("qty_kg, products(sweet_name, variant_type, price_per_kg)").execute()

    if not res.data:
        return pd.DataFrame(columns=["Trending data coming soon."])

    df = pd.json_normalize(res.data)
    trending_df = df.groupby(['products.sweet_name', 'products.variant_type', 'products.price_per_kg'])\
        .agg({'qty_kg': 'sum'}).reset_index()
    
    trending_df = trending_df.sort_values(by='qty_kg', ascending=False).head(4)
    trending_df.columns = ["Sweet Name", "Variant", "Price (₹/kg)", "Total Sold (kg)"]
    return trending_df

# --- 3. GRADIO UI LAYOUT ---

with gr.Blocks(css=mishtee_css, title="MishTee-Magic Portal") as demo:
    # Header Section
    with gr.Row():
        with gr.Column(scale=1): gr.Image(LOGO_URL, show_label=False, container=False, width=250)
    
    gr.Markdown("<h1 style='text-align: center;'>MishTee-Magic</h1>")
    gr.Markdown("<h3 style='text-align: center; letter-spacing: 2px;'>Pure Roots. Golden Moments.</h3>")
    
    # Welcome & Login
    with gr.Row():
        with gr.Column():
            greeting_output = gr.Markdown("### Welcome to the Magic \n Please enter your registered mobile number.")
            login_input = gr.Textbox(label="Mobile Number", placeholder="9xxxx xxxxx")
            login_btn = gr.Button("ENTER PORTAL", variant="primary")

    # Tabbed Content
    with gr.Tabs():
        with gr.TabItem("My Order History"):
            history_table = gr.DataFrame(interactive=False)
            
        with gr.TabItem("Trending Today"):
            trending_table = gr.DataFrame(value=get_trending_products(), interactive=False)

    # Event Mapping
    login_btn.click(
        fn=get_customer_portal_data,
        inputs=login_input,
        outputs=[greeting_output, history_table]
    )

    gr.Markdown("<br><p style='text-align: center; opacity: 0.5;'>Handcrafted with A2 Purity in Ahmedabad</p>")

if __name__ == "__main__":
    demo.launch()
