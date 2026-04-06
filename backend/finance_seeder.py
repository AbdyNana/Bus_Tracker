import random
from app.db.supabase_client import get_supabase

def seed_finance():
    print("Starting finance_seeder...")
    db = get_supabase()
    res = db.table('inventory').select('id,price').execute()
    items = res.data or []
    
    updated = 0
    for item in items:
        price = float(item['price'] or 0)
        # Cost price is 30-40% lower than price, meaning cost = price * (0.6 to 0.7)
        cost_price = price * random.uniform(0.6, 0.7)
        sold_qty = random.randint(5, 150)
        
        db.table('inventory').update({
            'cost_price': cost_price,
            'sold_quantity': sold_qty
        }).eq('id', item['id']).execute()
        updated += 1
        
    print(f"Successfully seeded finance data for {updated} items.")

if __name__ == "__main__":
    seed_finance()
