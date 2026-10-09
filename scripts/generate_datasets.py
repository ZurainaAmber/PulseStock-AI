"""
PulseStock AI - Dataset Generator
Cypher 2026 Challenge 6

Generates 7 realistic, interconnected CSV files into data/ for the dark-store inventory prediction system.
Reference Simulation Time: October 9, 2026, 17:00 IST (2026-10-09T17:00:00+05:30).
"""

import os
import csv
import math
import random
from datetime import datetime, timedelta, timezone

# Ensure deterministic generation
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Simulation Reference Time: October 9, 2026, 17:00 IST
IST = timezone(timedelta(hours=5, minutes=30))
REF_TIME = datetime(2026, 10, 9, 17, 0, 0, tzinfo=IST)

# ----------------------------------------------------
# 1. Dark Stores Definition (30 Stores)
# ----------------------------------------------------
STORES = [
    {"store_id": "STORE_001", "store_name": "Store 1 - Indiranagar Main", "location_zone": "Indiranagar", "stadium_proximity_km": 5.2},
    {"store_id": "STORE_002", "store_name": "Store 2 - MG Road Central", "location_zone": "Central Bangalore", "stadium_proximity_km": 0.8},
    {"store_id": "STORE_003", "store_name": "Store 3 - Domlur Hub", "location_zone": "Domlur", "stadium_proximity_km": 3.4},
    {"store_id": "STORE_004", "store_name": "Store 4 - Whitefield Tech Park", "location_zone": "Whitefield", "stadium_proximity_km": 14.5},
    {"store_id": "STORE_005", "store_name": "Store 5 - Electronic City Phase 1", "location_zone": "Electronic City", "stadium_proximity_km": 18.2},
    {"store_id": "STORE_006", "store_name": "Store 6 - Bellandur Ring Road", "location_zone": "Bellandur", "stadium_proximity_km": 9.1},
    {"store_id": "STORE_007", "store_name": "Store 7 - Koramangala Tech Park", "location_zone": "Koramangala Zone 4", "stadium_proximity_km": 1.4},
    {"store_id": "STORE_008", "store_name": "Store 8 - HSR Layout Sector 1", "location_zone": "HSR Layout", "stadium_proximity_km": 6.8},
    {"store_id": "STORE_009", "store_name": "Store 9 - Jayanagar 4th Block", "location_zone": "Jayanagar", "stadium_proximity_km": 4.5},
    {"store_id": "STORE_010", "store_name": "Store 10 - Malleshwaram 8th Main", "location_zone": "Malleshwaram", "stadium_proximity_km": 2.3},
    {"store_id": "STORE_011", "store_name": "Store 11 - Rajajinagar Industrial", "location_zone": "Rajajinagar", "stadium_proximity_km": 4.1},
    {"store_id": "STORE_012", "store_name": "Store 12 - Marathahalli Bridge", "location_zone": "Marathahalli", "stadium_proximity_km": 11.2},
    {"store_id": "STORE_013", "store_name": "Store 13 - BTM Layout 2nd Stage", "location_zone": "BTM Layout", "stadium_proximity_km": 5.9},
    {"store_id": "STORE_014", "store_name": "Store 14 - Hebbal Flyover Junction", "location_zone": "Hebbal", "stadium_proximity_km": 8.7},
    {"store_id": "STORE_015", "store_name": "Store 15 - Yelahanka New Town", "location_zone": "Yelahanka", "stadium_proximity_km": 16.4},
    {"store_id": "STORE_016", "store_name": "Store 16 - Banashankari 3rd Stage", "location_zone": "Banashankari", "stadium_proximity_km": 7.3},
    {"store_id": "STORE_017", "store_name": "Store 17 - Kalyan Nagar HRBR", "location_zone": "Kalyan Nagar", "stadium_proximity_km": 9.8},
    {"store_id": "STORE_018", "store_name": "Store 18 - Sarjapur Road Hub", "location_zone": "Sarjapur", "stadium_proximity_km": 12.1},
    {"store_id": "STORE_019", "store_name": "Store 19 - Richmond Town Circle", "location_zone": "Richmond Town", "stadium_proximity_km": 1.9},
    {"store_id": "STORE_020", "store_name": "Store 20 - Sadashivnagar Palace", "location_zone": "Sadashivnagar", "stadium_proximity_km": 3.1},
    {"store_id": "STORE_021", "store_name": "Store 21 - CV Raman Nagar", "location_zone": "CV Raman Nagar", "stadium_proximity_km": 6.2},
    {"store_id": "STORE_022", "store_name": "Store 22 - Mahadevapura ORR", "location_zone": "Mahadevapura", "stadium_proximity_km": 10.5},
    {"store_id": "STORE_023", "store_name": "Store 23 - Bannerghatta Road", "location_zone": "Bannerghatta", "stadium_proximity_km": 8.9},
    {"store_id": "STORE_024", "store_name": "Store 24 - KR Puram Station", "location_zone": "KR Puram", "stadium_proximity_km": 13.0},
    {"store_id": "STORE_025", "store_name": "Store 25 - Nagarbhavi 2nd Stage", "location_zone": "Nagarbhavi", "stadium_proximity_km": 11.8},
    {"store_id": "STORE_026", "store_name": "Store 26 - Kengeri Satellite Town", "location_zone": "Kengeri", "stadium_proximity_km": 17.5},
    {"store_id": "STORE_027", "store_name": "Store 27 - Yeshwanthpur APMC", "location_zone": "Yeshwanthpur", "stadium_proximity_km": 6.5},
    {"store_id": "STORE_028", "store_name": "Store 28 - Kammanahalli Main", "location_zone": "Kammanahalli", "stadium_proximity_km": 8.1},
    {"store_id": "STORE_029", "store_name": "Store 29 - Frazer Town Mosque", "location_zone": "Frazer Town", "stadium_proximity_km": 2.8},
    {"store_id": "STORE_030", "store_name": "Store 30 - RT Nagar Block 2", "location_zone": "RT Nagar", "stadium_proximity_km": 4.9},
]

# ----------------------------------------------------
# 2. Generate Products (150 SKUs)
# ----------------------------------------------------
CATEGORIES = [
    "Cold Beverages", "Hot Beverages", "Snacks & Chips", "Instant Meals", 
    "Dairy & Bakery", "Groceries", "Fruits & Vegetables", "Personal Care", "Sweets"
]

# Core scenario SKUs defined explicitly
SPECIAL_SKUS = [
    {
        "sku_id": "SKU_COLD_DRINK_750ML",
        "sku_name": "Sparkling Cola 750ml",
        "category": "Cold Beverages",
        "size": "750ml",
        "unit_selling_price_inr": 90.0,
        "margin_pct": 33.33,
        "unit_cost_price_inr": 60.0
    },
    {
        "sku_id": "SKU_DIET_HERBAL_TEA_250ML",
        "sku_name": "Diet Herbal Green Tea 250ml",
        "category": "Hot Beverages",
        "size": "250ml",
        "unit_selling_price_inr": 45.0,
        "margin_pct": 33.33,
        "unit_cost_price_inr": 30.0
    },
    {
        "sku_id": "SKU_ENERGY_DRINK_250ML",
        "sku_name": "Red Bull Energy Drink 250ml",
        "category": "Cold Beverages",
        "size": "250ml",
        "unit_selling_price_inr": 125.0,
        "margin_pct": 28.0,
        "unit_cost_price_inr": 90.0
    },
    {
        "sku_id": "SKU_KALE_CHIPS_50G",
        "sku_name": "Organic Roasted Kale Chips 50g",
        "category": "Snacks & Chips",
        "size": "50g",
        "unit_selling_price_inr": 180.0,
        "margin_pct": 40.0,
        "unit_cost_price_inr": 108.0
    },
    {
        "sku_id": "SKU_CHIPS_100G",
        "sku_name": "Classic Salted Potato Chips 100g",
        "category": "Snacks & Chips",
        "size": "100g",
        "unit_selling_price_inr": 40.0,
        "margin_pct": 30.0,
        "unit_cost_price_inr": 28.0
    },
]

PRODUCT_TEMPLATES = [
    # Cold Beverages
    ("Fresh Mango Juice 1L", "Cold Beverages", "1L", 110.0, 30.0),
    ("Lemon Ice Tea 500ml", "Cold Beverages", "500ml", 60.0, 35.0),
    ("Cold Brew Coffee 240ml", "Cold Beverages", "240ml", 95.0, 40.0),
    ("Orange Aerated Drink 750ml", "Cold Beverages", "750ml", 85.0, 32.0),
    ("Clear Lime Soda 750ml", "Cold Beverages", "750ml", 80.0, 33.0),
    ("Tonic Water 350ml", "Cold Beverages", "350ml", 75.0, 35.0),
    ("Ginger Ale 330ml", "Cold Beverages", "330ml", 70.0, 35.0),
    ("Coconut Water 200ml", "Cold Beverages", "200ml", 50.0, 25.0),
    ("Flavored Lassi 250ml", "Cold Beverages", "250ml", 35.0, 25.0),
    ("Apple Cider Drink 300ml", "Cold Beverages", "300ml", 90.0, 35.0),
    ("Pomegranate Juice 500ml", "Cold Beverages", "500ml", 120.0, 30.0),
    ("Guava Nectar 1L", "Cold Beverages", "1L", 105.0, 28.0),
    ("Electrolyte Drink 500ml", "Cold Beverages", "500ml", 55.0, 30.0),
    ("Sparkling Water 500ml", "Cold Beverages", "500ml", 45.0, 35.0),

    # Hot Beverages
    ("Assam Black Tea 250g", "Hot Beverages", "250g", 140.0, 30.0),
    ("Instant Coffee Powder 100g", "Hot Beverages", "100g", 210.0, 25.0),
    ("Green Tea Bags 25s", "Hot Beverages", "50g", 160.0, 35.0),
    ("Masala Chai Mix 200g", "Hot Beverages", "200g", 120.0, 30.0),
    ("Filter Coffee Roast 250g", "Hot Beverages", "250g", 190.0, 28.0),
    ("Earl Grey Tea 100g", "Hot Beverages", "100g", 250.0, 40.0),
    ("Chamomile Herbal Infusion 20s", "Hot Beverages", "40g", 220.0, 38.0),
    ("Dark Roast Espresso Beans 250g", "Hot Beverages", "250g", 350.0, 35.0),
    ("Cardamom Chai Mix 150g", "Hot Beverages", "150g", 115.0, 30.0),
    ("Ginger Turmeric Tea 20s", "Hot Beverages", "40g", 180.0, 35.0),
    ("Hot Chocolate Mix 200g", "Hot Beverages", "200g", 160.0, 32.0),

    # Snacks & Chips
    ("Nacho Cheese Corn Chips 150g", "Snacks & Chips", "150g", 75.0, 32.0),
    ("Salted Roasted Peanuts 200g", "Snacks & Chips", "200g", 65.0, 30.0),
    ("Butter Popcorn 100g", "Snacks & Chips", "100g", 45.0, 35.0),
    ("Roasted Almonds 100g", "Snacks & Chips", "100g", 220.0, 25.0),
    ("Cashew Nuts Salted 100g", "Snacks & Chips", "100g", 240.0, 25.0),
    ("Spicy Masala Makhana 80g", "Snacks & Chips", "80g", 130.0, 38.0),
    ("Cheese Balls Snack 100g", "Snacks & Chips", "100g", 50.0, 30.0),
    ("Wheat Khakhra Masala 200g", "Snacks & Chips", "200g", 70.0, 28.0),
    ("Diet Roasted Chana 200g", "Snacks & Chips", "200g", 60.0, 30.0),
    ("Multi-grain Crackers 150g", "Snacks & Chips", "150g", 90.0, 35.0),
    ("Banana Chips Salted 150g", "Snacks & Chips", "150g", 80.0, 30.0),
    ("Tapioca Crisps 100g", "Snacks & Chips", "100g", 55.0, 28.0),
    ("Ragi Crisps Sour Cream 100g", "Snacks & Chips", "100g", 85.0, 35.0),

    # Instant Meals & Dairy
    ("Pasteurized Toned Milk 1L", "Instant Meals", "1L", 56.0, 15.0),
    ("Fresh Creamy Curd 500g", "Instant Meals", "500g", 45.0, 20.0),
    ("Salted Butter 100g", "Instant Meals", "100g", 60.0, 18.0),
    ("Fresh Paneer Block 200g", "Instant Meals", "200g", 105.0, 22.0),
    ("Processed Cheese Slices 200g", "Instant Meals", "200g", 145.0, 25.0),
    ("Instant Masala Noodles 280g", "Instant Meals", "280g", 55.0, 25.0),
    ("Cup Noodles Chicken 70g", "Instant Meals", "70g", 65.0, 30.0),
    ("Frozen Veg Nuggets 500g", "Instant Meals", "500g", 180.0, 32.0),
    ("Rolled Oats 500g", "Instant Meals", "500g", 115.0, 28.0),
    ("Instant Rava Upma 200g", "Instant Meals", "200g", 75.0, 30.0),
    ("Instant Poha Mix 200g", "Instant Meals", "200g", 65.0, 30.0),
    ("Greek Yogurt Blueberry 100g", "Instant Meals", "100g", 60.0, 30.0),
    ("Mozzarella Shredded Cheese 200g", "Instant Meals", "200g", 195.0, 25.0),
    ("Frozen French Fries 450g", "Instant Meals", "450g", 140.0, 30.0),
    ("Ready to Eat Dal Makhani 300g", "Instant Meals", "300g", 125.0, 35.0),
    ("Instant Tomato Soup 50g", "Instant Meals", "50g", 35.0, 30.0),

    # Groceries & Staples
    ("Whole Wheat Atta 5kg", "Groceries", "5kg", 260.0, 18.0),
    ("Basmati Premium Rice 5kg", "Groceries", "5kg", 550.0, 20.0),
    ("Toor Dal Unpolished 1kg", "Groceries", "1kg", 165.0, 18.0),
    ("Refined Sunflower Oil 1L", "Groceries", "1L", 145.0, 15.0),
    ("Cold Pressed Mustard Oil 1L", "Groceries", "1L", 185.0, 20.0),
    ("Iodized Salt 1kg", "Groceries", "1kg", 28.0, 15.0),
    ("Refined Sugar 1kg", "Groceries", "1kg", 48.0, 15.0),
    ("Organic Turmeric Powder 200g", "Groceries", "200g", 75.0, 30.0),
    ("Red Chilli Powder 200g", "Groceries", "200g", 90.0, 28.0),
    ("Coriander Powder 200g", "Groceries", "200g", 70.0, 28.0),
    ("Garam Masala Powder 100g", "Groceries", "100g", 85.0, 32.0),
    ("Cumin Seeds Jeera 200g", "Groceries", "200g", 140.0, 25.0),
    ("Moong Dal Split 1kg", "Groceries", "1kg", 145.0, 20.0),
    ("Chana Dal 1kg", "Groceries", "1kg", 110.0, 18.0),
    ("Sona Masoori Rice 5kg", "Groceries", "5kg", 340.0, 18.0),
    ("Organic Honey 500g", "Groceries", "500g", 280.0, 35.0),
    ("Pure Cow Ghee 500ml", "Groceries", "500ml", 360.0, 20.0),

    # Fruits & Vegetables
    ("Robusta Bananas 1kg", "Fruits & Vegetables", "1kg", 50.0, 25.0),
    ("Royal Gala Apples 500g", "Fruits & Vegetables", "500g", 140.0, 30.0),
    ("Hybrid Tomatoes 1kg", "Fruits & Vegetables", "1kg", 35.0, 20.0),
    ("Fresh Onions 1kg", "Fruits & Vegetables", "1kg", 40.0, 20.0),
    ("New Crop Potatoes 1kg", "Fruits & Vegetables", "1kg", 35.0, 20.0),
    ("Fresh Spinach Palak 250g", "Fruits & Vegetables", "250g", 25.0, 25.0),
    ("Orange Carrots 500g", "Fruits & Vegetables", "500g", 40.0, 25.0),
    ("Fresh Green Lemons 250g", "Fruits & Vegetables", "250g", 30.0, 30.0),
    ("Button Mushrooms 200g", "Fruits & Vegetables", "200g", 60.0, 30.0),
    ("Green Cucumber 500g", "Fruits & Vegetables", "500g", 30.0, 25.0),
    ("Pomegranate Seedless 500g", "Fruits & Vegetables", "500g", 160.0, 28.0),
    ("Green Capsicum 250g", "Fruits & Vegetables", "250g", 35.0, 25.0),
    ("Fresh Coriander Bunch 100g", "Fruits & Vegetables", "100g", 15.0, 30.0),
    ("Ginger Local 250g", "Fruits & Vegetables", "250g", 45.0, 30.0),
    ("Garlic Indigenous 250g", "Fruits & Vegetables", "250g", 75.0, 30.0),

    # Personal Care
    ("Moisturizing Bath Soap 125g", "Personal Care", "125g", 45.0, 25.0),
    ("Anti-Dandruff Shampoo 180ml", "Personal Care", "180ml", 190.0, 30.0),
    ("Complete Care Toothpaste 150g", "Personal Care", "150g", 115.0, 28.0),
    ("Antibacterial Hand Wash 250ml", "Personal Care", "250ml", 95.0, 32.0),
    ("Laundry Detergent Powder 1kg", "Personal Care", "1kg", 160.0, 22.0),
    ("Dishwash Gel Lemon 250ml", "Personal Care", "250ml", 65.0, 25.0),
    ("Facial Tissue Box 100s", "Personal Care", "100s", 85.0, 35.0),
    ("Disinfectant Surface Cleaner 500ml", "Personal Care", "500ml", 110.0, 30.0),
    ("Power Toilet Cleaner 500ml", "Personal Care", "500ml", 95.0, 28.0),
    ("Garbage Trash Bags Medium 30s", "Personal Care", "30s", 120.0, 38.0),
    ("Soft Toothbrush 2 Pack", "Personal Care", "2 Pack", 70.0, 35.0),
    ("Body Wash Shower Gel 250ml", "Personal Care", "250ml", 210.0, 35.0),
    ("Hand Sanitizer Gel 100ml", "Personal Care", "100ml", 50.0, 40.0),
    ("Mosquito Repellent Liquid 45ml", "Personal Care", "45ml", 85.0, 30.0),

    # Sweets
    ("Milk Chocolate Bar 100g", "Sweets", "100g", 85.0, 30.0),
    ("Dark Chocolate 70% 80g", "Sweets", "80g", 150.0, 35.0),
    ("Gulab Jamun Tin 500g", "Sweets", "500g", 165.0, 28.0),
    ("Flavored Soan Papdi 250g", "Sweets", "250g", 90.0, 30.0),
    ("Gummy Bear Candies 100g", "Sweets", "100g", 65.0, 35.0),
    ("Chocolate Wafer Sticks 150g", "Sweets", "150g", 110.0, 32.0),
    ("Peppermint Candy Pack 50g", "Sweets", "50g", 25.0, 40.0),
    ("Kaju Katli Sweets 200g", "Sweets", "200g", 280.0, 25.0),
    ("Rasgulla Tin 500g", "Sweets", "500g", 160.0, 28.0),
    ("Butterscotch Cookies 150g", "Sweets", "150g", 75.0, 30.0),
]

def build_products_list():
    products = list(SPECIAL_SKUS)
    existing_ids = {p["sku_id"] for p in products}
    
    cat_counts = {}
    for idx, (name, cat, size, price, margin) in enumerate(PRODUCT_TEMPLATES, start=1):
        cat_code = "".join([w[:3].upper() for w in cat.split()])
        sku_id = f"SKU_{cat_code}_{idx:03d}"
        cost = round(price * (1.0 - margin / 100.0), 2)
        products.append({
            "sku_id": sku_id,
            "sku_name": name,
            "category": cat,
            "size": size,
            "unit_selling_price_inr": price,
            "margin_pct": margin,
            "unit_cost_price_inr": cost
        })
    
    # Fill up to 150 items if needed
    current_count = len(products)
    while len(products) < 150:
        i = len(products) + 1
        cat = CATEGORIES[i % len(CATEGORIES)]
        cat_code = "".join([w[:3].upper() for w in cat.split()])
        sku_id = f"SKU_GENERIC_{cat_code}_{i:03d}"
        price = round(random.uniform(30.0, 350.0), 2)
        margin = round(random.uniform(20.0, 38.0), 2)
        cost = round(price * (1.0 - margin / 100.0), 2)
        products.append({
            "sku_id": sku_id,
            "sku_name": f"Premium {cat} Item {i}",
            "category": cat,
            "size": "200g",
            "unit_selling_price_inr": price,
            "margin_pct": margin,
            "unit_cost_price_inr": cost
        })
    
    return products[:150]

PRODUCTS = build_products_list()

def write_products_csv():
    filepath = os.path.join(DATA_DIR, "products.csv")
    fieldnames = ["sku_id", "sku_name", "category", "size", "unit_selling_price_inr", "margin_pct", "unit_cost_price_inr"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(PRODUCTS)
    print(f"Generated products.csv with {len(PRODUCTS)} rows.")

# ----------------------------------------------------
# 3. Generate Store Inventory (store_inventory.csv)
# ----------------------------------------------------
def write_store_inventory_csv():
    filepath = os.path.join(DATA_DIR, "store_inventory.csv")
    fieldnames = [
        "store_id", "sku_id", "shelf_slot", "shelf_stock_units", 
        "shelf_capacity_units", "backroom_stock_units", "total_stock_units",
        "safety_stock_threshold_units", "reorder_point_units"
    ]
    rows = []
    
    for s in STORES:
        store_id = s["store_id"]
        for idx, p in enumerate(PRODUCTS):
            sku_id = p["sku_id"]
            cat = p["category"]
            cat_code = "".join([w[0].upper() for w in cat.split()])
            shelf_slot = f"SLOT_{cat_code}_{(idx % 30) + 1:02d}"
            
            # Defaults
            shelf_cap = 50
            shelf_stock = random.randint(25, 45)
            backroom_stock = random.randint(40, 100)
            safety = 20
            reorder = 40
            
            # Mandatory Scenario A:
            # Store 7 has 14 bottles total of SKU_COLD_DRINK_750ML
            if store_id == "STORE_007" and sku_id == "SKU_COLD_DRINK_750ML":
                shelf_cap = 40
                shelf_stock = 10
                backroom_stock = 4
                safety = 25
                reorder = 50

            # Store 9 has 60 bottles of SKU_COLD_DRINK_750ML
            elif store_id == "STORE_009" and sku_id == "SKU_COLD_DRINK_750ML":
                shelf_cap = 50
                shelf_stock = 40
                backroom_stock = 20
                safety = 20
                reorder = 35

            # Mandatory Scenario B:
            # Fast-selling SKU_ENERGY_DRINK_250ML approaching stockout at Store 7 (shelf cap 12, stock 3, backroom 80)
            elif store_id == "STORE_007" and sku_id == "SKU_ENERGY_DRINK_250ML":
                shelf_cap = 12
                shelf_stock = 3
                backroom_stock = 80
                safety = 20
                reorder = 40

            # Slow-selling SKU_KALE_CHIPS_50G on adjacent shelf at Store 7 (shelf cap 50, stock 45, backroom 100)
            elif store_id == "STORE_007" and sku_id == "SKU_KALE_CHIPS_50G":
                shelf_cap = 50
                shelf_stock = 45
                backroom_stock = 100
                safety = 10
                reorder = 15

            # Mandatory Scenario C:
            # Donor Store 12 looks like donor with 80 units of SKU_COLD_DRINK_750ML but high demand prevents transfer
            elif store_id == "STORE_012" and sku_id == "SKU_COLD_DRINK_750ML":
                shelf_cap = 50
                shelf_stock = 50
                backroom_stock = 30
                safety = 25
                reorder = 40

            # Mandatory Scenario D:
            # Store 4 has ample stock of SKU_COLD_DRINK_750ML (120 units)
            elif store_id == "STORE_004" and sku_id == "SKU_COLD_DRINK_750ML":
                shelf_cap = 50
                shelf_stock = 40
                backroom_stock = 80
                safety = 25
                reorder = 50

            # Mandatory Scenario F: Healthy Store 1 has high stock across all SKUs
            elif store_id == "STORE_001":
                shelf_cap = 50
                shelf_stock = random.randint(40, 50)
                backroom_stock = random.randint(100, 160)
                safety = 20
                reorder = 35

            # Ensure invariant: shelf_stock <= shelf_capacity
            shelf_stock = min(shelf_stock, shelf_cap)
            total_stock = shelf_stock + backroom_stock
            
            rows.append({
                "store_id": store_id,
                "sku_id": sku_id,
                "shelf_slot": shelf_slot,
                "shelf_stock_units": shelf_stock,
                "shelf_capacity_units": shelf_cap,
                "backroom_stock_units": backroom_stock,
                "total_stock_units": total_stock,
                "safety_stock_threshold_units": safety,
                "reorder_point_units": reorder
            })
            
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated store_inventory.csv with {len(rows)} rows.")

# ----------------------------------------------------
# 4. Generate Orders (orders.csv) - 14 Days Historical
# ----------------------------------------------------
def write_orders_csv():
    filepath = os.path.join(DATA_DIR, "orders.csv")
    fieldnames = ["timestamp", "store_id", "sku_id", "quantity"]
    rows = []
    
    # 14 days preceding REF_TIME (336 hours)
    start_time = REF_TIME - timedelta(days=14)
    
    # Active core SKUs to generate hourly order series (to keep dataset rich and clean)
    core_skus = [p["sku_id"] for p in PRODUCTS[:20]]
    
    for h in range(336):
        t = start_time + timedelta(hours=h)
        timestamp_str = t.isoformat()
        hour = t.hour
        
        # Diurnal demand multiplier
        if 8 <= hour <= 10:
            diurnal = 1.4
        elif 12 <= hour <= 14:
            diurnal = 1.3
        elif 18 <= hour <= 22:
            diurnal = 1.8
        elif 0 <= hour <= 5:
            diurnal = 0.15
        else:
            diurnal = 0.8
            
        for s in STORES:
            store_id = s["store_id"]
            
            for sku_id in core_skus:
                # Base rates
                if sku_id == "SKU_COLD_DRINK_750ML":
                    if store_id in ["STORE_007", "STORE_009"]:
                        base = 2.0
                    elif store_id == "STORE_012":
                        base = 9.0  # High baseline for Store 12 (Scenario C)
                    else:
                        base = 1.5
                elif sku_id == "SKU_ENERGY_DRINK_250ML" and store_id == "STORE_007":
                    base = 6.0  # Fast selling (Scenario B)
                elif sku_id == "SKU_KALE_CHIPS_50G" and store_id == "STORE_007":
                    base = 0.1  # Slow selling (Scenario B)
                else:
                    base = 1.0
                
                # Calculate deterministic hourly order quantity
                expected = base * diurnal
                # Add slight pseudo-random variation based on timestamp and store/sku hash
                val_hash = (hash(timestamp_str) + hash(store_id) + hash(sku_id)) % 100
                noise = (val_hash / 100.0) * 0.4 + 0.8
                qty = int(round(expected * noise))
                
                if qty > 0:
                    rows.append({
                        "timestamp": timestamp_str,
                        "store_id": store_id,
                        "sku_id": sku_id,
                        "quantity": qty
                    })
                    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated orders.csv with {len(rows)} rows.")

# ----------------------------------------------------
# 5. Generate Warehouse Stock (warehouse_stock.csv)
# ----------------------------------------------------
def write_warehouse_stock_csv():
    filepath = os.path.join(DATA_DIR, "warehouse_stock.csv")
    fieldnames = [
        "warehouse_id", "sku_id", "available_stock_units", 
        "reserved_stock_units", "free_stock_units"
    ]
    rows = []
    
    for p in PRODUCTS:
        sku_id = p["sku_id"]
        
        if sku_id == "SKU_COLD_DRINK_750ML":
            available = 2400
            reserved = 300
        elif sku_id == "SKU_ENERGY_DRINK_250ML":
            available = 1500
            reserved = 200
        else:
            available = random.randint(500, 4000)
            reserved = random.randint(50, 400)
            
        free_stock = max(0, available - reserved)
        rows.append({
            "warehouse_id": "WH_CENTRAL_01",
            "sku_id": sku_id,
            "available_stock_units": available,
            "reserved_stock_units": reserved,
            "free_stock_units": free_stock
        })
        
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated warehouse_stock.csv with {len(rows)} rows.")

# ----------------------------------------------------
# 6. Generate Truck Schedule (truck_schedule.csv)
# ----------------------------------------------------
def write_truck_schedule_csv():
    filepath = os.path.join(DATA_DIR, "truck_schedule.csv")
    fieldnames = [
        "truck_id", "store_id", "route_id", "driver_name", 
        "scheduled_departure_time", "scheduled_arrival_time", 
        "truck_capacity_units", "status", "sku_id", "allocated_quantity_units"
    ]
    rows = []
    
    # Mandatory Scenario A truck: arrives at Store 7 at 9:00 PM (21:00 IST) on Oct 9, 2026
    scenario_a_truck_dep = REF_TIME.replace(hour=18, minute=0)
    scenario_a_truck_arr = REF_TIME.replace(hour=21, minute=0)
    rows.append({
        "truck_id": "TRK_STANDARD_407",
        "store_id": "STORE_007",
        "route_id": "ROUTE_KORAMANGALA_01",
        "driver_name": "Rajesh Kumar",
        "scheduled_departure_time": scenario_a_truck_dep.isoformat(),
        "scheduled_arrival_time": scenario_a_truck_arr.isoformat(),
        "truck_capacity_units": 500,
        "status": "IN_TRANSIT",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "allocated_quantity_units": 100
    })
    
    # Express truck available for Store 7 option
    scenario_a_exp_dep = REF_TIME.replace(hour=17, minute=10)
    scenario_a_exp_arr = REF_TIME.replace(hour=17, minute=35)
    rows.append({
        "truck_id": "TRK_EXPRESS_109",
        "store_id": "STORE_007",
        "route_id": "ROUTE_EXPRESS_WEST",
        "driver_name": "Suresh Patel",
        "scheduled_departure_time": scenario_a_exp_dep.isoformat(),
        "scheduled_arrival_time": scenario_a_exp_arr.isoformat(),
        "truck_capacity_units": 200,
        "status": "SCHEDULED",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "allocated_quantity_units": 100
    })
    
    # Scheduled replenishment for remaining 29 stores across simulation window
    for idx, s in enumerate(STORES):
        store_id = s["store_id"]
        if store_id == "STORE_007":
            continue
            
        truck_num = 100 + idx
        dep = REF_TIME + timedelta(hours=(idx % 6) + 1)
        arr = dep + timedelta(hours=2)
        
        rows.append({
            "truck_id": f"TRK_STANDARD_{truck_num}",
            "store_id": store_id,
            "route_id": f"ROUTE_ZONE_{(idx % 5) + 1:02d}",
            "driver_name": f"Driver {idx + 1}",
            "scheduled_departure_time": dep.isoformat(),
            "scheduled_arrival_time": arr.isoformat(),
            "truck_capacity_units": 500,
            "status": "SCHEDULED",
            "sku_id": "SKU_COLD_DRINK_750ML",
            "allocated_quantity_units": 80
        })
        
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated truck_schedule.csv with {len(rows)} rows.")

# ----------------------------------------------------
# 7. Generate Riders Availability (riders.csv)
# ----------------------------------------------------
def write_riders_csv():
    filepath = os.path.join(DATA_DIR, "riders.csv")
    fieldnames = [
        "timestamp", "store_id", "available_riders", 
        "required_riders", "orders_per_rider_hour", 
        "rider_shortage_count", "shortage_severity"
    ]
    rows = []
    
    # 48 hourly records around reference date
    start_time = REF_TIME.replace(hour=0, minute=0) - timedelta(days=1)
    
    for h in range(48):
        t = start_time + timedelta(hours=h)
        timestamp_str = t.isoformat()
        
        for s in STORES:
            store_id = s["store_id"]
            
            # Default normal rider numbers
            avail = 8
            req = 5
            opr = 3.5
            
            # Mandatory Scenario A: Store 7 during match evening (19:00 - 22:00 on Oct 9)
            if store_id == "STORE_007" and t.date() == REF_TIME.date() and 19 <= t.hour <= 22:
                avail = 3
                req = 9
                opr = 3.0
            
            # Mandatory Scenario D: Store 4 severe rider shortage (17:00 - 22:00 on Oct 9)
            elif store_id == "STORE_004" and t.date() == REF_TIME.date() and 17 <= t.hour <= 22:
                avail = 1
                req = 9
                opr = 3.0

            # Mandatory Scenario F: Healthy Store 1 ample riders
            elif store_id == "STORE_001":
                avail = 10
                req = 4
                opr = 4.0
                
            shortage = max(0, req - avail)
            if shortage == 0:
                severity = "NONE"
            elif shortage <= 2:
                severity = "LOW"
            elif shortage <= 4:
                severity = "MEDIUM"
            elif shortage <= 6:
                severity = "HIGH"
            else:
                severity = "CRITICAL"
                
            rows.append({
                "timestamp": timestamp_str,
                "store_id": store_id,
                "available_riders": avail,
                "required_riders": req,
                "orders_per_rider_hour": opr,
                "rider_shortage_count": shortage,
                "shortage_severity": severity
            })
            
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated riders.csv with {len(rows)} rows.")

# ----------------------------------------------------
# 8. Generate External Events (events.csv)
# ----------------------------------------------------
def write_events_csv():
    filepath = os.path.join(DATA_DIR, "events.csv")
    fieldnames = [
        "event_id", "event_type", "title", "store_id", 
        "affected_category", "multiplier", "precipitation_mm_hr", 
        "is_active", "start_time", "end_time"
    ]
    
    match_start = REF_TIME.replace(hour=19, minute=30)
    match_end = REF_TIME.replace(hour=23, minute=30)
    
    rain_start = REF_TIME.replace(hour=16, minute=0)
    rain_end = REF_TIME.replace(hour=22, minute=0)
    
    fest_start = REF_TIME.replace(hour=12, minute=0)
    fest_end = REF_TIME.replace(hour=23, minute=59)

    events = [
        # Scenario A: India vs Pakistan match at Store 7 (Chinnaswamy Stadium proximity 1.4km)
        {
            "event_id": "EVT_CRICKET_20261009_007_BEV",
            "event_type": "CRICKET",
            "title": "India vs Pakistan T20 World Cup Super 8",
            "store_id": "STORE_007",
            "affected_category": "Cold Beverages",
            "multiplier": 3.0,
            "precipitation_mm_hr": 0.0,
            "is_active": 1,
            "start_time": match_start.isoformat(),
            "end_time": match_end.isoformat()
        },
        {
            "event_id": "EVT_CRICKET_20261009_007_SNK",
            "event_type": "CRICKET",
            "title": "India vs Pakistan T20 World Cup Super 8",
            "store_id": "STORE_007",
            "affected_category": "Snacks & Chips",
            "multiplier": 2.2,
            "precipitation_mm_hr": 0.0,
            "is_active": 1,
            "start_time": match_start.isoformat(),
            "end_time": match_end.isoformat()
        },
        {
            "event_id": "EVT_CRICKET_20261009_002_BEV",
            "event_type": "CRICKET",
            "title": "India vs Pakistan T20 World Cup Super 8",
            "store_id": "STORE_002",
            "affected_category": "Cold Beverages",
            "multiplier": 2.8,
            "precipitation_mm_hr": 0.0,
            "is_active": 1,
            "start_time": match_start.isoformat(),
            "end_time": match_end.isoformat()
        },

        # Scenario C: Festival at Store 12 causing high demand surge
        {
            "event_id": "EVT_FESTIVAL_20261009_012",
            "event_type": "FESTIVAL",
            "title": "Diwali Pre-Shopping Mega Mela",
            "store_id": "STORE_012",
            "affected_category": "Cold Beverages",
            "multiplier": 2.5,
            "precipitation_mm_hr": 0.0,
            "is_active": 1,
            "start_time": fest_start.isoformat(),
            "end_time": fest_end.isoformat()
        },

        # Scenario E: City-Wide Heavy Monsoon Rain affecting ALL stores
        {
            "event_id": "EVT_RAIN_20261009_CITY_BEV",
            "event_type": "RAIN",
            "title": "Heavy Monsoon Downpour",
            "store_id": "ALL",
            "affected_category": "Cold Beverages",
            "multiplier": 1.35,
            "precipitation_mm_hr": 22.5,
            "is_active": 1,
            "start_time": rain_start.isoformat(),
            "end_time": rain_end.isoformat()
        },
        {
            "event_id": "EVT_RAIN_20261009_CITY_HOT",
            "event_type": "RAIN",
            "title": "Heavy Monsoon Downpour",
            "store_id": "ALL",
            "affected_category": "Hot Beverages",
            "multiplier": 1.8,
            "precipitation_mm_hr": 22.5,
            "is_active": 1,
            "start_time": rain_start.isoformat(),
            "end_time": rain_end.isoformat()
        },

        # Additional regional events
        {
            "event_id": "EVT_FESTIVAL_20261009_GENERIC",
            "event_type": "FESTIVAL",
            "title": "Diwali Festival Peak Week",
            "store_id": "ALL",
            "affected_category": "Sweets",
            "multiplier": 2.0,
            "precipitation_mm_hr": 0.0,
            "is_active": 1,
            "start_time": fest_start.isoformat(),
            "end_time": fest_end.isoformat()
        }
    ]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)
    print(f"Generated events.csv with {len(events)} rows.")

# ----------------------------------------------------
# Main Generator Orchestrator
# ----------------------------------------------------
def main():
    print(f"Starting dataset generation with seed={RANDOM_SEED}...")
    write_products_csv()
    write_store_inventory_csv()
    write_orders_csv()
    write_warehouse_stock_csv()
    write_truck_schedule_csv()
    write_riders_csv()
    write_events_csv()
    print("All 7 CSV datasets generated successfully in data/.")

if __name__ == "__main__":
    main()
