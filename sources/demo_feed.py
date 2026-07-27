

import random
import datetime

GIFTS = [
    ("Plush Pepe", ["Diamond", "Neon", "Ghost"]),
    ("Mousse Cake", ["Fiesta Muerta", "Velvet", "Mint"]),
    ("Xmas Stocking", ["Pink Ink", "Frost", "Gold Leaf"]),
    ("Pool Float", ["Balloon Dog", "Flamingo", "Shark"]),
    ("Instant Ramen", ["Khinkali", "Tonkotsu", "Spicy Miso"]),
    ("Chill Flame", ["Bear Market", "Ember", "Azure"]),
    ("Whip Cupcake", ["Zero Sugar", "Berry", "Caramel"]),
]
SELLERS = ["liscorrise", "peelele", "waFelka67", "ArbuznyBober", "iinviii", "Murruett"]


def make_listing() -> dict:
    gift, models = random.choice(GIFTS)
    stars = random.choice([350, 380, 450, 550, 1500, 3000])
    ton = round(stars / 114.6, 2)
    seller = random.choice(SELLERS)
    num = random.randint(1000, 999999)
    slug = f"{gift.replace(' ', '')}-{num}"
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    return {
        "gift": gift,
        "model": random.choice(models),
        "price_stars": stars,
        "price_ton": ton,
        "seller_user": seller,
        "seller_id": random.randint(10**9, 9 * 10**9),
        "level": random.choice([-1, 1, 1, 2]),
        "dm": "бесплатно",
        "premium": random.random() > 0.4,
        "slug": slug,
        "ts": now.strftime("%d.%m.%Y %H:%M:%S"),
    }
